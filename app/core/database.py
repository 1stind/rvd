"""
Database session management (SQLAlchemy 2.0 async).

Production: PostgreSQL via asyncpg (DATABASE_URL=postgresql+asyncpg://...).
Dev/test fallback: SQLite via aiosqlite (DATABASE_URL=sqlite+aiosqlite:///...).
All repositories depend on app.core.database.get_db — never import the
engine directly in business code.

Schema is managed exclusively by Alembic migrations. No create_all().
"""
from collections.abc import AsyncGenerator
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


# Diagnostic startup log — logs driver type and URL source without exposing credentials.
_driver = settings.DATABASE_URL.split("://", 1)[0] if "://" in settings.DATABASE_URL else "unknown"
_host = ""
try:
    from urllib.parse import urlsplit
    parts = urlsplit(settings.DATABASE_URL)
    _host = parts.hostname or ""
    _port = parts.port or ""
except Exception:
    pass
logging.getLogger("app.core.database").warning(
    "DB diag: driver=%s host=%s port=%s is_sqlite=%s",
    _driver, _host, _port, settings.is_sqlite,
)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG and not settings.is_sqlite,
    pool_size=1,
    max_overflow=2,
    pool_timeout=5,
    pool_recycle=180,
    pool_pre_ping=True,
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
