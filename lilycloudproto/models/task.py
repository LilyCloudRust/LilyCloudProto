from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from lilycloudproto.domain.values.task import SortBy, SortOrder, TaskStatus, TaskType


class TaskCreate(BaseModel):
    type: TaskType
    src_dir: str | None = None
    dst_dirs: list[str] = []
    file_names: list[str] = []
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    message: str | None = None


class TaskUpdate(BaseModel):
    user_id: int | None = None
    type: TaskType | None = None
    src_dir: str | None = None
    dst_dirs: list[str] | None = None
    file_names: list[str] | None = None
    status: TaskStatus | None = None
    progress: float | None = None
    message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskResponse(BaseModel):
    task_id: int
    user_id: int
    type: str
    src_dir: str | None
    dst_dirs: list[str]
    file_names: list[str]
    status: str
    progress: float
    message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime

    model_config: ClassVar[ConfigDict] = {"from_attributes": True}


class TaskListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TaskResponse]


class TaskListQuery(BaseModel):
    keyword: str | None = Field(None)
    user_id: int | None = Field(None)
    type: TaskType | None = Field(None)
    status: TaskStatus | None = Field(None)
    sort_by: SortBy = Field(SortBy.CREATED_AT)
    sort_order: SortOrder = Field(SortOrder.DESC)
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class MessageResponse(BaseModel):
    message: str
