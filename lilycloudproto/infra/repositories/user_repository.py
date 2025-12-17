from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.domain.entities.user import User
from lilycloudproto.domain.values.user import (
    ListArgs,
    SortBy,
    SortOrder,
)


class UserRepository:
    """Repository class for user-related database operations."""

    db: AsyncSession

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user: User) -> User:
        """Create a new user in the database."""
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        """Retrieve a user by their ID. Returns None if not found."""
        result = await self.db.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Retrieve a user by their username. Returns None if not found."""
        statement = select(User).where(User.username == username)
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def get_all(self, page: int = 1, page_size: int = 20) -> list[User]:
        """Retrieve all users with pagination."""
        offset = (page - 1) * page_size
        statement = select(User)

        result = await self.db.execute(statement.offset(offset).limit(page_size))
        return list(result.scalars().all())

    async def search(self, args: ListArgs) -> list[User]:
        """Search for users based on query parameters."""
        offset = (args.page - 1) * args.page_size
        statement = select(User)

        if args.keyword:
            statement = statement.where(User.username.contains(args.keyword))

        field_map = {
            SortBy.USERNAME: User.username,
            SortBy.CREATED_AT: User.created_at,
            SortBy.UPDATED_AT: User.updated_at,
        }
        sort_column = field_map.get(args.sort_by, User.created_at)

        if args.sort_order == SortOrder.DESC:
            statement = statement.order_by(desc(sort_column))
        else:
            statement = statement.order_by(asc(sort_column))

        statement = statement.order_by(User.user_id)
        statement = statement.offset(offset).limit(args.page_size)

        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def count(self, args: ListArgs) -> int:
        """Count users based on query parameters."""
        statement = select(func.count()).select_from(User)

        if args.keyword:
            statement = statement.where(User.username.contains(args.keyword))

        result = await self.db.execute(statement)
        return result.scalar_one() or 0

    async def update(self, user: User) -> User:
        """Update a user's information."""
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        """Delete a user from the database."""
        await self.db.delete(user)
        await self.db.commit()
