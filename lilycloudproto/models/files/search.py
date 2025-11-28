from dataclasses import dataclass

from pydantic import BaseModel

from lilycloudproto.models.files.file import File
from lilycloudproto.models.files.sort import SortBy, SortOrder


@dataclass
class SearchArgs:
    keyword: str
    path: str
    recursive: bool = True
    type: str | None = None
    mime_type: str | None = None
    sort_by: SortBy = SortBy.NAME
    sort_order: SortOrder = SortOrder.ASC
    dir_first: bool = True


class SearchQuery(BaseModel):
    keyword: str
    path: str
    recursive: bool = True
    type: str | None = None
    mime_type: str | None = None
    sort_by: SortBy = SortBy.NAME
    sort_order: SortOrder = SortOrder.ASC
    dir_first: bool = True


class SearchResponse(BaseModel):
    path: str
    total: int
    items: list[File]
