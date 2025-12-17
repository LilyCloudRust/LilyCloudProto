import io
import os
import zipfile
from collections.abc import AsyncGenerator
from datetime import datetime

import aiofiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.domain.entities.task import Task
from lilycloudproto.domain.values.task import TaskStatus, TaskType
from lilycloudproto.infra.drivers.local_driver import LocalDriver
from lilycloudproto.models.task import TaskResponse


class FileTransferService:
    def __init__(self, storage_driver: LocalDriver, db: AsyncSession) -> None:
        self.driver = storage_driver
        # self.storage_root = os.path.abspath("./storage")
        self.db = db

    def _get_real_path(self, virtual_path: str) -> str:
        clean_path = virtual_path.lstrip("/\\")
        real_path = os.path.abspath(clean_path)
        return real_path

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
        return TaskResponse(**task.__dict__)

    async def process_upload_files(
        self, task_id: int, dst_dir: str, files: list[bytes], filenames: list[str]
    ) -> None:
        stmt = select(Task).where(Task.task_id == task_id)
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            return

        try:
            target_dir = self._get_real_path(dst_dir)
            os.makedirs(target_dir, exist_ok=True)

            total = len(files)
            for i, (content, name) in enumerate(zip(files, filenames, strict=True)):

                file_path = os.path.join(target_dir, name)
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(content)

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
        real_base = self._get_real_path(src_dir)
        if not os.path.exists(real_base):
            raise FileNotFoundError(f"Directory {src_dir} not found")
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
        return TaskResponse(**task.__dict__)

    async def get_task(self, task_id: int) -> Task:
        stmt = select(Task).where(Task.task_id == task_id)
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError("Task not found")
        return task

    def get_file_path_for_download(self, virtual_path: str) -> str:
        path = self._get_real_path(virtual_path)
        if not os.path.exists(path) or not os.path.isfile(path):
            raise FileNotFoundError("File not found")
        return path

    async def archive_stream_generator(self, task_id: int) -> AsyncGenerator[bytes]:
        task = await self.get_task(task_id)
        src_dir = task.src_dir or ""
        file_names = task.file_names

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        await self.db.commit()

        zip_buffer = io.BytesIO()
        async with aiofiles.tempfile.TemporaryDirectory():
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                total = len(file_names)
                processed = 0
                for processed, fname in enumerate(file_names, start=1):
                    full_path = self._get_real_path(os.path.join(src_dir, fname))
                    try:
                        async with aiofiles.open(full_path, "rb") as f:
                            data = await f.read()
                        zf.writestr(fname, data)
                    except Exception as e:
                        zf.writestr(f"{fname}.error.txt", f"Error: {e}")
                    task.progress = (processed / total) * 100
                    await self.db.commit()

                    if zip_buffer.tell() > 0:
                        zip_buffer.seek(0)
                        yield zip_buffer.read()
                        zip_buffer.seek(0)
                        zip_buffer.truncate(0)

            zip_buffer.seek(0)
            yield zip_buffer.read()

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        task.progress = 100.0
        await self.db.commit()
