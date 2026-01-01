from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from lilycloudproto.config import AuthSettings
from lilycloudproto.domain.entities.user import User
from lilycloudproto.error import AuthenticationError
from lilycloudproto.infra.repositories.user_repository import UserRepository


class Payload(BaseModel):
    sub: str
    exp: datetime


class AuthService:
    user_repo: UserRepository
    password_hash: PasswordHash
    settings: AuthSettings
    _dummy_hash: str | None = None

    def __init__(self, user_repo: UserRepository, settings: AuthSettings):
        self.user_repo = user_repo
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
        if AuthService._dummy_hash is None:
            AuthService._dummy_hash = self.password_hash.hash(
                "dummy_password_for_timing_protection"
            )

    async def authenticate_user(self, username: str, password: str) -> tuple[str, str]:
        user = await self.user_repo.get_by_username(username)
        hash_to_verify = user.hashed_password if user else str(self._dummy_hash)
        is_password_correct = self.password_hash.verify(password, hash_to_verify)
        if user is None or not is_password_correct:
            raise AuthenticationError("Incorrect username or password") from None
        return self._generate_tokens(user)

    async def register_user(self, username: str, password: str) -> User:
        hashed_password = self.password_hash.hash(password)
        user = User(username=username, hashed_password=hashed_password)
        try:
            created_user = await self.user_repo.create(user)
            return created_user
        except IntegrityError as error:
            raise AuthenticationError("Username already registered") from error

    async def refresh_access_token(self, refresh_token: str) -> str:
        payload = self._decode_token(refresh_token)
        user_id = payload.sub
        user = await self.user_repo.get_by_id(int(user_id))
        if not user:
            raise AuthenticationError("User not found") from None

        expires = datetime.now(UTC) + timedelta(
            minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        access_token = self._create_token(Payload(sub=str(user.user_id), exp=expires))
        return access_token

    async def get_user_from_token(self, token: str) -> User:
        payload = self._decode_token(token)
        user_id = payload.sub
        user = await self.user_repo.get_by_id(int(user_id))
        if user is None:
            raise AuthenticationError("User not found") from None
        return user

    def _create_token(self, payload: Payload) -> str:
        return jwt.encode(  # pyright: ignore[reportUnknownMemberType]
            payload.model_dump(),
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

    def _generate_tokens(self, user: User) -> tuple[str, str]:
        access_token_payload = Payload(
            sub=str(user.user_id),
            exp=datetime.now(UTC)
            + timedelta(minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token_payload = Payload(
            sub=str(user.user_id),
            exp=datetime.now(UTC)
            + timedelta(days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        access_token = self._create_token(access_token_payload)
        refresh_token = self._create_token(refresh_token_payload)
        return access_token, refresh_token

    async def authenticate_basic_user(
        self, username: str, password: str
    ) -> User | None:
        user = await self.user_repo.get_by_username(username)
        # 使用与 authenticate_user 相同的哈希验证逻辑
        hash_to_verify = user.hashed_password if user else str(self._dummy_hash)
        is_password_correct = self.password_hash.verify(password, hash_to_verify)

        if user is None or not is_password_correct:
            return None
        return user
