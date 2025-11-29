import mimetypes
import os
from collections.abc import Callable, Generator
from datetime import datetime
from typing import override

import magic

from lilycloudproto.error import NotFoundError
from lilycloudproto.infra.driver import Driver
from lilycloudproto.models.files.file import File, Type
from lilycloudproto.models.files.list import ListArgs
from lilycloudproto.models.files.search import SearchArgs
from lilycloudproto.models.files.sort import SortArgs


class LocalDriver(Driver):
    @override
    def list_dir(self, args: ListArgs) -> list[File]:
        files: list[File] = []
        if not os.path.exists(args.path) or os.path.islink(args.path):
            # Ignore symbolic links due to security reason for now.
            raise NotFoundError(f"Directory not found at '{args.path}'.")
        for entry in os.scandir(args.path):
            if not entry.is_junction() and not entry.is_symlink():
                # Ignore symbolic links due to security reason for now.
                files.append(self._entry_to_file(entry))
        return self._sort_files(files, args)

    @override
    def info(self, path: str) -> File:
        if not os.path.exists(path) or os.path.islink(path):
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
        if not os.path.exists(args.path) or os.path.islink(args.path):
            # Ignore symbolic links due to security reason for now.
            raise NotFoundError(f"Directory not found at '{args.path}'.")
        result: list[File] = []
        for entry in self._walk_entries(args.path, args.recursive):
            if self._match_entry(entry, args):
                result.append(self._entry_to_file(entry))
        return self._sort_files(result, args)

    def _get_mime_type(self, path: str) -> str:
        mime_type, _ = mimetypes.guess_type(path)
        if mime_type:
            return mime_type
        if os.path.isfile(path):
            return magic.from_file(  # type: ignore[no-any-return]
                path, mime=True
            )
        return "inode/directory"

    def _match_entry(self, entry: os.DirEntry[str], args: SearchArgs) -> bool:
        if args.type:
            return entry.is_file() if args.type == "file" else entry.is_dir()
        if args.keyword:
            return args.keyword.lower() in entry.name.lower()
        if args.mime_type:
            mime_type = self._get_mime_type(entry.path)
            return args.mime_type.lower() in mime_type.lower()
        return True

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
            "type": lambda file: file.mime_type or "",
        }
        files.sort(key=sort_key[args.sort_by], reverse=reverse)
        if args.dir_first:
            files.sort(key=lambda file: file.type == "file")
        return files
