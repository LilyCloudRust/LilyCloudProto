import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.dependencies import get_auth_service, get_current_user
from lilycloudproto.domain.entities.share import Share
from lilycloudproto.domain.entities.user import User
from lilycloudproto.domain.values.admin.user import Role
from lilycloudproto.domain.values.share import ListArgs
from lilycloudproto.error import ConflictError, NotFoundError
from lilycloudproto.infra.database import get_db
from lilycloudproto.infra.repositories.share_repository import ShareRepository
from lilycloudproto.infra.repositories.user_repository import UserRepository
from lilycloudproto.infra.services.auth_service import AuthService
from lilycloudproto.models.share import (
    MessageResponse,
    ShareCreate,
    ShareInfoResponse,
    ShareListQuery,
    ShareListResponse,
    ShareResponse,
    ShareUpdate,
)

router = APIRouter(prefix="/api/shares", tags=["Shares"])


@router.post("", response_model=ShareResponse, status_code=status.HTTP_201_CREATED)
async def create_share(
    data: ShareCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> ShareResponse:
    """Create a new share link."""
    repo = ShareRepository(db)

    # Hash the password if provided.
    hashed_password = None
    if data.password:
        hashed_password = service.password_hash.hash(data.password)

    # Generate a unique token (using UUID-like string).
    token = str(uuid.uuid4())

    share = Share(
        user_id=user.user_id,
        token=token,
        base_dir=data.base_dir,
        file_names=data.file_names,
        permission=data.permission,
        hashed_password=hashed_password,
        expires_at=data.expires_at,
    )

    try:
        created_share = await repo.create(share)
        return ShareResponse.from_entity(created_share)
    except IntegrityError as error:
        raise ConflictError("Share token already exists.") from error


@router.get("/{share_id}", response_model=ShareResponse)
async def get_share(
    share_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareResponse:
    """Get share link details by ID."""
    repo = ShareRepository(db)
    share = await repo.get_by_id(share_id)

    if not share:
        raise NotFoundError("Share not found.")

    if user.role != Role.ADMIN and share.user_id != user.user_id:
        raise NotFoundError("Share not found.")

    return ShareResponse.from_entity(share)


@router.get("", response_model=ShareListResponse)
async def list_shares(
    query: ShareListQuery = Depends(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareListResponse:
    """List share links with pagination and filtering."""
    repo = ShareRepository(db)

    if user.role != Role.ADMIN and query.user_id != user.user_id:
        raise NotFoundError("Share links not found.")

    list_args = ListArgs(
        keyword=query.keyword,
        user_id=query.user_id,
        permission=query.permission,
        active_first=query.active_first,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        page=query.page,
        page_size=query.page_size,
    )

    shares = await repo.search(list_args)
    total = await repo.count(list_args)

    return ShareListResponse(
        total=total,
        page=query.page,
        page_size=query.page_size,
        items=[ShareResponse.from_entity(share) for share in shares],
    )


@router.patch("/{share_id}", response_model=ShareResponse)
async def update_share(
    share_id: int,
    data: ShareUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> ShareResponse:
    """Update a share link by ID."""
    repo = ShareRepository(db)
    share = await repo.get_by_id(share_id)

    if not share:
        raise NotFoundError("Share link not found.")

    if user.role != Role.ADMIN and share.user_id != user.user_id:
        raise NotFoundError("Share link not found.")

    # Update fields if provided.
    if data.base_dir is not None:
        share.base_dir = data.base_dir
    if data.file_names is not None:
        share.file_names = data.file_names
    if data.permission is not None:
        share.permission = data.permission
    if data.expires_at is not None:
        share.expires_at = data.expires_at
    if data.password is not None:
        # Hash the password if provided.
        share.hashed_password = (
            service.password_hash.hash(data.password) if data.password else None
        )

    updated_share = await repo.update(share)
    return ShareResponse.from_entity(updated_share)


@router.delete("/{share_id}", response_model=MessageResponse)
async def delete_share(
    share_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(  # pyright: ignore[reportUnusedParameter]
        get_auth_service
    ),
) -> MessageResponse:
    """Delete a share link by ID."""
    repo = ShareRepository(db)
    share = await repo.get_by_id(share_id)

    if not share:
        raise NotFoundError("Share link not found.")

    if user.role != Role.ADMIN and share.user_id != user.user_id:
        raise NotFoundError("Share link not found.")

    await repo.delete(share)
    return MessageResponse(message="Share link deleted successfully.")


@router.get("/public/{share_token}", response_model=ShareInfoResponse)
async def get_share_info(
    share_token: str,
    db: AsyncSession = Depends(get_db),
) -> ShareInfoResponse:
    """
    Get Link Info via Token (public endpoint).
    """
    repo = ShareRepository(db)
    share = await repo.get_by_token(share_token)
    if not share:
        raise NotFoundError("Share link not found.")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(share.user_id)
    if user is None:
        raise NotFoundError("Share link creator not found.")

    return ShareInfoResponse(
        username=user.username,
        token=share.token,
        file_names=share.file_names,
        permission=share.permission,
        requires_password=share.hashed_password is not None,
        expires_at=share.expires_at,
    )
