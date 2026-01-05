from sqlalchemy import select

from lilycloudproto.config import admin_settings
from lilycloudproto.domain.entities.user import User
from lilycloudproto.infra.database import AsyncSessionLocal
from lilycloudproto.infra.services.auth_service import AuthService


async def seed_admin(auth_service: AuthService) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.role == "admin"))
        admin = result.scalar_one_or_none()
        if not admin:
            hashed_password = auth_service.password_hash.hash(
                admin_settings.ADMIN_PASSWORD
            )
            admin_user = User(
                username=admin_settings.ADMIN_USERNAME,
                hashed_password=hashed_password,
                role="admin",
            )
            session.add(admin_user)
            await session.commit()
