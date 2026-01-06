import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lilycloudproto.domain.driver import Base
from lilycloudproto.domain.entities.task import Task
from lilycloudproto.domain.entities.trash import Trash
from lilycloudproto.domain.values.admin.task import TaskStatus, TaskType
from lilycloudproto.error import BadRequestError, NotFoundError
from lilycloudproto.infra.repositories.task_repository import TaskRepository
from lilycloudproto.infra.repositories.trash_repository import TrashRepository
from lilycloudproto.infra.services.storage_service import StorageService

logger = logging.getLogger(__name__)


@dataclass
class TaskPayload:
    task_id: int


class TaskWorker:
    session_factory: async_sessionmaker[AsyncSession]
    storage_service: StorageService
    _queue: asyncio.Queue[TaskPayload]
    _running: bool
    _handlers: dict[
        TaskType,
        Callable[
            [Task, Callable[[int, int], Awaitable[None]]],
            Awaitable[None],
        ],
    ]

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        storage_service: StorageService,
    ) -> None:
        self.session_factory = session_factory
        self.storage_service = storage_service
        self._queue = asyncio.Queue()
        self._running = False
        self._handlers = {
            TaskType.COPY: self._handle_copy,
            TaskType.MOVE: self._handle_move,
            TaskType.DELETE: self._handle_delete,
            TaskType.TRASH: self._handle_trash,
            TaskType.RESTORE: self._handle_restore,
        }

    async def start(self) -> None:
        """Start the worker loop."""
        self._running = True
        logger.info("Background task worker started.")
        while self._running:
            # Wait for a task.
            payload = await self._queue.get()
            task_id = payload.task_id
            try:
                await self._process_task(task_id)
            except Exception as error:
                logger.error(f"Unexpected error in worker for task {task_id}: {error}")
            finally:
                self._queue.task_done()

    async def stop(self) -> None:
        """Stop the worker loop."""
        self._running = False

    async def add_task(self, task_id: int) -> None:
        await self._queue.put(TaskPayload(task_id))

    async def _process_task(self, task_id: int) -> None:
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
                handler = self._handlers.get(task.type)
                if handler is None:
                    raise BadRequestError(f"Unsupported task type '{task.type}'.")

                await handler(task, progress_callback)

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

    async def _handle_copy(
        self,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        driver = self.storage_service.get_driver(task.src_dir or task.dst_dirs[0])
        if task.src_dir is None:
            raise BadRequestError(
                f"Source directory is required for COPY task '{task.task_id}'."
            )
        src_dir = task.src_dir
        dst_dirs = task.dst_dirs
        await driver.copy(src_dir, dst_dirs[0], task.file_names, progress_callback)

    async def _handle_move(
        self,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        driver = self.storage_service.get_driver(task.src_dir or task.dst_dirs[0])
        if task.src_dir is None:
            raise BadRequestError(
                f"Source directory is required for MOVE task '{task.task_id}'."
            )
        src_dir = task.src_dir
        dst_dirs = task.dst_dirs
        await driver.move(src_dir, dst_dirs[0], task.file_names, progress_callback)

    async def _handle_delete(
        self,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        driver = self.storage_service.get_driver(
            task.src_dir or (task.dst_dirs[0] if task.dst_dirs else "")
        )
        if task.src_dir is None:
            raise BadRequestError(
                f"Source directory is required for DELETE task '{task.task_id}'."
            )
        await driver.delete(task.src_dir, task.file_names, progress_callback)

    async def _handle_trash(
        self,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        if not task.src_dir:
            raise BadRequestError(
                f"Source directory is required for TRASH task '{task.task_id}'."
            )
        driver = self.storage_service.get_driver(task.src_dir)
        await driver.trash(task.src_dir, task.file_names, progress_callback)
        driver = self.storage_service.get_driver(task.src_dir, Base.TRASH)

        # Record all info in the Trash table.
        async with self.session_factory() as session:
            trash_repo = TrashRepository(session)
            now = datetime.now(UTC)
            trash_entries: list[Trash] = []
            for name in task.file_names:
                try:
                    file_info = driver.info(name)
                except NotFoundError:
                    continue
                trash_entry = Trash(
                    user_id=task.user_id,
                    entry_name=file_info.name,
                    original_path=os.path.join(task.src_dir, name),
                    deleted_at=now,
                    size=file_info.size,
                    type=file_info.type,
                    mime_type=file_info.mime_type,
                    created_at=file_info.created_at,
                    modified_at=file_info.modified_at,
                    accessed_at=file_info.accessed_at,
                )
                trash_entries.append(trash_entry)
            await trash_repo.create_batch(trash_entries)

    async def _handle_restore(
        self,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        if not task.src_dir or not task.dst_dirs or len(task.dst_dirs) == 0:
            raise BadRequestError(
                "Source and destination directories are required for RESTORE task"
                + f"'{task.task_id}'."
            )

        src_paths = [os.path.join(task.src_dir, name) for name in task.file_names]

        if len(task.dst_dirs) == 1:
            # Use the single destination for all files.
            dst_dir = task.dst_dirs[0]
            dst_paths = [os.path.join(dst_dir, name) for name in task.file_names]
            driver = self.storage_service.get_driver(dst_dir)
            await driver.restore(src_paths, dst_paths, progress_callback)
        elif len(task.dst_dirs) == len(task.file_names):
            # Use each destination for each file, possibly different drivers.
            total = len(task.file_names)
            for index, (name, dst_dir) in enumerate(
                zip(task.file_names, task.dst_dirs, strict=True)
            ):
                src_path = os.path.join(task.src_dir, name)
                dst_path = os.path.join(dst_dir, name)
                driver = self.storage_service.get_driver(dst_dir)
                # Provide progress for each file.
                await driver.restore(
                    [src_path],
                    [dst_path],
                )
                await progress_callback(index + 1, total)
        else:
            raise BadRequestError(
                "dst_dirs must be length 1 or match file_names for RESTORE task"
                + f"'{task.task_id}'."
            )
