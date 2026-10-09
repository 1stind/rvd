"""
Database session management (SQLAlchemy 2.0 async).

Production: PostgreSQL via asyncpg (DATABASE_URL=postgresql+asyncpg://...).
Dev/test fallback: SQLite via aiosqlite (DATABASE_URL=sqlite+aiosqlite:///...).
All repositories depend on app.core.database.get_db — never import the
engine directly in business code.

Schema is managed exclusively by Alembic migrations. No create_all().
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG and not settings.is_sqlite,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a scoped async session."""
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
