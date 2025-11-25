from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from lilycloudproto.entities.storage import StorageType


# --- Config Schemas ---
class LocalConfig(BaseModel):
    root_path: str


class S3Config(BaseModel):
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str
    region: str | None = None


class WebDAVConfig(BaseModel):
    url: str
    username: str
    password: str


# --- Config Mapping ---
STORAGE_CONFIG_MAP: dict[StorageType, type[BaseModel]] = {
    StorageType.LOCAL: LocalConfig,
    StorageType.S3: S3Config,
    StorageType.WEBDAV: WebDAVConfig,
}


# --- Create Models ---
class StorageCreateLocal(BaseModel):
    mount_path: str
    type: Literal[StorageType.LOCAL]
    config: LocalConfig
    enabled: bool = True


class StorageCreateS3(BaseModel):
    mount_path: str
    type: Literal[StorageType.S3]
    config: S3Config
    enabled: bool = True


class StorageCreateWebDAV(BaseModel):
    mount_path: str
    type: Literal[StorageType.WEBDAV]
    config: WebDAVConfig
    enabled: bool = True


StorageCreate = Annotated[
    StorageCreateLocal | StorageCreateS3 | StorageCreateWebDAV,
    Field(discriminator="type"),
]


# --- Update Model ---
class StorageUpdate(BaseModel):
    mount_path: str | None = None
    type: StorageType | None = None
    config: LocalConfig | S3Config | WebDAVConfig | dict[str, Any] | None = None
    enabled: bool | None = None


# --- Response Models ---
class StorageResponseBase(BaseModel):
    storage_id: int
    mount_path: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StorageResponseLocal(StorageResponseBase):
    type: Literal[StorageType.LOCAL]
    config: LocalConfig


class StorageResponseS3(StorageResponseBase):
    type: Literal[StorageType.S3]
    config: S3Config


class StorageResponseWebDAV(StorageResponseBase):
    type: Literal[StorageType.WEBDAV]
    config: WebDAVConfig


StorageResponse = Annotated[
    StorageResponseLocal | StorageResponseS3 | StorageResponseWebDAV,
    Field(discriminator="type"),
]


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
