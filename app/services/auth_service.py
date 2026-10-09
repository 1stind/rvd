"""
Authentication business logic (service layer).

v1.0: JWT admin-only. No public user auth, no session cookies, no refresh tokens.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.jwt import create_access_token, decode_access_token
from app.core.security import hash_password, verify_password
from app.enums.user_role import UserRole
from app.models.user import User
from app.repositories import audit_log as audit_repo
from app.repositories import user as user_repo
from app.schemas.auth import AdminLoginResponse, AdminMeResponse
from app.utils import new_id


async def login_admin(session: AsyncSession, email: str, password: str) -> AdminLoginResponse:
    user = await user_repo.get_by_email(session, email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email atau kata sandi salah")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Akun dinonaktifkan")
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Akses ditolak: butuh role admin")

    user.last_login_at = datetime.now(timezone.utc)
    await session.flush()

    token = create_access_token(user_id=user.id, email=user.email, role=user.role.value)
    await audit_repo.create_audit_log(
        session,
        action="admin.login",
        actor_type="ADMIN",
        actor_name=user.email,
        entity_type="user",
        entity_id=user.id,
        detail={"method": "jwt"},
    )
    await session.flush()

    return AdminLoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=AdminMeResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            last_login_at=user.last_login_at,
        ),
    )


async def get_current_admin(session: AsyncSession, token: str) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token tidak valid atau kadaluarsa")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token tidak valid")
    user = await user_repo.get_by_id(session, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Akun tidak ditemukan atau dinonaktifkan")
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Akses ditolak: butuh role admin")
    return user


async def change_password(
    session: AsyncSession, user: User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Kata sandi saat ini salah")
    user.password_hash = hash_password(new_password)
    await session.flush()


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    name: str,
    password: str,
    role: UserRole = UserRole.ADMIN,
) -> User:
    existing = await user_repo.get_by_email(session, email)
    if existing:
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")
    user = User(
        id=new_id("usr"),
        email=email.lower(),
        name=name,
        password_hash=hash_password(password),
        role=role,
    )
    session.add(user)
    await session.flush()
    await audit_repo.create_audit_log(session, action="user.create", entity_type="user", entity_id=user.id)
    return user
