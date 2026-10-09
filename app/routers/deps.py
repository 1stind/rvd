"""
Shared router dependencies — JWT admin guard.

v1.0: Pure JWT via Authorization header. No session cookies, no cookie fallback.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.jwt import decode_access_token
from app.enums.user_role import UserRole
from app.models.user import User
from app.repositories import user as user_repo

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_admin_jwt(request: Request, session: AsyncSession = Depends(get_db)) -> User:
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan")

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


AdminUserJwt = Annotated[User, Depends(get_current_admin_jwt)]
