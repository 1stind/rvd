from enum import Enum


class AuditActor(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"
    SYSTEM = "SYSTEM"
    WEBHOOK = "WEBHOOK"
