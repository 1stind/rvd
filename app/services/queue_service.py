"""
Queue service — business logic for managing voting queue.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.queue_status import QueueStatus
from app.models.queue_session import QueueSession
from app.repositories import queue as queue_repo


async def enter_queue(
    session: AsyncSession, event_id: str, session_token: str, ttl_minutes: int = 15
) -> QueueSession:
    position = await queue_repo.get_next_position(session, event_id)
    entered_at = datetime.now(timezone.utc)
    expires_at = entered_at + timedelta(minutes=ttl_minutes)
    return await queue_repo.create_session(
        session,
        event_id=event_id,
        session_token=session_token,
        position=position,
        status=QueueStatus.WAITING,
        entered_at=entered_at,
        expires_at=expires_at,
    )


async def release_next(session: AsyncSession, event_id: str) -> Optional[QueueSession]:
    sessions = await queue_repo.list_by_event(session, event_id, QueueStatus.WAITING)
    if not sessions:
        return None
    next_session = sessions[0]
    next_session.status = QueueStatus.ACTIVE
    next_session.released_at = datetime.now(timezone.utc)
    await session.flush()
    return next_session


async def expire_old(session: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    stmt = (
        select(QueueSession)
        .where(QueueSession.status == QueueStatus.WAITING, QueueSession.expires_at < now)
    )
    result = await session.execute(stmt)
    expired = result.scalars().all()
    count = 0
    for qs in expired:
        qs.status = QueueStatus.EXPIRED
        count += 1
    if count:
        await session.flush()
    return count
