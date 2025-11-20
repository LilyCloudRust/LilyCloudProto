from typing import ClassVar

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

    model_config: ClassVar[ConfigDict] = {"from_attributes": True}
