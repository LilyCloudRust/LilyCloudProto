from datetime import datetime
from enum import Enum as PyEnum

from pydantic import BaseModel
from sqlalchemy import JSON, Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from lilycloudproto.database import Base


class StorageType(str, PyEnum):
    LOCAL = "local"
    S3 = "s3"


class LocalConfig(BaseModel):
    root_path: str


class S3Config(BaseModel):
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str
    region: str | None = None


StorageConfig = LocalConfig | S3Config


class Storage(Base):
    __tablename__: str = "storages"

    storage_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mount_path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    type: Mapped[StorageType] = mapped_column(
        Enum(StorageType, native_enum=False), nullable=False
    )
    config: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


CONFIG_MAP: dict[StorageType, type[StorageConfig]] = {
    StorageType.LOCAL: LocalConfig,
    StorageType.S3: S3Config,
}


def validate_config(
    storage_type: StorageType, config: StorageConfig | dict[str, str]
) -> dict[str, str]:
    model = CONFIG_MAP.get(storage_type)
    if not model:
        raise ValueError(f"Unknown storage type: {storage_type}")
    return model.model_validate(config).model_dump()
