from fastapi import APIRouter, Body, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.dependencies import get_current_user, get_task_service
from lilycloudproto.domain.entities.user import User
from lilycloudproto.domain.values.admin.task import TaskType
from lilycloudproto.domain.values.admin.user import Role
from lilycloudproto.domain.values.trash import ListArgs
from lilycloudproto.error import NotFoundError
from lilycloudproto.infra.database import get_db
from lilycloudproto.infra.repositories.trash_repository import TrashRepository
from lilycloudproto.infra.services.task_service import TaskService
from lilycloudproto.models.admin.task import TaskResponse
from lilycloudproto.models.files.trash import (
    DeleteCommand,
    RestoreCommand,
    TrashCommand,
    TrashListQuery,
    TrashListResponse,
    TrashResponse,
)

router = APIRouter(prefix="/api/files/trash", tags=["Files/Trash"])


@router.post("", response_model=TaskResponse)
async def trash(
    command: TrashCommand,
    user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    task = await task_service.add_task(
        user_id=user.user_id,
        type=TaskType.TRASH,
        src_dir=command.dir,
        dst_dirs=[],
        file_names=command.file_names,
    )
    return TaskResponse.model_validate(task)


@router.get("/{trash_id}", response_model=TrashResponse)
async def get_trash_entry(
    trash_id: int = Path(..., description="Trash entry ID"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrashResponse:
    repo = TrashRepository(db)
    trash_entry = await repo.get_by_id(trash_id)
    if not trash_entry:
        raise NotFoundError(f"Trash entry with ID '{trash_id}' not found.")
    if user.role != Role.ADMIN and trash_entry.user_id != user.user_id:
        raise NotFoundError(f"Trash entry with ID '{trash_id}' not found.")
    return TrashResponse.model_validate(trash_entry)


@router.get("", response_model=TrashListResponse)
async def list_trash_entries(
    query: TrashListQuery = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TrashListResponse:
    repo = TrashRepository(db)

    args = ListArgs(
        keyword=query.keyword,
        user_id=query.user_id,
        type=query.type,
        mime_type=query.mime_type,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        dir_first=query.dir_first,
    )
    items = await repo.search(args)
    total = await repo.count(args)
    return TrashListResponse(
        total=total,
        items=[TrashResponse.model_validate(trash_entry) for trash_entry in items],
    )


@router.post("/restore", response_model=TaskResponse)
async def restore(
    command: RestoreCommand,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    repo = TrashRepository(db)

    delete_entry = False
    if command.dir == "/":
        # If restoring from root trash directory, delete the trash entry after restore.
        delete_entry = True
        entry_names = command.file_names
        trash_entries = await repo.get_by_entry_names(entry_names, user.user_id)
        if len(trash_entries) != len(entry_names):
            raise NotFoundError("One or more trash entries not found.")
        src_dir = "/"  # logical trash root.
        dst_dirs = [entry.original_path.rsplit("/", 1)[0] for entry in trash_entries]
        file_names = [entry.entry_name for entry in trash_entries]
    else:
        # Restore files in a single trash directory.
        entry_name = command.dir.strip("/").split("/")[0]
        trash_entry = await repo.get_by_entry_name(entry_name, user.user_id)
        if not trash_entry:
            raise NotFoundError(f"Trash entry for '{entry_name}' not found.")
        src_dir = command.dir
        suffix = command.dir[len("/" + entry_name) + 1 :] or ""
        dst_dirs = [f"{trash_entry.original_path}/{suffix}"]
        file_names = command.file_names
        trash_entries = [trash_entry]

    # Create restore task for the worker.
    task = await task_service.add_task(
        user_id=user.user_id,
        type=TaskType.RESTORE,
        src_dir=src_dir,
        dst_dirs=dst_dirs,
        file_names=file_names,
        db=db,
    )

    # Optionally delete trash entries after restore.
    if delete_entry:
        for trash_entry in trash_entries:
            await repo.delete(trash_entry)

    return TaskResponse.model_validate(task)


@router.delete("", response_model=TaskResponse)
async def delete(
    command: DeleteCommand = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    repo = TrashRepository(db)
    user_id = user.user_id

    if command.empty:
        # Get all trash entries for the user.
        trash_entries = await repo.get_by_user_id(user.user_id)
        if not trash_entries:
            raise NotFoundError("Trash is already empty.")
        file_names = [entry.entry_name for entry in trash_entries]
        src_dir = "/"  # Logical trash root

        # Create delete task.
        task = await task_service.add_task(
            user_id=user_id,
            type=TaskType.DELETE,
            src_dir=src_dir,
            dst_dirs=[],
            file_names=file_names,
            db=db,
        )

        # Clear trash entries table for the user.
        for entry in trash_entries:
            await repo.delete(entry)

        return TaskResponse.model_validate(task)

    raise NotImplementedError
