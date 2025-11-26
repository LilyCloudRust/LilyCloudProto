from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from lilycloudproto.entities.storage import (
    StorageConfig,
    StorageType,
)


class StorageCreate(BaseModel):
    mount_path: str
    type: StorageType
    config: StorageConfig
    enabled: bool = True


class StorageUpdate(BaseModel):
    mount_path: str | None = None
    type: StorageType | None = None
    config: StorageConfig | None = None
    enabled: bool | None = None


class StorageResponse(BaseModel):
    storage_id: int
    mount_path: str
    type: StorageType
    config: StorageConfig
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config: ClassVar[ConfigDict] = {"from_attributes": True}


class StorageListResponse(BaseModel):
    total: int
    items: list[StorageResponse]


class StorageListQuert(BaseModel):
    keyword: str | None = Field(None)
    type: StorageType | None = Field(None)
    enabled_first: bool = Field(False)
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
