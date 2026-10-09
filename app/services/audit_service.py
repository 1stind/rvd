"""
Audit service — manual audit log writes from routers/handlers.
(Router pages & webhook handlers use this for fine-grained records.)

v1.0: No session cookies. Actor is extracted from JWT by middleware or passed explicitly.
"""
from typing import Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import decode_access_token
from app.enums.audit_actor import AuditActor
from app.repositories import audit_log as audit_repo


async def record(
    session: AsyncSession,
    *,
    action: str,
    request: Optional[Request] = None,
    actor_type: Optional[AuditActor] = None,
    actor_name: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    detail: Optional[dict] = None,
) -> None:
    """Write one audit log row using the given session (committed by caller)."""
    if request is not None:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer ") and not actor_name:
            token = auth_header.removeprefix("Bearer ").strip()
            payload = decode_access_token(token)
            if payload:
                actor_type = actor_type or AuditActor.ADMIN
                actor_name = payload.get("email")
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
    else:
        ip_address = None
        user_agent = None

    await audit_repo.create_audit_log(
        session,
        action=action,
        actor_type=actor_type,
        actor_name=actor_name,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
    )
