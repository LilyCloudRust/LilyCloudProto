from datetime import UTC, datetime, timedelta
from typing import Any, cast

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.exc import IntegrityError

from lilycloudproto.config import settings
from lilycloudproto.entities.user import User
from lilycloudproto.error import AuthenticationError
from lilycloudproto.infra.user_repository import UserRepository
from lilycloudproto.models.auth import TokenResponse

password_hash = PasswordHash(
    (
        Argon2Hasher(
            time_cost=settings.ARGON2_TIME_COST,
            memory_cost=settings.ARGON2_MEMORY_COST,
            parallelism=settings.ARGON2_PARALLELISM,
        ),
    )
)


class AuthService:
    _dummy_hash: str | None = None

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        if AuthService._dummy_hash is None:
            AuthService._dummy_hash = self.get_password_hash(
                "dummy_password_for_timing_protection"
            )

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return password_hash.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return password_hash.hash(password)

    def create_token(
        self, data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return encoded_jwt

    def decode_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            return cast(dict[str, Any], payload)
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired") from None
        except jwt.InvalidTokenError:
            raise AuthenticationError("Could not validate credentials") from None

    async def authenticate_user(self, username: str, password: str) -> TokenResponse:
        user = await self.user_repo.get_by_username(username)
        hash_to_verify = user.hashed_password if user else str(self._dummy_hash)
        is_password_correct = self.verify_password(password, hash_to_verify)

        if user is None or not is_password_correct:
            raise AuthenticationError("Incorrect username or password") from None

        return self._generate_tokens(user)

    async def register_user(self, username: str, password: str) -> User:
        hashed_password = self.get_password_hash(password)
        user = User(username=username, hashed_password=hashed_password)
        try:
            created_user = await self.user_repo.create(user)
            return created_user
        except IntegrityError:
            raise AuthenticationError("Username already registered") from None

    async def refresh_access_token(self, refresh_token: str) -> str:
        payload = self.decode_token(refresh_token)
        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid token") from None

        user = await self.user_repo.get_by_id(int(user_id))
        if not user:
            raise AuthenticationError("User not found") from None

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return self.create_token(
            data={"sub": str(user.user_id)}, expires_delta=access_token_expires
        )

    async def get_user_from_token(self, token: str) -> User:
        payload = self.decode_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid credentials") from None

        user = await self.user_repo.get_by_id(int(user_id))
        if user is None:
            raise AuthenticationError("User not found") from None
        return user

    def _generate_tokens(self, user: User) -> TokenResponse:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_token(
            data={"sub": str(user.user_id)}, expires_delta=access_token_expires
        )
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = self.create_token(
            data={"sub": str(user.user_id)}, expires_delta=refresh_token_expires
        )
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
