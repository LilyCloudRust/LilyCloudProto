import os

from lilycloudproto.domain.driver import Base, Driver
from lilycloudproto.domain.entities.storage import Storage
from lilycloudproto.domain.values.admin.storage import LocalConfig, StorageType
from lilycloudproto.infra.drivers.local_driver import LocalDriver
from lilycloudproto.infra.repositories.storage_repository import StorageRepository


class StorageService:
    storage_repo: StorageRepository

    def __init__(self, storage_repo: StorageRepository) -> None:
        self.storage_repo = storage_repo

    def get_driver(self, _path: str, base: Base = Base.REGULAR) -> Driver:
        # Create a temporary LocalConfig
        config = LocalConfig(
            root_path=os.path.join(os.getcwd(), "webdav"),
            trash_path=os.path.join(os.getcwd(), "webdav", ".Trash"),
        ).model_dump()

        # Create a temporary Storage entity
        storage = Storage(
            storage_id=0,
            mount_path="/",
            type=StorageType.LOCAL,
            config=config,
            enabled=True,
        )
        return LocalDriver(storage, base)

    def get_physical_path(self, path: str) -> str:
        return path

    def get_physical_paths(self, paths: list[str]) -> list[str]:
        return paths
