"""
Vote service — combines vote log + team update + audit into one unit.
The caller commits, then calls leaderboard_service.schedule_push().
"""
from typing import Optional

from fastapi import Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.payment import Payment
from app.models.team import Team
from app.repositories import vote_log as vote_log_repo
from app.services import audit_service
from app.services.leaderboard_service import refresh_team_ranks


async def process_successful_payment(
    session: AsyncSession,
    payment: Payment,
    request: Optional[Request] = None,
) -> None:
    """Create vote log, update team totals and ranks, write audit."""
    event_id = payment.event_id
    team_id = payment.team_id

    # Serialise vote application per event: ranks are computed from a
    # consistent ordering, and two webhooks never lock team rows in opposite
    # orders (deadlock). Each holder only runs a few short statements.
    # FOR NO KEY UPDATE (key_share=True): a plain FOR UPDATE would also wait for
    # every in-flight invoice insert, whose FK check holds KEY SHARE on this row.
    await session.execute(
        select(Event.id).where(Event.id == event_id).with_for_update(key_share=True)
    )

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

    # Atomic increment in SQL; a Python read-modify-write loses votes when two
    # payments for the same team settle at the same time.
    await session.execute(
        update(Team)
        .where(Team.id == team_id)
        .values(
            total_votes=Team.total_votes + payment.votes,
            supporter_count=Team.supporter_count + 1,
        )
    )

    await audit_service.record(
        session,
        action="vote.created",
        request=request,
        entity_type="vote_log",
        entity_id=vote_log.id,
        detail={"payment_id": payment.id, "votes": payment.votes},
    )

    await refresh_team_ranks(session, event_id)
