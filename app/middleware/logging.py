"""
Logging middleware — mencatat informasi dasar tentang setiap request dan response
ke terminal untuk keperluan debugging selama development.
"""
import logging
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("app.middleware.request_log")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Mencatat informasi request yang masuk dan response yang keluar.
        """
        start_time = time.time()

        # Log request yang masuk
        logger.info(
            f"--> {request.method} {request.url.path} | Client: {request.client.host if request.client else 'N/A'}"
        )

        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            # Log response yang keluar
            logger.info(
                f"<-- {response.status_code} | {request.method} {request.url.path} ({process_time:.2f}ms)"
            )
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"<-- 500 Internal Server Error | {request.method} {request.url.path} ({process_time:.2f}ms)",
                exc_info=e,
            )
            raise

        return response