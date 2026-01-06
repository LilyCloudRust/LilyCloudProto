from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lilycloudproto.domain.entities.task import Task
from lilycloudproto.domain.values.admin.task import TaskStatus, TaskType
from lilycloudproto.infra.repositories.task_repository import TaskRepository
from lilycloudproto.infra.services.storage_service import StorageService
from lilycloudproto.infra.services.task_worker import TaskWorker


class TaskService:
    task_worker: TaskWorker
    session_factory: async_sessionmaker[AsyncSession]

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        storage_service: StorageService,
    ):
        self.session_factory = session_factory
        self.task_worker = TaskWorker(session_factory, storage_service)

    async def start(self) -> None:
        await self.task_worker.start()

    async def stop(self) -> None:
        await self.task_worker.stop()

    async def add_task(  # noqa: PLR0913
        self,
        user_id: int,
        type: TaskType,
        src_dir: str | None,
        dst_dirs: list[str],
        file_names: list[str],
        db: AsyncSession | None = None,
    ) -> Task:
        # Define the logic to create task using a given session
        async def _create_in_session(session: AsyncSession) -> Task:
            task_repo = TaskRepository(session)
            task = Task(
                user_id=user_id,
                type=type,
                src_dir=src_dir,
                dst_dirs=dst_dirs,
                file_names=file_names,
                status=TaskStatus.PENDING,
                progress=0.0,
                message="",
            )
            # Ensure the repo creates AND commits (or we commit here if repo doesn't)
            created_task = await task_repo.create(task)
            return created_task

        # Use the passed db if available, otherwise create a new one
        if db:
            task = await _create_in_session(db)
        else:
            async with self.session_factory() as session:
                task = await _create_in_session(session)

        # Notify worker only AFTER successful DB commit
        await self.task_worker.add_task(task.task_id)
        return task
