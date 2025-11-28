from dataclasses import dataclass

from pydantic import BaseModel

from lilycloudproto.models.files.file import File
from lilycloudproto.models.files.sort import SortBy, SortOrder


@dataclass
class ListArgs:
    path: str
    sort_by: SortBy = SortBy.NAME
    sort_order: SortOrder = SortOrder.ASC
    dir_first: bool = True


class ListQuery(BaseModel):
    path: str
    sort_by: SortBy = SortBy.NAME
    sort_order: SortOrder = SortOrder.ASC
    dir_first: bool = True


class ListResponse(BaseModel):
    path: str
    total: int
    items: list[File]
