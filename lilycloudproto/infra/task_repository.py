from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.entities.task import Task


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

    async def get_all(self, page: int = 1, page_size: int = 20) -> list[Task]:
        """Retrieve all tasks with pagination."""
        offset = (page - 1) * page_size
        statement = select(Task)

        result = await self.db.execute(statement.offset(offset).limit(page_size))
        return list(result.scalars().all())

    async def search(
        self,
        user_id: int | None = None,
        status: str | None = None,
        type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Task]:
        """Search for tasks by user, status, or type."""
        offset = (page - 1) * page_size
        statement = select(Task)

        if user_id:
            statement = statement.where(Task.user_id == user_id)
        if status:
            statement = statement.where(Task.status == status)
        if type:
            statement = statement.where(Task.type == type)

        statement = statement.order_by(Task.created_at.desc())
        statement = statement.offset(offset).limit(page_size)

        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def count(
        self,
        user_id: int | None = None,
        status: str | None = None,
        type: str | None = None,
    ) -> int:
        """Count tasks with optional filters."""
        statement = select(Task)

        if user_id:
            statement = statement.where(Task.user_id == user_id)
        if status:
            statement = statement.where(Task.status == status)
        if type:
            statement = statement.where(Task.type == type)

        count_statement = select(func.count()).select_from(statement.subquery())
        total_count = (await self.db.execute(count_statement)).scalar_one()
        return total_count

    async def update(self, task: Task) -> Task:
        """Update a task."""
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        """Delete a task."""
        await self.db.delete(task)
        await self.db.commit()
