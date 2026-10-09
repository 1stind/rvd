"""Vote-related schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class LeaderboardEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    team_id: str
    name: str
    school: str | None = None
    votes: int
    trend: str = "same"


class LeaderboardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    event_name: str
    updated_at: datetime
    entries: list[LeaderboardEntry]
