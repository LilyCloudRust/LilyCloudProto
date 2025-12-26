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
    async def save_file(self, path: str, content: bytes) -> None:
        pass

    @abstractmethod
    def get_file_stream(
        self, path: str, chunk_size: int = 1024 * 64
    ) -> AsyncGenerator[bytes]:
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        pass

    @abstractmethod
    def get_absolute_path(self, virtual_path: str) -> str:
        pass

    async def get_download_link(self, virtual_path: str) -> str | None:
        return None
