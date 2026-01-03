from fastapi import Request

from lilycloudproto.infra.services.auth_service import AuthService
from lilycloudproto.infra.services.storage_service import StorageService
from lilycloudproto.infra.services.task_service import TaskService


def get_auth_service(request: Request) -> AuthService:
    service = getattr(
        request.app.state,  # pyright: ignore[reportAny]
        "auth_service",
        None,
    )
    if not isinstance(service, AuthService):
        raise RuntimeError("AuthService is not initialized on app.state")
    return service


def get_storage_service(request: Request) -> StorageService:
    service = getattr(
        request.app.state,  # pyright: ignore[reportAny]
        "storage_service",
        None,
    )
    if not isinstance(service, StorageService):
        raise RuntimeError("StorageService is not initialized on app.state")
    return service


def get_task_service(request: Request) -> TaskService:
    service = getattr(
        request.app.state,  # pyright: ignore[reportAny]
        "task_service",
        None,
    )
    if not isinstance(service, TaskService):
        raise RuntimeError("TaskService is not initialized on app.state")
    return service
