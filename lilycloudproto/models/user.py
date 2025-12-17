from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from lilycloudproto.domain.values.user import SortBy, SortOrder


class UserCreate(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None


class UserResponse(BaseModel):
    user_id: int
    username: str
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
    sort_by: SortBy = Field(SortBy.CREATED_AT)
    sort_order: SortOrder = Field(SortOrder.DESC)
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class MessageResponse(BaseModel):
    message: str
