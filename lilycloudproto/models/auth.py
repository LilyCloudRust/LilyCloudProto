from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class UserAuthResponse(BaseModel):
    user_id: int
    username: str

    model_config: ClassVar[ConfigDict] = {"from_attributes": True}


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshResponse(BaseModel):
    access_token: str


class LogoutResponse(BaseModel):
    message: str
