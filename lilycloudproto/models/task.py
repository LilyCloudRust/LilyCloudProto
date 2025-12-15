from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from lilycloudproto.domain.values.task import TaskStatus, TaskType


class TaskUpdate(BaseModel):
    status: TaskStatus | None = None
    progress: float | None = None
    message: str | None = None


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
    items: list[TaskResponse]


class TaskListQuery(BaseModel):
    keyword: str | None = Field(None)
    type: TaskType | None = Field(None)
    status: TaskStatus | None = Field(None)
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
