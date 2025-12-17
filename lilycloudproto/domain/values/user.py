from dataclasses import dataclass
from enum import Enum


class SortBy(str, Enum):
    USERNAME = "username"
    CREATED_AT = "created"
    UPDATED_AT = "updated"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@dataclass
class ListArgs:
    keyword: str | None = None
    sort_by: SortBy = SortBy.CREATED_AT
    sort_order: SortOrder = SortOrder.DESC
    page: int = 1
    page_size: int = 20
