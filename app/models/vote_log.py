"""
Vote log model — one row per granted vote batch, created only after a
payment reaches SUCCESS status. Immutable history; no hard delete.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDMixin
from app.utils import new_id


class VoteLog(TimestampMixin, UUIDMixin, Base):
    __tablename__ = "vote_logs"

    id: Mapped[str] = mapped_column(
        String(40), primary_key=True, default=lambda: new_id("vlog")
    )
    payment_id: Mapped[str] = mapped_column(
        ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False, index=True, unique=True
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    event_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    package_code: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    package_label: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    payment: Mapped["Payment"] = relationship(back_populates="vote_logs")  # noqa: F821
    team: Mapped["Team"] = relationship(back_populates="vote_logs")  # noqa: F821

    __table_args__ = (
        CheckConstraint("votes > 0", name="ck_vote_log_votes_positive"),
    )
