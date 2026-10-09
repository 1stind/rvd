"""
Public vote history API — no authentication required.

Lookup by order ID, phone, or email.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories import team as team_repo
from app.schemas.common import ok
from app.schemas.history import HistoryLookupResponse
from app.services import history_service

router = APIRouter(prefix="/api/v1/history", tags=["history"])


@router.get("/order/{order_id}")
async def lookup_order(order_id: str, session: AsyncSession = Depends(get_db)):
    payment = await history_service.lookup_by_order_id(session, order_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    team = await history_service.get_team_for_payment(session, payment.team_id)
    item = _build_item(payment, team)
    return ok({"payments": [item.model_dump()]})


@router.get("/phone/{phone}")
async def lookup_phone(phone: str, session: AsyncSession = Depends(get_db)):
    payments = await history_service.lookup_by_phone(session, phone)
    if not payments:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    items = []
    for p in payments:
        team = await history_service.get_team_for_payment(session, p.team_id)
        items.append(_build_item(p, team).model_dump())
    return ok({"payments": items})


@router.get("/email/{email}")
async def lookup_email(email: str, session: AsyncSession = Depends(get_db)):
    payments = await history_service.lookup_by_email(session, email)
    if not payments:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    items = []
    for p in payments:
        team = await history_service.get_team_for_payment(session, p.team_id)
        items.append(_build_item(p, team).model_dump())
    return ok({"payments": items})


def _build_item(payment, team):
    from app.schemas.history import HistoryPaymentItem
    return HistoryPaymentItem(
        id=payment.id,
        team_name=team.name if team else payment.team_id,
        package_label=payment.package_label,
        qty=payment.qty,
        amount=payment.amount,
        votes=payment.votes,
        status=payment.status,
        created_at=payment.created_at,
        supporter_name=payment.supporter_name,
        is_anonymous=payment.is_anonymous,
    )
