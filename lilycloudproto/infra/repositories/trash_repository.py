import mimetypes
import os
from datetime import datetime
from typing import Any

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.domain.entities.trash import TrashEntry
from lilycloudproto.domain.values.trash import TrashSortBy, TrashSortOrder
from lilycloudproto.infra.services.storage_service import StorageService
from lilycloudproto.models.trash import TrashItem, TrashListQuery


class TrashRepository:
    db: AsyncSession
    storage_service: StorageService

    def __init__(self, db: AsyncSession, storage_service: StorageService):
        self.db = db
        self.storage_service = storage_service

    def _get_physical_path(self, entry: TrashEntry) -> str:
        """Construct the physical path for a trash entry."""
        # Use StorageService to determine the trash root for this file's original path
        trash_root = self.storage_service.get_trash_root(entry.original_path)
        # Strict adherence to requirement: No ID in filename.
        # The entry_name in DB must match the physical filename (which might
        # be renamed to avoid conflict).
        return os.path.join(trash_root, entry.entry_name)

    def _enrich_entry(self, entry: TrashEntry) -> TrashItem:
        """Convert DB entry to TrashItem with filesystem metadata."""
        physical_path = self._get_physical_path(entry)

        # Defaults if file missing
        size = 0
        type_ = "file"
        mime_type = "application/octet-stream"
        created_at = None
        modified_at = None
        accessed_at = None

        if os.path.exists(physical_path):
            stat = os.stat(physical_path)
            size = stat.st_size
            type_ = "directory" if os.path.isdir(physical_path) else "file"
            created_at = datetime.fromtimestamp(stat.st_ctime)
            modified_at = datetime.fromtimestamp(stat.st_mtime)
            accessed_at = datetime.fromtimestamp(stat.st_atime)

            if type_ == "file":
                mime, _ = mimetypes.guess_type(entry.entry_name)
                mime_type = mime or "application/octet-stream"
            else:
                mime_type = "inode/directory"

        return TrashItem(
            trash_id=entry.trash_id,
            user_id=entry.user_id,
            entry_name=entry.entry_name,
            original_path=entry.original_path,
            deleted_at=entry.deleted_at,
            type=type_,
            size=size,
            mime_type=mime_type,
            created_at=created_at,
            modified_at=modified_at,
            accessed_at=accessed_at,
        )

    async def create(self, entry: TrashEntry) -> TrashEntry:
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def get_by_id(self, trash_id: int) -> TrashEntry | None:
        result = await self.db.execute(
            select(TrashEntry).where(TrashEntry.trash_id == trash_id)
        )
        return result.scalar_one_or_none()

    async def get_item_by_id(self, trash_id: int) -> TrashItem | None:
        """Get fully enriched trash item by ID."""
        entry = await self.get_by_id(trash_id)
        if not entry:
            return None
        return self._enrich_entry(entry)

    async def get_by_original_path(self, path: str) -> TrashEntry | None:
        result = await self.db.execute(
            select(TrashEntry).where(TrashEntry.original_path == path)
        )
        return result.scalar_one_or_none()

    async def get_latest_by_original_path(self, path: str) -> TrashEntry | None:
        """Get the most recently deleted entry for a given original path."""
        result = await self.db.execute(
            select(TrashEntry)
            .where(TrashEntry.original_path == path)
            .order_by(desc(TrashEntry.deleted_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_entry_name(self, entry_name: str) -> TrashEntry | None:
        """
        Get a trash entry by its unique entry name in the trash folder.
        This is the 'Linux-style' lookup: entry_name is the unique handle.
        """
        result = await self.db.execute(
            select(TrashEntry).where(TrashEntry.entry_name == entry_name)
        )
        return result.scalar_one_or_none()

    async def search(self, query: TrashListQuery) -> tuple[list[TrashItem], int]:
        # 1. DB Filtering
        statement = select(TrashEntry)
        if query.keyword:
            statement = statement.where(TrashEntry.entry_name.contains(query.keyword))

        if query.path:
            if query.recursive:
                statement = statement.where(
                    TrashEntry.original_path.startswith(query.path)
                )
            else:
                prefix = query.path if query.path.endswith("/") else f"{query.path}/"
                statement = statement.where(TrashEntry.original_path.startswith(prefix))

        # Fetch all candidates from DB
        result = await self.db.execute(statement)
        entries = result.scalars().all()

        # 2. Enrich with FS data
        items: list[TrashItem] = [self._enrich_entry(entry) for entry in entries]

        # 3. Memory Filtering
        filtered_items = []
        for item in items:
            if query.type and item.type != query.type:
                continue
            if query.mime_type and (
                not item.mime_type or query.mime_type not in item.mime_type
            ):
                continue
            filtered_items.append(item)

        items = filtered_items

        # 4. Sorting
        def get_sort_key(item: TrashItem) -> Any:
            key_map = {
                TrashSortBy.NAME: item.entry_name,
                TrashSortBy.PATH: item.original_path,
                TrashSortBy.SIZE: item.size,
                TrashSortBy.TYPE: item.type,
                TrashSortBy.DELETED: item.deleted_at,
                TrashSortBy.CREATED: item.created_at or datetime.min,
                TrashSortBy.MODIFIED: item.modified_at or datetime.min,
                TrashSortBy.ACCESSED: item.accessed_at or datetime.min,
            }
            return key_map.get(query.sort_by, item.entry_name)

        reverse = query.sort_order == TrashSortOrder.DESC

        items.sort(key=get_sort_key, reverse=reverse)

        if query.dir_first:
            items.sort(key=lambda x: 0 if x.type == "directory" else 1)

        # 5. Pagination
        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        paged_items = items[start:end]

        return paged_items, total

    async def count(self, query: TrashListQuery) -> int:
        # This count is inaccurate if we have memory filters (type/mime_type)
        # So we should rely on search returning total.
        # But for DB-only filters:
        statement = select(func.count()).select_from(TrashEntry)
        if query.keyword:
            statement = statement.where(TrashEntry.entry_name.contains(query.keyword))
        if query.path and query.recursive:
            statement = statement.where(TrashEntry.original_path.startswith(query.path))

        # If we have type/mime filters, we can't count in DB efficiently
        # without FS access.
        # If strict count is needed, we have to do the full scan like search.
        # For now, let's assume search handles it.
        result = await self.db.execute(statement)
        return result.scalar_one()

    async def delete(self, entry: TrashEntry) -> None:
        await self.db.delete(entry)
        await self.db.commit()

    async def delete_all(self) -> None:
        await self.db.execute(delete(TrashEntry))
        await self.db.commit()
