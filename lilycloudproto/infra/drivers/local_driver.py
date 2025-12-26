import asyncio
import mimetypes
import os
import shutil
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from datetime import datetime
from typing import override

import aiofiles
import magic

from lilycloudproto.domain.driver import Driver
from lilycloudproto.domain.values.files.file import File, Type
from lilycloudproto.domain.values.files.list import ListArgs
from lilycloudproto.domain.values.files.search import SearchArgs
from lilycloudproto.domain.values.files.sort import SortArgs
from lilycloudproto.error import (
    BadRequestError,
    ConflictError,
    InternalServerError,
    NotFoundError,
)


class LocalDriver(Driver):
    @override
    def list_dir(self, args: ListArgs) -> list[File]:
        files: list[File] = []
        self._validate_directory(args.path)
        for entry in os.scandir(args.path):
            if not entry.is_junction() and not entry.is_symlink():
                # Ignore symbolic links due to security reason for now.
                files.append(self._entry_to_file(entry))
        return self._sort_files(files, args)

    @override
    def info(self, path: str) -> File:
        if not self._validate_path(path):
            # Ignore symbolic links due to security reason for now.
            raise NotFoundError(f"File not found at '{path}'.")
        stat = os.stat(path)
        name = os.path.basename(path)
        mime_type = self._get_mime_type(path)
        return File(
            name=name,
            path=path,
            type=Type.DIRECTORY if os.path.isdir(path) else Type.FILE,
            size=stat.st_size,
            mime_type=mime_type,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            accessed_at=datetime.fromtimestamp(stat.st_atime),
        )

    @override
    def search(self, args: SearchArgs) -> list[File]:
        self._validate_directory(args.path)
        result: list[File] = []
        for entry in self._walk_entries(args.path, args.recursive):
            if (
                not entry.is_symlink()
                and not entry.is_junction()
                and self._match_entry(entry, args)
            ):
                result.append(self._entry_to_file(entry))
        return self._sort_files(result, args)

    @override
    def mkdir(self, path: str, parents: bool = False) -> File:
        if os.path.exists(path):
            raise ConflictError(f"Directory already exists at '{path}'.")
        try:
            if parents:
                os.makedirs(path, exist_ok=False)
            else:
                os.mkdir(path)
        except Exception as error:
            raise InternalServerError(
                f"Failed to create directory '{path}': {error}."
            ) from error
        stat = os.stat(path)
        return File(
            name=os.path.basename(path),
            path=path,
            type=Type.DIRECTORY,
            size=stat.st_size,
            mime_type="inode/directory",
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            accessed_at=datetime.fromtimestamp(stat.st_atime),
        )

    @override
    async def copy(
        self,
        src_dir: str,
        dst_dir: str,
        file_names: list[str],
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        total = len(file_names)
        self._validate_directory(src_dir)
        self._validate_directory(dst_dir)

        for index, name in enumerate(file_names, 1):
            src_path = os.path.join(src_dir, name)
            dst_path = os.path.join(dst_dir, name)
            if not self._validate_path(src_path):
                continue
            if os.path.exists(dst_path):
                raise ConflictError(f"Destination '{dst_path}' already exists.")
            try:
                if os.path.isdir(src_path):
                    _ = shutil.copytree(src_path, dst_path, symlinks=False)
                else:
                    _ = shutil.copy2(src_path, dst_path)
            except Exception as error:
                raise InternalServerError(
                    f"Failed to copy '{src_path}' to '{dst_path}': {error}"
                ) from error
            if progress_callback:
                await progress_callback(index, total)
            await asyncio.sleep(0)

    @override
    async def move(
        self,
        src_dir: str,
        dst_dir: str,
        file_names: list[str],
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        total = len(file_names)
        self._validate_directory(src_dir)
        self._validate_directory(dst_dir)

        for index, name in enumerate(file_names, 1):
            src_path = os.path.join(src_dir, name)
            dst_path = os.path.join(dst_dir, name)
            if not self._validate_path(src_path):
                continue
            if os.path.exists(dst_path):
                raise ConflictError(f"Destination '{dst_path}' already exists.")
            try:
                _ = shutil.move(src_path, dst_path)
            except Exception as error:
                raise InternalServerError(
                    f"Failed to move '{src_path}' to '{dst_path}': {error}"
                ) from error
            if progress_callback:
                await progress_callback(index, total)
            await asyncio.sleep(0)

    @override
    async def delete(
        self,
        dir: str,
        file_names: list[str],
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        total = len(file_names)
        self._validate_directory(dir)

        for index, name in enumerate(file_names, 1):
            path = os.path.join(dir, name)
            if not self._validate_path(path):
                continue
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as error:
                raise InternalServerError(
                    f"Failed to delete '{path}': {error}"
                ) from error
            if progress_callback:
                await progress_callback(index, total)
            await asyncio.sleep(0)

    def _validate_directory(self, dir: str) -> None:
        dir = os.path.normpath(dir)
        if not os.path.exists(dir) or os.path.islink(dir) or os.path.isjunction(dir):
            # Ignore symbolic links due to security reason for now.
            raise NotFoundError(f"Directory '{dir}' not found.")
        if not os.path.isdir(dir):
            raise BadRequestError(f"Path '{dir}' is not a directory.")

    def _validate_path(self, file: str) -> bool:
        file = os.path.normpath(file)
        return (
            os.path.exists(file)
            and not os.path.islink(file)
            and not os.path.isjunction(file)
        )

    def _get_mime_type(self, path: str) -> str:
        mime_type, _ = mimetypes.guess_type(path)
        if mime_type:
            return mime_type
        if os.path.isfile(path):
            return str(magic.from_file(path, mime=True))
        return "inode/directory"

    def _entry_to_file(self, entry: os.DirEntry[str]) -> File:
        stat = entry.stat()
        mime_type = self._get_mime_type(entry.path)
        return File(
            name=entry.name,
            path=entry.path,
            type=Type.DIRECTORY if entry.is_dir() else Type.FILE,
            size=stat.st_size,
            mime_type=mime_type,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            accessed_at=datetime.fromtimestamp(stat.st_atime),
        )

    def _match_entry(self, entry: os.DirEntry[str], args: SearchArgs) -> bool:
        if args.type:
            type_match = entry.is_file() if args.type == "file" else entry.is_dir()
            if not type_match:
                return False
        if args.keyword:
            keyword_match = args.keyword.lower() in entry.name.lower()
            if not keyword_match:
                return False
        if args.mime_type:
            mime_type = self._get_mime_type(entry.path)
            if args.mime_type.lower() not in mime_type.lower():
                return False
        return True

    def _walk_entries(self, path: str, recursive: bool) -> Generator[os.DirEntry[str]]:
        if recursive:
            for root, _dirs, _files in os.walk(path):
                for entry in os.scandir(root):
                    # Ignore symbolic links due to security reason for now.
                    if not entry.is_junction() and not entry.is_symlink():
                        yield entry

        else:
            for entry in os.scandir(path):
                # Ignore symbolic links due to security reason for now.
                if not entry.is_junction() and not entry.is_symlink():
                    yield entry

    def _sort_files(self, files: list[File], args: SortArgs) -> list[File]:
        reverse = args.sort_order == "desc"
        sort_key: dict[str, Callable[[File], str | int | float | datetime]] = {
            "name": lambda file: file.name,
            "size": lambda file: file.size,
            "created": lambda file: file.created_at,
            "modified": lambda file: file.modified_at,
            "accessed": lambda file: file.accessed_at,
            "type": lambda file: file.mime_type,
        }
        files.sort(key=sort_key[args.sort_by], reverse=reverse)
        if args.dir_first:
            files.sort(key=lambda file: file.type == "file")
        return files

    def _resolve_path(self, virtual_path: str) -> str:
        clean_path = virtual_path.lstrip("/\\")
        full_path = os.path.abspath(clean_path)
        return full_path

    async def save_file(self, path: str, content: bytes) -> None:
        full_path = self._resolve_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(content)

    async def get_file_bytes(self, path: str) -> bytes:
        full_path = self._resolve_path(path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {path}")
        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def get_file_stream(
        self, path: str, chunk_size: int = 1024 * 64
    ) -> AsyncGenerator[bytes]:
        full_path = self._resolve_path(path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {path}")
        async with aiofiles.open(full_path, "rb") as f:
            while chunk := await f.read(chunk_size):
                yield chunk

    async def exists(self, path: str) -> bool:
        full_path = self._resolve_path(path)
        return os.path.exists(full_path)

    async def is_file(self, path: str) -> bool:
        full_path = self._resolve_path(path)
        return os.path.isfile(full_path)

    async def create_dir(self, path: str) -> None:
        full_path = self._resolve_path(path)
        os.makedirs(full_path, exist_ok=True)

    def get_absolute_path(self, virtual_path: str) -> str:
        return self._resolve_path(virtual_path)
