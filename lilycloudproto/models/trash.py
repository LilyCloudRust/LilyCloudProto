from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from lilycloudproto.domain.values.trash import TrashSortBy, TrashSortOrder


class TrashRequest(BaseModel):
    dir: str
    file_names: list[str]


class RestoreRequest(BaseModel):
    dir: str
    file_names: list[str]


class DeleteTrashRequest(BaseModel):
    empty: bool = False
    trash_ids: list[int] = []
    dir: str | None = None
    file_names: list[str] = []


class TrashItem(BaseModel):
    trash_id: int
    user_id: int
    entry_name: str
    original_path: str
    type: str
    size: int
    mime_type: str | None
    deleted_at: datetime
    created_at: datetime | None = None
    modified_at: datetime | None = None
    accessed_at: datetime | None = None

    model_config: ClassVar[ConfigDict] = {"from_attributes": True}


class TrashListQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    keyword: str | None = Field(None)
    path: str | None = Field(None)
    recursive: bool = True
    type: str | None = None
    mime_type: str | None = None
    sort_by: TrashSortBy = TrashSortBy.NAME
    sort_order: TrashSortOrder = TrashSortOrder.ASC
    dir_first: bool = True


class TrashResponse(BaseModel):
    path: str | None
    total: int
    items: list[TrashItem]
