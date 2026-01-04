from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from lilycloudproto.domain.values.files.file import Type
from lilycloudproto.domain.values.trash import SortBy, SortOrder


class TrashFilesRequest(BaseModel):
    dir: str
    file_names: list[str]


class TrashRestoreRequest(BaseModel):
    dir: str
    file_names: list[str]


class TrashDeleteRequest(BaseModel):
    empty: bool = False
    trash_ids: list[int] = Field(default_factory=list)
    dir: str | None = None
    file_names: list[str] = Field(default_factory=list)


class TrashListQuery(BaseModel):
    keyword: str | None = None
    user_id: int | None = None
    type: Type | None = None
    mime_type: str | None = None
    sort_by: SortBy = SortBy.DELETED
    sort_order: SortOrder = SortOrder.DESC
    dir_first: bool = True


class TrashResponse(BaseModel):
    trash_id: int
    user_id: int
    entry_name: str
    original_path: str
    type: str
    size: int
    mime_type: str
    created_at: datetime
    modified_at: datetime
    accessed_at: datetime
    deleted_at: datetime

    model_config: ClassVar[ConfigDict] = {"from_attributes": True}


class TrashListResponse(BaseModel):
    total: int
    items: list[TrashResponse]
