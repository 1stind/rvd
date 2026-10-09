from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CANCELED = "CANCELED"
