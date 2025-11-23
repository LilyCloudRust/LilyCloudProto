from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from lilycloudproto.config import settings
from lilycloudproto.entities.user import User
from lilycloudproto.models.auth import TokenResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthRepository:
    """Repository class for auth-related database operations."""

    db: AsyncSession

    def __init__(self, db: AsyncSession):
        self.db = db
    def verify_password(self, pwd: str, hashed_pwd: str) -> bool:
        return pwd_context.verify(pwd, hashed_pwd)

    def generate_token(self, data: dict, minutes: int | None = None) -> str:
        to_encode = data.copy()
        expire_minutes = (
            minutes if minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        expire = datetime.now(UTC) + timedelta(minutes=expire_minutes)

        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return encoded_jwt

    async def authenticate(self, username: str, pwd: str) -> TokenResponse | None:
        statement = select(User).where(User.username == username)
        result = await self.db.execute(statement)
        user = result.scalar_one_or_none()
        if not user:
            return None
        if not self.verify_password(pwd, user.hashed_password):
            return None
        access_token = self.generate_token({"sub": str(user.user_id)})
        refresh_token = self.generate_token(
            {"sub": str(user.user_id)}, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 24 * 7
        )
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
