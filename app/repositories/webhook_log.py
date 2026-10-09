"""
Webhook log repository — immutable records of incoming webhook payloads.
"""
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_log import WebhookLog
from app.utils import new_id


async def create_log(
    session: AsyncSession,
    *,
    payment_id: str,
    payload: dict,
    signature: Optional[str] = None,
    is_valid: bool = True,
) -> WebhookLog:
    log = WebhookLog(
        id=new_id("wlog"),
        payment_id=payment_id,
        payload=payload,
        signature=signature,
        is_valid=is_valid,
    )
    session.add(log)
    await session.flush()
    return log


async def list_by_payment(
    session: AsyncSession, payment_id: str
) -> Sequence[WebhookLog]:
    stmt = (
        select(WebhookLog)
        .where(WebhookLog.payment_id == payment_id, WebhookLog.deleted_at.is_(None))
        .order_by(WebhookLog.received_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()
