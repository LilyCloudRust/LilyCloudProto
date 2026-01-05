from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.dependencies import get_current_user
from lilycloudproto.domain.entities.task import Task
from lilycloudproto.domain.entities.user import User
from lilycloudproto.domain.values.admin.task import ListArgs
from lilycloudproto.error import NotFoundError
from lilycloudproto.infra.database import get_db
from lilycloudproto.infra.repositories.task_repository import TaskRepository
from lilycloudproto.models.admin.task import (
    MessageResponse,
    TaskCreate,
    TaskListQuery,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)

router = APIRouter(prefix="/api/admin/tasks", tags=["Admin/Tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Create a new task manually."""
    repo = TaskRepository(db)
    task = Task(
        user_id=current_user.user_id,
        type=data.type,
        src_dir=data.src_dir,
        dst_dirs=data.dst_dirs,
        file_names=data.file_names,
        status=data.status,
        progress=data.progress,
        message=data.message,
    )
    created = await repo.create(task)
    return TaskResponse.model_validate(created)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    params: TaskListQuery = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TaskListResponse:
    """List all tasks."""
    repo = TaskRepository(db)
    args = ListArgs(
        keyword=params.keyword,
        user_id=params.user_id,
        type=params.type,
        status=params.status,
        sort_by=params.sort_by,
        sort_order=params.sort_order,
        page=params.page,
        page_size=params.page_size,
    )
    tasks = await repo.search(args)
    total = await repo.count(args)
    return TaskListResponse(
        items=[TaskResponse.model_validate(task) for task in tasks],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Update task details."""
    repo = TaskRepository(db)
    task = await repo.get_by_id(task_id)
    if not task:
        raise NotFoundError(f"Task with ID '{task_id}' not found.")

    if data.user_id is not None:
        task.user_id = data.user_id
    if data.type is not None:
        task.type = data.type
    if data.src_dir is not None:
        task.src_dir = data.src_dir
    if data.dst_dirs is not None:
        task.dst_dirs = data.dst_dirs
    if data.file_names is not None:
        task.file_names = data.file_names
    if data.status is not None:
        task.status = data.status
    if data.progress is not None:
        task.progress = data.progress
    if data.message is not None:
        task.message = data.message
    if data.started_at is not None:
        task.started_at = data.started_at
    if data.completed_at is not None:
        task.completed_at = data.completed_at

    updated = await repo.update(task)
    return TaskResponse.model_validate(updated)


@router.delete("/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Delete a task by ID."""
    repo = TaskRepository(db)
    task = await repo.get_by_id(task_id)
    if not task:
        raise NotFoundError(f"Task with ID '{task_id}' not found.")
    await repo.delete(task)
    return MessageResponse(message="Task deleted successfully.")
