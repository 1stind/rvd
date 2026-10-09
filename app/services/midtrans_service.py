"""
Midtrans service — thin wrapper around midtransclient.
"""
import hashlib
import hmac
from typing import Any


def create_transaction(payment, server_key: str, is_production: bool) -> dict:
    import midtransclient

    client = midtransclient.Snap(
        is_production=is_production,
        server_key=server_key,
    )
    return client.create_transaction(
        {
            "transaction_details": {
                "order_id": payment.id,
                "gross_amount": payment.amount,
            },
            "payment_type": "qris",
            "customer_details": {
                "first_name": "Anonymous",
            },
            "expiry": {
                "unit": "minutes",
                "duration": 15,
            },
        }
    )


def verify_signature(payload: dict, raw_body: bytes, server_key: str) -> bool:
    if not server_key:
        return True
    order_id = payload.get("order_id", "")
    status_code = str(payload.get("status_code", ""))
    gross_amount = str(payload.get("gross_amount", ""))
    expected = hashlib.sha512(f"{order_id}{status_code}{gross_amount}{server_key}".encode()).hexdigest()
    got = payload.get("signature_key", "")
    return hmac.compare_digest(expected, got)


def parse_notification(payload: dict) -> dict:
    return {
        "order_id": payload.get("order_id"),
        "transaction_status": payload.get("transaction_status"),
        "fraud_status": payload.get("fraud_status"),
        "transaction_id": payload.get("transaction_id"),
        "gross_amount": payload.get("gross_amount"),
    }
