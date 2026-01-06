from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///./test.db"
# DATABASE_URL = "mysql+aiomysql://username:password@localhost:3306/database_name"
# DATABASE_URL = "postgresql+asyncpg://username:password@localhost:5432/database_name"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        # Ensure shares table is created before tokens due to foreign key dependency.
        from lilycloudproto.domain.entities import (  # noqa: PLC0415
            share,  # pyright: ignore[reportUnusedImport]  # noqa: F401
        )

        await conn.run_sync(Base.metadata.create_all)
