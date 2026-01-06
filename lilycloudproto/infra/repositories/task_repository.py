from sqlalchemy import String, asc, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.domain.entities.task import Task
from lilycloudproto.domain.values.admin.task import ListArgs, SortBy, SortOrder


class TaskRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, task: Task) -> Task:
        """Create a new task."""
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_by_id(self, task_id: int) -> Task | None:
        """Retrieve a task by ID."""
        result = await self.db.execute(select(Task).where(Task.task_id == task_id))
        return result.scalar_one_or_none()

    async def search(
        self,
        args: ListArgs,
    ) -> list[Task]:
        """Search for tasks by user, status, or type."""
        offset = (args.page - 1) * args.page_size
        statement = select(Task)

        if args.keyword:
            statement = statement.where(
                (Task.message.contains(args.keyword))
                | (Task.src_dir.contains(args.keyword))
                | (cast(Task.dst_dirs, String).contains(args.keyword))
                | (cast(Task.file_names, String).contains(args.keyword))
            )
        if args.user_id:
            statement = statement.where(Task.user_id == args.user_id)
        if args.status:
            statement = statement.where(Task.status == args.status)
        if args.type:
            statement = statement.where(Task.type == args.type)
        if args.base:
            statement = statement.where(Task.base == args.base)

        field_map = {
            SortBy.CREATED_AT: Task.created_at,
            SortBy.UPDATED_AT: Task.updated_at,
            SortBy.TYPE: Task.type,
            SortBy.STATUS: Task.status,
            SortBy.SRC: Task.src_dir,
            SortBy.STARTED_AT: Task.started_at,
            SortBy.COMPLETED_AT: Task.completed_at,
        }
        sort_column = field_map.get(args.sort_by, Task.created_at)

        if args.sort_order == SortOrder.DESC:
            statement = statement.order_by(desc(sort_column))
        else:
            statement = statement.order_by(asc(sort_column))

        statement = statement.order_by(Task.task_id)
        statement = statement.offset(offset).limit(args.page_size)

        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def count(
        self,
        args: ListArgs,
    ) -> int:
        """Count tasks with optional filters."""
        statement = select(func.count()).select_from(Task)

        if args.keyword:
            statement = statement.where(
                (Task.message.contains(args.keyword))
                | (Task.src_dir.contains(args.keyword))
                | (cast(Task.dst_dirs, String).contains(args.keyword))
                | (cast(Task.file_names, String).contains(args.keyword))
            )
        if args.user_id:
            statement = statement.where(Task.user_id == args.user_id)
        if args.status:
            statement = statement.where(Task.status == args.status)
        if args.type:
            statement = statement.where(Task.type == args.type)
        if args.base:
            statement = statement.where(Task.base == args.base)

        result = await self.db.execute(statement)
        return result.scalar_one() or 0

    async def update(self, task: Task) -> Task:
        """Update a task."""
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        """Delete a task."""
        await self.db.delete(task)
        await self.db.commit()
