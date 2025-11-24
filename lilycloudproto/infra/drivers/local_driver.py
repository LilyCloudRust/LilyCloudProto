import os
from collections.abc import Callable, Generator
from datetime import datetime
from typing import override

import magic

from lilycloudproto.error import NotFoundError
from lilycloudproto.infra.driver import Driver
from lilycloudproto.models.files.file import File
from lilycloudproto.models.files.list import ListArgs
from lilycloudproto.models.files.search import SearchArgs
from lilycloudproto.models.files.sort import SortArgs


class LocalDriver(Driver):
    @override
    def list_dir(self, args: ListArgs) -> list[File]:
        files: list[File] = []
        for entry in os.scandir(args.path):
            files.append(self._entry_to_file(entry))
        return self._sort_files(files, args)

    @override
    def info(self, path: str) -> File:
        if not os.path.exists(path):
            raise NotFoundError(f"File not found at '{path}'.")
        stat = os.stat(path)
        name = os.path.basename(path)
        mime_type = self._get_mime_type(path)
        return File(
            name=name,
            path=path,
            type="directory" if os.path.isdir(path) else "file",
            size=stat.st_size,
            mime_type=mime_type,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            accessed_at=datetime.fromtimestamp(stat.st_atime),
        )

    @override
    def search(self, args: SearchArgs) -> list[File]:
        result: list[File] = []
        for entry in self._walk_entries(args.path, args.recursive):
            if self._match_entry(entry, args):
                result.append(self._entry_to_file(entry))
        return self._sort_files(result, args)

    def _get_mime_type(self, path: str) -> str:
        if os.path.isfile(path):
            return magic.from_file(  # pyright: ignore[reportUnknownMemberType]
                path, mime=True
            )
        return "inode/directory"

    def _match_entry(self, entry: os.DirEntry[str], args: SearchArgs) -> bool:
        if args.type:
            return entry.is_file() if args.type == "file" else entry.is_dir()
        if args.keyword:
            return args.keyword in entry.name
        if args.mime_type:
            mime_type = self._get_mime_type(entry.path)
            return mime_type == args.mime_type
        return True

    def _entry_to_file(self, entry: os.DirEntry[str]) -> File:
        stat = entry.stat()
        mime_type = self._get_mime_type(entry.path)
        return File(
            name=entry.name,
            path=entry.path,
            type="directory" if entry.is_dir() else "file",
            size=stat.st_size,
            mime_type=mime_type,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            accessed_at=datetime.fromtimestamp(stat.st_atime),
        )

    def _walk_entries(self, path: str, recursive: bool) -> Generator[os.DirEntry[str]]:
        if recursive:
            for root, _dirs, _files in os.walk(path):
                try:
                    for entry in os.scandir(root):
                        yield entry
                except Exception:
                    continue
        else:
            for entry in os.scandir(path):
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
