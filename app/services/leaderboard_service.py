"""
Leaderboard service — business logic for ranking and trends.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from app.models.leaderboard_snapshot import LeaderboardSnapshot
from app.models.team import Team
from app.repositories import leaderboard_snapshot as snapshot_repo
from app.repositories import team as team_repo
from app.utils import new_id


async def build_leaderboard(
    session: AsyncSession, event_id: str, limit: Optional[int] = None
) -> dict:
    """Return leaderboard payload ordered by votes desc, with ranking."""
    pairs = await team_repo.get_teams_with_votes(session, event_id)
    team_ids = [team.id for team, _ in pairs]
    trend_map = await _get_trends_batch(session, event_id, team_ids)

    entries = []
    for rank, (team, votes) in enumerate(pairs, start=1):
        if limit is not None and rank > limit:
            break
        trend = trend_map.get(team.id, "same")
        entries.append(
            {
                "id": team.id,
                "rank": rank,
                "team_id": team.id,
                "name": team.name,
                "school": team.school,
                "votes": votes,
                "trend": trend,
                "logo_url": getattr(team, "logo_url", None),
            }
        )
    return {
        "event_id": event_id,
        "entries": entries,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


async def _get_trends_batch(
    session: AsyncSession, event_id: str, team_ids: list[str]
) -> dict[str, str]:
    """Batch fetch latest two snapshots per team in a single query.

    Uses a subquery with ROW_NUMBER() window function, filtered to rn <= 2
    at the database level to avoid N+1 queries and minimize data transfer.
    """
    if not team_ids:
        return {}

    ranked = (
        select(
            LeaderboardSnapshot.team_id,
            LeaderboardSnapshot.rank,
            func.row_number()
            .over(
                partition_by=LeaderboardSnapshot.team_id,
                order_by=LeaderboardSnapshot.captured_at.desc(),
            )
            .label("rn"),
        )
        .where(
            LeaderboardSnapshot.event_id == event_id,
            LeaderboardSnapshot.team_id.in_(team_ids),
            LeaderboardSnapshot.deleted_at.is_(None),
        )
        .subquery("ranked_snapshots")
    )

    stmt = (
        select(ranked.c.team_id, ranked.c.rank, ranked.c.rn)
        .where(ranked.c.rn <= 2)
        .order_by(ranked.c.team_id, ranked.c.rn)
    )

    result = await session.execute(stmt)
    rows = result.all()

    latest: dict[str, list[tuple[int, int]]] = {}
    for team_id, rank, rn in rows:
        latest.setdefault(team_id, []).append((rn, rank))

    trend_map: dict[str, str] = {}
    for team_id, ranks in latest.items():
        ranks.sort(key=lambda x: x[0])
        if len(ranks) >= 2:
            current = ranks[0][1]
            previous = ranks[1][1]
            if current < previous:
                trend_map[team_id] = "up"
            elif current > previous:
                trend_map[team_id] = "down"
            else:
                trend_map[team_id] = "same"
        else:
            trend_map[team_id] = "same"
    return trend_map


async def refresh_team_ranks(session: AsyncSession, event_id: str) -> None:
    """Update current_rank on each team and create a new snapshot."""
    pairs = await team_repo.get_teams_with_votes(session, event_id)
    for rank, (team, votes) in enumerate(pairs, start=1):
        team.current_rank = rank
        await snapshot_repo.create_snapshot(
            session,
            event_id=event_id,
            team_id=team.id,
            rank=rank,
            total_votes=votes,
        )
    await session.flush()


async def get_trend(session: AsyncSession, team_id: str, event_id: str) -> str:
    return await _get_trend(session, event_id, team_id)


async def _get_trend(session: AsyncSession, event_id: str, team_id: str) -> str:
    """Compare current rank vs previous snapshot (single team — kept for backward compat)."""
    stmt = (
        select(LeaderboardSnapshot)
        .where(
            LeaderboardSnapshot.event_id == event_id,
            LeaderboardSnapshot.team_id == team_id,
            LeaderboardSnapshot.deleted_at.is_(None),
        )
        .order_by(LeaderboardSnapshot.captured_at.desc())
        .limit(2)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    if len(rows) < 2:
        return "same"
    current_rank = rows[0].rank
    previous_rank = rows[1].rank
    if current_rank < previous_rank:
        return "up"
    if current_rank > previous_rank:
        return "down"
    return "same"
