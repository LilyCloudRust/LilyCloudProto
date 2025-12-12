from dataclasses import dataclass

from lilycloudproto.domain.values.files.sort import SortBy, SortOrder


@dataclass
class ListArgs:
    path: str
    sort_by: SortBy = SortBy.NAME
    sort_order: SortOrder = SortOrder.ASC
    dir_first: bool = True
