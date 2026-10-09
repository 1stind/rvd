from enum import Enum


class EventStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    VOTING_OPEN = "VOTING_OPEN"
    VOTING_CLOSED = "VOTING_CLOSED"
    FINISHED = "FINISHED"
    ARCHIVED = "ARCHIVED"
