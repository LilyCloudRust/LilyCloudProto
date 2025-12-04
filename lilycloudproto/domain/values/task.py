from dataclasses import dataclass
from enum import Enum


class TaskType(str, Enum):
    COPY = "copy"
    MOVE = "move"
    TRASH = "trash"
    RESTORE = "restore"
    DELETE = "delete"
    UPLOAD = "upload"
    DOWNLOAD = "download"


class TaskStatus(str, Enum):
    PENDING = "pending"
    ARCHIVING = "archiving"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ListArgs:
    keyword: str | None
    type: TaskType | None
    status: TaskStatus | None
    page: int
    page_size: int
