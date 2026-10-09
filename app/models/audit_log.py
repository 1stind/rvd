"""
Audit log model — append-only trail for sensitive admin actions.
Automatically written by the audit middleware; never edited or deleted.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.enums.audit_actor import AuditActor
from app.models.mixins import TimestampMixin, UUIDMixin
from app.utils import new_id


class AuditLog(UUIDMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(40), primary_key=True, default=lambda: new_id("alog")
    )

    actor_type: Mapped[Optional[AuditActor]] = mapped_column(
        Enum(AuditActor, name="audit_actor", create_type=False),
        nullable=True,
        index=True,
    )

    actor_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    detail: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
