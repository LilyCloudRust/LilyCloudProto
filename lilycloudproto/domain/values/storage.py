from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel


class StorageType(str, Enum):
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


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class SortBy(str, Enum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    MOUNT_PATH = "mount_path"
    TYPE = "type"
    ENABLED = "enabled"


@dataclass
class ListArgs:
    keyword: str | None
    type: StorageType | None
    sort_by: SortBy
    sort_order: SortOrder
    page: int
    page_size: int
