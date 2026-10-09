from enum import Enum


class PaymentGateway(str, Enum):
    MIDTRANS = "MIDTRANS"
    MANUAL = "MANUAL"
    TRANSFER = "TRANSFER"
