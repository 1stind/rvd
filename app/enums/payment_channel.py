from enum import Enum


class PaymentChannel(str, Enum):
    QRIS = "QRIS"
    BANK_TRANSFER = "BANK_TRANSFER"
    E_WALLET = "E_WALLET"
    CASH = "CASH"
