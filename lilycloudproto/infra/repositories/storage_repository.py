from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.domain.entities.storage import Storage, StorageType
from lilycloudproto.models.storage import SortBy, SortOrder, StorageListQuery


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

    async def get_all(self, page: int = 1, page_size: int = 20) -> list[Storage]:
        """Retrieve all storage configurations with pagination."""
        offset = (page - 1) * page_size
        result = await self.db.execute(select(Storage).offset(offset).limit(page_size))
        return list(result.scalars().all())

    async def search(
        self,
        params: StorageListQuery,
    ) -> list[Storage]:
        """Search for storage configurations by keyword or type."""
        offset = (params.page - 1) * params.page_size
        statement = select(Storage)
        if params.keyword:
            statement = statement.where(Storage.mount_path.contains(params.keyword))
        if params.type:
            statement = statement.where(Storage.type == params.type)

        # Apply sorting
        field_map = {
            SortBy.CREATED_AT: Storage.created_at,
            SortBy.UPDATED_AT: Storage.updated_at,
            SortBy.MOUNT_PATH: Storage.mount_path,
            SortBy.TYPE: Storage.type,
            SortBy.ENABLED: Storage.enabled,
        }

        sort_column = field_map.get(params.sort_by, Storage.created_at)
        if params.sort_order == SortOrder.DESC:
            statement = statement.order_by(desc(sort_column))
        else:
            statement = statement.order_by(asc(sort_column))

        # Always order by ID for consistent pagination
        statement = statement.order_by(Storage.storage_id)

        statement = statement.offset(offset).limit(params.page_size)
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def count(
        self,
        keyword: str | None = None,
        type: StorageType | None = None,
    ) -> int:
        """Count storage configurations with optional filters."""
        statement = select(Storage)
        if keyword:
            statement = statement.where(Storage.mount_path.contains(keyword))
        if type:
            statement = statement.where(Storage.type == type)

        count_statement = select(func.count()).select_from(statement.subquery())
        total_count = (await self.db.execute(count_statement)).scalar_one()
        return total_count

    async def update(self, storage: Storage) -> Storage:
        """Update a storage configuration."""
        await self.db.commit()
        await self.db.refresh(storage)
        return storage

    async def delete(self, storage: Storage) -> None:
        """Delete a storage configuration."""
        await self.db.delete(storage)
        await self.db.commit()
