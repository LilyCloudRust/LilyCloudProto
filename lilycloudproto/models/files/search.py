from pydantic import BaseModel

from lilycloudproto.domain.values.files.file import File, Type
from lilycloudproto.domain.values.files.sort import SortBy, SortOrder


class SearchQuery(BaseModel):
    keyword: str
    path: str
    recursive: bool = True
    type: Type | None = None
    mime_type: str | None = None
    sort_by: SortBy = SortBy.NAME
    sort_order: SortOrder = SortOrder.ASC
    dir_first: bool = True


class SearchResponse(BaseModel):
    path: str
    total: int
    items: list[File]
