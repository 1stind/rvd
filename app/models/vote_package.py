"""
Vote package model — kept for historical data compatibility.
New payments no longer depend on vote packages; votes are derived from
qty * price_per_vote directly.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.utils import new_id


class VotePackage(TimestampMixin, SoftDeleteMixin, UUIDMixin, Base):
    __tablename__ = "vote_packages"

    id: Mapped[str] = mapped_column(
        String(40), primary_key=True, default=lambda: new_id("vp")
    )
    event_id: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    bonus_votes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit_price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("event_id", "code", name="uq_vote_package_event_code"),
    )
