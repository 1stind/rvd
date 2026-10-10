"""Shared test setup.

The suite writes real rows (events, teams, payments) and never cleans up, so it
refuses to run unless DATABASE_URL points at a disposable database whose name
ends in "test" (e.g. postgresql+asyncpg://user@localhost/web_voting_test).
"""
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

# Test-only secrets; must exist before app.core.config is imported.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")

from app.core.config import settings  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models.event import EventStatus  # noqa: E402
from app.services import event_service  # noqa: E402

_db_name = Path(urlsplit(settings.DATABASE_URL).path).name.removesuffix(".db")
if not _db_name.endswith("test"):
    raise pytest.UsageError(
        f"Refusing to run tests against database {_db_name!r}. "
        "Set DATABASE_URL to a disposable database whose name ends in 'test'."
    )

# pytest-asyncio gives every test its own event loop; a pooled asyncpg
# connection from one loop breaks in the next. No pooling in tests.
async_session.configure(bind=create_async_engine(settings.DATABASE_URL, poolclass=NullPool))


@pytest.fixture(autouse=True)
def _fresh_discovery_cache(monkeypatch):
    import asyncio
    from app.services import public_page_cache

    public_page_cache._pages.clear()
    monkeypatch.setattr(public_page_cache, "_lock", asyncio.Lock())


@pytest.fixture(autouse=True)
def _mock_midtrans(monkeypatch):
    """Explicit mock mode by default; tests of the real gateway path override it."""
    monkeypatch.setattr(settings, "MIDTRANS_SERVER_KEY", "")
    monkeypatch.setattr(settings, "MIDTRANS_MOCK_MODE", True)


@pytest.fixture(autouse=True)
def _fresh_rate_limits(monkeypatch):
    """Each test starts with empty in-memory rate-limit windows (one fake client IP)."""
    from app.middleware import rate_limit

    monkeypatch.setattr(settings, "REDIS_URL", "memory://")
    rate_limit._memory_limiter._hits.clear()


@pytest.fixture(autouse=True)
def _inline_leaderboard_push(monkeypatch):
    """Push synchronously after each vote so tests can assert on it; coalescing has its own test."""
    monkeypatch.setattr(settings, "LEADERBOARD_PUSH_INTERVAL_SECONDS", 0)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncSession:
    """A new database session for each test function."""
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncClient:
    """An async test client bound to the ASGI app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def test_data(db_session: AsyncSession):
    """A voting-open event (Rp1.000 per vote) with one team."""
    event = await event_service.create_event(
        db_session,
        event_service.EventCreate(
            name="Test Event",
            status=EventStatus.VOTING_OPEN,
            price_per_vote=1000,
        ),
    )
    team = await event_service.create_team(
        db_session,
        event_service.TeamCreate(
            event_id=event.id,
            name="Test Team",
            school="Test School",
        ),
    )
    await db_session.commit()
    return {"event": event, "team": team}
