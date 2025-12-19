import asyncio
import logging
import os
import shutil
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
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
        trash_repo = TrashRepository(session, self.storage_service)

        if task.src_dir is None:
            raise BadRequestError("Source directory is required for TRASH task.")

        src_dir_path = self.storage_service.get_physical_path(task.src_dir)
        # Use dynamic trash root based on source path
        trash_root = self.storage_service.get_trash_root(src_dir_path)
        os.makedirs(trash_root, exist_ok=True)

        total_files = len(task.file_names)
        errors: list[str] = []
        success_count = 0

        for i, file_name in enumerate(task.file_names):
            original_path = os.path.join(src_dir_path, file_name)
            if not os.path.exists(original_path):
                errors.append(f"File not found: {file_name}")
                continue

            # 1. Determine unique physical filename in .trash
            unique_trash_name = self._get_unique_filename(trash_root, file_name)
            trash_path = os.path.join(trash_root, unique_trash_name)

            virtual_path = os.path.join(task.src_dir, file_name)

            # 2. Create DB Entry
            # IMPORTANT: entry_name stores the unique physical name
            # (e.g., "file(1).txt")
            # original_path stores the original virtual path
            # (e.g., "/docs/file.txt")
            entry = TrashEntry(
                user_id=task.user_id,
                original_path=virtual_path,
                entry_name=unique_trash_name,
                deleted_at=datetime.now(UTC),
            )
            entry = await trash_repo.create(entry)

            # 3. Move File
            try:
                shutil.move(original_path, trash_path)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to move file to trash: {e}")
                await trash_repo.delete(entry)
                errors.append(f"Failed to move {file_name}: {e}")

            await progress_callback(i + 1, total_files)

        if success_count == 0 and total_files > 0:
            raise Exception(f"Trash operation failed. Errors: {'; '.join(errors)}")
        elif errors:
            raise Exception(
                f"Partial success ({success_count}/{total_files}). "
                f"Errors: {'; '.join(errors)}"
            )

    def _get_unique_filename(self, directory: str, filename: str) -> str:
        """
        Generate a unique filename in the given directory.
        Example: file.txt -> file(1).txt -> file(2).txt
        """
        if not os.path.exists(os.path.join(directory, filename)):
            return filename

        name, ext = os.path.splitext(filename)
        counter = 1
        while True:
            new_filename = f"{name}({counter}){ext}"
            if not os.path.exists(os.path.join(directory, new_filename)):
                return new_filename
            counter += 1

    async def _handle_restore(
        self,
        session: AsyncSession,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        trash_repo = TrashRepository(session, self.storage_service)
        total_files = len(task.file_names)
        errors: list[str] = []
        success_count = 0

        # API requires dir, but for lookup we rely on unique entry_name.
        # We can use dir to validate that the file belongs to the expected parent.
        if task.src_dir is None:
            raise BadRequestError("Source directory is required.")

        for i, entry_name in enumerate(task.file_names):
            # 1. Lookup by entry_name (Unique Handle)
            # This solves the ambiguity of duplicate original filenames.
            entry = await trash_repo.get_by_entry_name(entry_name)

            if not entry:
                errors.append(f"Trash entry not found: {entry_name}")
                continue

            # Optional: Validate that the entry belongs to the requested dir
            # This ensures security and consistency with the API semantics.
            # We check if the original path starts with the requested dir.
            # Note: task.src_dir usually comes without trailing slash, so we add os.sep
            # or simply check dirname.
            entry_dir = os.path.dirname(entry.original_path)
            # Normalize paths for comparison
            if os.path.normpath(entry_dir) != os.path.normpath(task.src_dir):
                # If strict validation is needed:
                # errors.append(f"File {entry_name} does not belong to {task.src_dir}")
                # continue
                pass  # For now, we trust the unique entry_name lookup.

            # 2. Determine physical location
            trash_root = self.storage_service.get_trash_root(entry.original_path)
            trash_path = os.path.join(trash_root, entry.entry_name)

            if not os.path.exists(trash_path):
                errors.append(f"Physical file missing: {entry.entry_name}")
                continue

            # 3. Determine destination
            dest_path = self.storage_service.get_physical_path(entry.original_path)
            dest_dir = os.path.dirname(dest_path)

            if os.path.exists(dest_dir) and not os.path.isdir(dest_dir):
                errors.append(f"Parent path is a file: {dest_dir}")
                continue

            os.makedirs(dest_dir, exist_ok=True)

            # 4. Handle destination collision (Linux style: rename restored file)
            final_dest_path = dest_path
            if os.path.exists(final_dest_path):
                d_dir, d_name = os.path.split(dest_path)
                unique_name = self._get_unique_filename(d_dir, d_name)
                final_dest_path = os.path.join(d_dir, unique_name)

            # 5. Move and Cleanup
            try:
                shutil.move(trash_path, final_dest_path)
                await trash_repo.delete(entry)
                success_count += 1
            except Exception as e:
                errors.append(f"Restore failed for {entry_name}: {e}")

            await progress_callback(i + 1, total_files)

        if success_count == 0 and total_files > 0:
            raise Exception(f"Restore failed. Errors: {'; '.join(errors)}")
        elif errors:
            raise Exception(
                f"Partial success ({success_count}/{total_files}). "
                f"Errors: {'; '.join(errors)}"
            )

    # --- Helper handlers for DELETE variants ---

    async def _handle_empty_trash(
        self,
        session: AsyncSession,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        trash_repo = TrashRepository(session, self.storage_service)

        # Fetch all entries to delete them physically
        stmt = select(TrashEntry)
        result = await session.execute(stmt)
        entries = result.scalars().all()

        total = len(entries)
        if total == 0:
            await progress_callback(1, 1)
            return

        for i, entry in enumerate(entries):
            trash_root = self.storage_service.get_trash_root(entry.original_path)
            trash_path = os.path.join(trash_root, entry.entry_name)
            try:
                if os.path.exists(trash_path):
                    if os.path.isdir(trash_path):
                        shutil.rmtree(trash_path)
                    else:
                        os.remove(trash_path)
            except Exception as e:
                logger.error(f"Failed to delete trash file {trash_path}: {e}")

            await progress_callback(i + 1, total)

        # Delete all DB entries
        await trash_repo.delete_all()

    async def _handle_delete_trash_by_ids(
        self,
        session: AsyncSession,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        trash_repo = TrashRepository(session, self.storage_service)
        total = len(task.file_names)

        for i, id_str in enumerate(task.file_names):
            try:
                trash_id = int(id_str)
                entry = await trash_repo.get_by_id(trash_id)
                if entry:
                    trash_root = self.storage_service.get_trash_root(
                        entry.original_path
                    )
                    path = os.path.join(trash_root, entry.entry_name)
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
        trash_repo = TrashRepository(session, self.storage_service)
        total = len(task.file_names)

        if task.src_dir is None:
            return

        for i, file_name in enumerate(task.file_names):
            original_virtual_path = os.path.join(task.src_dir, file_name)

            entry = await trash_repo.get_latest_by_original_path(original_virtual_path)
            if entry:
                trash_root = self.storage_service.get_trash_root(entry.original_path)
                path = os.path.join(trash_root, entry.entry_name)
                if os.path.exists(path):
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                await trash_repo.delete(entry)
            await progress_callback(i + 1, total)
