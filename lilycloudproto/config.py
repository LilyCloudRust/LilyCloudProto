import os
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class AdminSettings(BaseSettings):
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "root")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "password")
    model_config: ClassVar[SettingsConfigDict] = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "frozen": True,
    }


class AuthSettings(BaseSettings):
    SECRET_KEY: str = os.getenv("SECRET_KEY", "secret")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ARGON2_TIME_COST: int = int(os.getenv("ARGON2_TIME_COST", "2"))
    ARGON2_MEMORY_COST: int = int(os.getenv("ARGON2_MEMORY_COST", "131072"))  # 128 MiB.
    ARGON2_PARALLELISM: int = int(os.getenv("ARGON2_PARALLELISM", "2"))
    model_config: ClassVar[SettingsConfigDict] = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "frozen": True,
    }


admin_settings = AdminSettings()
auth_settings = AuthSettings()
