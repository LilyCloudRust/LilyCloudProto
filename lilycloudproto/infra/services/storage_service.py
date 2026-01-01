import os

from lilycloudproto.domain.driver import Driver
from lilycloudproto.infra.drivers.local_driver import LocalDriver
from lilycloudproto.infra.repositories.storage_repository import StorageRepository


class StorageService:
    storage_repo: StorageRepository
    # Temporary fixed trash root; future: derive from storage config/mount table.
    DEFAULT_TRASH_ROOT: str = os.getenv("TRASH_ROOT", "/tmp/lilycloud/.trash")

    def __init__(self, storage_repo: StorageRepository) -> None:
        self.storage_repo = storage_repo

    def get_driver(self, _path: str) -> Driver:
        return LocalDriver()

    def get_physical_path(self, path: str) -> str:
        return path

    def get_physical_paths(self, paths: list[str]) -> list[str]:
        return paths

    def get_user_root(self, user_id: int, path: str) -> str:
        return path

    def get_trash_root(self, src_path: str) -> str:
        """
        Get trash root directory.

        Temporary strategy: use a fixed trash root (env TRASH_ROOT or default),
        ignoring src_path. Future versions should fetch mount info from storage
        configuration and return the mount-specific trash directory.

        Args:
            src_path: Source file path (ignored for now, kept for API compatibility)

        Returns:
            Trash root directory path
        """
        _ = src_path  # placeholder until storage config is wired
        return os.path.normpath(self.DEFAULT_TRASH_ROOT)

    def validate_user_path(self, user_id: int, path: str) -> bool:
        # Temporarily skipped
        return True
