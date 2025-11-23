from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.database import get_db
from lilycloudproto.entities.storage import Storage
from lilycloudproto.error import ConflictError, NotFoundError
from lilycloudproto.infra.storage_repository import StorageRepository
from lilycloudproto.models.storage import (
    StorageCreate,
    StorageListResponse,
    StorageQueryParams,
    StorageResponse,
    StorageUpdate,
)

router = APIRouter(prefix="/api/admin/storages", tags=["Admin"])


@router.post("", response_model=StorageResponse, status_code=status.HTTP_201_CREATED)
async def create_storage(
    data: StorageCreate,
    db: AsyncSession = Depends(get_db),
) -> StorageResponse:
    """Create a new storage configuration."""
    repo = StorageRepository(db)
    storage = Storage(
        mount_path=data.mount_path,
        type=data.type,
        config=data.config,
        enabled=data.enabled,
    )
    try:
        created = await repo.create(storage)
    except IntegrityError as error:
        raise ConflictError(
            f"Storage with mount path '{data.mount_path}' already exists."
        ) from error
    return StorageResponse.model_validate(created)


@router.get("/{storage_id}", response_model=StorageResponse)
async def get_storage(
    storage_id: int,
    db: AsyncSession = Depends(get_db),
) -> StorageResponse:
    """Get storage details by ID."""
    repo = StorageRepository(db)
    storage = await repo.get_by_id(storage_id)
    if not storage:
        raise NotFoundError(f"Storage with ID '{storage_id}' not found.")
    return StorageResponse.model_validate(storage)


@router.get("", response_model=StorageListResponse)
async def list_storages(
    params: StorageQueryParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> StorageListResponse:
    """List all storage configurations."""
    repo = StorageRepository(db)
    storages, total_count = await repo.search(
        keyword=params.keyword,
        type=params.type,
        enabled_first=params.enabled_first,
        page=params.page,
        page_size=params.page_size,
    )
    return StorageListResponse(
        items=[StorageResponse.model_validate(s) for s in storages],
        total_count=total_count,
    )


@router.patch("/{storage_id}", response_model=StorageResponse)
async def update_storage(
    storage_id: int,
    data: StorageUpdate,
    db: AsyncSession = Depends(get_db),
) -> StorageResponse:
    """Update storage configuration."""
    repo = StorageRepository(db)
    storage = await repo.get_by_id(storage_id)
    if not storage:
        raise NotFoundError(f"Storage with ID '{storage_id}' not found.")

    if data.mount_path is not None:
        storage.mount_path = data.mount_path
    if data.type is not None:
        storage.type = data.type
    if data.config is not None:
        storage.config = data.config
    if data.enabled is not None:
        storage.enabled = data.enabled

    try:
        updated = await repo.update(storage)
    except IntegrityError as error:
        raise ConflictError(
            f"Storage with mount path '{data.mount_path}' already exists."
        ) from error
    return StorageResponse.model_validate(updated)


@router.delete("/{storage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_storage(
    storage_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a storage configuration."""
    repo = StorageRepository(db)
    storage = await repo.get_by_id(storage_id)
    if not storage:
        raise NotFoundError(f"Storage with ID '{storage_id}' not found.")
    await repo.delete(storage)
