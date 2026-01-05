from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from lilycloudproto.config import auth_settings
from lilycloudproto.dependencies import (
    get_auth_service,
    get_current_user,
    oauth2_scheme,
)
from lilycloudproto.domain.entities.user import User
from lilycloudproto.infra.services.auth_service import AuthService
from lilycloudproto.models.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshResponse,
    RegisterRequest,
    UserAuthResponse,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=UserAuthResponse)
async def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> UserAuthResponse:
    user = await service.register(payload.username, payload.password)
    return UserAuthResponse.model_validate(user)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    access_token, refresh_token = await service.authenticate(
        payload.username, payload.password
    )

    # Set access token cookie for all endpoints that need auth.
    response.set_cookie(
        key="access_token",
        value=access_token,
        secure=True,
        httponly=True,
        samesite="lax",
        path="/",  # Send for all paths.
        max_age=auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    # Set refresh token cookie only for refresh endpoint.
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        secure=True,
        httponly=True,
        samesite="lax",
        path="/api/auth",  # Only send for refresh endpoint.
        max_age=auth_settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return LoginResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    token: Annotated[str, Depends(oauth2_scheme)],
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> RefreshResponse:
    # Try to get refresh_token from cookie first.
    refresh_token = request.cookies.get("refresh_token")
    # Fallback to Authorization header if not in cookie.
    if not refresh_token:
        refresh_token = token
    refreshed_token = await service.refresh(refresh_token)

    response.set_cookie(
        key="access_token",
        value=refreshed_token,
        secure=True,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return RefreshResponse(access_token=refreshed_token)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> LogoutResponse:
    # Remove the access token cookie.
    response.delete_cookie(
        key="access_token",
        path="/",
    )
    # Remove the refresh token cookie.
    response.delete_cookie(
        key="refresh_token",
        path="/api/auth/refresh",
    )

    # Delete the tokens from database.
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await auth_service.delete(refresh_token)
    access_token = request.cookies.get("access_token")
    if access_token:
        await auth_service.delete(access_token)

    return LogoutResponse(message="Logout successful")


@router.get("/whoami", response_model=UserAuthResponse)
async def whoami(
    current_user: User = Depends(get_current_user),
) -> UserAuthResponse:
    return UserAuthResponse.model_validate(current_user)
