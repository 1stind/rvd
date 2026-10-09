"""
Leaderboard snapshot model — point-in-time capture of team rankings.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.utils import new_id


class LeaderboardSnapshot(TimestampMixin, SoftDeleteMixin, UUIDMixin, Base):
    __tablename__ = "leaderboard_snapshots"

    id: Mapped[str] = mapped_column(
        String(40), primary_key=True, default=lambda: new_id("lsnap")
    )
    event_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    total_votes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
