"""
Audit middleware — mencatat aksi sensitif (mutasi) secara append-only ke audit_logs.
Hanya mencatat request yang mengubah state (POST/PUT/PATCH/DELETE) di bawah /api/v1.
Menggunakan session DB sendiri agar tidak mengganggu transaksi request utama.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.database import async_session
from app.core.jwt import decode_access_token
from app.enums.audit_actor import AuditActor
from app.repositories import audit_log as audit_repo

_SKIP_PATHS = ("/api/v1/payments/webhook",)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        method = request.method.upper()
        path = request.url.path

        if method not in ("POST", "PUT", "PATCH", "DELETE"):
            return response
        if not path.startswith("/api/v1/"):
            return response
        if path in _SKIP_PATHS:
            return response

        actor_type = None
        actor_name = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            payload = decode_access_token(token)
            if payload:
                actor_type = AuditActor.ADMIN
                actor_name = payload.get("email")

        status = getattr(response, "status_code", 200)
        try:
            async with async_session() as session:
                await audit_repo.create_audit_log(
                    session,
                    action=f"{method} {path}",
                    actor_type=actor_type,
                    actor_name=actor_name,
                    request_id=None,
                    entity_type=path.split("/")[2] if len(path.split("/")) > 3 else None,
                    detail={"status_code": status},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
                await session.commit()
        except Exception:
            pass

        return response
