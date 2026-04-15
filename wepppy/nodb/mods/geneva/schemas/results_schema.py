from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

GENEVA_LIFECYCLE_STATES: tuple[str, ...] = (
    "idle",
    "prepared",
    "running",
    "completed",
    "completed_with_gaps",
    "failed",
)


@dataclass(frozen=True)
class GenevaProgress:
    completed: int
    total: int
    unit: str = "storms"
    updated_at: str | None = None

    @property
    def percent(self) -> float:
        if self.total <= 0:
            return 0.0
        return round((self.completed / self.total) * 100.0, 4)

    def to_payload(self) -> dict[str, Any]:
        return {
            "completed": int(self.completed),
            "total": int(self.total),
            "unit": self.unit,
            "percent": self.percent,
            "updated_at": self.updated_at,
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_progress_payload(*, completed: int, total: int, unit: str = "storms") -> dict[str, Any]:
    return GenevaProgress(
        completed=completed,
        total=total,
        unit=unit,
        updated_at=utc_now_iso(),
    ).to_payload()


def empty_progress_payload() -> dict[str, Any]:
    return GenevaProgress(completed=0, total=0, unit="storms", updated_at=None).to_payload()


def validate_lifecycle_state(state: str) -> str:
    normalized = str(state).strip()
    if normalized not in GENEVA_LIFECYCLE_STATES:
        raise ValueError(
            f"status must be one of: {', '.join(GENEVA_LIFECYCLE_STATES)}"
        )
    return normalized


__all__ = [
    "GENEVA_LIFECYCLE_STATES",
    "GenevaProgress",
    "build_progress_payload",
    "empty_progress_payload",
    "utc_now_iso",
    "validate_lifecycle_state",
]
