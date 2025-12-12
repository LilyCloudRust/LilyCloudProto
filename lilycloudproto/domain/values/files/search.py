from dataclasses import dataclass

from lilycloudproto.domain.values.files.file import Type
from lilycloudproto.domain.values.files.sort import SortBy, SortOrder


@dataclass
class SearchArgs:
    keyword: str
    path: str
    recursive: bool = True
    type: Type | None = None
    mime_type: str | None = None
    sort_by: SortBy = SortBy.NAME
    sort_order: SortOrder = SortOrder.ASC
    dir_first: bool = True
