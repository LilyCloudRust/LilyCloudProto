from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lilycloudproto.domain.entities.task import Task
from lilycloudproto.domain.values.task import TaskStatus, TaskType
from lilycloudproto.infra.repositories.task_repository import TaskRepository
from lilycloudproto.infra.services.storage_service import StorageService
from lilycloudproto.infra.services.task_worker import TaskWorker


class TaskService:
    task_repo: TaskRepository
    task_worker: TaskWorker

    def __init__(
        self,
        task_repo: TaskRepository,
        session_factory: async_sessionmaker[AsyncSession],
        storage_service: StorageService,
    ):
        self.task_repo = task_repo
        self.task_worker = TaskWorker(session_factory, storage_service)

    async def start(self) -> None:
        await self.task_worker.start()

    async def stop(self) -> None:
        await self.task_worker.stop()

    async def add_task(
        self,
        user_id: int,
        type: TaskType,
        src_dir: str | None,
        dst_dirs: list[str],
        file_names: list[str],
    ) -> Task:
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
        task = await self.task_repo.create(task)
        await self.task_worker.add_task(task.task_id)
        return task
