"""Admin API auth: a token is trusted for its signature, never for its shape."""
import time
import uuid

import jwt
import pytest
import pytest_asyncio

from app.core.config import settings
from app.seeds.admin import seed_admin

PROTECTED = "/api/v1/admin/dashboard"


@pytest_asyncio.fixture
async def admin_credentials():
    email = f"admin-{uuid.uuid4().hex[:8]}@test.local"
    password = uuid.uuid4().hex
    await seed_admin(email, password)
    return email, password


@pytest.mark.asyncio
async def test_admin_api_requires_a_token(async_client):
    assert (await async_client.get(PROTECTED)).status_code == 401


@pytest.mark.asyncio
async def test_admin_api_rejects_random_and_forged_tokens(async_client):
    forged = jwt.encode(
        {"sub": "usr_anything", "exp": int(time.time()) + 600}, "not-the-real-secret", algorithm=settings.JWT_ALGORITHM
    )
    for token in ("aaaa.bbbb.cccc", uuid.uuid4().hex, forged):
        response = await async_client.get(PROTECTED, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401, token


@pytest.mark.asyncio
async def test_admin_login_issues_a_working_token_and_rejects_bad_password(async_client, admin_credentials):
    email, password = admin_credentials

    bad = await async_client.post("/api/v1/auth/admin/login", json={"email": email, "password": "wrong-password"})
    assert bad.status_code in (400, 401)

    good = await async_client.post("/api/v1/auth/admin/login", json={"email": email, "password": password})
    assert good.status_code == 200, good.text
    token = good.json()["data"]["access_token"]

    response = await async_client.get(PROTECTED, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_dashboard_counts_payments_by_status(async_client, admin_credentials, test_data):
    email, password = admin_credentials
    login = await async_client.post("/api/v1/auth/admin/login", json={"email": email, "password": password})
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    event_id = test_data["event"].id

    for phone, settle in (("081500000001", True), ("081500000002", False)):
        created = await async_client.post("/api/v1/payments", json={
            "event_id": event_id, "team_id": test_data["team"].id, "qty": 2,
            "supporter_name": "Voter", "supporter_phone": phone,
        })
        if settle:
            await async_client.post(
                f"/api/v1/payments/mock/{created.json()['data']['id']}/simulate", json={"action": "success"}
            )

    data = (await async_client.get(f"{PROTECTED}?event_id={event_id}", headers=headers)).json()["data"]
    assert (data["payments"], data["successful_payments"], data["pending_payments"]) == (2, 1, 1)
    assert data["total_amount"] == 2 * test_data["event"].price_per_vote
