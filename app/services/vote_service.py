"""
Vote service — combines vote log + team update + audit + cache into one unit.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.models.team import Team
from app.repositories import audit_log as audit_repo
from app.repositories import vote_log as vote_log_repo
from app.services import audit_service, cache
from app.services.leaderboard_service import refresh_team_ranks


async def process_successful_payment(
    session: AsyncSession,
    payment: Payment,
    request: Optional[Request] = None,
) -> None:
    """Create vote log, update team totals, write audit, publish to cache."""
    event_id = payment.event_id
    team_id = payment.team_id

    vote_log = await vote_log_repo.create_vote_log(
        session,
        payment_id=payment.id,
        team_id=team_id,
        event_id=event_id,
        votes=payment.votes,
        payment_amount=payment.amount,
        package_code=payment.package_code,
        package_label=payment.package_label,
    )
    await session.flush()

    team = await session.get(Team, team_id)
    if team:
        team.total_votes += payment.votes
        team.supporter_count += 1
        await session.flush()

    await audit_service.record(
        session,
        action="vote.created",
        request=request,
        entity_type="vote_log",
        entity_id=vote_log.id,
        detail={"payment_id": payment.id, "votes": payment.votes},
    )
    await session.flush()

    await refresh_team_ranks(session, event_id)
    await cache.publish({"type": "leaderboard_update", "event_id": event_id})
