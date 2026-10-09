"""Auth schemas — JWT admin-only authentication."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.enums.user_role import UserRole


class AdminLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128)


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "AdminMeResponse"


class AdminMeResponse(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    last_login_at: Optional[datetime] = None


class AdminUserOut(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    last_login_at: Optional[datetime] = None


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
