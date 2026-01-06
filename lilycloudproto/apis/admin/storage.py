from fastapi import APIRouter, Depends, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.dependencies import get_storage_service
from lilycloudproto.domain.entities.storage import Storage
from lilycloudproto.domain.values.admin.storage import ListArgs, validate_config
from lilycloudproto.error import ConflictError, NotFoundError, UnprocessableEntityError
from lilycloudproto.infra.database import get_db
from lilycloudproto.infra.repositories.storage_repository import StorageRepository
from lilycloudproto.infra.services.storage_service import StorageService
from lilycloudproto.models.admin.storage import (
    MessageResponse,
    StorageCreate,
    StorageListQuery,
    StorageListResponse,
    StorageResponse,
    StorageUpdate,
)

router = APIRouter(prefix="/api/admin/storages", tags=["Admin/Storages"])


@router.post("", response_model=StorageResponse, status_code=status.HTTP_201_CREATED)
async def create_storage(
    data: StorageCreate,
    db: AsyncSession = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
) -> StorageResponse:
    """Create a new storage configuration."""
    # Validate the configuration based on the storage type.
    try:
        config = validate_config(data.type, data.config)
    except ValidationError as error:
        raise UnprocessableEntityError(
            f"Invalid configuration for type '{data.type}': {error}"
        ) from error

    repo = StorageRepository(db)
    storage = Storage(
        mount_path=data.mount_path,
        type=data.type,
        config=config,
        enabled=data.enabled,
    )
    try:
        created = await repo.create(storage)
        storage_service.update_cache(created)
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
    query: StorageListQuery = Depends(),
    db: AsyncSession = Depends(get_db),
) -> StorageListResponse:
    """List all storage configurations."""
    repo = StorageRepository(db)
    args = ListArgs(
        keyword=query.keyword,
        type=query.type,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        enabled_first=query.enabled_first,
        page=query.page,
        page_size=query.page_size,
    )

    storages = await repo.search(args)
    total = await repo.count(args)

    return StorageListResponse(
        items=[StorageResponse.model_validate(storage) for storage in storages],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


@router.patch("/{storage_id}", response_model=StorageResponse)
async def update_storage(
    storage_id: int,
    data: StorageUpdate,
    db: AsyncSession = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
) -> StorageResponse:
    """Update storage configuration."""
    repo = StorageRepository(db)
    storage = await repo.get_by_id(storage_id)
    if not storage:
        raise NotFoundError(f"Storage with ID '{storage_id}' not found.")
    old_mount_path = storage.mount_path

    # Validate new state.
    type = data.type if data.type is not None else storage.type
    config = data.config if data.config is not None else storage.config
    try:
        config = validate_config(type, config)
    except ValidationError as error:
        raise UnprocessableEntityError(
            f"Invalid configuration for type '{type}': {error}"
        ) from error

    # Apply updates.
    if data.mount_path is not None:
        storage.mount_path = data.mount_path
    storage.type = type
    storage.config = config
    if data.enabled is not None:
        storage.enabled = data.enabled

    updated = await repo.update(storage)

    if old_mount_path != updated.mount_path:
        storage_service.remove_from_cache(old_mount_path)
    storage_service.update_cache(updated)

    return StorageResponse.model_validate(updated)


@router.delete("/{storage_id}", response_model=MessageResponse)
async def delete_storage(
    storage_id: int,
    db: AsyncSession = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
) -> MessageResponse:
    """Delete a storage configuration."""
    repo = StorageRepository(db)
    storage = await repo.get_by_id(storage_id)
    if not storage:
        raise NotFoundError(f"Storage with ID '{storage_id}' not found.")
    await repo.delete(storage)
    storage_service.remove_from_cache(storage.mount_path)  # <--- Update Cache
    return MessageResponse(message="Storage deleted successfully.")
