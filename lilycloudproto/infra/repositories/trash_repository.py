from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.domain.entities.trash import Trash


class TrashRepository:
    """Repository class for trash-related database operations."""

    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, trash: Trash) -> Trash:
        """Create a new trash entry in the database."""
        self.db.add(trash)
        await self.db.commit()
        await self.db.refresh(trash)
        return trash

    async def create_batch(self, trash_list: list[Trash]) -> None:
        """Batch create trash entries in the database."""
        if not trash_list:
            return
        self.db.add_all(trash_list)
        await self.db.commit()

    async def get_by_id(self, trash_id: int) -> Trash | None:
        """Retrieve a trash entry by ID. Returns None if not found."""
        result = await self.db.execute(select(Trash).where(Trash.trash_id == trash_id))
        return result.scalar_one_or_none()

    async def find_by_entry_name(self, entry_name: str) -> Trash | None:
        """Find a trash entry by entry_name. Returns None if not found."""
        result = await self.db.execute(
            select(Trash).where(Trash.entry_name == entry_name)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int) -> list[Trash]:
        """List all trash entries for a user."""
        result = await self.db.execute(select(Trash).where(Trash.user_id == user_id))
        return list(result.scalars().all())

    async def find_by_entry_names(self, entry_names: list[str]) -> dict[str, Trash]:
        """Batch find trash entries by entry_names. Returns a dict mapping
        entry_name to Trash."""
        if not entry_names:
            return {}
        result = await self.db.execute(
            select(Trash).where(Trash.entry_name.in_(entry_names))
        )
        trash_list = list(result.scalars().all())
        return {trash.entry_name: trash for trash in trash_list}

    async def find_by_user_and_path(
        self, user_id: int, dir: str, file_names: list[str]
    ) -> list[Trash]:
        """
        Find trash entries by user, directory, and file names.

        Args:
            user_id: User ID
            dir: Directory path in trash (relative to trash root)
            file_names: List of file names

        Returns:
            List of matching Trash entries
        """
        if not file_names:
            return []
        # Build entry_name patterns
        dir_prefix = dir.lstrip("/") if dir else ""
        entry_names = []
        for file_name in file_names:
            entry_name = f"{dir_prefix}/{file_name}" if dir_prefix else file_name
            entry_names.append(entry_name)
        result = await self.db.execute(
            select(Trash).where(
                Trash.user_id == user_id, Trash.entry_name.in_(entry_names)
            )
        )
        return list(result.scalars().all())

    async def delete(self, trash: Trash) -> None:
        """Delete a trash entry from the database."""
        await self.db.delete(trash)
        await self.db.commit()

    async def delete_by_ids(self, trash_ids: list[int]) -> None:
        """Delete multiple trash entries by IDs."""
        if not trash_ids:
            return
        await self.db.execute(delete(Trash).where(Trash.trash_id.in_(trash_ids)))
        await self.db.commit()

    async def delete_all_by_user(self, user_id: int) -> None:
        """Delete all trash entries for a user."""
        await self.db.execute(delete(Trash).where(Trash.user_id == user_id))
        await self.db.commit()

    async def delete_by_entry_names(self, entry_names: list[str]) -> None:
        """Delete multiple trash entries by entry_names."""
        if not entry_names:
            return
        await self.db.execute(delete(Trash).where(Trash.entry_name.in_(entry_names)))
        await self.db.commit()
