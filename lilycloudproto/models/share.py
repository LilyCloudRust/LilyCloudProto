from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from lilycloudproto.domain.entities.share import Share
from lilycloudproto.domain.values.share import Permission, SortBy, SortOrder


class ShareCreate(BaseModel):
    base_dir: str
    file_names: list[str]
    permission: Permission
    password: str | None = None
    expires_at: datetime


class ShareUpdate(BaseModel):
    base_dir: str | None = None
    file_names: list[str] | None = None
    permission: Permission | None = None
    password: str | None = None
    expires_at: datetime | None = None


class ShareResponse(BaseModel):
    share_id: int
    user_id: int
    token: str
    base_dir: str
    file_names: list[str]
    permission: Permission
    requires_password: bool
    expired_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, entity: Share) -> "ShareResponse":
        return cls(
            share_id=entity.share_id,
            user_id=entity.user_id,
            token=entity.token,
            base_dir=entity.base_dir,
            file_names=entity.file_names,
            permission=entity.permission,
            requires_password=entity.hashed_password is not None,
            expired_at=entity.expires_at,  # Note: use the correct field name
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    model_config: ClassVar[ConfigDict] = {"from_attributes": True}


class ShareListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ShareResponse]


class ShareListQuery(BaseModel):
    keyword: str | None = None
    user_id: int | None = None
    permission: Permission | None = None
    active_first: bool = True
    sort_by: SortBy = SortBy.CREATED_AT
    sort_order: SortOrder = SortOrder.DESC
    page: int = 1
    page_size: int = 20


class MessageResponse(BaseModel):
    message: str


class ShareInfoResponse(BaseModel):
    username: str
    token: str
    file_names: list[str]
    permission: Permission
    requires_password: bool
    expires_at: datetime
