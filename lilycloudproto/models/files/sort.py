from typing import Literal, Protocol

SortBy = Literal["name", "size", "created", "modified", "accessed", "type"]
SortOrder = Literal["asc", "desc"]


class SortArgs(Protocol):
    sort_by: SortBy
    sort_order: SortOrder
    dir_first: bool
