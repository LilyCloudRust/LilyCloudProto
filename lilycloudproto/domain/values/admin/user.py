from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"


class SortBy(str, Enum):
    USERNAME = "username"
    ROLE = "role"
    CREATED_AT = "created"
    UPDATED_AT = "updated"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@dataclass
class ListArgs:
    keyword: str | None = None
    role: Role | None = None
    sort_by: SortBy = SortBy.CREATED_AT
    sort_order: SortOrder = SortOrder.DESC
    page: int = 1
    page_size: int = 20
