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

    def get_user_root(self, user_id: int, path: str) -> str:
        return path

    def get_trash_root(self, src_path: str) -> str:
        """
        Get trash root directory from source path.

        Temporarily implemented by inferring mount point from src_path.
        Future: Query Storage table for mount_path and use {mount_path}/.trash.

        Args:
            src_path: Source file path

        Returns:
            Trash root directory path (e.g., /mnt/data/.trash)
        """
        # Temporarily: infer mount point from src_path
        # Example: /mnt/data/user_1/Documents -> /mnt/data/.trash
        user_root = self.get_user_root(0, src_path)  # user_id not needed for inference
        # Get parent directory as mount point
        mount_point = os.path.dirname(user_root)
        if not mount_point or mount_point == os.sep:
            # If no parent, use user_root as mount point
            mount_point = user_root
        return os.path.join(mount_point, ".trash")

    def validate_user_path(self, user_id: int, path: str) -> bool:
        # Temporarily skipped
        return True
