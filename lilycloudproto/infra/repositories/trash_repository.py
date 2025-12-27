import mimetypes
import os
from datetime import datetime
from typing import Any

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.domain.entities.trash import Trash
from lilycloudproto.domain.values.trash import TrashSortBy, TrashSortOrder
from lilycloudproto.infra.services.storage_service import StorageService
from lilycloudproto.models.trash import TrashEntry, TrashFile, TrashListQuery


class TrashRepository:
    """Repository for trash entries with filesystem metadata enrichment."""

    def __init__(self, db: AsyncSession, storage_service: StorageService):
        self.db = db
        self.storage_service = storage_service

    async def create(self, entry: Trash) -> Trash:
        """Create a new trash entry."""
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def get_by_id(self, trash_id: int) -> Trash | None:
        """Get trash entry by ID."""
        result = await self.db.execute(select(Trash).where(Trash.trash_id == trash_id))
        return result.scalar_one_or_none()

    async def get_by_original_path(self, path: str) -> Trash | None:
        """Get trash entry by original path."""
        result = await self.db.execute(select(Trash).where(Trash.original_path == path))
        return result.scalar_one_or_none()

    async def get_latest_by_original_path(self, path: str) -> Trash | None:
        """Get the latest trash entry by original path (most recently deleted)."""
        result = await self.db.execute(
            select(Trash)
            .where(Trash.original_path == path)
            .order_by(desc(Trash.deleted_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_entry_name(self, entry_name: str) -> Trash | None:
        """Get trash entry by entry name (physical filename in trash)."""
        result = await self.db.execute(
            select(Trash).where(Trash.entry_name == entry_name)
        )
        return result.scalar_one_or_none()

    async def get_by_original_path_prefix(
        self, path_prefix: str, user_id: int | None = None
    ) -> list[Trash]:
        """Get trash entries whose original_path starts with the given prefix."""
        statement = select(Trash).where(Trash.original_path.startswith(path_prefix))
        if user_id is not None:
            statement = statement.where(Trash.user_id == user_id)
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def delete(self, entry: Trash) -> None:
        """Delete a trash entry from database."""
        await self.db.delete(entry)
        await self.db.commit()

    async def delete_all(self, user_id: int | None = None) -> None:
        """Delete all trash entries, optionally filtered by user_id."""
        statement = delete(Trash)
        if user_id is not None:
            statement = statement.where(Trash.user_id == user_id)
        await self.db.execute(statement)
        await self.db.commit()

    def _get_physical_path(self, entry: Trash) -> str:
        """Construct the physical path for a trash entry."""
        trash_root = self.storage_service.get_trash_root(entry.original_path)
        return os.path.join(trash_root, entry.entry_name)

    def _get_fs_metadata(self, entry: Trash) -> dict[str, Any]:
        """Get filesystem metadata for a trash entry."""
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

        return {
            "size": size,
            "type": type_,
            "mime_type": mime_type,
            "created_at": created_at,
            "modified_at": modified_at,
            "accessed_at": accessed_at,
        }

    def _enrich_to_item(self, entry: Trash) -> TrashEntry:
        """Convert DB entry to TrashEntry (Detail view with full metadata)."""
        meta = self._get_fs_metadata(entry)
        return TrashEntry(
            trash_id=entry.trash_id,
            user_id=entry.user_id,
            entry_name=entry.entry_name,
            original_path=entry.original_path,
            deleted_at=entry.deleted_at,
            type=meta["type"],
            size=meta["size"],
            mime_type=meta["mime_type"],
            created_at=meta["created_at"],
            modified_at=meta["modified_at"],
            accessed_at=meta["accessed_at"],
        )

    def _enrich_to_file(self, entry: Trash) -> TrashFile:
        """Convert DB entry to TrashFile (List view with original path info)."""
        meta = self._get_fs_metadata(entry)
        name = os.path.basename(entry.original_path)
        return TrashFile(
            name=name,
            path=entry.original_path,
            type=meta["type"],
            size=meta["size"],
            mime_type=meta["mime_type"],
            deleted_at=entry.deleted_at,
            created_at=meta["created_at"],
            modified_at=meta["modified_at"],
            accessed_at=meta["accessed_at"],
        )

    async def get_item_by_id(self, trash_id: int) -> TrashEntry | None:
        """Get fully enriched trash item by ID."""
        entry = await self.get_by_id(trash_id)
        if not entry:
            return None
        return self._enrich_to_item(entry)

    def _normalize_path(self, path: str) -> str:
        """Normalize a path for comparison."""
        # Remove leading/trailing slashes and normalize
        normalized = os.path.normpath(path.strip("/"))
        # If empty after normalization, it's root
        return "/" if not normalized or normalized == "." else f"/{normalized}"

    def _get_path_depth(self, path: str) -> int:
        """Get the depth of a path (number of path components)."""
        normalized = self._normalize_path(path)
        if normalized == "/":
            return 0
        # Count non-empty parts
        parts = [p for p in normalized.split("/") if p]
        return len(parts)

    def _is_direct_child(self, child_path: str, parent_path: str) -> bool:
        """Check if child_path is a direct child of parent_path."""
        child_norm = self._normalize_path(child_path)
        parent_norm = self._normalize_path(parent_path)

        # If parent is root, check if child is at depth 1
        if parent_norm == "/":
            return self._get_path_depth(child_path) == 1

        # Check if child starts with parent and is exactly one level deeper
        if not child_norm.startswith(parent_norm):
            return False

        # Remove parent prefix
        relative = child_norm[len(parent_norm) :].lstrip("/")
        if not relative:
            return False

        # Check if it's a direct child (no additional slashes)
        return "/" not in relative

    def _is_descendant(self, descendant_path: str, ancestor_path: str) -> bool:
        """Check if descendant_path is under ancestor_path (any depth)."""
        descendant_norm = self._normalize_path(descendant_path)
        ancestor_norm = self._normalize_path(ancestor_path)

        # If ancestor is root, everything is a descendant
        if ancestor_norm == "/":
            return descendant_norm != "/"

        # Check if descendant starts with ancestor
        if not descendant_norm.startswith(ancestor_norm):
            return False

        # Must have additional path components
        relative = descendant_norm[len(ancestor_norm) :].lstrip("/")
        return bool(relative)

    def _matches_path_filter(
        self, item_path: str, query_path: str | None, recursive: bool
    ) -> bool:
        """Check if item path matches the query path filter."""
        # Normalize item path
        item_norm = self._normalize_path(item_path)

        # Case 1: No path filter specified
        if not query_path:
            if recursive:
                # Show all items
                return True
            else:
                # Show only root-level items (depth 1)
                return self._get_path_depth(item_path) == 1

        # Case 2: Path filter specified
        query_norm = self._normalize_path(query_path)

        # Don't return the query path itself, only its children
        if item_norm == query_norm:
            return False

        if recursive:
            # Show all items under query path (descendants only)
            return self._is_descendant(item_path, query_path)
        else:
            # Show only direct children of query path
            return self._is_direct_child(item_path, query_path)

    def _matches_type_filter(self, item: TrashFile, query: TrashListQuery) -> bool:
        """Check if item matches type and MIME type filters."""
        # Type filter
        if query.type and item.type != query.type:
            return False

        # MIME type filter
        if query.mime_type:
            if not item.mime_type:
                return False
            if query.mime_type not in item.mime_type:
                return False

        return True

    def _get_sort_key(self, item: TrashFile, sort_by: TrashSortBy) -> Any:
        """Get sort key value for an item."""
        key_map = {
            TrashSortBy.NAME: item.name,
            TrashSortBy.PATH: item.path,
            TrashSortBy.SIZE: item.size,
            TrashSortBy.TYPE: item.type,
            TrashSortBy.DELETED: item.deleted_at,
            TrashSortBy.CREATED: item.created_at or datetime.min,
            TrashSortBy.MODIFIED: item.modified_at or datetime.min,
            TrashSortBy.ACCESSED: item.accessed_at or datetime.min,
        }
        return key_map.get(sort_by, item.name)

    def _apply_sorting(
        self, items: list[TrashFile], query: TrashListQuery
    ) -> list[TrashFile]:
        """Sort items according to query parameters."""
        # Primary sort
        reverse = query.sort_order == TrashSortOrder.DESC
        sorted_items = sorted(
            items, key=lambda x: self._get_sort_key(x, query.sort_by), reverse=reverse
        )

        # Secondary sort: directories first if requested
        if query.dir_first:
            sorted_items = sorted(
                sorted_items, key=lambda x: 0 if x.type == "directory" else 1
            )

        return sorted_items

    async def search(
        self, query: TrashListQuery, user_id: int | None = None
    ) -> tuple[list[TrashFile], int]:
        """Search trash entries with filtering, sorting, and pagination."""
        # Step 1: Database query with basic filters
        statement = select(Trash)

        if user_id is not None:
            statement = statement.where(Trash.user_id == user_id)

        if query.keyword:
            statement = statement.where(Trash.entry_name.contains(query.keyword))

        if query.path:
            # Use consistent normalization with _normalize_path
            # but keep trailing slash for database prefix matching
            normalized_query = self._normalize_path(query.path)
            prefix = "/" if normalized_query == "/" else f"{normalized_query}/"
            statement = statement.where(Trash.original_path.startswith(prefix))

        result = await self.db.execute(statement)
        entries = result.scalars().all()

        # Step 2: Enrich with filesystem metadata
        items = [self._enrich_to_file(entry) for entry in entries]

        # Step 3: Apply memory filters (path recursive logic, type, mime_type)
        filtered_items = [
            item
            for item in items
            if self._matches_path_filter(item.path, query.path, query.recursive)
            and self._matches_type_filter(item, query)
        ]

        # Step 4: Sort items
        sorted_items = self._apply_sorting(filtered_items, query)

        # Step 5: Paginate
        total = len(sorted_items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        paged_items = sorted_items[start:end]

        return paged_items, total

    async def count(self, query: TrashListQuery, user_id: int | None = None) -> int:
        """Count trash entries matching the query."""
        # If we have memory filters (type/mime_type) or complex path logic,
        # we must rely on search to get the accurate count.
        if query.type or query.mime_type or (query.path and not query.recursive):
            _, total = await self.search(query, user_id)
            return total

        # Simple DB count for basic recursive queries
        statement = select(func.count()).select_from(Trash)

        if user_id is not None:
            statement = statement.where(Trash.user_id == user_id)

        if query.keyword:
            statement = statement.where(Trash.entry_name.contains(query.keyword))

        if query.path:
            # Use consistent normalization with _normalize_path
            # but keep trailing slash for database prefix matching
            normalized_query = self._normalize_path(query.path)
            prefix = "/" if normalized_query == "/" else f"{normalized_query}/"
            statement = statement.where(Trash.original_path.startswith(prefix))

        result = await self.db.execute(statement)
        return result.scalar_one()
