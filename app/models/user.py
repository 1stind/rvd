"""
User model — admin/organizer accounts. Passwords hashed with Argon2
(see app.core.security); never stored plain.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.enums.user_role import UserRole
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.utils import new_id


class User(TimestampMixin, SoftDeleteMixin, UUIDMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(40), primary_key=True, default=lambda: new_id("usr")
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", create_type=False), default=UserRole.ADMIN, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
