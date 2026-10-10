"""
Request log middleware (pure ASGI): one line per request, written when the
response starts, so long-lived SSE streams are logged too. Static assets and
health checks are not logged. Run uvicorn with --no-access-log to avoid a
second line per request.
"""
import logging
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("app.middleware.request_log")

_QUIET_PREFIXES = ("/static/", "/health")


class LoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"].startswith(_QUIET_PREFIXES):
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        client = scope.get("client")
        client_ip = client[0] if client else "-"

        async def send_logged(message: Message) -> None:
            if message["type"] == "http.response.start":
                logger.info(
                    "%s %s %s %.1fms %s",
                    scope["method"], scope["path"], message["status"],
                    (time.perf_counter() - start) * 1000, client_ip,
                )
            await send(message)

        try:
            await self.app(scope, receive, send_logged)
        except Exception:
            logger.exception(
                "%s %s 500 %.1fms %s",
                scope["method"], scope["path"], (time.perf_counter() - start) * 1000, client_ip,
            )
            raise
