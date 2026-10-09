"""
Public vote history lookup — no authentication required.

Supports lookup by:
- Order ID
- Phone number
- Email address
"""
import logging
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.models.team import Team

logger = logging.getLogger(__name__)


async def lookup_by_order_id(session: AsyncSession, order_id: str) -> Optional[Payment]:
    stmt = select(Payment).where(Payment.id == order_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def lookup_by_phone(session: AsyncSession, phone: str) -> Sequence[Payment]:
    stmt = (
        select(Payment)
        .where(Payment.supporter_phone == phone)
        .order_by(Payment.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def lookup_by_email(session: AsyncSession, email: str) -> Sequence[Payment]:
    stmt = (
        select(Payment)
        .where(Payment.supporter_email == email.lower())
        .order_by(Payment.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_team_for_payment(session: AsyncSession, team_id: str) -> Optional[Team]:
    return await session.get(Team, team_id)
