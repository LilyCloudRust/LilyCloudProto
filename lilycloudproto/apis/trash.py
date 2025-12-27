from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.apis.auth import get_current_user
from lilycloudproto.database import get_db
from lilycloudproto.domain.entities.user import User
from lilycloudproto.domain.values.task import TaskType
from lilycloudproto.error import BadRequestError, NotFoundError
from lilycloudproto.infra.repositories.trash_repository import TrashRepository
from lilycloudproto.infra.services.storage_service import StorageService
from lilycloudproto.infra.services.task_service import TaskService
from lilycloudproto.models.task import TaskResponse
from lilycloudproto.models.trash import (
    DeleteTrashRequest,
    RestoreRequest,
    TrashEntry,
    TrashListQuery,
    TrashRequest,
    TrashResponse,
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
async def move_to_trash(
    request: TrashRequest,
    user: Annotated[User, Depends(get_current_user)],
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Move files to trash."""
    task = await task_service.add_task(
        user_id=user.user_id,
        type=TaskType.TRASH,
        src_dir=request.dir,
        dst_dirs=[],
        file_names=request.file_names,
    )
    return TaskResponse.model_validate(task)


@router.post("/restore", response_model=TaskResponse)
async def restore_from_trash(
    request: RestoreRequest,
    user: Annotated[User, Depends(get_current_user)],
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Restore files from trash."""
    task = await task_service.add_task(
        user_id=user.user_id,
        type=TaskType.RESTORE,
        src_dir=request.dir,
        dst_dirs=[],
        file_names=request.file_names,
    )
    return TaskResponse.model_validate(task)


@router.delete("", response_model=TaskResponse)
async def delete_permanently(
    request: DeleteTrashRequest,
    user: Annotated[User, Depends(get_current_user)],
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Delete files permanently from trash or empty trash."""
    # Validate mutual exclusivity
    has_empty = request.empty
    has_ids = len(request.trash_ids) > 0
    has_path = len(request.file_names) > 0  # dir is optional, only file_names required

    if (int(has_empty) + int(has_ids) + int(has_path)) > 1:
        raise BadRequestError(
            "Only one of 'empty', 'trash_ids', or 'file_names' can be provided."
        )

    src_dir = ""
    dst_dirs = []
    file_names = []

    if request.empty:
        src_dir = "__TRASH_EMPTY__"
    elif request.trash_ids:
        src_dir = "__TRASH_IDS__"
        file_names = [str(tid) for tid in request.trash_ids]
    elif has_path:
        # dir is optional - if provided, use it; if None, search all entries
        src_dir = request.dir if request.dir else ""
        file_names = request.file_names
        dst_dirs = ["__TRASH__"]  # Marker for delete by path in trash

    task = await task_service.add_task(
        user_id=user.user_id,
        type=TaskType.DELETE,
        src_dir=src_dir,
        dst_dirs=dst_dirs,
        file_names=file_names,
    )
    return TaskResponse.model_validate(task)


@router.get("", response_model=TrashResponse)
async def list_trash(
    user: Annotated[User, Depends(get_current_user)],
    query: TrashListQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
) -> TrashResponse:
    """List files in trash."""
    repo = TrashRepository(db, storage_service)

    # Security: Only show current user's trash
    items, total = await repo.search(query, user_id=user.user_id)

    return TrashResponse(
        path=query.path,
        items=items,
        total=total,
    )


@router.get("/{trash_id}", response_model=TrashEntry)
async def get_trash_entry(
    trash_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
) -> TrashEntry:
    """Get trash entry details."""
    repo = TrashRepository(db, storage_service)
    item = await repo.get_item_by_id(trash_id)

    if not item:
        raise NotFoundError(f"Trash entry {trash_id} not found.")

    if item.user_id != user.user_id:
        # Assuming users can only see their own trash
        raise NotFoundError(f"Trash entry {trash_id} not found.")

    return item
