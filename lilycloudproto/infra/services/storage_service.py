import os

from lilycloudproto.domain.driver import Base, Driver
from lilycloudproto.domain.entities.storage import Storage
from lilycloudproto.domain.values.admin.storage import LocalConfig, StorageType
from lilycloudproto.infra.drivers.local_driver import LocalDriver
from lilycloudproto.infra.repositories.storage_repository import StorageRepository


class StorageService:
    storage_repo: StorageRepository
    _cache: dict[str, Storage]

    def __init__(self, storage_repo: StorageRepository) -> None:
        self.storage_repo = storage_repo
        self._cache = {}

    async def initialize(self) -> None:
        """
        Build the storage cache table from the database.
        Should be called on application startup.
        """
        storages = await self.storage_repo.get_all()
        for storage in storages:
            self._cache[storage.mount_path] = storage

    def update_cache(self, storage: Storage) -> None:
        """Update the cache when a storage is created or updated."""
        self._cache[storage.mount_path] = storage

    def remove_from_cache(self, mount_path: str) -> None:
        """Remove a storage from the cache when deleted."""
        if mount_path in self._cache:
            del self._cache[mount_path]

    def get_driver(self, path: str, base: Base = Base.REGULAR) -> Driver:
        """Get the appropriate driver for the given path using longest prefix match."""
        print(f"Getting driver for path: {path}")
        storage = self._match_storage(path)
        print(f"Matched storage: {storage.type if storage else 'None'}")

        # Fallback to default local storage if no match found.
        if not storage:
            config = LocalConfig(
                root_path=os.path.join(os.getcwd(), "webdav"),
                trash_path=os.path.join(os.getcwd(), "webdav", ".Trash"),
            ).model_dump()

            storage = Storage(
                storage_id=0,
                mount_path="/",
                type=StorageType.LOCAL,
                config=config,
                enabled=True,
            )

        if storage.type == StorageType.LOCAL:
            return LocalDriver(storage, base)

        # Add other drivers here (S3, SMB, etc.)
        raise NotImplementedError(f"Driver for type '{storage.type}' not implemented.")

    def _match_storage(self, path: str) -> Storage | None:
        """Find the storage with the longest matching prefix."""
        matches: list[Storage] = []

        # Ensure path is clean for matching
        clean_path = path.rstrip("/") if path != "/" else path

        for mount_path, storage in self._cache.items():
            # Clean mount path for consistent comparison
            clean_mount = mount_path.rstrip("/") if mount_path != "/" else mount_path

            if clean_mount == "/":
                # Root always matches everything
                matches.append(storage)
            elif clean_path == clean_mount or clean_path.startswith(clean_mount + "/"):
                # Exact match OR path starts with "mount_path/" (directory boundary)
                matches.append(storage)

        if not matches:
            return None

        # Return the match with the longest mount_path (Longest Prefix Match)
        return max(matches, key=lambda s: len(s.mount_path))
