import asyncio
import logging
import os
import shutil
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lilycloudproto.domain.entities.task import Task
from lilycloudproto.domain.entities.trash import TrashEntry
from lilycloudproto.domain.values.task import TaskStatus, TaskType
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
            [AsyncSession, Task, Callable[[int, int], Awaitable[None]]],
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

                await handler(session, task, progress_callback)

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
        session: AsyncSession,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        driver = self.storage_service.get_driver(task.src_dir or task.dst_dirs[0])
        if task.src_dir is None:
            raise BadRequestError(
                f"Source directory is required for COPY task '{task.task_id}'."
            )
        src_dir = self.storage_service.get_physical_path(task.src_dir)
        dst_dirs = self.storage_service.get_physical_paths(task.dst_dirs)
        await driver.copy(src_dir, dst_dirs[0], task.file_names, progress_callback)

    async def _handle_move(
        self,
        session: AsyncSession,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        driver = self.storage_service.get_driver(task.src_dir or task.dst_dirs[0])
        if task.src_dir is None:
            raise BadRequestError(
                f"Source directory is required for MOVE task '{task.task_id}'."
            )
        src_dir = self.storage_service.get_physical_path(task.src_dir)
        dst_dirs = self.storage_service.get_physical_paths(task.dst_dirs)
        await driver.move(src_dir, dst_dirs[0], task.file_names, progress_callback)

    async def _handle_delete(
        self,
        session: AsyncSession,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        # Check for Trash Operations Markers
        if task.src_dir == "__TRASH_EMPTY__":
            await self._handle_empty_trash(session, task, progress_callback)
            return

        if task.src_dir == "__TRASH_IDS__":
            await self._handle_delete_trash_by_ids(session, task, progress_callback)
            return

        if task.dst_dirs and task.dst_dirs[0] == "__TRASH__":
            await self._handle_delete_trash_by_path(session, task, progress_callback)
            return

        # Normal File System Delete
        driver = self.storage_service.get_driver(
            task.src_dir or (task.dst_dirs[0] if task.dst_dirs else "")
        )
        if task.src_dir is None:
            raise BadRequestError(
                f"Source directory is required for DELETE task '{task.task_id}'."
            )
        src_dir = self.storage_service.get_physical_path(task.src_dir)
        await driver.delete(src_dir, task.file_names, progress_callback)

    async def _handle_trash(
        self,
        session: AsyncSession,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        trash_repo = TrashRepository(session)
        trash_root = self.storage_service.get_trash_root()
        os.makedirs(trash_root, exist_ok=True)

        if task.src_dir is None:
            raise BadRequestError("Source directory is required for TRASH task.")

        src_dir_path = self.storage_service.get_physical_path(task.src_dir)
        total_files = len(task.file_names)

        for i, file_name in enumerate(task.file_names):
            original_path = os.path.join(src_dir_path, file_name)
            if not os.path.exists(original_path):
                continue

            virtual_path = os.path.join(task.src_dir, file_name)

            entry = TrashEntry(
                user_id=task.user_id,
                original_path=virtual_path,
                entry_name=file_name,
                deleted_at=datetime.now(UTC),
            )
            entry = await trash_repo.create(entry)

            trash_path = os.path.join(trash_root, str(entry.trash_id))
            try:
                shutil.move(original_path, trash_path)
            except Exception as e:
                logger.error(f"Failed to move file to trash: {e}")
                await trash_repo.delete(entry)
                raise e

            await progress_callback(i + 1, total_files)

    async def _handle_restore(
        self,
        session: AsyncSession,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        trash_repo = TrashRepository(session)
        trash_root = self.storage_service.get_trash_root()
        total_files = len(task.file_names)

        if task.src_dir is None:
            raise BadRequestError(
                "Source directory (original location) is required for RESTORE task."
            )

        for i, file_name in enumerate(task.file_names):
            # Construct original virtual path to find the entry
            original_virtual_path = os.path.join(task.src_dir, file_name)

            # Find the latest entry for this path
            entry = await trash_repo.get_latest_by_original_path(original_virtual_path)
            if not entry:
                logger.warning(
                    f"Trash entry not found for path: {original_virtual_path}"
                )
                continue

            trash_path = os.path.join(trash_root, str(entry.trash_id))
            dest_path = self.storage_service.get_physical_path(entry.original_path)

            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            # Handle collision if file exists at destination
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(dest_path)
                dest_path = f"{base} (restored){ext}"

            if os.path.exists(trash_path):
                shutil.move(trash_path, dest_path)
            else:
                logger.error(f"Physical trash file missing: {trash_path}")

            await trash_repo.delete(entry)
            await progress_callback(i + 1, total_files)

    # --- Helper handlers for DELETE variants ---

    async def _handle_empty_trash(
        self,
        session: AsyncSession,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        trash_repo = TrashRepository(session)
        trash_root = self.storage_service.get_trash_root()

        # Delete all physical files
        if os.path.exists(trash_root):
            for filename in os.listdir(trash_root):
                file_path = os.path.join(trash_root, filename)
                try:
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    else:
                        os.remove(file_path)
                except Exception as e:
                    logger.error(f"Failed to delete trash file {file_path}: {e}")

        # Delete all DB entries
        await trash_repo.delete_all()
        await progress_callback(1, 1)

    async def _handle_delete_trash_by_ids(
        self,
        session: AsyncSession,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        trash_repo = TrashRepository(session)
        trash_root = self.storage_service.get_trash_root()
        total = len(task.file_names)

        for i, id_str in enumerate(task.file_names):
            try:
                trash_id = int(id_str)
                entry = await trash_repo.get_by_id(trash_id)
                if entry:
                    path = os.path.join(trash_root, str(entry.trash_id))
                    if os.path.exists(path):
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
                    await trash_repo.delete(entry)
            except ValueError:
                pass
            await progress_callback(i + 1, total)

    async def _handle_delete_trash_by_path(
        self,
        session: AsyncSession,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        trash_repo = TrashRepository(session)
        trash_root = self.storage_service.get_trash_root()
        total = len(task.file_names)

        if task.src_dir is None:
            return

        for i, file_name in enumerate(task.file_names):
            original_virtual_path = os.path.join(task.src_dir, file_name)
            # Find all entries for this path (or just latest? Usually delete
            # permanently means specific one,
            # but by path implies all versions or latest. Let's assume latest for
            # consistency with restore)
            entry = await trash_repo.get_latest_by_original_path(original_virtual_path)
            if entry:
                path = os.path.join(trash_root, str(entry.trash_id))
                if os.path.exists(path):
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                await trash_repo.delete(entry)
            await progress_callback(i + 1, total)
