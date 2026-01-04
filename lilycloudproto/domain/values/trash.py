from dataclasses import dataclass
from enum import Enum


class SortBy(str, Enum):
    NAME = "name"
    PATH = "path"
    SIZE = "size"
    TYPE = "type"
    DELETED = "deleted"
    CREATED = "created"
    MODIFIED = "modified"
    ACCESSED = "accessed"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@dataclass
class ListArgs:
    keyword: str | None = None
    user_id: int | None = None
    type: str | None = None
    mime_type: str | None = None
    sort_by: SortBy = SortBy.NAME
    sort_order: SortOrder = SortOrder.DESC
    dir_first: bool = True
