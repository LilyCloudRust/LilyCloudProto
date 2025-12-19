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


class SortBy(str, Enum):
    TYPE = "type"
    SRC = "src"
    STATUS = "status"
    CREATED_AT = "created"
    STARTED_AT = "started"
    COMPLETED_AT = "completed"
    UPDATED_AT = "updated"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@dataclass
class ListArgs:
    keyword: str | None
    user_id: int | None
    type: TaskType | None
    status: TaskStatus | None
    sort_by: SortBy
    sort_order: SortOrder
    page: int = 1
    page_size: int = 20
