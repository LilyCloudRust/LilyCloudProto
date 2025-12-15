from fastapi import APIRouter, Depends, Query, Request

from lilycloudproto.domain.entities.task import Task
from lilycloudproto.domain.values.files.file import File
from lilycloudproto.domain.values.files.list import ListArgs
from lilycloudproto.domain.values.files.search import (
    SearchArgs,
)
from lilycloudproto.domain.values.task import TaskType
from lilycloudproto.infra.services.storage_service import StorageService
from lilycloudproto.infra.services.task_service import TaskService
from lilycloudproto.models.files.command import CopyCommand, DeleteCommand, MoveCommand
from lilycloudproto.models.files.list import ListQuery, ListResponse
from lilycloudproto.models.files.search import SearchQuery, SearchResponse
from lilycloudproto.models.task import TaskResponse

router = APIRouter(prefix="/api/files", tags=["Files"])


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


@router.get("/list", response_model=ListResponse)
def list_files(
    query: ListQuery = Depends(), service: StorageService = Depends(get_storage_service)
) -> ListResponse:
    args = ListArgs(
        path=query.path,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        dir_first=query.dir_first,
    )
    driver = service.get_driver(query.path)
    files = driver.list_dir(args)
    return ListResponse(path=query.path, total=len(files), items=files)


@router.get("/info", response_model=File)
def info(
    path: str = Query(),
    service: StorageService = Depends(get_storage_service),
) -> File:
    driver = service.get_driver(path)
    file = driver.info(path)
    return file


@router.get("/search", response_model=SearchResponse)
def search_files(
    query: SearchQuery = Depends(),
    service: StorageService = Depends(get_storage_service),
) -> SearchResponse:
    args = SearchArgs(
        keyword=query.keyword,
        path=query.path,
        recursive=query.recursive,
        type=query.type,
        mime_type=query.mime_type,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        dir_first=query.dir_first,
    )
    driver = service.get_driver(query.path)
    files = driver.search(args)
    return SearchResponse(path=query.path, total=len(files), items=files)


@router.post("/directory", response_model=File)
def mkdir(
    path: str = Query(..., embed=True, description="Directory path"),
    parents: bool = Query(
        False, embed=True, description="Create parent directories if missing"
    ),
    service: StorageService = Depends(get_storage_service),
) -> File:
    driver = service.get_driver(path)
    return driver.mkdir(path, parents)


@router.post("/copy", response_model=TaskResponse)
async def copy(
    command: CopyCommand = Depends(),
    task_service: TaskService = Depends(get_task_service),
) -> Task:
    task = await task_service.add_task(
        user_id=0,
        type=TaskType.COPY,
        src_dir=command.src_dir,
        dst_dirs=[command.dst_dir],
        file_names=command.file_names,
    )
    return task


@router.post("/move", response_model=TaskResponse)
async def move(
    command: MoveCommand = Depends(),
    task_service: TaskService = Depends(get_task_service),
) -> Task:
    task = await task_service.add_task(
        user_id=0,
        type=TaskType.MOVE,
        src_dir=command.src_dir,
        dst_dirs=[command.dst_dir],
        file_names=command.file_names,
    )
    return task


@router.delete("", response_model=TaskResponse)
async def delete(
    command: DeleteCommand = Depends(),
    task_service: TaskService = Depends(get_task_service),
) -> Task:
    task = await task_service.add_task(
        user_id=0,
        type=TaskType.DELETE,
        src_dir=command.dir,
        dst_dirs=[],
        file_names=command.file_names,
    )
    return task
