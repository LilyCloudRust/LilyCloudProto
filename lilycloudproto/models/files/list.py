from pydantic import BaseModel

from lilycloudproto.domain.values.files.file import File
from lilycloudproto.domain.values.files.sort import SortBy, SortOrder


class ListQuery(BaseModel):
    path: str
    sort_by: SortBy = SortBy.NAME
    sort_order: SortOrder = SortOrder.ASC
    dir_first: bool = True


class ListResponse(BaseModel):
    path: str
    total: int
    items: list[File]
