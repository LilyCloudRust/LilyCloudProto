from enum import Enum
from typing import Protocol


class SortBy(str, Enum):
    NAME = "name"
    SIZE = "size"
    CREATED = "created"
    MODIFIED = "modified"
    ACCESSED = "accessed"
    TYPE = "type"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class SortArgs(Protocol):
    sort_by: SortBy
    sort_order: SortOrder
    dir_first: bool
