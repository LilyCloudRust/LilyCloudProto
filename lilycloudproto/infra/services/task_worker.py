import asyncio
import logging
import os
import shutil
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lilycloudproto.domain.entities.task import Task
from lilycloudproto.domain.entities.trash import Trash
from lilycloudproto.domain.values.task import TaskStatus, TaskType
from lilycloudproto.error import BadRequestError, InternalServerError, NotFoundError
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
        src_dir = self.storage_service.get_physical_path(task.src_dir)
        dst_dirs = self.storage_service.get_physical_paths(task.dst_dirs)
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
        src_dir = self.storage_service.get_physical_path(task.src_dir)
        dst_dirs = self.storage_service.get_physical_paths(task.dst_dirs)
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
        src_dir = self.storage_service.get_physical_path(task.src_dir)
        await driver.delete(src_dir, task.file_names, progress_callback)

    async def _handle_trash(
        self,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        """Handle TRASH task: move files to trash with directory structure preserved."""
        if task.src_dir is None:
            raise BadRequestError(
                f"Source directory is required for TRASH task '{task.task_id}'."
            )

        # Get session from current context (created in _process_task)
        # Note: This requires the handler to be called within a session context
        # We'll create a new session here for TrashRepository operations
        async with self.session_factory() as session:
            trash_repo = TrashRepository(session)
            await self._process_trash_task(task, trash_repo, progress_callback)

    async def _process_trash_task(
        self,
        task: Task,
        trash_repo: TrashRepository,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        """Process trash task with TrashRepository."""
        if task.src_dir is None:
            raise BadRequestError(
                f"Source directory is required for TRASH task '{task.task_id}'."
            )
        src_dir = self.storage_service.get_physical_path(task.src_dir)
        trash_root = self.storage_service.get_trash_root(src_dir)

        # Ensure trash directory exists
        os.makedirs(trash_root, exist_ok=True)

        total_files = len(task.file_names)
        processed = 0
        failed_files: list[str] = []

        for file_name in task.file_names:
            try:
                await self._trash_single_file(
                    task,
                    file_name,
                    src_dir,
                    trash_root,
                    trash_repo,
                )
                processed += 1
                if progress_callback is not None:
                    await progress_callback(processed, total_files)
            except Exception as error:
                error_msg = (
                    f"Failed to trash file '{file_name}' "
                    f"in task '{task.task_id}': {error}"
                )
                logger.error(error_msg)
                failed_files.append(file_name)

        self._validate_trash_task_result(
            processed, total_files, failed_files, task.task_id
        )

    async def _trash_single_file(
        self,
        task: Task,
        file_name: str,
        src_dir: str,
        trash_root: str,
        trash_repo: TrashRepository,
    ) -> None:
        """Trash a single file or directory."""
        src_path = os.path.join(src_dir, file_name)
        if not self._validate_path(src_path):
            raise NotFoundError(f"File not found: '{src_path}'.")

        # Calculate entry_name (preserve relative path structure)
        entry_name = self._calculate_entry_name(src_dir, file_name, trash_root)

        # Handle name conflicts
        unique_entry_name = await self._get_unique_entry_name(
            trash_root, entry_name, trash_repo
        )

        # Original path for restoration
        original_path = os.path.join(src_dir, file_name)

        # Create Trash database record
        trash = Trash(
            user_id=task.user_id,
            entry_name=unique_entry_name,
            original_path=original_path,
            deleted_at=task.created_at,
        )
        trash = await trash_repo.create(trash)

        # Move file to trash
        dst_path = os.path.join(trash_root, unique_entry_name)
        dst_dir = os.path.dirname(dst_path)
        if dst_dir:
            os.makedirs(dst_dir, exist_ok=True)

        try:
            shutil.move(src_path, dst_path)
        except Exception as error:
            # Rollback: delete database record if file move failed
            await trash_repo.delete(trash)
            raise InternalServerError(
                f"Failed to move file to trash: {error}"
            ) from error

        # Handle directory recursion
        if os.path.isdir(dst_path):
            await self._trash_directory_recursive(
                dst_path, original_path, trash_root, task, trash_repo
            )

    async def _trash_directory_recursive(
        self,
        dir_path: str,
        original_dir_path: str,
        trash_root: str,
        task: Task,
        trash_repo: TrashRepository,
    ) -> None:
        """Recursively create Trash records for all files in a directory."""
        # Walk through directory tree
        for root, _dirs, files in os.walk(dir_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                # Calculate relative path from trash_root
                relative_path = os.path.relpath(file_path, trash_root).replace(
                    os.sep, "/"
                )
                # Calculate original path
                rel_from_dir = os.path.relpath(file_path, dir_path)
                original_file_path = os.path.join(original_dir_path, rel_from_dir)

                # Create Trash record for file
                trash = Trash(
                    user_id=task.user_id,
                    entry_name=relative_path,
                    original_path=original_file_path,
                    deleted_at=task.created_at,
                )
                await trash_repo.create(trash)

    def _validate_trash_task_result(
        self,
        processed: int,
        total_files: int,
        failed_files: list[str],
        task_id: int,
    ) -> None:
        """Validate trash task result and raise error if all files failed."""
        # If all files failed, raise an error to mark task as FAILED
        if processed == 0 and total_files > 0:
            error_summary = f"All {total_files} file(s) failed to trash"
            if failed_files:
                error_summary += f": {', '.join(failed_files)}"
            raise InternalServerError(error_summary)

        # If some files failed, log warning but don't fail the task
        if failed_files:
            logger.warning(
                f"Task {task_id}: {len(failed_files)} file(s) failed: "
                f"{', '.join(failed_files)}"
            )

    def _validate_path(self, path: str) -> bool:
        """Validate that path exists and is not a symlink."""
        path = os.path.normpath(path)
        return (
            os.path.exists(path)
            and not os.path.islink(path)
            and not os.path.isjunction(path)
        )

    def _calculate_entry_name(
        self, src_dir: str, file_name: str, trash_root: str
    ) -> str:
        """
        Calculate entry_name preserving relative path structure.
        """
        src_path = os.path.join(src_dir, file_name)
        # Get relative path from trash_root
        try:
            relative_path = os.path.relpath(src_path, trash_root)
        except ValueError:
            # If paths are on different drives (Windows), use file_name
            relative_path = file_name
        # Normalize path separators to forward slashes
        return relative_path.replace(os.sep, "/")

    async def _get_unique_entry_name(
        self, trash_root: str, desired_entry_name: str, trash_repo: TrashRepository
    ) -> str:
        """
        Generate unique entry_name handling conflicts.

        If conflict exists, generates: name(1).ext, name(2).ext, etc.
        """
        # Check if desired name is available
        if not os.path.exists(os.path.join(trash_root, desired_entry_name)):
            existing = await trash_repo.find_by_entry_name(desired_entry_name)
            if existing is None:
                return desired_entry_name

        # Conflict: generate unique name
        name, ext = os.path.splitext(desired_entry_name)
        counter = 1
        while True:
            new_name = f"{name}({counter}){ext}"
            new_path = os.path.join(trash_root, new_name)
            if not os.path.exists(new_path):
                existing = await trash_repo.find_by_entry_name(new_name)
                if existing is None:
                    return new_name
            counter += 1
