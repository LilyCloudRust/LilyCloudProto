from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.domain.entities.token import Token


class TokenRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, token: Token) -> Token:
        """Create a new token."""
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)
        return token

    async def get_by_id(self, token_id: int) -> Token | None:
        """Retrieve a token by ID."""
        result = await self.db.execute(select(Token).where(Token.token_id == token_id))
        return result.scalar_one_or_none()

    async def update(self, token: Token) -> Token:
        """Update a token."""
        await self.db.commit()
        await self.db.refresh(token)
        return token

    async def delete(self, token: Token) -> None:
        """Delete a token."""
        await self.db.delete(token)
        await self.db.commit()
