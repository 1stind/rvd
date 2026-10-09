"""
Leaderboard SSE stream — Server-Sent Events, bukan WebSocket (aturan CLAUDE.md).
Klien subscribe, server push update setiap kali vote sukses diproses.
Fallback tanpa Redis: terjaga via in-memory queue (dev/test).
"""
import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services import cache

router = APIRouter(prefix="/api/v1", tags=["leaderboard"])


def _encode_sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/leaderboard/stream")
async def leaderboard_stream(
    event_id: str = Query(..., description="ID event"),
    session: AsyncSession = Depends(get_db),
):
    async def event_source() -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=50)

        async def heartbeat() -> None:
            try:
                while True:
                    await asyncio.sleep(20)
                    await queue.put(": keepalive\n\n")
            except asyncio.CancelledError:
                pass

        async def feed() -> None:
            try:
                async for raw in cache.subscribe():
                    try:
                        message = json.loads(raw)
                    except (TypeError, ValueError):
                        continue
                    if message.get("type") == "leaderboard" and message.get("event_id") == event_id:
                        await queue.put(_encode_sse(message))
            except asyncio.CancelledError:
                pass

        initial = await _load_initial(session, event_id)
        if initial:
            yield _encode_sse({"type": "leaderboard", "event_id": event_id, "data": initial})

        hb_task = asyncio.create_task(heartbeat())
        feed_task = asyncio.create_task(feed())
        try:
            while True:
                chunk = await queue.get()
                yield chunk
        finally:
            hb_task.cancel()
            feed_task.cancel()
            await asyncio.gather(hb_task, feed_task, return_exceptions=True)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _load_initial(session: AsyncSession, event_id: str):
    from app.services import event_service

    try:
        return await event_service.build_leaderboard(session, event_id)
    except Exception:
        return None
