from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.domain.entities.storage import Storage
from lilycloudproto.domain.values.admin.storage import (
    ListArgs,
    SortBy,
    SortOrder,
)


class StorageRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, storage: Storage) -> Storage:
        """Create a new storage configuration."""
        self.db.add(storage)
        await self.db.commit()
        await self.db.refresh(storage)
        return storage

    async def get_by_id(self, storage_id: int) -> Storage | None:
        """Retrieve a storage configuration by ID."""
        result = await self.db.execute(
            select(Storage).where(Storage.storage_id == storage_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Storage]:
        """Retrieve all storage configurations."""
        result = await self.db.execute(select(Storage))
        return list(result.scalars().all())

    async def search(
        self,
        args: ListArgs,
    ) -> list[Storage]:
        """Search for storage configurations by keyword or type."""
        offset = (args.page - 1) * args.page_size
        statement = select(Storage)

        if args.keyword:
            statement = statement.where(Storage.mount_path.contains(args.keyword))
        if args.type:
            statement = statement.where(Storage.type == args.type)

        # Enabled First Logic
        if args.enabled_first:
            statement = statement.order_by(desc(Storage.enabled))

        field_map = {
            SortBy.CREATED_AT: Storage.created_at,
            SortBy.UPDATED_AT: Storage.updated_at,
            SortBy.MOUNT_PATH: Storage.mount_path,
            SortBy.TYPE: Storage.type,
            SortBy.ENABLED: Storage.enabled,
        }

        sort_column = field_map.get(args.sort_by, Storage.created_at)
        if args.sort_order == SortOrder.DESC:
            statement = statement.order_by(desc(sort_column))
        else:
            statement = statement.order_by(asc(sort_column))

        statement = statement.order_by(Storage.storage_id)
        statement = statement.offset(offset).limit(args.page_size)
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def count(
        self,
        args: ListArgs,
    ) -> int:
        """Count storage configurations with optional filters."""
        statement = select(func.count()).select_from(Storage)

        if args.keyword:
            statement = statement.where(Storage.mount_path.contains(args.keyword))
        if args.type:
            statement = statement.where(Storage.type == args.type)

        result = await self.db.execute(statement)
        return result.scalar_one() or 0

    async def update(self, storage: Storage) -> Storage:
        """Update a storage configuration."""
        await self.db.commit()
        await self.db.refresh(storage)
        return storage

    async def delete(self, storage: Storage) -> None:
        """Delete a storage configuration."""
        await self.db.delete(storage)
        await self.db.commit()
