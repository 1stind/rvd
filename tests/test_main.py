import pytest
import httpx
from fastapi.testclient import TestClient
from httpx import ASGITransport

from app.main import app
from app.core.config import settings

# Using TestClient for synchronous tests if needed
client = TestClient(app)

def test_read_main_sync():
    response = client.get("/")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_read_main_async():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_health_check():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "ok",
        "data": {"app": settings.APP_NAME, "version": settings.APP_VERSION},
    }
