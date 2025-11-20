from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from lilycloudproto.entities.user import User


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

    async def get_all(self, page: int = 1, page_size: int = 20) -> list[User]:
        """Retrieve all users with pagination."""
        offset = (page - 1) * page_size
        result = await self.db.execute(select(User).offset(offset).limit(page_size))
        return list(result.scalars().all())

    async def search(
        self, keyword: str | None = None, page: int = 1, page_size: int = 20
    ) -> list[User]:
        """Search for users by keyword with pagination."""
        offset = (page - 1) * page_size
        statement = select(User)
        if keyword:
            statement = statement.where(User.username.contains(keyword))
        statement = statement.offset(offset).limit(page_size)
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def update(self, user: User) -> User:
        """Update a user's information."""
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        """Delete a user from the database."""
        await self.db.delete(user)
        await self.db.commit()
