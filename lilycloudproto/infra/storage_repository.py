from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.entities.storage import Storage, StorageType


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
        keyword: str | None = None,
        type: StorageType | None = None,
        enabled_first: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Storage]:
        """Search for storage configurations by keyword or type."""
        offset = (page - 1) * page_size
        statement = select(Storage)
        if keyword:
            statement = statement.where(Storage.mount_path.contains(keyword))
        if type:
            statement = statement.where(Storage.type == type)

        # Apply sorting
        if enabled_first:
            statement = statement.order_by(desc(Storage.enabled))

        # Always order by ID for consistent pagination
        statement = statement.order_by(Storage.storage_id)

        statement = statement.offset(offset).limit(page_size)
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
