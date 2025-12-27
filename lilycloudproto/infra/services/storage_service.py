import os

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

    def get_trash_root(self, path: str = "") -> str:
        """
        Get the trash root directory for a given path.
        Follows AList strategy: .trash directory at the mount point (storage root).
        If mount point is root (/), use user's home directory instead.
        """
        if not path:
            return os.path.abspath(".trash")

        # Find mount point or root of the path
        current_path = os.path.abspath(path)
        while not os.path.ismount(current_path):
            parent = os.path.dirname(current_path)
            if parent == current_path:  # Reached root
                break
            current_path = parent

        # If mount point is root (/), use home directory to avoid permission issues
        if current_path == "/":
            home_dir = os.path.expanduser("~")
            return os.path.join(home_dir, ".trash")

        return os.path.join(current_path, ".trash")
