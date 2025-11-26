from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from lilycloudproto.entities.task import TaskStatus, TaskType


class TaskBase(BaseModel):
    type: TaskType
    src_dir: str | None = None
    dst_dirs: list[str]
    file_names: list[str]
    status: TaskStatus
    progress: float
    message: str | None = None


class TaskUpdate(BaseModel):
    status: TaskStatus | None = None
    progress: float | None = None
    message: str | None = None


class TaskResponse(TaskBase):
    task_id: int
    user_id: int
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime

    model_config: ClassVar[ConfigDict] = {"from_attributes": True}


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total_count: int
