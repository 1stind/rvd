"""
Queue repository — all DB queries for queue sessions.
"""
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.queue_status import QueueStatus
from app.models.queue_session import QueueSession
from app.utils import new_id


async def create_session(
    session: AsyncSession,
    *,
    event_id: str,
    session_token: str,
    position: int,
    status: QueueStatus,
    entered_at: datetime,
    expires_at: Optional[datetime] = None,
) -> QueueSession:
    qs = QueueSession(
        id=new_id("qs"),
        event_id=event_id,
        session_token=session_token,
        position=position,
        status=status,
        entered_at=entered_at,
        expires_at=expires_at,
    )
    session.add(qs)
    await session.flush()
    return qs


async def get_by_token(session: AsyncSession, token: str) -> Optional[QueueSession]:
    stmt = select(QueueSession).where(QueueSession.session_token == token)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_by_event(
    session: AsyncSession, event_id: str, status: Optional[QueueStatus] = None
) -> Sequence[QueueSession]:
    stmt = select(QueueSession).where(QueueSession.event_id == event_id)
    if status is not None:
        stmt = stmt.where(QueueSession.status == status)
    stmt = stmt.order_by(QueueSession.position.asc())
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_status(session: AsyncSession, session_id: str, status: QueueStatus) -> None:
    qs = await session.get(QueueSession, session_id)
    if qs:
        qs.status = status
        await session.flush()


async def get_next_position(session: AsyncSession, event_id: str) -> int:
    stmt = (
        select(QueueSession)
        .where(QueueSession.event_id == event_id, QueueSession.status == QueueStatus.WAITING)
        .order_by(QueueSession.position.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    last = result.scalar_one_or_none()
    return (last.position + 1) if last else 1
