"""
Payment & vote engine business logic (service layer).

Rules enforced here:
- votes are derived from qty * price_per_vote for new payments
- vote_snapshot is stored per payment so future price changes never
  alter past transactions
- a vote is inserted ONLY after the payment reaches SUCCESS
- payments are never hard-deleted
- webhook is idempotent (re-process is a no-op)
"""
import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.enums.payment_gateway import PaymentGateway
from app.enums.payment_status import PaymentStatus
from app.models.payment import Payment
from app.models.team import Team
from app.repositories import payment as payment_repo
from app.repositories import team as team_repo
from app.repositories import vote_log as vote_log_repo
from app.repositories import webhook_log as webhook_log_repo
from app.schemas.payment import PaymentCreate, PaymentOut
from app.services import cache, event_service
from app.services.midtrans_service import create_transaction as midtrans_create_transaction
from app.services.midtrans_service import verify_signature as midtrans_verify_signature
from app.services.vote_service import process_successful_payment
from app.utils import new_id

logger = logging.getLogger(__name__)

INVOICE_TTL_MINUTES = 15
MOCK_QRIS_BASE = "WVC2026"

# Status Midtrans yang dianggap sukses → vote diberikan.
_SUCCESS_TRANSACTIONS = {"settlement", "capture"}
# Status yang final gagal (tidak akan berubah lagi).
_FAILED_TRANSACTIONS = {"deny", "cancel", "expire", "failure"}


class PaymentError(Exception):
    """Raised for expected business errors inside payment flow."""


def _build_snapshot(
    package_name: Optional[str],
    package_code: Optional[str],
    unit_price: Optional[int],
    bonus_votes: int,
    qty: int,
    is_anonymous: bool,
) -> dict:
    return {
        "package_name": package_name,
        "package_code": package_code,
        "unit_price": unit_price,
        "bonus_votes": bonus_votes,
        "qty": qty,
        "is_anonymous": is_anonymous,
    }


async def create_payment(
    session: AsyncSession,
    payload: PaymentCreate,
    user_id: Optional[str] = None,
) -> Payment:
    team = await team_repo.get_team(session, payload.team_id)
    if not team or team.deleted_at is not None:
        raise PaymentError("Tim tidak ditemukan")

    if team.event_id != payload.event_id:
        raise PaymentError("Event ID tidak cocok untuk tim yang dipilih")

    event = await event_service.get_event_or_404(session, payload.event_id)
    await event_service.require_voting_open(event)

    if not event.price_per_vote or event.price_per_vote <= 0:
        raise PaymentError("Harga vote untuk event ini belum diatur.")

    package_code = "custom"
    package_label = f"{payload.qty} vote"
    unit_price = event.price_per_vote
    bonus_votes = 0
    qty = payload.qty

    amount = (unit_price or 0) * qty
    votes = (unit_price or event.price_per_vote) * qty + bonus_votes

    snapshot = _build_snapshot(
        package_name=package_label,
        package_code=package_code,
        unit_price=unit_price,
        bonus_votes=bonus_votes,
        qty=qty,
        is_anonymous=payload.is_anonymous,
    )

    # Bersihkan PENDING yang sudah kedaluwarsa untuk phone+event yang sama.
    await payment_repo.expire_old_pendings_by_phone_and_event(
        session, event.id, payload.supporter_phone
    )

    # Cek PENDING aktif dengan pessimistic lock untuk mencegah race condition
    # pada kasus user klik checkout berkali-kali.
    existing = await payment_repo.get_active_pending_by_phone_and_event_for_update(
        session, event.id, payload.supporter_phone
    )
    if existing:
        raise PaymentError(
            "Anda masih memiliki invoice pembayaran yang belum selesai "
            "untuk event ini. Silakan selesaikan pembayaran atau tunggu "
            "invoice tersebut kedaluwarsa."
        )

    payment = Payment(
        id=new_id("pay"),
        team_id=team.id,
        event_id=event.id,
        user_id=user_id,
        package_id=payload.package_id,
        package_code=package_code,
        package_label=package_label,
        qty=qty,
        amount=amount,
        votes=votes,
        vote_snapshot=snapshot,
        supporter_name=payload.supporter_name,
        supporter_email=payload.supporter_email,
        supporter_phone=payload.supporter_phone,
        is_anonymous=payload.is_anonymous,
        status=PaymentStatus.PENDING,
        payment_gateway=PaymentGateway.MIDTRANS,
        currency=event.currency or "IDR",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=INVOICE_TTL_MINUTES),
    )
    session.add(payment)
    await session.flush()

    if settings.MIDTRANS_SERVER_KEY:
        try:
            result = midtrans_create_transaction(
                payment,
                server_key=settings.MIDTRANS_SERVER_KEY,
                is_production=settings.MIDTRANS_IS_PRODUCTION,
            )
            payment.midtrans_order_id = result.get("order_id", payment.id)
            payment.midtrans_transaction_id = result.get("transaction_id")
            payment.midtrans_payload = result
        except Exception as exc:
            logger.exception("Midtrans charge failed for payment %s", payment.id)
            raise PaymentError("Gagal membuat invoice pembayaran. Coba lagi.") from exc
    else:
        payment.midtrans_order_id = payment.id
        payment.midtrans_payload = {
            "mock": True,
            "qr_string": f"{MOCK_QRIS_BASE}:{event.id}:{payment.id}:{payment.amount}:{payment.votes}",
        }

    await session.flush()
    return payment


def to_payment_out(payment: Payment, team: Team) -> PaymentOut:
    is_mock = bool(payment.midtrans_payload and payment.midtrans_payload.get("mock"))
    return PaymentOut(
        id=payment.id,
        invoice_id=payment.id,
        team_id=payment.team_id,
        team_name=team.name,
        event_id=payment.event_id,
        package_code=payment.package_code,
        package_label=payment.package_label,
        qty=payment.qty,
        amount=payment.amount,
        votes=payment.votes,
        status=payment.status,
        payment_gateway=payment.payment_gateway,
        payment_channel=payment.payment_channel,
        currency=payment.currency,
        signature_key=payment.signature_key,
        qris_url=None if is_mock else (payment.midtrans_payload or {}).get("qr_url"),
        qr_string=None if not is_mock else (payment.midtrans_payload or {}).get("qr_string"),
        expires_at=payment.expires_at,
        webhook_received_at=payment.webhook_received_at,
        settled_at=payment.settled_at,
        created_at=payment.created_at,
        message="",
        supporter_name=payment.supporter_name,
        supporter_email=payment.supporter_email,
        supporter_phone=payment.supporter_phone,
        is_anonymous=payment.is_anonymous,
        is_mock=is_mock,
    )


def verify_webhook_signature(payload: dict, raw_body: bytes) -> bool:
    """Midtrans v2 webhook signature: SHA512(order_id+status_code+gross_amount+ServerKey)."""
    if not settings.MIDTRANS_SERVER_KEY:
        return True
    return midtrans_verify_signature(payload, raw_body, settings.MIDTRANS_SERVER_KEY)


async def process_webhook(session: AsyncSession, payload: dict) -> tuple[Payment, bool]:
    """Process a Midtrans notification.

    Returns (payment, voted_now) where voted_now tells the caller whether
    new votes were granted in this call (already flushed, not committed).
    """
    order_id = payload.get("order_id")
    if not order_id:
        raise PaymentError("order_id tidak ada di payload webhook")

    payment = await payment_repo.get_by_midtrans_order_id(session, order_id)
    if not payment:
        raise PaymentError(f"Payment {order_id} tidak ditemukan")

    # Signature sudah diverifikasi di level router menggunakan raw body asli.
    is_valid = True
    await webhook_log_repo.create_log(
        session,
        payment_id=payment.id,
        payload=payload,
        signature=payload.get("signature_key"),
        is_valid=is_valid,
    )
    await session.flush()

    if payment.status == PaymentStatus.SUCCESS:
        return payment, False

    transaction_status = (payload.get("transaction_status") or "").lower()
    fraud_status = (payload.get("fraud_status") or "").lower()

    if transaction_status in _SUCCESS_TRANSACTIONS and fraud_status != "challenge":
        if payment.status != PaymentStatus.SUCCESS:
            payment.status = PaymentStatus.SUCCESS
            payment.midtrans_transaction_id = payload.get("transaction_id")
            payment.midtrans_payload = payload
            payment.webhook_payload = payload
            payment.webhook_received_at = datetime.now(timezone.utc)
            payment.settled_at = datetime.now(timezone.utc)
            payment.paid_at = datetime.now(timezone.utc)
            await session.flush()
            await process_successful_payment(session, payment)
            await session.flush()
            return payment, True
    elif transaction_status in _FAILED_TRANSACTIONS or transaction_status == "cancel":
        payment.status = PaymentStatus.FAILED if transaction_status != "cancel" else PaymentStatus.CANCELED
        payment.midtrans_payload = payload
        payment.webhook_payload = payload
        payment.webhook_received_at = datetime.now(timezone.utc)
        await session.flush()

    return payment, False


async def simulate_payment_status(
    session: AsyncSession, payment_id: str, action: str
) -> Payment:
    """Simulate a Midtrans payment outcome for mock mode (no Midtrans call).

    Only meant to be used when ``settings.MIDTRANS_SERVER_KEY`` is empty (the
    same condition that gates the mock QRIS fallback in ``create_payment``).

    Reuses the *exact* idempotency guard from ``process_webhook``: an already
    SUCCESS payment is returned untouched so votes are never double-processed.
    After a SUCCESS simulation the full vote / leaderboard / cache / SSE
    sequence is run, mirroring the webhook router so leaderboard behaviour is
    identical whether the outcome came from Midtrans or the mock simulator.
    """
    payment = await payment_repo.get_payment(session, payment_id)
    if not payment:
        raise PaymentError("Invoice tidak ditemukan")

    # Idempotency guard — identical to process_webhook (line ~230).
    if payment.status == PaymentStatus.SUCCESS:
        return payment

    action_to_status = {
        "success": PaymentStatus.SUCCESS,
        "failed": PaymentStatus.FAILED,
        "pending": PaymentStatus.PENDING,
    }
    status = action_to_status.get(action)
    if status is None:
        raise PaymentError("Action simulasi tidak valid (success|failed|pending)")

    # Failed/pending transitions only make sense from a PENDING invoice.
    if status != PaymentStatus.SUCCESS and payment.status != PaymentStatus.PENDING:
        raise PaymentError(
            f"Tidak dapat mensimulasikan dari status {payment.status.value}"
        )

    await payment_repo.mark_status(session, payment, status)

    if status == PaymentStatus.SUCCESS:
        await process_successful_payment(session, payment)
        await session.flush()

        # Mirror the webhook router's cache + SSE broadcast sequence.
        event = await event_service.get_event_or_404(session, payment.event_id)
        fresh = await event_service.build_leaderboard(session, event.id)
        await cache.set_cached_leaderboard(event.id, fresh)
        await cache.publish({"type": "leaderboard", "event_id": payment.event_id})

    return payment
