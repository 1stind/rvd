"""
Leaderboard SSE stream — Server-Sent Events, bukan WebSocket.
Klien subscribe, server push update setiap kali vote sukses diproses.

Per client this costs one small queue and this generator: no Redis connection
(see cache.subscription), no extra tasks, and no DB connection after the first
message (the initial ranking comes from the shared cache).
"""
import asyncio
import logging
import random
from typing import AsyncGenerator

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.database import async_session
from app.services import cache, leaderboard_service
from app.utils import dumps

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["leaderboard"])

KEEPALIVE_SECONDS = 20


def _encode_sse(data: dict) -> str:
    return f"data: {dumps(data)}\n\n"


@router.get("/leaderboard/stream")
async def leaderboard_stream(
    event_id: str = Query(..., description="ID event"),
):
    async def event_source() -> AsyncGenerator[str, None]:
        # Spread browser reconnects (e.g. after a restart) over 2-7 s instead of
        # every viewer reconnecting in the same second.
        yield f"retry: {random.randint(2000, 7000)}\n\n"
        async with cache.subscription(event_id) as queue:
            # Queue registered before reading the initial ranking, so no push that
            # reaches this worker is lost in between.
            initial = await _load_initial(event_id)
            if initial:
                yield _encode_sse({"type": "leaderboard", "event_id": event_id, "data": initial})
            while True:
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SECONDS)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _load_initial(event_id: str):
    """Ranking for the first message. Uses its own short-lived session: a request-scoped
    one would stay checked out for as long as the stream is open (one pooled connection
    per viewer)."""
    try:
        async with async_session() as session:
            return await leaderboard_service.get_leaderboard(session, event_id)
    except Exception as exc:
        # The stream still works (pushes arrive); the viewer just starts empty.
        logger.warning("SSE initial leaderboard failed for %s: %s", event_id, exc)
        return None
