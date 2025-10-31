from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MessageStatus(str, Enum):
    """Status of inbox messages understood by the shim."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"


@dataclass
class InboxMessage:
    """Minimal inbox message payload used in tests."""

    id: int
    sender_id: str
    receiver_id: str
    message: str
    status: MessageStatus
    created_at: datetime


__all__ = ["InboxMessage", "MessageStatus"]
