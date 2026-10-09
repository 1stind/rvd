"""
Audit log repository — append-only records of sensitive actions.
"""
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.audit_actor import AuditActor
from app.models.audit_log import AuditLog


async def create_audit_log(
    session: AsyncSession,
    *,
    action: str,
    actor_type: Optional[AuditActor] = None,
    actor_name: Optional[str] = None,
    request_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    detail: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    log = AuditLog(
        action=action,
        actor_type=actor_type,
        actor_name=actor_name,
        request_id=request_id,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(log)
    await session.flush()
    return log


async def list_audit_logs(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    action: Optional[str] = None,
    entity_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Sequence[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            stmt = stmt.where(AuditLog.created_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            stmt = stmt.where(AuditLog.created_at <= end_dt)
        except ValueError:
            pass
    result = await session.execute(stmt)
    return result.scalars().all()
