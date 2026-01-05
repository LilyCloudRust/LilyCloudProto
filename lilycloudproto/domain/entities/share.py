from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from lilycloudproto.domain.values.share import Permission
from lilycloudproto.infra.database import Base


class Share(Base):
    __tablename__: str = "shares"

    share_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    base_dir: Mapped[str] = mapped_column(String, nullable=False)
    file_names: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    permission: Mapped[Permission] = mapped_column(String, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    expired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
