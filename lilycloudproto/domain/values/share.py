from dataclasses import dataclass
from enum import Enum


class Permission(str, Enum):
    READ = "read"
    DOWNLOAD = "download"
    WRITE = "write"
    UPLOAD = "upload"


class SortBy(str, Enum):
    BASE_DIR = "base_dir"
    PERMISSION = "permission"
    EXPIRED_AT = "expired_at"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@dataclass
class ListArgs:
    keyword: str | None = None
    user_id: int | None = None
    permission: Permission | None = None
    active_first: bool = True
    sort_by: SortBy = SortBy.CREATED_AT
    sort_order: SortOrder = SortOrder.DESC
    page: int = 1
    page_size: int = 20
