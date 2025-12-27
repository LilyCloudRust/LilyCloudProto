from typing import Annotated

from fastapi import APIRouter, Depends, Request

from lilycloudproto.apis.auth import get_current_user
from lilycloudproto.domain.entities.task import Task
from lilycloudproto.domain.entities.user import User
from lilycloudproto.domain.values.task import TaskType
from lilycloudproto.error import BadRequestError
from lilycloudproto.infra.services.storage_service import StorageService
from lilycloudproto.infra.services.task_service import TaskService
from lilycloudproto.models.task import TaskResponse
from lilycloudproto.models.trash import (
    TrashRequest,
)

router = APIRouter(prefix="/api/files/trash", tags=["Trash"])


def get_task_service(request: Request) -> TaskService:
    service = getattr(
        request.app.state,  # pyright: ignore[reportAny]
        "task_service",
        None,
    )
    if not isinstance(service, TaskService):
        raise RuntimeError("TaskService is not initialized on app.state")
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


@router.post("", response_model=TaskResponse)
async def trash_files(
    request: TrashRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    task_service: Annotated[TaskService, Depends(get_task_service)],
) -> Task:
    """
    Move files to trash.

    Creates an asynchronous task to move files to the trash directory
    while preserving directory structure.
    """
    if not request.file_names:
        raise BadRequestError("file_names cannot be empty.")

    task = await task_service.add_task(
        user_id=current_user.user_id,
        type=TaskType.TRASH,
        src_dir=request.dir,
        dst_dirs=[],
        file_names=request.file_names,
    )
    return task
