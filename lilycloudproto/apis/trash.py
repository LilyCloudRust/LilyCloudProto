import os
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.apis.auth import get_current_user
from lilycloudproto.database import get_db
from lilycloudproto.domain.entities.task import Task
from lilycloudproto.domain.entities.trash import Trash
from lilycloudproto.domain.entities.user import User
from lilycloudproto.domain.values.files.file import File
from lilycloudproto.domain.values.task import TaskType
from lilycloudproto.domain.values.trash import TrashSortBy, TrashSortOrder
from lilycloudproto.error import BadRequestError, ConflictError, NotFoundError
from lilycloudproto.infra.repositories.trash_repository import TrashRepository
from lilycloudproto.infra.services.storage_service import StorageService
from lilycloudproto.infra.services.task_service import TaskService
from lilycloudproto.models.task import TaskResponse
from lilycloudproto.models.trash import (
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


@router.post("/restore", response_model=TaskResponse)
async def restore_files(
    request: RestoreRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    task_service: Annotated[TaskService, Depends(get_task_service)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Task:
    if not request.file_names:
        raise BadRequestError("file_names cannot be empty.")

    dir_prefix = request.dir or ""
    repo = TrashRepository(db)
    records = await repo.find_by_user_and_path(
        current_user.user_id, dir_prefix, request.file_names
    )
    if len(records) != len(request.file_names):
        raise NotFoundError("Trash entry not found.")

    trash_root = storage_service.get_trash_root(dir_prefix)
    for record in records:
        fs_path = _ensure_inside_trash(trash_root, record.entry_name)
        if not os.path.exists(fs_path):
            raise NotFoundError("Trash entry not found.")
        if os.path.exists(record.original_path):
            raise ConflictError("Original path already exists.")

    task = await task_service.add_task(
        user_id=current_user.user_id,
        type=TaskType.RESTORE,
        src_dir=request.dir,
        dst_dirs=[],
        file_names=request.file_names,
    )
    return task


def _ensure_inside_trash(trash_root: str, entry_name: str) -> str:
    """Join trash_root and entry_name ensuring the path stays within trash_root."""
    normalized_root = os.path.normpath(trash_root)
    candidate = os.path.normpath(os.path.join(normalized_root, entry_name))
    if os.path.commonpath([normalized_root, candidate]) != normalized_root:
        raise BadRequestError("Invalid entry path.")
    return candidate


def _trash_entry_from_record(
    record: Trash,
    file_info: File,
) -> TrashEntry:
    return TrashEntry(
        trash_id=record.trash_id,
        user_id=record.user_id,
        entry_name=record.entry_name,
        original_path=record.original_path,
        type=file_info.type.value,
        size=file_info.size,
        mime_type=file_info.mime_type,
        deleted_at=record.deleted_at,
        created_at=file_info.created_at,
        modified_at=file_info.modified_at,
        accessed_at=file_info.accessed_at,
    )


def _matches_path(entry_name: str, query: TrashListQuery) -> bool:
    target = (query.path or "").lstrip("/")
    normalized_entry = entry_name
    if not target:
        return True
    if query.recursive:
        return normalized_entry == target or normalized_entry.startswith(target + "/")
    parent = os.path.dirname(normalized_entry)
    return parent == target


def _matches_filters(entry: TrashEntry, query: TrashListQuery) -> bool:
    if query.keyword and query.keyword.lower() not in entry.entry_name.lower():
        return False
    if query.type and entry.type != query.type:
        return False
    return not (
        query.mime_type
        and entry.mime_type
        and query.mime_type.lower() not in entry.mime_type.lower()
    )


KeyFunc = Callable[[TrashEntry], Any]


def _sort_entries(entries: list[TrashEntry], query: TrashListQuery) -> list[TrashEntry]:
    sort_key_map: dict[TrashSortBy, KeyFunc] = {
        TrashSortBy.NAME: lambda e: os.path.basename(e.entry_name),
        TrashSortBy.PATH: lambda e: e.entry_name,
        TrashSortBy.SIZE: lambda e: e.size,
        TrashSortBy.DELETED: lambda e: e.deleted_at,
        TrashSortBy.CREATED: lambda e: e.created_at or e.deleted_at,
        TrashSortBy.MODIFIED: lambda e: e.modified_at or e.deleted_at,
        TrashSortBy.ACCESSED: lambda e: e.accessed_at or e.deleted_at,
        TrashSortBy.TYPE: lambda e: e.type,
    }
    key_func = sort_key_map[query.sort_by]
    reverse = query.sort_order == TrashSortOrder.DESC
    sorted_entries = sorted(entries, key=key_func, reverse=reverse)
    if query.dir_first:
        sorted_entries = sorted(sorted_entries, key=lambda e: e.type == "file")
    return sorted_entries


@router.get("/{trash_id}", response_model=TrashEntry)
async def get_trash_entry(
    trash_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrashEntry:
    repo = TrashRepository(db)
    record = await repo.get_by_id(trash_id)
    if record is None or record.user_id != current_user.user_id:
        raise NotFoundError("Trash entry not found.")

    trash_root = storage_service.get_trash_root(record.original_path)
    fs_path = _ensure_inside_trash(trash_root, record.entry_name)
    driver = storage_service.get_driver(trash_root)
    file_info = driver.info(fs_path)
    return _trash_entry_from_record(record, file_info)


@router.get("", response_model=TrashResponse)
async def list_trash_entries(
    query: Annotated[TrashListQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrashResponse:
    repo = TrashRepository(db)
    records = await repo.list_by_user(current_user.user_id)
    trash_root = storage_service.get_trash_root("")
    driver = storage_service.get_driver(trash_root)

    entries: list[TrashEntry] = []
    for record in records:
        fs_path = _ensure_inside_trash(trash_root, record.entry_name)
        if not os.path.exists(fs_path):
            continue
        try:
            file_info = driver.info(fs_path)
        except NotFoundError:
            continue

        candidate = _trash_entry_from_record(record, file_info)
        if not _matches_path(candidate.entry_name, query):
            continue
        if not _matches_filters(candidate, query):
            continue
        entries.append(candidate)

    sorted_entries = _sort_entries(entries, query)
    total = len(sorted_entries)
    start = (query.page - 1) * query.page_size
    end = start + query.page_size
    paged = sorted_entries[start:end]

    return TrashResponse(path=query.path, total=total, items=paged)
