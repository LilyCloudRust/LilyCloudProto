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

TRASH_DELETE_EMPTY = "__trash_empty__"
TRASH_DELETE_IDS = "__trash_ids__"
TRASH_DELETE_PATH = "__trash_path__"


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
        if task.dst_dirs and task.dst_dirs[0] in {
            TRASH_DELETE_EMPTY,
            TRASH_DELETE_IDS,
            TRASH_DELETE_PATH,
        }:
            async with self.session_factory() as session:
                repo = TrashRepository(session)
                await self._process_delete_trash_task(task, repo, progress_callback)
            return

        driver = self.storage_service.get_driver(
            task.src_dir or (task.dst_dirs[0] if task.dst_dirs else "")
        )
        if task.src_dir is None:
            raise BadRequestError(
                f"Source directory is required for DELETE task '{task.task_id}'."
            )

        src_dir = self.storage_service.get_physical_path(task.src_dir)
        await driver.delete(src_dir, task.file_names, progress_callback)

    async def _process_delete_trash_task(  # noqa: PLR0912
        self,
        task: Task,
        trash_repo: TrashRepository,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        if not task.dst_dirs:
            raise BadRequestError("Trash delete mode is required.")

        mode_marker = task.dst_dirs[0]
        dir_prefix = task.src_dir or ""
        trash_root = self.storage_service.get_trash_root(dir_prefix)

        records: list[Trash]
        if mode_marker == TRASH_DELETE_EMPTY:
            records = await trash_repo.list_by_user(task.user_id)
        elif mode_marker == TRASH_DELETE_IDS:
            try:
                trash_ids = [int(item) for item in task.dst_dirs[1:]]
            except ValueError as error:
                raise BadRequestError("Invalid trash ids.") from error

            records = await trash_repo.find_by_ids(trash_ids)
            if len(records) != len(trash_ids) or any(
                record.user_id != task.user_id for record in records
            ):
                raise NotFoundError("Trash entry not found.")
        elif mode_marker == TRASH_DELETE_PATH:
            if not task.file_names:
                raise BadRequestError("file_names are required for delete path mode.")
            records = await trash_repo.find_by_user_and_path(
                task.user_id, dir_prefix, task.file_names
            )
            if len(records) != len(task.file_names):
                raise NotFoundError("Trash entry not found.")
        else:
            raise BadRequestError("Invalid trash delete mode.")

        total = len(records)
        processed = 0
        failed: list[str] = []

        for record in records:
            fs_path = self._ensure_inside_trash(trash_root, record.entry_name)
            try:
                if os.path.isdir(fs_path):
                    shutil.rmtree(fs_path)
                else:
                    os.remove(fs_path)
            except FileNotFoundError:
                failed.append(record.entry_name)
                continue
            except Exception as error:  # pragma: no cover - defensive
                logger.error(
                    "Failed to remove trash entry '%s' in task '%s': %s",
                    record.entry_name,
                    task.task_id,
                    error,
                )
                failed.append(record.entry_name)
                continue

            try:
                await trash_repo.delete(record)
                processed += 1
                if progress_callback is not None:
                    await progress_callback(processed, total)
            except Exception as error:  # pragma: no cover - defensive
                failed.append(record.entry_name)
                logger.error(
                    "Failed to delete trash record '%s' in task '%s': %s",
                    record.entry_name,
                    task.task_id,
                    error,
                )

        self._validate_trash_task_result(processed, total, failed, task.task_id)

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

    async def _handle_restore(
        self,
        task: Task,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        """Handle RESTORE task: move files from trash back to original paths."""
        async with self.session_factory() as session:
            repo = TrashRepository(session)
            await self._process_restore_task(task, repo, progress_callback)

    async def _process_restore_task(
        self,
        task: Task,
        trash_repo: TrashRepository,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        if task.file_names is None:
            raise BadRequestError(
                f"file_names are required for RESTORE task '{task.task_id}'."
            )

        dir_prefix = task.src_dir or ""
        trash_root = self.storage_service.get_trash_root(dir_prefix)

        records = await trash_repo.find_by_user_and_path(
            task.user_id, dir_prefix, task.file_names
        )
        if len(records) != len(task.file_names):
            raise NotFoundError("Trash entry not found.")

        total = len(records)
        processed = 0
        failed: list[str] = []

        for record in records:
            fs_path = self._ensure_inside_trash(trash_root, record.entry_name)
            if not os.path.exists(fs_path):
                failed.append(record.entry_name)
                continue

            if os.path.exists(record.original_path):
                failed.append(record.entry_name)
                continue

            dst_parent = os.path.dirname(record.original_path)
            if dst_parent:
                os.makedirs(dst_parent, exist_ok=True)

            try:
                shutil.move(fs_path, record.original_path)
                await trash_repo.delete(record)
                processed += 1
                if progress_callback is not None:
                    await progress_callback(processed, total)
            except Exception as error:  # pragma: no cover - defensive
                failed.append(record.entry_name)
                logger.error(
                    "Failed to restore entry '%s' in task '%s': %s",
                    record.entry_name,
                    task.task_id,
                    error,
                )

        self._validate_trash_task_result(processed, total, failed, task.task_id)

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

        # Collect all entries to create (before moving files)
        entries = self._collect_all_entries(src_path, src_dir)

        if not entries:
            raise InternalServerError(f"No entries found for path: '{src_path}'.")

        # Handle name conflicts for the top-level entry
        top_entry = entries[0]
        original_top_entry_name = top_entry["entry_name"]
        unique_top_entry_name = await self._get_unique_entry_name(
            trash_root, original_top_entry_name, trash_repo
        )

        if unique_top_entry_name != original_top_entry_name:
            entries = self._adjust_entry_names(
                entries, original_top_entry_name, unique_top_entry_name
            )

        # Batch create database records
        trash_list = []
        for entry in entries:
            trash = Trash(
                user_id=task.user_id,
                entry_name=entry["entry_name"],
                original_path=entry["original_path"],
                deleted_at=task.created_at,
            )
            trash_list.append(trash)

        await trash_repo.create_batch(trash_list)

        # Move file/directory to trash (single operation moves entire tree)
        dst_path = os.path.join(trash_root, unique_top_entry_name)
        dst_dir = os.path.dirname(dst_path)
        if dst_dir:
            os.makedirs(dst_dir, exist_ok=True)

        try:
            shutil.move(src_path, dst_path)
        except Exception as error:
            # Rollback: delete database records if file move failed
            entry_names = [entry["entry_name"] for entry in entries]
            await trash_repo.delete_by_entry_names(entry_names)
            raise InternalServerError(
                f"Failed to move file to trash: {error}"
            ) from error

    def _collect_all_entries(
        self, src_path: str, base_dir: str
    ) -> list[dict[str, str]]:
        """
        Collect all entries (files and directories) that need Trash records.

        This method walks the source path before moving files, collecting
        all entries that should be recorded in the database.

        Args:
            src_path: Source file or directory path
            base_dir: Directory provided by request; entry_names are relative to this

        Returns:
            List of dicts with 'entry_name' and 'original_path' keys,
            sorted with top-level entry first
        """
        entries: list[dict[str, str]] = []

        # Normalize base_dir to ensure relative path calculation matches request context
        normalized_base = os.path.normpath(base_dir)

        if os.path.isfile(src_path):
            # Single file
            entry_name = os.path.relpath(src_path, normalized_base).replace(os.sep, "/")
            entries.append(
                {
                    "entry_name": entry_name,
                    "original_path": src_path,
                }
            )
        else:
            # Directory: walk through all contents
            for root, _dirs, files in os.walk(src_path):
                # Add directory entry
                dir_entry_name = os.path.relpath(root, normalized_base).replace(
                    os.sep, "/"
                )
                entries.append(
                    {
                        "entry_name": dir_entry_name,
                        "original_path": root,
                    }
                )

                # Add file entries
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    file_entry_name = os.path.relpath(
                        file_path, normalized_base
                    ).replace(os.sep, "/")
                    entries.append(
                        {
                            "entry_name": file_entry_name,
                            "original_path": file_path,
                        }
                    )

        return entries

    def _adjust_entry_names(
        self,
        entries: list[dict[str, str]],
        original_prefix: str,
        new_prefix: str,
    ) -> list[dict[str, str]]:
        """
        Adjust entry_names when top-level name changes due to conflicts.

        Args:
            entries: List of entry dicts with 'entry_name' keys
            original_prefix: Original top-level entry_name
            new_prefix: New top-level entry_name (after conflict resolution)

        Returns:
            List of entries with adjusted entry_names
        """
        adjusted_entries = []
        for entry in entries:
            entry_name = entry["entry_name"]
            if entry_name == original_prefix:
                # Top-level entry: use new name
                adjusted_entries.append(
                    {
                        **entry,
                        "entry_name": new_prefix,
                    }
                )
            elif entry_name.startswith(original_prefix + "/"):
                # Sub-entry: replace prefix
                relative_part = entry_name[len(original_prefix) + 1 :]
                new_entry_name = f"{new_prefix}/{relative_part}"
                adjusted_entries.append(
                    {
                        **entry,
                        "entry_name": new_entry_name,
                    }
                )
            else:
                # Should not happen, but keep as-is
                adjusted_entries.append(entry)
        return adjusted_entries

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

    def _ensure_inside_trash(self, trash_root: str, entry_name: str) -> str:
        """Ensure entry_name resolves inside trash_root and return joined path."""
        normalized_root = os.path.normpath(trash_root)
        candidate = os.path.normpath(os.path.join(normalized_root, entry_name))
        if os.path.commonpath([normalized_root, candidate]) != normalized_root:
            raise BadRequestError("Invalid entry path.")
        return candidate

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
