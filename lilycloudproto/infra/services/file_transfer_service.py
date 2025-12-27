import asyncio
import os
import tempfile
import zipfile
from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.domain.driver import Driver
from lilycloudproto.domain.entities.task import Task
from lilycloudproto.domain.values.task import TaskStatus, TaskType
from lilycloudproto.infra.services.storage_service import StorageService
from lilycloudproto.models.files.transfer import DownloadResource
from lilycloudproto.models.task import TaskResponse


class FileTransferService:
    driver: Driver
    storage_service: StorageService
    db: AsyncSession

    def __init__(
        self, storage_driver: Driver, storage_service: StorageService, db: AsyncSession
    ) -> None:
        self.driver = storage_driver
        self.storage_service = storage_service
        self.db = db

    async def create_upload_task(
        self, user_id: int, dst_dir: str, file_names: list[str]
    ) -> TaskResponse:
        now = datetime.now()
        task = Task(
            task_id=None,
            user_id=user_id,
            type=TaskType.UPLOAD,
            src_dir=None,
            dst_dirs=[dst_dir],
            file_names=file_names,
            status=TaskStatus.RUNNING,
            progress=0.0,
            message="Uploading...",
            created_at=now,
            started_at=now,
            updated_at=now,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return TaskResponse.model_validate(task)

    async def process_upload_files(
        self, task_id: int, dst_dir: str, files: list[bytes], filenames: list[str]
    ) -> None:
        stmt = select(Task).where(Task.task_id == task_id)
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            return

        try:
            total = len(files)
            for i, (content, name) in enumerate(zip(files, filenames, strict=True)):
                file_virtual_path = os.path.join(dst_dir, name)
                await self.driver.write(file_virtual_path, content)

                task.progress = ((i + 1) / total) * 100
                task.updated_at = datetime.now()

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.message = "Upload success"
            await self.db.commit()

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.message = str(e)
            await self.db.commit()

    async def create_download_task(
        self, user_id: int, src_dir: str, file_names: list[str]
    ) -> TaskResponse:
        now = datetime.now()
        task = Task(
            task_id=None,
            user_id=user_id,
            type=TaskType.DOWNLOAD,
            src_dir=src_dir,
            dst_dirs=[],
            file_names=file_names,
            status=TaskStatus.PENDING,
            progress=0.0,
            message="Ready to stream",
            created_at=now,
            updated_at=now,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return TaskResponse.model_validate(task)

    async def get_task(self, task_id: int) -> Task:
        stmt = select(Task).where(Task.task_id == task_id)
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError("Task not found")
        return task

    async def get_download_resource(self, virtual_path: str) -> DownloadResource:
        filename = os.path.basename(virtual_path)

        url = await self.driver.get_link(virtual_path)
        if url:
            return DownloadResource("url", url, filename)

        real_path = self.storage_service.get_physical_path(virtual_path)
        if real_path and os.path.exists(real_path):
            return DownloadResource("path", real_path, filename)
        return DownloadResource("stream", self.driver.read(virtual_path), filename)

    async def archive_stream_generator(self, task_id: int) -> AsyncGenerator[bytes]:
        task = await self.get_task(task_id)
        src_dir = task.src_dir or ""
        file_names = task.file_names

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        await self.db.commit()

        # Create a temporary file to build the ZIP.
        fd, temp_path = tempfile.mkstemp(suffix=".zip")
        os.close(fd)  # Close the file descriptor, we will use the path

        try:
            # Build the complete ZIP file.
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                total_files = len(file_names)

                for idx, fname in enumerate(file_names, start=1):
                    file_virtual_path = os.path.join(src_dir, fname)

                    try:
                        # Open a writable stream inside the ZIP.
                        with zf.open(fname, "w", force_zip64=True) as dest_file:
                            source_stream = self.driver.read(
                                file_virtual_path, chunk_size=64 * 1024
                            )

                            async for chunk in source_stream:
                                dest_file.write(chunk)
                                await asyncio.sleep(0)

                    except Exception as e:
                        error_msg = f"Error compressing {fname}: {e!s}"
                        zf.writestr(f"{fname}.error.txt", error_msg)

                    task.progress = (idx / total_files) * 100
                    await self.db.commit()

            with open(temp_path, "rb") as f:
                while True:
                    chunk = f.read(64 * 1024)
                    if not chunk:
                        break
                    yield chunk
                    await asyncio.sleep(0)  # Yield control during streaming

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 100.0
            await self.db.commit()

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.message = str(e)
            await self.db.commit()
            raise e
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
