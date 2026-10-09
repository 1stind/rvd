"""
Seed: initial admin user.
Production-safe: only creates user if it does not already exist.
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.security import hash_password
from app.enums.user_role import UserRole
from app.models.user import User
from app.utils import new_id

logger = logging.getLogger(__name__)


async def seed_admin(email: str, password: str, name: str = "Panitia Admin") -> None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == email.lower()))
        existing = result.scalar_one_or_none()
        if existing:
            logger.info("Admin %s sudah ada, lewati.", email)
            return

        user = User(
            id=new_id("usr"),
            email=email.lower(),
            name=name,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        logger.info("Admin seed selesai: %s", email)
