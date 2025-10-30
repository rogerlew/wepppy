"""Minimal Flow model for tests.

This mirrors the fields used by tests without pulling in external
dependencies like Pydantic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Flow:
    """Represents a scheduled agent session (test minimal surface)."""

    name: str
    file_path: str
    schedule: str
    agent_profile: str
    script: str = ""
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True

