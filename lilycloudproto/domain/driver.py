from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Awaitable, Callable

from lilycloudproto.domain.values.files.file import File
from lilycloudproto.domain.values.files.list import ListArgs
from lilycloudproto.domain.values.files.search import SearchArgs


class Driver(ABC):
    @abstractmethod
    def list_dir(self, args: ListArgs) -> list[File]:
        pass

    @abstractmethod
    def info(self, path: str) -> File:
        pass

    @abstractmethod
    def search(self, args: SearchArgs) -> list[File]:
        pass

    @abstractmethod
    def mkdir(self, path: str, parents: bool = False) -> File:
        pass

    @abstractmethod
    async def copy(
        self,
        src_dir: str,
        dst_dir: str,
        file_names: list[str],
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        pass

    @abstractmethod
    async def move(
        self,
        src_dir: str,
        dst_dir: str,
        file_names: list[str],
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        """
        Batch move files into a destination directory (keeping original filenames).
        """
        pass

    @abstractmethod
    async def delete(
        self,
        dir: str,
        file_names: list[str],
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        pass

    @abstractmethod
    def read(self, path: str, chunk_size: int = 1024 * 64) -> AsyncGenerator[bytes]:
        pass

    @abstractmethod
    async def write(self, path: str, content: bytes) -> None:
        """
        Write all bytes to a file at once.
        """
        pass

    @abstractmethod
    async def get_link(self, path: str) -> str | None:
        pass

    @abstractmethod
    async def rename(self, src_path: str, dst_path: str) -> None:
        """
        Rename or move a file/directory from src_path to dst_path.
        Crucial for WebDAV MOVE operations which often involve renaming.
        """
        pass

    @abstractmethod
    async def write_stream(
        self, path: str, content_stream: AsyncGenerator[bytes]
    ) -> None:
        """
        Write to a file using an async generator stream.
        Crucial for WebDAV PUT operations with large files to avoid memory exhaustion.
        """
        pass
