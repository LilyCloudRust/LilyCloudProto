from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.domain.entities.share import Share
from lilycloudproto.domain.values.share import ListArgs, SortBy, SortOrder


class ShareRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, share: Share) -> Share:
        """Create a new share."""
        self.db.add(share)
        await self.db.commit()
        await self.db.refresh(share)
        return share

    async def get_by_id(self, share_id: int) -> Share | None:
        """Retrieve a share by ID."""
        result = await self.db.execute(select(Share).where(Share.share_id == share_id))
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> Share | None:
        """Retrieve a share by its token."""
        result = await self.db.execute(select(Share).where(Share.token == token))
        return result.scalar_one_or_none()

    async def search(self, args: ListArgs) -> list[Share]:
        """Search for shares based on query parameters."""
        offset = (args.page - 1) * args.page_size
        statement = select(Share)

        if args.keyword:
            statement = statement.where(
                or_(
                    Share.base_dir.contains(args.keyword),
                    Share.token.contains(args.keyword),
                )
            )
        if args.user_id:
            statement = statement.where(Share.user_id == args.user_id)
        if args.permission:
            statement = statement.where(Share.permission == args.permission)

        field_map = {
            SortBy.BASE_DIR: Share.base_dir,
            SortBy.PERMISSION: Share.permission,
            SortBy.EXPIRES_AT: Share.expires_at,
            SortBy.CREATED_AT: Share.created_at,
            SortBy.UPDATED_AT: Share.updated_at,
        }
        sort_column = field_map.get(args.sort_by, Share.created_at)

        # Handle active_first by sorting active shares first.
        if args.active_first:
            statement = statement.order_by(
                (Share.expires_at > func.now()).desc(),
                (
                    sort_column.desc()
                    if args.sort_order == SortOrder.DESC
                    else sort_column.asc()
                ),
            )
        elif args.sort_order == SortOrder.DESC:
            statement = statement.order_by(desc(sort_column))
        else:
            statement = statement.order_by(asc(sort_column))

        statement = statement.order_by(Share.share_id)
        statement = statement.offset(offset).limit(args.page_size)

        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def count(self, args: ListArgs) -> int:
        """Count shares based on query parameters."""
        statement = select(func.count()).select_from(Share)

        if args.keyword:
            statement = statement.where(
                or_(
                    Share.base_dir.contains(args.keyword),
                    Share.token.contains(args.keyword),
                )
            )
        if args.user_id:
            statement = statement.where(Share.user_id == args.user_id)
        if args.permission:
            statement = statement.where(Share.permission == args.permission)

        result = await self.db.execute(statement)
        return result.scalar_one() or 0

    async def update(self, share: Share) -> Share:
        """Update a share."""
        await self.db.commit()
        await self.db.refresh(share)
        return share

    async def delete(self, share: Share) -> None:
        """Delete a share."""
        await self.db.delete(share)
        await self.db.commit()
