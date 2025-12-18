import mimetypes
import os
from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.apis.auth import get_current_user
from lilycloudproto.database import get_db
from lilycloudproto.domain.entities.user import User
from lilycloudproto.domain.values.task import TaskType
from lilycloudproto.error import NotFoundError
from lilycloudproto.infra.repositories.trash_repository import TrashRepository
from lilycloudproto.infra.services.storage_service import StorageService
from lilycloudproto.infra.services.task_service import TaskService
from lilycloudproto.models.task import TaskResponse
from lilycloudproto.models.trash import (
    DeleteTrashRequest,
    RestoreRequest,
    TrashItem,
    TrashListQuery,
    TrashRequest,
    TrashResponse,
)

router = APIRouter(prefix="/api/files/trash", tags=["Trash"])


def get_task_service(request: Request) -> TaskService:
    return cast(TaskService, request.app.state.task_service)


def get_storage_service(request: Request) -> StorageService:
    return cast(StorageService, request.app.state.storage_service)


@router.post("", response_model=TaskResponse)
async def move_to_trash(
    request: TrashRequest,
    user: Annotated[User, Depends(get_current_user)],
    task_service: Annotated[TaskService, Depends(get_task_service)],
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
    task_service: Annotated[TaskService, Depends(get_task_service)],
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
    task_service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskResponse:
    """Delete files permanently from trash or empty trash."""
    src_dir = ""
    dst_dirs = []
    file_names = []

    if request.empty:
        src_dir = "__TRASH_EMPTY__"
    elif request.trash_ids:
        src_dir = "__TRASH_IDS__"
        file_names = [str(tid) for tid in request.trash_ids]
    elif request.dir and request.file_names:
        src_dir = request.dir
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
    db: Annotated[AsyncSession, Depends(get_db)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    query: Annotated[TrashListQuery, Depends()],
) -> TrashResponse:
    """List files in trash."""
    repo = TrashRepository(db, storage_service.get_trash_root())

    items, total = await repo.search(query)

    return TrashResponse(
        path=query.path,
        items=items,
        total=total,
    )


@router.get("/{trash_id}", response_model=TrashItem)
async def get_trash_entry(
    trash_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
) -> TrashItem:
    """Get trash entry details."""
    repo = TrashRepository(db, storage_service.get_trash_root())
    entry = await repo.get_by_id(trash_id)

    if not entry:
        raise NotFoundError(f"Trash entry {trash_id} not found.")

    if entry.user_id != user.user_id:
        # Assuming users can only see their own trash
        raise NotFoundError(f"Trash entry {trash_id} not found.")

    # We need to construct TrashItem which includes FS info (size, type, etc.)
    # The repo.search does this logic, but get_by_id only returns the DB entity.
    # We should probably expose a method in repo to get the full item or do it here.
    # Since repo.search logic is complex (hybrid), let's reuse a similar logic here or
    # add a helper in repo.
    # For now, I will implement the FS lookup here to match the response model.

    trash_path = os.path.join(repo.trash_root, str(entry.trash_id))

    item_type = "unknown"
    size = 0
    mime_type = None
    created_at = None
    modified_at = None
    accessed_at = None

    if os.path.exists(trash_path):
        stat = os.stat(trash_path)
        size = stat.st_size
        created_at = datetime.fromtimestamp(stat.st_ctime)
        modified_at = datetime.fromtimestamp(stat.st_mtime)
        accessed_at = datetime.fromtimestamp(stat.st_atime)

        if os.path.isdir(trash_path):
            item_type = "directory"
        else:
            item_type = "file"
            mime_type, _ = mimetypes.guess_type(entry.entry_name)

    return TrashItem(
        trash_id=entry.trash_id,
        user_id=entry.user_id,
        entry_name=entry.entry_name,
        original_path=entry.original_path,
        type=item_type,
        size=size,
        mime_type=mime_type,
        deleted_at=entry.deleted_at,
        created_at=created_at,
        modified_at=modified_at,
        accessed_at=accessed_at,
    )
