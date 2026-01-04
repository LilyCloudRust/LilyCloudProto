from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Awaitable, Callable

from lilycloudproto.domain.entities.storage import Storage
from lilycloudproto.domain.values.files.file import File
from lilycloudproto.domain.values.files.list import ListArgs
from lilycloudproto.domain.values.files.search import SearchArgs


class Driver(ABC):
    storage: Storage

    def __init__(self, storage: Storage):
        self.storage = storage

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
    async def write(self, path: str, content_stream: AsyncGenerator[bytes]) -> None:
        pass

    @abstractmethod
    def read(self, path: str, chunk_size: int = 1024 * 64) -> AsyncGenerator[bytes]:
        pass

    @abstractmethod
    async def get_link(self, path: str) -> str | None:
        pass

    @abstractmethod
    async def rename(self, src_path: str, dst_path: str) -> None:
        pass
