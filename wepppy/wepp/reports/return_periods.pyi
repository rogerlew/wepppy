from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

__all__ = [
    "ReturnPeriodDataset",
    "ReturnPeriods",
    "refresh_return_period_events",
]

EVENTS_REL_PATH: Path
RANKS_REL_PATH: Path
EBE_DATASET: str
TOTALWATSED3_DATASET: str


@dataclass(frozen=True)
class MeasureSpec:
    measure_id: str
    label: str
    value_column: str
    units: str
    optional: bool = ...


MEASURE_SPECS: Tuple[MeasureSpec, ...]
MEASURE_LOOKUP: Dict[str, MeasureSpec]


def refresh_return_period_events(
    wd: str | Path,
    *,
    topaz_ids: Optional[Sequence[int]] = ...,
    max_rank: int = ...,
    buffer: int = ...,
) -> tuple[Path, Path]: ...


class ReturnPeriodDataset:
    def __init__(
        self,
        wd: str | Path,
        *,
        auto_refresh: bool = ...,
        max_rank: int = ...,
        buffer: int = ...,
    ) -> None: ...

    @property
    def topaz_ids(self) -> list[int]: ...

    def create_report(
        self,
        recurrence: Sequence[int],
        *,
        exclude_yr_indxs: Optional[Sequence[int]] = ...,
        exclude_months: Optional[Sequence[int]] = ...,
        method: str = ...,
        gringorten_correction: bool = ...,
        topaz_id: Optional[int] = ...,
    ) -> ReturnPeriods: ...


class ReturnPeriods:
    header: list[str]
    units_d: Dict[str, str]
    has_phosphorus: bool
    years: int
    num_events: int
    wsarea: float | None
    recurrence: list[int]
    return_periods: Dict[str, Dict[int, Dict[str, Any]]]
    exclude_yr_indxs: list[int] | None
    exclude_months: list[int] | None

    def to_dict(self) -> Dict[str, Any]: ...

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ReturnPeriods: ...

    def export_tsv_summary(self, summary_path: str | Path, extraneous: bool = ...) -> None: ...
