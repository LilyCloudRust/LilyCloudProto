from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.database import get_db
from lilycloudproto.error import NotFoundError
from lilycloudproto.infra.task_repository import TaskRepository
from lilycloudproto.models.task import TaskListResponse, TaskResponse, TaskUpdate

router = APIRouter(prefix="/api/admin/tasks", tags=["Admin"])


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> TaskListResponse:
    """List all tasks."""
    repo = TaskRepository(db)
    tasks = await repo.get_all(page=page, page_size=page_size)
    total_count = await repo.count()
    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in tasks],
        total_count=total_count,
    )


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Update task status or progress."""
    repo = TaskRepository(db)
    task = await repo.get_by_id(task_id)
    if not task:
        raise NotFoundError(f"Task with ID '{task_id}' not found.")

    if data.status is not None:
        task.status = data.status
    if data.progress is not None:
        task.progress = data.progress
    if data.message is not None:
        task.message = data.message

    updated = await repo.update(task)
    return TaskResponse.model_validate(updated)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a task by ID."""
    repo = TaskRepository(db)
    task = await repo.get_by_id(task_id)
    if not task:
        raise NotFoundError(f"Task with ID '{task_id}' not found.")
    await repo.delete(task)
