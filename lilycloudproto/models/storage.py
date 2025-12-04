from datetime import datetime
from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from lilycloudproto.domain.entities.storage import (
    StorageConfig,
    StorageType,
)


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class StorageSortField(str, Enum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    MOUNT_PATH = "mount_path"
    TYPE = "type"
    ENABLED = "enabled"


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


class StorageListQuery(BaseModel):
    keyword: str | None = Field(None)
    type: StorageType | None = Field(None)
    sort_by: StorageSortField = Field(StorageSortField.CREATED_AT)
    sort_order: SortOrder = Field(SortOrder.DESC)
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
