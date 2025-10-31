from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Flow:
    """Represents a scheduled agent workflow for tests."""

    name: str
    file_path: str
    schedule: str
    agent_profile: str
    script: str = ""
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True


__all__ = ["Flow"]
