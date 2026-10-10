import asyncio

import pytest
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from app.services import public_page_cache as cache


def request(path="/events"):
    return Request({"type": "http", "path": path, "headers": [], "query_string": b""})


@pytest.mark.asyncio
async def test_cold_burst_renders_once_and_expires(monkeypatch):
    now = [0]
    monkeypatch.setattr(cache.time, "monotonic", lambda: now[0])
    calls = []

    @cache.cache_discovery_page
    async def render(request, event_id=None):
        calls.append(event_id)
        await asyncio.sleep(0)
        return HTMLResponse(f"{event_id}:{len(calls)}")

    replies = await asyncio.gather(*[render(request=request(), event_id="a") for _ in range(100)])
    assert len(calls) == 1
    assert all(reply.body == b"a:1" for reply in replies)
    assert (await render(request=request(), event_id="b")).body == b"b:2"
    now[0] = 6
    assert (await render(request=request(), event_id="a")).body == b"a:3"


@pytest.mark.asyncio
async def test_errors_are_retried_and_cache_is_bounded():
    calls = []

    @cache.cache_discovery_page
    async def render(request, event_id=None):
        calls.append(event_id)
        return HTMLResponse(event_id, status_code=503 if event_id == "error" else 200)

    for _ in range(2):
        assert (await render(request=request(), event_id="error")).status_code == 503
    assert calls == ["error", "error"]
    for i in range(cache.MAX_PAGES + 1):
        await render(request=request(), event_id=str(i))
    assert len(cache._pages) == cache.MAX_PAGES
    assert ("/events", "0") not in cache._pages
