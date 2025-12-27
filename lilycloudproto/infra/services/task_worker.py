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
from lilycloudproto.domain.entities.trash import Trash
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

            # 2. Move File First (Better transaction consistency)
            # If file move fails, we don't create a DB entry
            try:
                shutil.move(original_path, trash_path)
            except Exception as e:
                error_msg = f"Failed to move {file_name} to trash: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                await progress_callback(i + 1, total_files)
                continue

            # 3. Create DB Entry (Only after successful file move)
            # IMPORTANT: entry_name stores the unique physical name
            # (e.g., "file(1).txt")
            # original_path stores the original virtual path
            # (e.g., "/docs/file.txt")
            try:
                entry = Trash(
                    user_id=task.user_id,
                    original_path=virtual_path,
                    entry_name=unique_trash_name,
                    deleted_at=datetime.now(UTC),
                )
                entry = await trash_repo.create(entry)
                success_count += 1
            except Exception as e:
                # If DB creation fails, try to move file back
                error_msg = f"Failed to create DB entry for {file_name}: {e}"
                logger.error(error_msg)
                try:
                    shutil.move(trash_path, original_path)
                except Exception as rollback_error:
                    logger.error(
                        f"Failed to rollback file move for {file_name}:"
                        f"{rollback_error}"
                    )
                errors.append(error_msg)

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

        # Lookup by entry_name (Unique Handle) - dir is optional for validation only
        for i, entry_name in enumerate(task.file_names):
            # 1. Lookup by entry_name (Unique Handle)
            # This solves the ambiguity of duplicate original filenames.
            entry = await trash_repo.get_by_entry_name(entry_name)

            if not entry:
                errors.append(f"Trash entry not found: {entry_name}")
                continue

            # 2. Optional validation: if dir is provided, verify entry belongs to it
            # dir is "relative path to the trash root", which means the directory
            # part of the original_path. This is an optional safety check.
            if task.src_dir:
                normalized_dir = os.path.normpath(task.src_dir)
                normalized_entry_path = os.path.normpath(entry.original_path)

                # Check if entry's original_path is under the requested dir
                # For exact match or subdirectory
                if normalized_dir != "/":
                    dir_with_sep = normalized_dir + os.sep
                    is_under_dir = normalized_entry_path.startswith(dir_with_sep)
                    is_exact_match = normalized_entry_path == normalized_dir
                    if not is_under_dir and not is_exact_match:
                        errors.append(
                            f"File {entry_name} does not belong to directory "
                            f"{task.src_dir}"
                        )
                        continue

            # 3. Determine physical location
            trash_root = self.storage_service.get_trash_root(entry.original_path)
            trash_path = os.path.join(trash_root, entry.entry_name)

            if not os.path.exists(trash_path):
                errors.append(f"Physical file missing: {entry.entry_name}")
                continue

            # 4. Determine destination
            dest_path = self.storage_service.get_physical_path(entry.original_path)
            dest_dir = os.path.dirname(dest_path)

            if os.path.exists(dest_dir) and not os.path.isdir(dest_dir):
                errors.append(f"Parent path is a file: {dest_dir}")
                continue

            os.makedirs(dest_dir, exist_ok=True)

            # 5. Handle destination collision (Linux style: rename restored file)
            final_dest_path = dest_path
            if os.path.exists(final_dest_path):
                d_dir, d_name = os.path.split(dest_path)
                unique_name = self._get_unique_filename(d_dir, d_name)
                final_dest_path = os.path.join(d_dir, unique_name)

            # 6. Move and Cleanup
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

        # Security: Only fetch entries for the current user
        stmt = select(Trash).where(Trash.user_id == task.user_id)
        result = await session.execute(stmt)
        entries = result.scalars().all()

        total = len(entries)
        if total == 0:
            await progress_callback(1, 1)
            return

        # Track failed deletions
        failed_entries: list[Trash] = []
        errors: list[str] = []

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
                error_msg = f"Failed to delete trash file {trash_path}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed_entries.append(entry)

            await progress_callback(i + 1, total)

        # Only delete DB entries for successfully deleted files
        if failed_entries:
            # Delete only successful entries
            successful_entries = [e for e in entries if e not in failed_entries]
            for entry in successful_entries:
                await trash_repo.delete(entry)

            # Report partial failure
            if len(failed_entries) == total:
                raise Exception(
                    f"Failed to delete all trash files. Errors: {'; '.join(errors)}"
                )
            else:
                raise Exception(
                    f"Partial success ({len(successful_entries)}/{total}). "
                    f"Errors: {'; '.join(errors)}"
                )
        else:
            # All successful, delete all DB entries for this user
            await trash_repo.delete_all(user_id=task.user_id)

    async def _handle_delete_trash_by_ids(
        self,
        session: AsyncSession,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        trash_repo = TrashRepository(session, self.storage_service)
        total = len(task.file_names)
        errors: list[str] = []
        success_count = 0

        for i, id_str in enumerate(task.file_names):
            try:
                trash_id = int(id_str)
                entry = await trash_repo.get_by_id(trash_id)

                if not entry:
                    errors.append(f"Trash entry not found: {trash_id}")
                    await progress_callback(i + 1, total)
                    continue

                trash_root = self.storage_service.get_trash_root(entry.original_path)
                path = os.path.join(trash_root, entry.entry_name)
                try:
                    if os.path.exists(path):
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
                    await trash_repo.delete(entry)
                    success_count += 1
                except Exception as e:
                    error_msg = f"Failed to delete trash file {path}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            except ValueError:
                errors.append(f"Invalid trash ID: {id_str}")
            except Exception as e:
                error_msg = f"Unexpected error processing trash ID {id_str}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

            await progress_callback(i + 1, total)

        if success_count == 0 and total > 0:
            raise Exception(f"Delete operation failed. Errors: {'; '.join(errors)}")
        elif errors:
            raise Exception(
                f"Partial success ({success_count}/{total}). "
                f"Errors: {'; '.join(errors)}"
            )

    def _delete_file_from_trash_entry(
        self, entry: Trash, file_name: str
    ) -> tuple[bool, str | None]:
        """Delete a file from a trash entry directory.

        Args:
            entry: The trash entry (should be a directory)
            file_name: Name of the file to delete

        Returns:
            tuple[bool, str | None]: (success, error_message)
        """
        trash_root = self.storage_service.get_trash_root(entry.original_path)
        trash_entry_path = os.path.join(trash_root, entry.entry_name)

        if not os.path.isdir(trash_entry_path):
            return False, None

        file_path = os.path.join(trash_entry_path, file_name)
        if not os.path.exists(file_path):
            return False, None

        try:
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
            logger.info(f"Deleted {file_name} from trash entry {entry.entry_name}")
            return True, None
        except Exception as e:
            error_msg = f"Failed to delete {file_path}: {e}"
            logger.error(error_msg)
            return False, error_msg

    async def _handle_delete_trash_by_path(
        self,
        session: AsyncSession,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        """
        Delete files in subdirectories of trash entries.

        This method finds trash entries (directories) that match the given dir,
        and then deletes the specified file_names from within those directories.
        If dir is None, it will search all trash entries.
        """
        trash_repo = TrashRepository(session, self.storage_service)
        total = len(task.file_names)
        errors: list[str] = []
        success_count = 0

        # If dir is provided, use it for filtering; otherwise search all entries
        if task.src_dir and task.src_dir.strip():
            # Normalize the directory path for matching
            normalized_dir = os.path.normpath(task.src_dir)
            if normalized_dir == ".":
                normalized_dir = "/"

            # Find all trash entries whose original_path starts with the given dir
            matching_entries = await trash_repo.get_by_original_path_prefix(
                normalized_dir, user_id=task.user_id
            )

            if not matching_entries:
                errors.append(f"No trash entries found for directory: {task.src_dir}")
                for i in range(total):
                    await progress_callback(i + 1, total)
                raise Exception(f"Delete operation failed. Errors: {'; '.join(errors)}")
        else:
            # If dir is None, get all trash entries for the user

            statement = select(Trash).where(Trash.user_id == task.user_id)
            result = await session.execute(statement)
            matching_entries = list(result.scalars().all())

            if not matching_entries:
                errors.append("No trash entries found")
                for i in range(total):
                    await progress_callback(i + 1, total)
                raise Exception(f"Delete operation failed. Errors: {'; '.join(errors)}")

        # For each file_name, try to delete it from matching trash entries
        for i, file_name in enumerate(task.file_names):
            file_deleted = False

            for entry in matching_entries:
                success, error_msg = self._delete_file_from_trash_entry(
                    entry, file_name
                )
                if success:
                    file_deleted = True
                    success_count += 1
                    break
                if error_msg:
                    errors.append(error_msg)

            if not file_deleted:
                errors.append(
                    f"File {file_name} not found in any entries for directory "
                    f"{task.src_dir}"
                )

            await progress_callback(i + 1, total)
