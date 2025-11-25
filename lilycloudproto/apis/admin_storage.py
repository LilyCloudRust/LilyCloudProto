from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.database import get_db
from lilycloudproto.entities.storage import Storage
from lilycloudproto.error import ConflictError, NotFoundError, UnprocessableEntityError
from lilycloudproto.infra.storage_repository import StorageRepository
from lilycloudproto.models.storage import (
    STORAGE_CONFIG_MAP,
    StorageCreate,
    StorageListResponse,
    StorageQueryParams,
    StorageResponse,
    StorageUpdate,
)

router = APIRouter(prefix="/api/admin/storages", tags=["Admin"])

storage_response_adapter: TypeAdapter[StorageResponse] = TypeAdapter(StorageResponse)


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
        config=data.config.model_dump(),
        enabled=data.enabled,
    )
    try:
        created = await repo.create(storage)
    except IntegrityError as error:
        raise ConflictError(
            f"Storage with mount path '{data.mount_path}' already exists."
        ) from error
    return storage_response_adapter.validate_python(created)


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
    return storage_response_adapter.validate_python(storage)


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
        items=[storage_response_adapter.validate_python(s) for s in storages],
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

    # Determine effective new state
    effective_type = data.type if data.type is not None else storage.type

    raw_new_config = data.config if data.config is not None else storage.config
    effective_config_dict: dict[str, Any] = {}
    if isinstance(raw_new_config, BaseModel):
        effective_config_dict = raw_new_config.model_dump()
    elif isinstance(raw_new_config, dict):
        effective_config_dict = raw_new_config
    else:
        # Should not happen given the types, but safe fallback
        effective_config_dict = dict(raw_new_config)

    # Validate consistency between Type and Config
    config_model = STORAGE_CONFIG_MAP.get(effective_type)
    if config_model:
        try:
            config_model.model_validate(effective_config_dict)
        except ValidationError as e:
            raise UnprocessableEntityError(
                f"Invalid config for storage type '{effective_type.value}': {e}"
            ) from e
    else:
        # Fallback or error if type is unknown (should be covered by Enum validation)
        pass

    # Apply updates
    if data.mount_path is not None:
        storage.mount_path = data.mount_path

    storage.type = effective_type
    storage.config = effective_config_dict

    if data.enabled is not None:
        storage.enabled = data.enabled

    try:
        updated = await repo.update(storage)
    except IntegrityError as error:
        raise ConflictError(
            f"Storage with mount path '{data.mount_path}' already exists."
        ) from error
    return storage_response_adapter.validate_python(updated)


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
