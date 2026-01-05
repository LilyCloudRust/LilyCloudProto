from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from lilycloudproto.domain.values.admin.user import Role, SortBy, SortOrder


class UserCreate(BaseModel):
    username: str
    password: str
    role: Role = Role.USER


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    role: Role | None = None


class UserResponse(BaseModel):
    user_id: int
    username: str
    role: Role
    created_at: datetime
    updated_at: datetime

    model_config: ClassVar[ConfigDict] = {"from_attributes": True}


class UserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[UserResponse]


class UserListQuery(BaseModel):
    keyword: str | None = Field(None)
    role: Role | None = Field(None)
    sort_by: SortBy = Field(SortBy.CREATED_AT)
    sort_order: SortOrder = Field(SortOrder.DESC)
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class MessageResponse(BaseModel):
    message: str
