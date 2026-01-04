from fastapi import APIRouter, Body, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.database import get_db
from lilycloudproto.domain.values.trash import ListArgs
from lilycloudproto.error import NotFoundError
from lilycloudproto.infra.repositories.trash_repository import TrashRepository
from lilycloudproto.models.files.trash import (
    DeleteCommand,
    RestoreCommand,
    TrashCommand,
    TrashListQuery,
    TrashListResponse,
    TrashResponse,
)
from lilycloudproto.models.task import TaskResponse

router = APIRouter(prefix="/api/files/trash", tags=["Files/Trash"])


@router.post("", response_model=TaskResponse)
async def trash(
    command: TrashCommand,
    # user: User = Depends(get_current_user)
) -> TaskResponse:
    # TODO: Implement logic to create trash task and return TaskResponse
    raise NotImplementedError


@router.get("/{trash_id}", response_model=TrashResponse)
async def get_trash_entry(
    trash_id: int = Path(..., description="Trash entry ID"),
    db: AsyncSession = Depends(get_db),
) -> TrashResponse:
    repo = TrashRepository(db)
    entry = await repo.get_by_id(trash_id)
    if not entry:
        raise NotFoundError(f"Trash entry with ID '{trash_id}' not found.")
    return TrashResponse.model_validate(entry)


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
        items=[TrashResponse.model_validate(e) for e in items],
    )


@router.post("/restore", response_model=TaskResponse)
async def restore(
    command: RestoreCommand,
    # user: User = Depends(get_current_user)
) -> TaskResponse:
    # TODO: Implement logic to create restore task and return TaskResponse
    raise NotImplementedError


@router.delete("", response_model=TaskResponse)
async def delete(
    command: DeleteCommand = Body(...),
    # user: User = Depends(get_current_user)
) -> TaskResponse:
    # TODO: Implement logic to create delete task and return TaskResponse
    raise NotImplementedError
