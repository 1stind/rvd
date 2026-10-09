"""History schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.enums.payment_status import PaymentStatus


class HistoryPaymentItem(BaseModel):
    id: str
    team_name: str
    package_label: str
    qty: int
    amount: int
    votes: int
    status: PaymentStatus
    created_at: datetime
    supporter_name: str
    is_anonymous: bool


class HistoryLookupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payments: list[HistoryPaymentItem]
