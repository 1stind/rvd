"""Common response envelope per CLAUDE.md API rules."""
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str = ""
    data: Optional[T] = None


def ok(data: Any = None, message: str = "") -> dict:
    return {"success": True, "message": message, "data": data}


def fail(message: str, data: Any = None) -> dict:
    return {"success": False, "message": message, "data": data}
