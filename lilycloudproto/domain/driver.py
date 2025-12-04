from abc import ABC, abstractmethod

from lilycloudproto.models.files.file import File
from lilycloudproto.models.files.list import ListArgs
from lilycloudproto.models.files.search import SearchArgs


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
