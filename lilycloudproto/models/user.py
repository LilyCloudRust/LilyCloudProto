from datetime import datetime
from typing import ClassVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict


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
    items: list[UserResponse]
    total_count: int


class UserQueryParams:
    def __init__(
        self,
        keyword: str | None = Query(None, min_length=1),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
    ):
        self.keyword = keyword
        self.page = page
        self.page_size = page_size
