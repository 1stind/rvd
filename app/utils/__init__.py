"""Shared helpers: id generation and JSON/datetime serialization."""
import json
import uuid
from datetime import date, datetime
from typing import Any


def new_id(prefix: str = "") -> str:
    """Short, URL-safe unique id: [prefix_]<uuid4 hex 12 chars>."""
    raw = uuid.uuid4().hex[:12]
    return f"{prefix}_{raw}" if prefix else raw


class AppJSONEncoder(json.JSONEncoder):
    """JSON encoder that knows how to serialize datetime/date objects."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if hasattr(obj, "value") and isinstance(obj.value, str):  # enums
            return obj.value
        return super().default(obj)


def dumps(data: Any) -> str:
    return json.dumps(data, cls=AppJSONEncoder, ensure_ascii=False)
