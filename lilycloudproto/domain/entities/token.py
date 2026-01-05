from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from lilycloudproto.domain.values.auth import TokenType
from lilycloudproto.infra.database import Base


class Token(Base):
    __tablename__: str = "tokens"

    token_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    type: Mapped[TokenType] = mapped_column(Enum(TokenType), nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True
    )
    share_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("shares.share_id", ondelete="CASCADE"), nullable=True
    )
    expired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
