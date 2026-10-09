from enum import Enum


class QueueStatus(str, Enum):
    WAITING = "WAITING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    RELEASED = "RELEASED"
