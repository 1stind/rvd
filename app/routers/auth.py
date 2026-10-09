"""
Auth API — JWT admin-only.

Public user endpoints (register, login, session) are removed.
All admin endpoints require Authorization: Bearer <token>.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.repositories import user as user_repo
from app.schemas.auth import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminMeResponse,
)
from app.schemas.common import ok
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Legacy session-based auth removed
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# New JWT admin auth
# ---------------------------------------------------------------------------

admin_router = APIRouter(prefix="/admin", tags=["auth-admin"])


@admin_router.post("/login", response_model=dict)
async def admin_login(
    payload: AdminLoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
):
    result = await auth_service.login_admin(session, payload.email, payload.password)
    await session.commit()
    return ok(result.model_dump(), "Login admin berhasil")


@admin_router.get("/me", response_model=dict)
async def admin_me(request: Request, session: AsyncSession = Depends(get_db)):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan")

    user = await auth_service.get_current_admin(session, token)
    return ok(AdminMeResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        last_login_at=user.last_login_at,
    ).model_dump())


@admin_router.post("/logout", response_model=dict)
async def admin_logout(response: Response):
    return ok(message="Logout admin berhasil")


router.include_router(admin_router)
