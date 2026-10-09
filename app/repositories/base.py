"""Generic async CRUD helpers shared by all repositories."""
from typing import Any, Optional, Sequence, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


async def get_by_id(session: AsyncSession, model: type[ModelT], entity_id: Any) -> Optional[ModelT]:
    result = await session.get(model, entity_id)
    return result


async def add(session: AsyncSession, obj: ModelT) -> ModelT:
    session.add(obj)
    await session.flush()
    return obj


async def list_all(session: AsyncSession, model: type[ModelT]) -> Sequence[ModelT]:
    result = await session.execute(select(model))
    return result.scalars().all()
