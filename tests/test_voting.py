"""
Tests for the voting and payment workflow.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from datetime import datetime, timedelta, timezone

from app.main import app
from app.core.config import settings
from app.models.event import EventStatus
from app.services import event_service, payment_service
from app.utils import new_id
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session as SessionLocal
import asyncio


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncSession:
    """Fixture to create a new database session for each test function."""
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncClient:
    """Fixture for an async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def test_data(db_session: AsyncSession):
    """Fixture to create test data (event, team)."""
    event = await event_service.create_event(
        db_session,
        event_service.EventCreate(
            name="Test Event",
            status=EventStatus.VOTING_OPEN,
            price_per_vote=1000,
        ),
    )
    team = await event_service.create_team(
        db_session,
        event_service.TeamCreate(
            event_id=event.id,
            name="Test Team",
            school="Test School",
        ),
    )
    await db_session.commit()
    return {"event": event, "team": team}


@pytest.mark.asyncio
async def test_create_payment_and_vote(async_client: AsyncClient, db_session: AsyncSession, test_data: dict):
    """
    Tests the full vote flow:
    1. Create a payment (invoice).
    2. Simulate a successful payment webhook.
    3. Verify that the vote is logged correctly.
    """
    event = test_data["event"]
    team = test_data["team"]
    vote_qty = 5

    # 0. Get CSRF token from a page load first
    pre_response = await async_client.get("/")
    assert "wvc_csrf" in pre_response.cookies
    csrf_token = pre_response.cookies["wvc_csrf"]

    # 1. Create a payment
    create_payload = {
        "event_id": event.id,
        "team_id": team.id,
        "qty": vote_qty,
        "voter_name": "Test Voter",
        "voter_phone": "1234567890",
    }
    headers = {"X-CSRF-Token": csrf_token}
    response = await async_client.post("/api/v1/payments", json=create_payload, headers=headers)
    assert response.status_code == 200
    payment_data = response.json()["data"]
    assert payment_data["status"] == "pending"
    assert payment_data["votes"] == vote_qty
    assert payment_data["amount"] == event.price_per_vote * vote_qty

    payment_id = payment_data["id"]

    # 2. Simulate a successful webhook callback from Midtrans
    # In a real scenario, we'd mock the webhook signature verification
    # For local testing, we bypass it if no server key is set.
    webhook_payload = {
        "order_id": payment_id,
        "transaction_status": "settlement",
        "status_code": "200",
        "gross_amount": str(float(payment_data["amount"])),
        "signature_key": "will_be_ignored_in_test_if_no_key",
    }

    # Temporarily disable webhook signature verification for the test
    original_verify = payment_service.verify_webhook_signature
    payment_service.verify_webhook_signature = lambda payload, raw_body: True

    webhook_response = await async_client.post("/api/v1/payments/webhook", json=webhook_payload)

    # Restore the original function
    payment_service.verify_webhook_signature = original_verify

    assert webhook_response.status_code == 200
    assert webhook_response.json()["data"]["status"] == "success"

    # 3. Verify vote log and payment status in the database
    from app.repositories import payment as payment_repo
    from app.repositories import vote_log as vote_log_repo

    db_payment = await payment_repo.get_payment(db_session, payment_id)
    assert db_payment is not None
    assert db_payment.status == payment_service.PaymentStatus.SUCCESS

    # Check that the votes were correctly logged for the team
    team_votes = await vote_log_repo.get_vote_count_for_team(db_session, team.id)
    assert team_votes == vote_qty


@pytest.mark.asyncio
async def test_failed_payment_does_not_add_vote(async_client: AsyncClient, db_session: AsyncSession, test_data: dict):
    """
    Tests that a failed payment webhook does not grant any votes.
    1. Create a payment (invoice).
    2. Simulate a failed payment webhook ('deny').
    3. Verify that the payment status is FAILED and no vote is logged.
    """
    event = test_data["event"]
    team = test_data["team"]
    vote_qty = 10

    # 0. Get CSRF token
    pre_response = await async_client.get("/")
    csrf_token = pre_response.cookies["wvc_csrf"]

    # 1. Create a payment
    create_payload = {
        "event_id": event.id,
        "team_id": team.id,
        "qty": vote_qty,
        "voter_name": "Failing Voter",
        "voter_phone": "0987654321",
    }
    headers = {"X-CSRF-Token": csrf_token}
    response = await async_client.post("/api/v1/payments", json=create_payload, headers=headers)
    assert response.status_code == 200
    payment_data = response.json()["data"]
    payment_id = payment_data["id"]

    # 2. Simulate a failed webhook callback
    webhook_payload = {
        "order_id": payment_id,
        "transaction_status": "deny",  # Failed status
        "status_code": "201",
        "gross_amount": str(float(payment_data["amount"])),
        "signature_key": "will_be_ignored_in_test_if_no_key",
    }

    original_verify = payment_service.verify_webhook_signature
    payment_service.verify_webhook_signature = lambda payload, raw_body: True
    webhook_response = await async_client.post("/api/v1/payments/webhook", json=webhook_payload)
    payment_service.verify_webhook_signature = original_verify

    assert webhook_response.status_code == 200
    # The webhook processor itself doesn't return failure, just the processed status
    assert webhook_response.json()["data"]["status"] == "failed"

    # 3. Verify vote log and payment status in the database
    from app.repositories import payment as payment_repo
    from app.repositories import vote_log as vote_log_repo

    db_payment = await payment_repo.get_payment(db_session, payment_id)
    assert db_payment is not None
    assert db_payment.status == payment_service.PaymentStatus.FAILED

    # CRITICAL: Ensure no votes were logged for this team
    team_votes = await vote_log_repo.get_vote_count_for_team(db_session, team.id)
    assert team_votes == 0


@pytest.mark.asyncio
async def test_duplicate_pending_returns_400(async_client: AsyncClient, db_session: AsyncSession, test_data: dict):
    """
    Tests that creating a second payment with the same phone+event returns 400.
    """
    event = test_data["event"]
    team = test_data["team"]

    create_payload = {
        "event_id": event.id,
        "team_id": team.id,
        "qty": 1,
        "supporter_name": "Duplicate Voter",
        "supporter_phone": "081234567890",
    }

    # First creation should succeed
    response1 = await async_client.post("/api/v1/payments", json=create_payload)
    assert response1.status_code == 200
    payment_data_1 = response1.json()["data"]
    assert payment_data_1["status"] == "PENDING"

    # Second creation with same phone+event should fail with 400
    response2 = await async_client.post("/api/v1/payments", json=create_payload)
    assert response2.status_code == 400
    assert "invoice pembayaran" in response2.json()["message"]

    # Verify only one PENDING payment exists for this phone+event
    from app.repositories import payment as payment_repo
    from app.enums.payment_status import PaymentStatus

    pendings = await payment_repo.list_payments(
        db_session, event_id=event.id, status=PaymentStatus.PENDING
    )
    phone_pendings = [p for p in pendings if p.supporter_phone == create_payload["supporter_phone"]]
    assert len(phone_pendings) == 1


@pytest.mark.asyncio
async def test_expired_pending_allows_new_payment(async_client: AsyncClient, db_session: AsyncSession, test_data: dict):
    """
    Tests that after a PENDING invoice expires, a new payment can be created.
    """
    event = test_data["event"]
    team = test_data["team"]

    create_payload = {
        "event_id": event.id,
        "team_id": team.id,
        "qty": 1,
        "supporter_name": "Expired Voter",
        "supporter_phone": "082345678901",
    }

    # First creation
    response1 = await async_client.post("/api/v1/payments", json=create_payload)
    assert response1.status_code == 200
    payment_data_1 = response1.json()["data"]
    payment_id_1 = payment_data_1["id"]
    assert payment_data_1["status"] == "PENDING"

    # Manually expire the payment by setting expires_at to the past
    from app.repositories import payment as payment_repo
    from app.enums.payment_status import PaymentStatus
    from datetime import datetime, timezone

    payment = await payment_repo.get_payment(db_session, payment_id_1)
    assert payment is not None
    payment.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    # Second creation should succeed because the first one is expired
    response2 = await async_client.post("/api/v1/payments", json=create_payload)
    assert response2.status_code == 200
    payment_data_2 = response2.json()["data"]
    assert payment_data_2["status"] == "PENDING"
    assert payment_data_2["id"] != payment_id_1

    # Verify the first payment is now EXPIRED
    await db_session.refresh(payment)
    assert payment.status == PaymentStatus.EXPIRED


@pytest.mark.asyncio
async def test_success_payment_allows_new_payment(async_client: AsyncClient, db_session: AsyncSession, test_data: dict):
    """
    Tests that after a payment succeeds, a new payment can be created.
    """
    event = test_data["event"]
    team = test_data["team"]

    create_payload = {
        "event_id": event.id,
        "team_id": team.id,
        "qty": 1,
        "supporter_name": "Success Voter",
        "supporter_phone": "083456789012",
    }

    # First creation
    response1 = await async_client.post("/api/v1/payments", json=create_payload)
    assert response1.status_code == 200
    payment_data_1 = response1.json()["data"]
    payment_id_1 = payment_data_1["id"]

    # Simulate successful webhook
    webhook_payload = {
        "order_id": payment_id_1,
        "transaction_status": "settlement",
        "status_code": "200",
        "gross_amount": str(float(payment_data_1["amount"])),
        "signature_key": "will_be_ignored_in_test_if_no_key",
    }

    original_verify = payment_service.verify_webhook_signature
    payment_service.verify_webhook_signature = lambda payload, raw_body: True
    webhook_response = await async_client.post("/api/v1/payments/webhook", json=webhook_payload)
    payment_service.verify_webhook_signature = original_verify

    assert webhook_response.status_code == 200
    assert webhook_response.json()["data"]["status"] == "SUCCESS"

    # Second creation should succeed because the first one is SUCCESS
    response2 = await async_client.post("/api/v1/payments", json=create_payload)
    assert response2.status_code == 200
    payment_data_2 = response2.json()["data"]
    assert payment_data_2["status"] == "PENDING"
    assert payment_data_2["id"] != payment_id_1


@pytest.mark.asyncio
async def test_different_phone_allows_new_payment(async_client: AsyncClient, db_session: AsyncSession, test_data: dict):
    """
    Tests that a different phone number can create a new PENDING payment
    even if another phone has an active PENDING for the same event.
    """
    event = test_data["event"]
    team = test_data["team"]

    create_payload_1 = {
        "event_id": event.id,
        "team_id": team.id,
        "qty": 1,
        "supporter_name": "Phone A",
        "supporter_phone": "084567890123",
    }

    create_payload_2 = {
        "event_id": event.id,
        "team_id": team.id,
        "qty": 1,
        "supporter_name": "Phone B",
        "supporter_phone": "085678901234",
    }

    # Both should succeed because phones are different
    response1 = await async_client.post("/api/v1/payments", json=create_payload_1)
    assert response1.status_code == 200

    response2 = await async_client.post("/api/v1/payments", json=create_payload_2)
    assert response2.status_code == 200

    # Verify two different PENDING payments exist
    from app.repositories import payment as payment_repo
    from app.enums.payment_status import PaymentStatus

    pendings = await payment_repo.list_payments(
        db_session, event_id=event.id, status=PaymentStatus.PENDING
    )
    assert len(pendings) == 2
