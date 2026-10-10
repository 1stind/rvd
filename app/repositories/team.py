"""
Team repository — all DB queries for teams live here.
Vote counts are stored directly on teams.total_votes (never derived from amount).
"""
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team


async def get_team(session: AsyncSession, team_id: str) -> Optional[Team]:
    return await session.get(Team, team_id)


async def list_teams(session: AsyncSession, event_id: str) -> Sequence[Team]:
    stmt = (
        select(Team)
        .where(Team.event_id == event_id, Team.deleted_at.is_(None))
        .order_by(Team.sort_order.asc(), Team.name.asc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def stats_by_event(
    session: AsyncSession, event_ids: Sequence[str]
) -> dict[str, tuple[int, int]]:
    """event_id -> (team count, total votes) for all given events in one query."""
    if not event_ids:
        return {}
    stmt = (
        select(Team.event_id, func.count(Team.id), func.coalesce(func.sum(Team.total_votes), 0))
        .where(Team.event_id.in_(event_ids), Team.deleted_at.is_(None))
        .group_by(Team.event_id)
    )
    result = await session.execute(stmt)
    return {event_id: (count, int(votes)) for event_id, count, votes in result.all()}


async def get_teams_with_votes(
    session: AsyncSession, event_id: str
) -> Sequence[tuple[Team, int]]:
    """Return (team, total_votes) pairs ordered by votes DESC, then name."""
    stmt = (
        select(Team, Team.total_votes)
        .where(Team.event_id == event_id, Team.deleted_at.is_(None))
        .order_by(Team.total_votes.desc(), Team.name.asc())
    )
    result = await session.execute(stmt)
    return result.all()
