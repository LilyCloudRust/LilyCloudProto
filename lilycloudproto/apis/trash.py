from fastapi import APIRouter, Body, Path

from lilycloudproto.models.files.trash import (
    DeleteCommand,
    RestoreCommand,
    TrashCommand,
    TrashListQuery,
    TrashListResponse,
    TrashResponse,
)
from lilycloudproto.models.task import TaskResponse

router = APIRouter(prefix="/api/files/trash", tags=["files/trash"])


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
    # user: User = Depends(get_current_user)
) -> TrashResponse:
    # TODO: Implement logic to fetch trash entry by ID
    raise NotImplementedError


@router.get("", response_model=TrashListResponse)
async def list_trash_entries(
    query: TrashListQuery,
    # user: User = Depends(get_current_user)
) -> TrashListResponse:
    # TODO: Implement logic to list trash entries
    raise NotImplementedError


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
