from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from lilycloudproto.entities.storage import StorageType


class StorageBase(BaseModel):
    mount_path: str
    type: StorageType
    config: dict[str, Any]
    enabled: bool = True


class StorageCreate(StorageBase):
    pass


class StorageUpdate(BaseModel):
    mount_path: str | None = None
    type: StorageType | None = None
    config: dict[str, Any] | None = None
    enabled: bool | None = None


class StorageResponse(StorageBase):
    storage_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StorageListResponse(BaseModel):
    items: list[StorageResponse]
    total_count: int
