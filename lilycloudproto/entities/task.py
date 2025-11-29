from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from lilycloudproto.database import Base


class TaskType(str, PyEnum):
    COPY = "copy"
    MOVE = "move"
    TRASH = "trash"
    RESTORE = "restore"
    DELETE = "delete"
    UPLOAD = "upload"
    DOWNLOAD = "download"


class TaskStatus(str, PyEnum):
    PENDING = "pending"
    ARCHIVING = "archiving"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(Base):
    __tablename__: str = "tasks"

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[TaskType] = mapped_column(
        Enum(TaskType, native_enum=False), nullable=False
    )
    src_dir: Mapped[str | None] = mapped_column(Text, nullable=True)
    dst_dirs: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    file_names: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False), nullable=False, default=TaskStatus.PENDING
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
