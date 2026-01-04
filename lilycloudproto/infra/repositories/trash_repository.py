from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.domain.entities.trash import Trash
from lilycloudproto.domain.values.trash import ListArgs, SortBy, SortOrder


class TrashRepository:
    """Repository class for trash-related database operations."""

    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, trash: Trash) -> Trash:
        """Create a new trash entry in the database."""
        self.db.add(trash)
        await self.db.commit()
        await self.db.refresh(trash)
        return trash

    async def get_by_id(self, trash_id: int) -> Trash | None:
        """Retrieve a trash entry by ID. Returns None if not found."""
        result = await self.db.execute(select(Trash).where(Trash.trash_id == trash_id))
        return result.scalar_one_or_none()

    async def search(self, args: ListArgs) -> list[Trash]:
        statement = select(Trash)

        if args.keyword:
            statement = statement.where(
                (Trash.entry_name.ilike(f"%{args.keyword}%"))
                | (
                    getattr(Trash, "original_path", Trash.entry_name).ilike(
                        f"%{args.keyword}%"
                    )
                )
            )
        if args.user_id:
            statement = statement.where(Trash.user_id == args.user_id)
        if args.type:
            statement = statement.where(Trash.type == args.type)
        if args.mime_type:
            statement = statement.where(Trash.mime_type == args.mime_type)

        # Map sort_by to Trash columns
        field_map = {
            SortBy.NAME: Trash.entry_name,
            SortBy.PATH: getattr(Trash, "original_path", Trash.entry_name),
            SortBy.SIZE: Trash.size,
            SortBy.TYPE: Trash.type,
            SortBy.DELETED: Trash.deleted_at,
            SortBy.CREATED: Trash.created_at,
            SortBy.MODIFIED: Trash.modified_at,
            SortBy.ACCESSED: Trash.accessed_at,
        }
        sort_column = field_map.get(args.sort_by, Trash.deleted_at)

        if args.sort_order == SortOrder.DESC:
            statement = statement.order_by(desc(sort_column))
        else:
            statement = statement.order_by(asc(sort_column))

        # Optionally, add directory-first sorting if needed.
        if args.dir_first:
            statement = statement.order_by(desc(Trash.type == "directory"))

        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def count(self, args: ListArgs) -> int:
        statement = select(func.count()).select_from(Trash)

        if args.keyword:
            statement = statement.where(
                (Trash.entry_name.ilike(f"%{args.keyword}%"))
                | (
                    getattr(Trash, "original_path", Trash.entry_name).ilike(
                        f"%{args.keyword}%"
                    )
                )
            )
        if args.user_id:
            statement = statement.where(Trash.user_id == args.user_id)
        if args.type:
            statement = statement.where(Trash.type == args.type)
        if args.mime_type:
            statement = statement.where(Trash.mime_type == args.mime_type)

        result = await self.db.execute(statement)
        return result.scalar_one() or 0

    async def update(self, trash: Trash) -> Trash:
        """Update an existing trash entry in the database."""
        await self.db.commit()
        await self.db.refresh(trash)
        return trash

    async def delete(self, trash: Trash) -> None:
        """Delete a trash entry from the database."""
        await self.db.delete(trash)
        await self.db.commit()
