"""
Rate limiter middleware — sliding window per IP.

Production: Redis (INCR + EXPIRE).
Dev/test fallback: in-memory dict (single-process only; Redis is required
in production for multi-worker correctness).
"""
import time
from collections import defaultdict, deque
from typing import Deque, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.services import cache

# Default limits: (window_seconds, max_requests)
DEFAULT_LIMITS = {
    "public": (60, 120),        # halaman & API publik
    "payment": (60, 20),        # pembuatan invoice
    "webhook": (60, 60),        # callback Midtrans
    "auth": (60, 10),           # login
}


def _bucket_name(path: str) -> str:
    if path.startswith("/api/v1/auth"):
        return "auth"
    if path.startswith("/api/v1/payments") and path.endswith("/webhook"):
        return "webhook"
    if path.startswith("/api/v1/payments"):
        return "payment"
    return "public"


class InMemoryLimiter:
    """Sliding window counter — safe for single-process dev/test."""

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], Deque[float]] = defaultdict(deque)

    def allow(self, key: str, bucket: str) -> bool:
        window, limit = DEFAULT_LIMITS[bucket]
        now = time.monotonic()
        history = self._hits[(key, bucket)]
        while history and history[0] <= now - window:
            history.popleft()
        if len(history) >= limit:
            return False
        history.append(now)
        return True


_memory_limiter = InMemoryLimiter()


async def _redis_allow(key: str, bucket: str) -> bool:
    window, limit = DEFAULT_LIMITS[bucket]
    redis_key = f"wvc:ratelimit:{bucket}:{key}"
    try:
        import redis.asyncio as aioredis

        r: Optional[aioredis.Redis] = await cache._get_redis()
        if r is None:
            return _memory_limiter.allow(key, bucket)
        current = await r.incr(redis_key)
        if current == 1:
            await r.expire(redis_key, window)
        return current <= limit
    except Exception:
        # Jangan blokir traffic saat Redis bermasalah.
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        bucket = _bucket_name(request.url.path)
        key = f"{client_ip}:{bucket}"

        if not settings.is_redis_available:
            allowed = _memory_limiter.allow(key, bucket)
        else:
            allowed = await _redis_allow(key, bucket)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "Terlalu banyak permintaan. Silakan coba beberapa saat lagi.",
                    "data": None,
                },
            )
        return await call_next(request)
