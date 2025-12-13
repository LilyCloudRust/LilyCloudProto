import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lilycloudproto.domain.driver import Driver
from lilycloudproto.domain.values.task import TaskStatus, TaskType
from lilycloudproto.error import BadRequestError, NotFoundError
from lilycloudproto.infra.repositories.task_repository import TaskRepository
from lilycloudproto.infra.tasks.task_queue import task_queue

logger = logging.getLogger(__name__)


class TaskWorker:
    session_factory: async_sessionmaker[AsyncSession]
    driver: Driver
    _running: bool

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        driver: Driver,
    ) -> None:
        self.session_factory = session_factory
        self.driver = driver
        self._running = False

    async def start(self) -> None:
        """Start the worker loop."""
        self._running = True
        logger.info("Background task worker started.")
        while self._running:
            # Wait for a task.
            payload = await task_queue.dequeue()
            task_id = payload.task_id
            try:
                await self.process_task(task_id)
            except Exception as error:
                logger.error(f"Unexpected error in worker for task {task_id}: {error}")
            finally:
                task_queue.task_done()

    async def stop(self) -> None:
        """Stop the worker loop."""
        self._running = False

    async def process_task(self, task_id: int) -> None:
        async with self.session_factory() as session:
            repo = TaskRepository(session)
            task = await repo.get_by_id(task_id)
            if not task:
                raise NotFoundError(f"Task '{task_id}' not found in database.")

            # Update status to running.
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(UTC)
            _ = await repo.update(task)

            async def progress_callback(done: int, total: int) -> None:
                progress = float(done) / float(total) * 100.0 if total else 0.0
                task.progress = min(max(progress, 0.0), 100.0)
                task.updated_at = datetime.now(UTC)
                _ = await repo.update(task)

            try:
                if task.type == TaskType.COPY:
                    if task.src_dir is None:
                        raise BadRequestError(
                            f"Source directory is required for COPY task '{task_id}'."
                        )
                    await self.driver.copy(
                        task.src_dir,
                        task.dst_dirs[0],
                        task.file_names,
                        progress_callback,
                    )
                    pass

                elif task.type == TaskType.MOVE:
                    if task.src_dir is None:
                        raise BadRequestError(
                            f"Source directory is required for MOVE task '{task_id}'."
                        )
                    await self.driver.move(
                        task.src_dir,
                        task.dst_dirs[0],
                        task.file_names,
                        progress_callback,
                    )
                    pass

                elif task.type == TaskType.DELETE:
                    if task.src_dir is None:
                        raise BadRequestError(
                            f"Source directory is required for DELETE task '{task_id}'."
                        )
                    await self.driver.delete(
                        task.src_dir,
                        task.file_names,
                        progress_callback,
                    )

                # Mark task as completed.
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now(UTC)
                task.progress = 100.0
                _ = await repo.update(task)

            except Exception as error:
                logger.exception(f"Task '{task_id}' failed.")
                task.status = TaskStatus.FAILED
                task.message = str(error)
                task.completed_at = datetime.now(UTC)
                _ = await repo.update(task)
