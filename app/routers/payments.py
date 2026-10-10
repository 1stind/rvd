"""
Payments API — create invoice (QRIS), status polling, Midtrans webhook.

Webhook menerima semua event Midtrans, memverifikasi signature, memproses
secara idempotent, membroadcast SSE leaderboard setelah vote masuk.
Dikecualikan dari CSRF (signature = otentikasi), tapi tetap dirate-limit.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.enums.payment_status import PaymentStatus
from app.repositories import payment as payment_repo
from app.repositories import team as team_repo
from app.schemas.common import ok
from app.schemas.payment import PaymentCreate, PaymentSimulateRequest
from app.services import cache, event_service, payment_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["payments"])


@router.post("/payments")
async def create_payment(
    payload: PaymentCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    idempotency_key = request.headers.get("Idempotency-Key")
    if idempotency_key:
        payload.idempotency_key = idempotency_key
    try:
        payment = await payment_service.create_payment(session, payload)
    except payment_service.PaymentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    team = await team_repo.get_team(session, payment.team_id)
    data = payment_service.to_payment_out(payment, team).model_dump()
    await session.commit()
    return ok(data, "Invoice pembayaran sudah dibuat")


@router.get("/payments/{payment_id}/status")
async def payment_status(
    payment_id: str,
    session: AsyncSession = Depends(get_db),
):
    payment = await payment_repo.get_payment(session, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")

    # Invoice kedaluwarsa secara lokal jika melewati expires_at.
    if payment.status == PaymentStatus.PENDING and payment.expires_at:
        from datetime import datetime, timezone

        if datetime.now(timezone.utc) > payment.expires_at:
            payment.status = PaymentStatus.EXPIRED
            await session.commit()

    team = await team_repo.get_team(session, payment.team_id)
    data = payment_service.to_payment_out(payment, team).model_dump()
    return ok(data)


@router.post("/payments/webhook")
async def midtrans_webhook(request: Request, session: AsyncSession = Depends(get_db)):
    raw = await request.body()
    try:
        payload = json.loads(raw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Payload JSON tidak valid") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload harus berupa JSON object")

    if not payment_service.verify_webhook_signature(payload, raw):
        logger.warning("Webhook signature invalid: %s", payload.get("order_id"))
        raise HTTPException(status_code=403, detail="Signature tidak valid")

    try:
        payment, voted_now = await payment_service.process_webhook(session, payload)
    except payment_service.PaymentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    await session.commit()

    if voted_now:
        # Update cache & broadcast SSE leaderboard refresh.
        event = await event_service.get_event_or_404(session, payment.event_id)
        fresh = await event_service.build_leaderboard(session, event.id)
        await cache.set_cached_leaderboard(event.id, fresh)
        await cache.publish({"type": "leaderboard", "event_id": event.id})

    return ok({"order_id": payment.id, "status": payment.status.value}, "Webhook diterima")


@router.post("/payments/mock/{payment_id}/simulate")
async def mock_simulate_payment(
    payment_id: str,
    payload: PaymentSimulateRequest,
    session: AsyncSession = Depends(get_db),
):
    """Simulate a Midtrans payment outcome (mock mode only).

    Mirrors ``POST /payments/webhook`` but without any Midtrans call — it is
    gated on ``settings.MIDTRANS_SERVER_KEY`` being empty (same condition that
    produces the mock QRIS fallback in ``create_payment``). When the server
    key is set the endpoint is intentionally hidden (404).
    """
    if settings.MIDTRANS_SERVER_KEY:
        raise HTTPException(status_code=404, detail="Mock endpoint tidak tersedia")

    try:
        payment = await payment_service.simulate_payment_status(
            session, payment_id, payload.action
        )
    except payment_service.PaymentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    team = await team_repo.get_team(session, payment.team_id)
    data = payment_service.to_payment_out(payment, team).model_dump()
    await session.commit()
    return ok(data, "Simulasi status pembayaran")