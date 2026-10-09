"""
User repository — all DB queries for users live here.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_email(session: AsyncSession, email: str) -> Optional[User]:
    stmt = select(User).where(User.email == email.lower(), User.deleted_at.is_(None))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: str) -> Optional[User]:
    stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_users(session: AsyncSession) -> list[User]:
    stmt = select(User).where(User.deleted_at.is_(None)).order_by(User.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())
