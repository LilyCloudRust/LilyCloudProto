from fastapi import APIRouter, Depends

from lilycloudproto.apis.webdav import get_current_user
from lilycloudproto.dependencies import get_auth_service
from lilycloudproto.domain.entities.user import User
from lilycloudproto.infra.services.auth_service import AuthService
from lilycloudproto.models.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
)
from lilycloudproto.models.user import UserResponse

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse)
async def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    user = await service.register_user(payload.username, payload.password)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    access_token, refresh_token = await service.authenticate_user(
        payload.username, payload.password
    )
    return LoginResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    payload: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> RefreshResponse:
    refreshed_token = await service.refresh_access_token(payload.refresh_token)
    return RefreshResponse(access_token=refreshed_token)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    current_user: User = Depends(get_current_user),
) -> LogoutResponse:
    return LogoutResponse(message="Logout successful")


@router.get("/whoami", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)
