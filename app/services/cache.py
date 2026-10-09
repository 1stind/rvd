"""
Leaderboard cache + SSE fan-out.

Production: Redis pub/sub + cache.
Dev/test fallback (REDIS_URL=memory://...): in-memory dict + asyncio queues.
Leaderboard payload disimpan di cache agar read-heavy tidak membebani DB.
SSE memakai pub/sub broadcast — bukan WebSocket (aturan CLAUDE.md).
"""
import asyncio
import json
import time
from collections import defaultdict
from typing import Any, Optional

from redis.asyncio import Redis, from_url

from app.core.config import settings
from app.utils import dumps

_CHANNEL = "wvc:leaderboard"

# --- Redis vs in-memory backend selection --------------------------------
_redis: Optional[Redis] = None
_memory_subs: dict[int, set[asyncio.Queue]] = defaultdict(set)
_memory_cache: dict[str, tuple[float, str]] = {}
_memory_lock = asyncio.Lock()

CACHE_TTL = 10  # detik


def _use_redis() -> bool:
    return settings.is_redis_available


async def _get_redis() -> Optional[Redis]:
    global _redis
    if not _use_redis():
        return None
    if _redis is None:
        _redis = from_url(settings.REDIS_URL, decode_responses=True)
        await _redis.ping()
    return _redis


# --- Cache ----------------------------------------------------------------
async def cache_get(key: str) -> Optional[str]:
    if not _use_redis():
        item = _memory_cache.get(key)
        if item and item[0] > time.time():
            return item[1]
        return None
    r = await _get_redis()
    if r is None:
        return None
    try:
        return await r.get(key)
    except Exception:
        return None


async def cache_set(key: str, value: str, ttl: int = CACHE_TTL) -> None:
    if not _use_redis():
        _memory_cache[key] = (time.time() + ttl, value)
        return
    r = await _get_redis()
    if r is None:
        return
    try:
        await r.set(key, value, ex=ttl)
    except Exception:
        pass


# --- Pub/sub broadcast ------------------------------------------------------
async def publish(payload: dict[str, Any]) -> None:
    message = dumps(payload)
    if not _use_redis():
        async with _memory_lock:
            snapshot = list(_memory_subs.values())
        for queue_set in snapshot:
            for queue in list(queue_set):
                try:
                    queue.put_nowait(message)
                except Exception:
                    pass
        return
    r = await _get_redis()
    if r is None:
        return
    try:
        await r.publish(_CHANNEL, message)
    except Exception:
        pass


async def subscribe() -> Any:
    """Return an async iterator of broadcast messages (str)."""
    if not _use_redis():
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with _memory_lock:
            _memory_subs[id(queue)].add(queue)
        try:
            while True:
                message = await queue.get()
                yield message
        finally:
            async with _memory_lock:
                _memory_subs[id(queue)].discard(queue)
        return

    r = await _get_redis()
    if r is None:
        while True:
            await asyncio.sleep(30)
            yield dumps({})
        return

    pubsub = r.pubsub()
    await pubsub.subscribe(_CHANNEL)
    try:
        async for raw in pubsub.listen():
            if raw["type"] == "message":
                yield raw["data"]
    finally:
        await pubsub.unsubscribe(_CHANNEL)
        await pubsub.close()


async def get_cached_leaderboard(event_id: str, limit: Optional[int] = None) -> Optional[dict]:
    key = f"wvc:leaderboard:{event_id}:{limit or 'all'}"
    raw = await cache_get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


async def set_cached_leaderboard(event_id: str, payload: dict, limit: Optional[int] = None) -> None:
    key = f"wvc:leaderboard:{event_id}:{limit or 'all'}"
    await cache_set(key, dumps(payload))
