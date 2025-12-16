from lilycloudproto.domain.driver import Driver
from lilycloudproto.infra.drivers.local_driver import LocalDriver
from lilycloudproto.infra.repositories.storage_repository import StorageRepository


class StorageService:
    storage_repo: StorageRepository

    def __init__(self, storage_repo: StorageRepository) -> None:
        self.storage_repo = storage_repo

    def get_driver(self, _path: str) -> Driver:
        return LocalDriver()

    def get_physical_path(self, path: str) -> str:
        return path

    def get_physical_paths(self, paths: list[str]) -> list[str]:
        return paths
