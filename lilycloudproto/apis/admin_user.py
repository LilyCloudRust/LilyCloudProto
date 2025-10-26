from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.database import get_db
from lilycloudproto.entities.user import User
from lilycloudproto.error import ConflictError, NotFoundError
from lilycloudproto.infra.user_repository import UserRepository
from lilycloudproto.models.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/api/admin/users", tags=["Admin"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    repo = UserRepository(db)
    # Check for duplicate username.
    statement = select(User).where(User.username == data.username)
    result = await db.execute(statement)
    if result.scalar_one_or_none():
        raise ConflictError(f"Username '{data.username}' already exists.")
    user = User(username=data.username, hashed_password=data.password)
    created = await repo.create(user)
    return UserResponse.model_validate(created)


@router.get("", response_model=list[UserResponse])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    repo = UserRepository(db)
    users = await repo.get_all(page=page, page_size=page_size)
    return [UserResponse.model_validate(user) for user in users]


@router.get("/search", response_model=list[UserResponse])
async def search_users(
    keyword: str = Query(None, min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    repo = UserRepository(db)
    users = await repo.search(keyword=keyword, page=page, page_size=page_size)
    return [UserResponse.model_validate(user) for user in users]


@router.get("/{id}", response_model=UserResponse)
async def get_user(
    id: int,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    repo = UserRepository(db)
    user = await repo.get_by_id(id)
    if not user:
        raise NotFoundError(f"User with ID '{id}' not found.")
    return UserResponse.model_validate(user)


@router.put("/{id}", response_model=UserResponse)
async def update_user(
    id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    repo = UserRepository(db)
    user = await repo.get_by_id(id)
    if not user:
        raise NotFoundError(f"User with ID '{id}' not found.")
    if data.username is not None:
        # Check for duplicate username.
        statement = select(User).where(User.username == data.username)
        result = await db.execute(statement)
        if result.scalar_one_or_none():
            raise ConflictError(f"Username '{data.username}' already exists.")
        user.username = data.username
    if data.password is not None:
        user.hashed_password = data.password
    updated = await repo.update(user)
    return UserResponse.model_validate(updated)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = UserRepository(db)
    user = await repo.get_by_id(id)
    if not user:
        raise NotFoundError(f"User with ID '{id}' not found.")
    await repo.delete(user)
