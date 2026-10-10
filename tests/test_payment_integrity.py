"""Payment rules that must hold however the gateway is configured:
votes come from qty (never from the rupiah amount), retries are idempotent, and
an unconfigured gateway fails closed instead of granting free votes.
"""
import hashlib
import uuid

import pytest

from app.core.config import settings
from app.repositories import payment as payment_repo
from app.repositories import vote_log as vote_log_repo
from app.services import cache, payment_service

SERVER_KEY = "server-key-for-tests"


def _body(test_data, qty=5, phone="081200000001"):
    return {
        "event_id": test_data["event"].id,
        "team_id": test_data["team"].id,
        "qty": qty,
        "supporter_name": "Voter",
        "supporter_phone": phone,
    }


def _notification(payment_id, amount, status="settlement", key=None, **override):
    gross = f"{amount}.00"
    body = {
        "order_id": payment_id,
        "transaction_status": status,
        "status_code": "200",
        "gross_amount": gross,
    }
    if key:
        body["signature_key"] = hashlib.sha512(f"{payment_id}200{gross}{key}".encode()).hexdigest()
    return {**body, **override}


@pytest.mark.asyncio
async def test_votes_equal_qty_not_rupiah_amount(async_client, test_data):
    response = await async_client.post("/api/v1/payments", json=_body(test_data, qty=5))
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["votes"] == 5
    assert data["amount"] == 5 * test_data["event"].price_per_vote


@pytest.mark.asyncio
async def test_retry_with_same_idempotency_key_returns_same_invoice(async_client, test_data):
    headers = {"Idempotency-Key": uuid.uuid4().hex}
    first = await async_client.post("/api/v1/payments", json=_body(test_data), headers=headers)
    assert first.status_code == 200, first.text
    retry = await async_client.post("/api/v1/payments", json=_body(test_data), headers=headers)
    assert retry.status_code == 200, retry.text
    assert retry.json()["data"]["id"] == first.json()["data"]["id"]


@pytest.mark.asyncio
@pytest.mark.parametrize("settle_via", ["simulate", "webhook"])
async def test_leaderboard_api_reflects_paid_votes_immediately(async_client, test_data, settle_via):
    event_id, team_id = test_data["event"].id, test_data["team"].id

    async def team_votes():
        body = (await async_client.get(f"/api/v1/leaderboard?event_id={event_id}")).json()
        return next(e["votes"] for e in body["data"]["entries"] if e["team_id"] == team_id)

    assert await team_votes() == 0  # also primes the leaderboard cache

    created = await async_client.post("/api/v1/payments", json=_body(test_data, qty=4))
    payment = created.json()["data"]
    if settle_via == "simulate":
        settled = await async_client.post(
            f"/api/v1/payments/mock/{payment['id']}/simulate", json={"action": "success"}
        )
    else:
        settled = await async_client.post(
            "/api/v1/payments/webhook", json=_notification(payment["id"], payment["amount"])
        )
    assert settled.status_code == 200, settled.text

    assert await team_votes() == 4


@pytest.mark.asyncio
@pytest.mark.parametrize("settle_via", ["simulate", "webhook"])
async def test_settlement_pushes_full_ranking_to_sse_clients(
    async_client, test_data, monkeypatch, settle_via
):
    """leaderboard.js only applies pushes that carry data.entries."""
    sent = []

    async def capture(payload):
        sent.append(payload)

    monkeypatch.setattr(cache, "publish", capture)

    created = await async_client.post("/api/v1/payments", json=_body(test_data, qty=6))
    payment = created.json()["data"]
    if settle_via == "simulate":
        await async_client.post(
            f"/api/v1/payments/mock/{payment['id']}/simulate", json={"action": "success"}
        )
    else:
        await async_client.post(
            "/api/v1/payments/webhook", json=_notification(payment["id"], payment["amount"])
        )

    pushes = [m for m in sent if m["type"] == "leaderboard"]  # the only type the stream forwards
    assert len(pushes) == 1
    message = pushes[0]
    assert message["event_id"] == test_data["event"].id
    ranked = {e["team_id"]: e["votes"] for e in message["data"]["entries"]}
    assert ranked[test_data["team"].id] == 6


@pytest.mark.asyncio
async def test_oversized_idempotency_key_is_rejected_with_400(async_client, test_data):
    response = await async_client.post(
        "/api/v1/payments", json=_body(test_data), headers={"Idempotency-Key": "k" * 65}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_unconfigured_gateway_fails_closed(async_client, db_session, test_data, monkeypatch):
    created = await async_client.post("/api/v1/payments", json=_body(test_data))
    payment = created.json()["data"]

    # Misconfigured deploy: no server key and no explicit mock mode.
    monkeypatch.setattr(settings, "MIDTRANS_MOCK_MODE", False)

    forged = await async_client.post(
        "/api/v1/payments/webhook", json=_notification(payment["id"], payment["amount"])
    )
    assert forged.status_code == 403

    simulated = await async_client.post(
        f"/api/v1/payments/mock/{payment['id']}/simulate", json={"action": "success"}
    )
    assert simulated.status_code == 404

    new_invoice = await async_client.post(
        "/api/v1/payments", json=_body(test_data, phone="081200000002")
    )
    assert new_invoice.status_code == 503

    db_payment = await payment_repo.get_payment(db_session, payment["id"])
    assert db_payment.status == payment_service.PaymentStatus.PENDING
    assert await vote_log_repo.get_vote_count_for_team(db_session, test_data["team"].id) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_signature", ["0" * 128, 12345, None])
async def test_webhook_rejects_bad_signature_when_key_set(
    async_client, db_session, test_data, monkeypatch, bad_signature
):
    created = await async_client.post("/api/v1/payments", json=_body(test_data))
    payment = created.json()["data"]
    monkeypatch.setattr(settings, "MIDTRANS_MOCK_MODE", False)
    monkeypatch.setattr(settings, "MIDTRANS_SERVER_KEY", SERVER_KEY)

    response = await async_client.post(
        "/api/v1/payments/webhook",
        json=_notification(payment["id"], payment["amount"], signature_key=bad_signature),
    )
    assert response.status_code == 403

    db_payment = await payment_repo.get_payment(db_session, payment["id"])
    assert db_payment.status == payment_service.PaymentStatus.PENDING


@pytest.mark.asyncio
async def test_webhook_accepts_valid_signature_and_grants_votes(
    async_client, db_session, test_data, monkeypatch
):
    created = await async_client.post("/api/v1/payments", json=_body(test_data, qty=3))
    payment = created.json()["data"]
    monkeypatch.setattr(settings, "MIDTRANS_MOCK_MODE", False)
    monkeypatch.setattr(settings, "MIDTRANS_SERVER_KEY", SERVER_KEY)

    response = await async_client.post(
        "/api/v1/payments/webhook",
        json=_notification(payment["id"], payment["amount"], key=SERVER_KEY),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "SUCCESS"
    assert await vote_log_repo.get_vote_count_for_team(db_session, test_data["team"].id) == 3


@pytest.mark.asyncio
async def test_webhook_rejects_amount_mismatch(async_client, db_session, test_data, monkeypatch):
    created = await async_client.post("/api/v1/payments", json=_body(test_data, qty=5))
    payment = created.json()["data"]
    monkeypatch.setattr(settings, "MIDTRANS_MOCK_MODE", False)
    monkeypatch.setattr(settings, "MIDTRANS_SERVER_KEY", SERVER_KEY)

    underpaid = _notification(payment["id"], 1000, key=SERVER_KEY)  # validly signed, wrong amount
    response = await async_client.post("/api/v1/payments/webhook", json=underpaid)
    assert response.status_code == 400

    db_payment = await payment_repo.get_payment(db_session, payment["id"])
    assert db_payment.status == payment_service.PaymentStatus.PENDING
    assert await vote_log_repo.get_vote_count_for_team(db_session, test_data["team"].id) == 0
