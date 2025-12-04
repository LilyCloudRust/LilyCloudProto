from abc import ABC, abstractmethod

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
