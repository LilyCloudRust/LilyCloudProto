from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.database import get_db
from lilycloudproto.domain.entities.user import User
from lilycloudproto.domain.values.user import ListArgs
from lilycloudproto.error import ConflictError, NotFoundError
from lilycloudproto.infra.repositories.user_repository import UserRepository
from lilycloudproto.models.user import (
    MessageResponse,
    UserCreate,
    UserListQuery,
    UserListResponse,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/api/admin/users", tags=["Admin/Users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new user."""
    repo = UserRepository(db)
    user = User(username=data.username, hashed_password=data.password)
    # Check for duplicate username.
    try:
        created = await repo.create(user)
    except IntegrityError as error:
        raise ConflictError(f"Username '{data.username}' already exists.") from error
    return UserResponse.model_validate(created)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get user details by ID."""
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise NotFoundError(f"User with ID '{user_id}' not found.")
    return UserResponse.model_validate(user)


@router.get("", response_model=UserListResponse)
async def list_users(
    query: UserListQuery = Depends(),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """List all users with pagination and optional keyword search."""
    repo = UserRepository(db)
    args = ListArgs(
        keyword=query.keyword,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        page=query.page,
        page_size=query.page_size,
    )

    users = await repo.search(args)
    total = await repo.count(args)

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update user details."""
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise NotFoundError(f"User with ID '{user_id}' not found.")
    if data.username is not None:
        user.username = data.username
    if data.password is not None:
        user.hashed_password = data.password
    # Check for duplicate username.
    try:
        updated = await repo.update(user)
    except IntegrityError as error:
        raise ConflictError(f"Username '{data.username}' already exists.") from error
    return UserResponse.model_validate(updated)


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Delete a user by ID."""
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise NotFoundError(f"User with ID '{user_id}' not found.")
    await repo.delete(user)
    return MessageResponse(message="User deleted successfully.")
