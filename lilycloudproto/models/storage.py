from datetime import datetime
from typing import Any

from fastapi import Query
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


class StorageQueryParams:
    def __init__(
        self,
        keyword: str | None = Query(None),
        type: StorageType | None = Query(None),
        enabled_first: bool = Query(False),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
    ):
        self.keyword = keyword
        self.type = type
        self.enabled_first = enabled_first
        self.page = page
        self.page_size = page_size
