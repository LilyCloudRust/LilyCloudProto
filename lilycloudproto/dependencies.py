from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.config import auth_settings
from lilycloudproto.domain.entities.user import User
from lilycloudproto.infra.database import get_db
from lilycloudproto.infra.services.auth_service import AuthService
from lilycloudproto.infra.services.storage_service import StorageService
from lilycloudproto.infra.services.task_service import TaskService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    # Create AuthService per request with shared session.
    return AuthService(auth_settings, db)


def get_storage_service(request: Request) -> StorageService:
    service = getattr(
        request.app.state,  # pyright: ignore[reportAny]
        "storage_service",
        None,
    )
    if not isinstance(service, StorageService):
        raise RuntimeError("StorageService is not initialized on app.state.")
    return service


def get_task_service(request: Request) -> TaskService:
    service = getattr(
        request.app.state,  # pyright: ignore[reportAny]
        "task_service",
        None,
    )
    if not isinstance(service, TaskService):
        raise RuntimeError("TaskService is not initialized on app.state.")
    return service


async def get_current_user(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    # Try to get token from cookie first.
    access_token = request.cookies.get("access_token")
    # Fallback to Authorization header if not in cookie.
    if not access_token:
        access_token = token
    return await service.get_user_from_token(access_token)
