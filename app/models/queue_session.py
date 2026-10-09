"""
Queue session model — tracks users waiting to enter voting.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.enums.queue_status import QueueStatus
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.utils import new_id


class QueueSession(TimestampMixin, SoftDeleteMixin, UUIDMixin, Base):
    __tablename__ = "queue_sessions"

    id: Mapped[str] = mapped_column(
        String(40), primary_key=True, default=lambda: new_id("qs")
    )
    event_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_token: Mapped[str] = mapped_column(String(64), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[QueueStatus] = mapped_column(
        Enum(QueueStatus, name="queue_status", create_type=False), default=QueueStatus.WAITING, nullable=False, index=True
    )
    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_queue_event_status", "event_id", "status"),
        Index("ix_queue_position", "position"),
    )
