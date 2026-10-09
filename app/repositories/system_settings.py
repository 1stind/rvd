"""
System settings repository — key-value store for application configuration.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_settings import SystemSettings


async def get(session: AsyncSession, key: str) -> Optional[SystemSettings]:
    return await session.get(SystemSettings, key)


async def get_bulk(session: AsyncSession, keys: list[str]) -> dict[str, str]:
    stmt = select(SystemSettings).where(SystemSettings.key.in_(keys), SystemSettings.deleted_at.is_(None))
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return {row.key: row.value or "" for row in rows}


async def set(
    session: AsyncSession,
    key: str,
    value: Optional[str],
    description: Optional[str] = None,
) -> SystemSettings:
    existing = await session.get(SystemSettings, key)
    if existing:
        existing.value = value
        existing.description = description
        await session.flush()
        return existing
    settings = SystemSettings(
        key=key,
        value=value,
        description=description,
    )
    session.add(settings)
    await session.flush()
    return settings
