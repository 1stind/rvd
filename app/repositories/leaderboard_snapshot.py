"""
Leaderboard snapshot repository — point-in-time captures of team rankings.
"""
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leaderboard_snapshot import LeaderboardSnapshot
from app.utils import new_id


async def create_snapshot(
    session: AsyncSession,
    *,
    event_id: str,
    team_id: str,
    rank: int,
    total_votes: int,
) -> LeaderboardSnapshot:
    snap = LeaderboardSnapshot(
        id=new_id("lsnap"),
        event_id=event_id,
        team_id=team_id,
        rank=rank,
        total_votes=total_votes,
    )
    session.add(snap)
    await session.flush()
    return snap


async def get_latest_for_event(
    session: AsyncSession, event_id: str
) -> Sequence[LeaderboardSnapshot]:
    stmt = (
        select(LeaderboardSnapshot)
        .where(LeaderboardSnapshot.event_id == event_id, LeaderboardSnapshot.deleted_at.is_(None))
        .order_by(LeaderboardSnapshot.captured_at.desc(), LeaderboardSnapshot.rank.asc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_previous_rank(
    session: AsyncSession, event_id: str, team_id: str
) -> Optional[int]:
    stmt = (
        select(LeaderboardSnapshot.rank)
        .where(
            LeaderboardSnapshot.event_id == event_id,
            LeaderboardSnapshot.team_id == team_id,
            LeaderboardSnapshot.deleted_at.is_(None),
        )
        .order_by(LeaderboardSnapshot.captured_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return row if row is None else int(row)
