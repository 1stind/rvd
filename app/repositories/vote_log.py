"""
Vote log repository — immutable vote records. Queries only; no updates/deletes.
"""
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vote_log import VoteLog


async def create_vote_log(
    session: AsyncSession,
    *,
    payment_id: str,
    team_id: str,
    event_id: str,
    votes: int,
    payment_amount: int,
    package_code: Optional[str] = None,
    package_label: Optional[str] = None,
) -> VoteLog:
    log = VoteLog(
        payment_id=payment_id,
        team_id=team_id,
        event_id=event_id,
        votes=votes,
        payment_amount=payment_amount,
        package_code=package_code,
        package_label=package_label,
    )
    session.add(log)
    await session.flush()
    return log


async def get_total_votes(session: AsyncSession, event_id: Optional[str] = None) -> int:
    stmt = select(func.coalesce(func.sum(VoteLog.votes), 0))
    if event_id:
        stmt = stmt.where(VoteLog.event_id == event_id)
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def get_vote_count_for_team(session: AsyncSession, team_id: str) -> int:
    """Returns the total number of votes for a single team."""
    stmt = (
        select(func.coalesce(func.sum(VoteLog.votes), 0))
        .where(VoteLog.team_id == team_id)
    )
    result = await session.execute(stmt)
    return int(result.scalar_one())
