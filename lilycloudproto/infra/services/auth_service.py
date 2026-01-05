from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from lilycloudproto.config import AuthSettings
from lilycloudproto.domain.entities.token import Token
from lilycloudproto.domain.entities.user import User
from lilycloudproto.domain.values.auth import TokenType
from lilycloudproto.error import AuthenticationError
from lilycloudproto.infra.repositories.token_repository import TokenRepository
from lilycloudproto.infra.repositories.user_repository import UserRepository


class Payload(BaseModel):
    token_id: int
    user_id: int
    expires_at: datetime


class AuthService:
    user_repo: UserRepository
    token_repo: TokenRepository
    password_hash: PasswordHash
    settings: AuthSettings
    _dummy_hash: str | None = None

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: TokenRepository,
        settings: AuthSettings,
    ):
        self.user_repo = user_repo
        self.token_repo = token_repo
        self.settings = settings
        self.password_hash = PasswordHash(
            (
                Argon2Hasher(
                    time_cost=self.settings.ARGON2_TIME_COST,
                    memory_cost=self.settings.ARGON2_MEMORY_COST,
                    parallelism=self.settings.ARGON2_PARALLELISM,
                ),
            )
        )
        self._dummy_hash = self.password_hash.hash(
            "dummy_password_for_timing_protection"
        )

    async def authenticate(self, username: str, password: str) -> tuple[str, str]:
        user = await self.user_repo.get_by_username(username)
        hash_to_verify = user.hashed_password if user else str(self._dummy_hash)
        is_password_correct = self.password_hash.verify(password, hash_to_verify)
        if user is None or not is_password_correct:
            raise AuthenticationError("Incorrect username or password.")
        return await self._generate_tokens(user)

    async def authenticate_basic(self, username: str, password: str) -> User | None:
        user = await self.user_repo.get_by_username(username)
        hash_to_verify = user.hashed_password if user else str(self._dummy_hash)
        is_password_correct = self.password_hash.verify(password, hash_to_verify)
        if user is None or not is_password_correct:
            return None
        return user

    async def register(self, username: str, password: str) -> User:
        hashed_password = self.password_hash.hash(password)
        user = User(username=username, hashed_password=hashed_password)
        try:
            created_user = await self.user_repo.create(user)
            return created_user
        except IntegrityError as error:
            raise AuthenticationError("Username already registered.") from error

    async def refresh(self, refresh_token: str) -> str:
        payload = self._decode_token(refresh_token)

        # Check if user exists.
        user = await self.user_repo.get_by_id(payload.user_id)
        if not user:
            raise AuthenticationError("User not found.")

        # Get the token from database to validate the refresh token.
        token_entity = await self.token_repo.get_by_id(payload.token_id)

        # Check if the token exists.
        if not token_entity:
            raise AuthenticationError("Invalid refresh token.")

        # Check if the token is valid.
        if token_entity.expires_at.tzinfo is None:
            # SQLite3 does not support timezone-aware datetime.
            token_entity.expires_at = token_entity.expires_at.replace(tzinfo=UTC)
        if (
            token_entity.type != TokenType.REFRESH
            or token_entity.user_id != payload.user_id
            or token_entity.expires_at != payload.expires_at
        ):
            raise AuthenticationError("Invalid refresh token.")

        # Create new access token entity.
        expires_at = datetime.now(UTC) + timedelta(
            minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        access_token_entity = Token(
            type=TokenType.ACCESS, user_id=user.user_id, expires_at=expires_at
        )
        access_token_entity = await self.token_repo.create(access_token_entity)

        # Create new access token.
        payload = Payload(
            token_id=access_token_entity.token_id,
            user_id=user.user_id,
            expires_at=expires_at,
        )
        access_token = self._encode_token(payload)
        return access_token

    async def get_user_from_token(self, token: str) -> User:
        payload = self._decode_token(token)

        # Check if user exists.
        user = await self.user_repo.get_by_id(payload.user_id)
        if not user:
            raise AuthenticationError("User not found.")

        # Get the token from database to validate the access token.
        token_entity = await self.token_repo.get_by_id(payload.token_id)

        # Check if the token exists.
        if not token_entity:
            raise AuthenticationError("Invalid access token.")

        # Check if the token is valid.
        if token_entity.expires_at.tzinfo is None:
            # SQLite3 does not support timezone-aware datetime.
            token_entity.expires_at = token_entity.expires_at.replace(tzinfo=UTC)
        if (
            token_entity.type != TokenType.ACCESS
            or token_entity.user_id != payload.user_id
            or token_entity.expires_at != payload.expires_at
        ):
            raise AuthenticationError("Invalid access token.")

        return user

    def _encode_token(self, payload: Payload) -> str:
        return jwt.encode(  # pyright: ignore[reportUnknownMemberType]
            payload.model_dump(mode="json"),
            self.settings.SECRET_KEY,
            algorithm=self.settings.ALGORITHM,
        )

    def _decode_token(self, token: str) -> Payload:
        try:
            data = jwt.decode(  # pyright: ignore[reportAny, reportUnknownMemberType]
                token, self.settings.SECRET_KEY, algorithms=[self.settings.ALGORITHM]
            )
            return Payload.model_validate(data)
        except jwt.ExpiredSignatureError as error:
            raise AuthenticationError("Token has expired.") from error
        except jwt.InvalidTokenError as error:
            raise AuthenticationError("Could not validate credentials.") from error

    async def _generate_tokens(self, user: User) -> tuple[str, str]:
        # Create access token.
        access_token_expires = datetime.now(UTC) + timedelta(
            minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        access_token_entity = Token(
            type=TokenType.ACCESS, user_id=user.user_id, expires_at=access_token_expires
        )
        access_token_entity = await self.token_repo.create(access_token_entity)

        # Create refresh token.
        refresh_token_expires = datetime.now(UTC) + timedelta(
            days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        refresh_token_entity = Token(
            type=TokenType.REFRESH,
            user_id=user.user_id,
            expires_at=refresh_token_expires,
        )
        refresh_token_entity = await self.token_repo.create(refresh_token_entity)

        # Create payloads.
        access_token_payload = Payload(
            token_id=access_token_entity.token_id,
            user_id=user.user_id,
            expires_at=access_token_expires,
        )
        refresh_token_payload = Payload(
            token_id=refresh_token_entity.token_id,
            user_id=user.user_id,
            expires_at=refresh_token_expires,
        )

        access_token = self._encode_token(access_token_payload)
        refresh_token = self._encode_token(refresh_token_payload)
        return access_token, refresh_token
