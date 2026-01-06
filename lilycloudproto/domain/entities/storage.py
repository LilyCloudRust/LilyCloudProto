from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from lilycloudproto.domain.values.admin.storage import StorageType
from lilycloudproto.infra.database import Base


class Storage(Base):
    __tablename__: str = "storages"

    storage_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mount_path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    type: Mapped[StorageType] = mapped_column(Enum(StorageType), nullable=False)
    config: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
