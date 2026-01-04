import asyncio
import mimetypes
import os
import shutil
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from datetime import datetime
from typing import override

import aiofiles
import magic

from lilycloudproto.domain.driver import Base, Driver
from lilycloudproto.domain.entities.storage import Storage
from lilycloudproto.domain.values.files.file import File, Type
from lilycloudproto.domain.values.files.list import ListArgs
from lilycloudproto.domain.values.files.search import SearchArgs
from lilycloudproto.domain.values.files.sort import SortArgs
from lilycloudproto.domain.values.storage import LocalConfig, StorageType
from lilycloudproto.error import (
    BadRequestError,
    ConflictError,
    InternalServerError,
    NotFoundError,
)


class LocalDriver(Driver):
    root_path: str
    trash_path: str
    base: Base

    def __init__(self, storage: Storage, base: Base = Base.REGULAR):
        super().__init__(storage)
        try:
            if storage.type != StorageType.LOCAL:
                raise ValueError(
                    f"LocalDriver requires storage type 'local', got '{storage.type}'"
                )
            config = LocalConfig.model_validate(storage.config)
        except Exception as error:
            raise ValueError(f"Invalid Local storage config: {error}") from error

        self.root_path = os.path.abspath(config.root_path)
        self.trash_path = os.path.abspath(config.trash_path)
        self.base = base

        if not os.path.exists(self.root_path):
            os.makedirs(self.root_path, exist_ok=True)
        if not os.path.exists(self.trash_path):
            os.makedirs(self.trash_path, exist_ok=True)

    @override
    def list_dir(self, args: ListArgs) -> list[File]:
        files: list[File] = []
        physical_path = self._get_physical_path(args.path)
        self._validate_directory(physical_path)

        for entry in os.scandir(physical_path):
            if not entry.is_junction() and not entry.is_symlink():
                logical_path = os.path.join(args.path, entry.name).replace("\\", "/")
                files.append(self._entry_to_file(entry, logical_path))

        return self._sort_files(files, args)

    @override
    def info(self, path: str) -> File:
        physical_path = self._get_physical_path(path)

        if not self._validate_path(physical_path):
            raise NotFoundError(f"File not found at '{path}'.")

        stat = os.stat(physical_path)
        name = os.path.basename(physical_path)
        mime_type = self._get_mime_type(physical_path)

        return File(
            name=name,
            path=path,
            type=Type.DIRECTORY if os.path.isdir(physical_path) else Type.FILE,
            size=stat.st_size,
            mime_type=mime_type,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            accessed_at=datetime.fromtimestamp(stat.st_atime),
        )

    @override
    def search(self, args: SearchArgs) -> list[File]:
        physical_path = self._get_physical_path(args.path)
        self._validate_directory(physical_path)

        result: list[File] = []
        for entry in self._walk_entries(physical_path, args.recursive):
            if (
                not entry.is_symlink()
                and not entry.is_junction()
                and self._match_entry(entry, args)
            ):
                try:
                    rel_path = os.path.relpath(entry.path, self.root_path)
                except ValueError:
                    continue
                logical_path = rel_path.replace("\\", "/")
                result.append(self._entry_to_file(entry, logical_path))
        return self._sort_files(result, args)

    @override
    def mkdir(self, path: str, parents: bool = False) -> File:
        physical_path = self._get_physical_path(path)

        if os.path.exists(physical_path):
            raise ConflictError(f"Directory already exists at '{path}'.")
        try:
            if parents:
                os.makedirs(physical_path, exist_ok=False)
            else:
                os.mkdir(physical_path)
        except Exception as error:
            raise InternalServerError(
                f"Failed to create directory '{path}': {error}."
            ) from error
        return self.info(path)

    @override
    async def copy(
        self,
        src_dir: str,
        dst_dir: str,
        file_names: list[str],
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        total = len(file_names)

        phys_src_dir = self._get_physical_path(src_dir)
        phys_dst_dir = self._get_physical_path(dst_dir)

        self._validate_directory(phys_src_dir)
        self._validate_directory(phys_dst_dir)

        for index, name in enumerate(file_names, 1):
            src_path = os.path.join(phys_src_dir, name)
            dst_path = os.path.join(phys_dst_dir, name)

            if not self._validate_path(src_path):
                continue
            if os.path.exists(dst_path):
                raise ConflictError(f"Destination '{name}' already exists.")
            try:
                if os.path.isdir(src_path):
                    _ = shutil.copytree(src_path, dst_path, symlinks=False)
                else:
                    _ = shutil.copy2(src_path, dst_path)
            except Exception as error:
                raise InternalServerError(
                    f"Failed to copy '{name}': {error}"
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
        phys_src_dir = self._get_physical_path(src_dir)
        phys_dst_dir = self._get_physical_path(dst_dir)

        self._validate_directory(phys_src_dir)
        self._validate_directory(phys_dst_dir)

        for index, name in enumerate(file_names, 1):
            src_path = os.path.join(phys_src_dir, name)
            dst_path = os.path.join(phys_dst_dir, name)
            if not self._validate_path(src_path):
                continue
            if os.path.exists(dst_path):
                raise ConflictError(f"Destination '{name}' already exists.")
            try:
                _ = shutil.move(src_path, dst_path)
            except Exception as error:
                raise InternalServerError(
                    f"Failed to move '{name}': {error}"
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
        phys_dir = self._get_physical_path(dir)
        self._validate_directory(phys_dir)

        for index, name in enumerate(file_names, 1):
            path = os.path.join(phys_dir, name)
            if not self._validate_path(path):
                continue
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as error:
                raise InternalServerError(
                    f"Failed to delete '{name}': {error}"
                ) from error
            if progress_callback:
                await progress_callback(index, total)
            await asyncio.sleep(0)

    @override
    async def write(self, path: str, content_stream: AsyncGenerator[bytes]) -> None:
        physical_path = self._get_physical_path(path)

        os.makedirs(os.path.dirname(physical_path), exist_ok=True)
        try:
            async with aiofiles.open(physical_path, "wb") as f:
                async for chunk in content_stream:
                    _ = await f.write(chunk)
        except Exception as error:
            raise InternalServerError(
                f"Failed to write stream to '{path}': {error}"
            ) from error

    @override
    async def read(
        self, path: str, chunk_size: int = 1024 * 64
    ) -> AsyncGenerator[bytes]:
        physical_path = self._get_physical_path(path)
        if not os.path.exists(physical_path):
            raise FileNotFoundError(f"File not found: {path}")
        async with aiofiles.open(physical_path, "rb") as f:
            while chunk := await f.read(chunk_size):
                yield chunk

    @override
    async def get_link(self, path: str) -> str | None:
        return None

    @override
    async def rename(self, src_path: str, dst_path: str) -> None:
        phys_src_path = self._get_physical_path(src_path)
        phys_dst_path = self._get_physical_path(dst_path)

        if not self._validate_path(phys_src_path):
            raise NotFoundError(f"Source file not found at '{src_path}'.")

        dst_dir = os.path.dirname(phys_dst_path)
        if not os.path.exists(dst_dir):
            raise NotFoundError("Destination directory does not exist.")

        if os.path.exists(phys_dst_path):
            raise ConflictError(f"Destination '{dst_path}' already exists.")

        try:
            _ = shutil.move(phys_src_path, phys_dst_path)
        except Exception as error:
            raise InternalServerError(f"Failed to rename: {error}") from error

    @override
    async def trash(
        self,
        dir: str,
        file_names: list[str],
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        """
        Move files from dir to trash_path.
        """
        total = len(file_names)
        phys_src_dir = self._get_physical_path(dir)
        self._validate_directory(phys_src_dir)

        for index, name in enumerate(file_names, 1):
            src_path = os.path.join(phys_src_dir, name)
            if not self._validate_path(src_path):
                continue

            # Move to trash root.
            trash_dst = os.path.join(self.trash_path, name)
            # Ensure no overwrite in trash.
            if os.path.exists(trash_dst):
                raise ConflictError(f"Trash already contains a file named '{name}'.")

            try:
                _ = shutil.move(src_path, trash_dst)
            except Exception as error:
                raise InternalServerError(
                    f"Failed to move '{name}' to trash: {error}."
                ) from error

            if progress_callback:
                await progress_callback(index, total)
            await asyncio.sleep(0)

    @override
    async def restore(
        self,
        src_paths: list[str],
        dst_paths: list[str],
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        """
        Move files from trash_path (src_paths, relative to trash root) to dst_paths.
        """
        if len(src_paths) != len(dst_paths):
            raise ValueError("src_paths and dst_paths must have the same length.")
        total = len(src_paths)

        for index, (src_rel, dst_rel) in enumerate(
            zip(src_paths, dst_paths, strict=True), 1
        ):
            trash_src = os.path.join(self.trash_path, src_rel.lstrip("/\\"))
            restore_dst = self._get_physical_path(dst_rel)

            if not self._validate_path(trash_src):
                continue

            os.makedirs(os.path.dirname(restore_dst), exist_ok=True)

            try:
                _ = shutil.move(trash_src, restore_dst)
            except Exception as error:
                raise InternalServerError(
                    f"Failed to restore '{src_rel}' to '{dst_rel}': {error}"
                ) from error

            if progress_callback:
                await progress_callback(index, total)
            await asyncio.sleep(0)

    def _get_physical_path(self, logical_path: str) -> str:
        logical_path = logical_path.lstrip("/\\")
        if self.base == Base.REGULAR:
            root = self.root_path
        elif self.base == Base.TRASH:
            root = self.trash_path
        elif self.base == Base.SHARE:
            # Update when share functionality is implemented.
            root = self.root_path
        else:
            raise ValueError(f"Unknown base: {self.base}")
        physical_path = os.path.join(root, logical_path)
        physical_path = os.path.normpath(physical_path)
        if not physical_path.startswith(root):
            raise BadRequestError("Path traversal detected.")
        return physical_path

    def _validate_directory(self, dir: str) -> None:
        dir = os.path.normpath(dir)
        if not os.path.exists(dir) or os.path.islink(dir) or os.path.isjunction(dir):
            raise NotFoundError("Directory not found.")
        if not os.path.isdir(dir):
            raise BadRequestError("Path is not a directory.")

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
            return str(
                magic.from_file(  # pyright: ignore[reportUnknownMemberType]
                    path, mime=True
                )
            )
        return "inode/directory"

    def _entry_to_file(self, entry: os.DirEntry[str], logical_path: str) -> File:
        stat = entry.stat()
        mime_type = self._get_mime_type(entry.path)
        return File(
            name=entry.name,
            path=logical_path,
            type=Type.DIRECTORY if entry.is_dir() else Type.FILE,
            size=stat.st_size,
            mime_type=mime_type,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            accessed_at=datetime.fromtimestamp(stat.st_atime),
        )

    def _walk_entries(self, path: str, recursive: bool) -> Generator[os.DirEntry[str]]:
        if recursive:
            for root, _dirs, _files in os.walk(path):
                for entry in os.scandir(root):
                    if not entry.is_junction() and not entry.is_symlink():
                        yield entry
        else:
            for entry in os.scandir(path):
                if not entry.is_junction() and not entry.is_symlink():
                    yield entry

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
