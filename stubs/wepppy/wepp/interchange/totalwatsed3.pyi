from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

DATE_COLUMNS: Tuple[str, ...]
PASS_METRIC_COLUMNS: Tuple[str, ...]
ASH_METRIC_BASES: Tuple[str, ...]
ASH_TONNE_COLUMNS: Tuple[str, ...]
ASH_PER_HA_COLUMNS: Tuple[str, ...]
ASH_METRIC_COLUMNS: Tuple[str, ...]
SCHEMA: Any
EMPTY_TABLE: Any
__all__ = ["run_totalwatsed3"]

@dataclass(frozen=True)
class _QueryTargets:
    pass_path: Path
    wat_path: Path
    output_path: Path

def _normalize_wepp_ids(wepp_ids: Optional[Sequence[int]]) -> Optional[list[int]]: ...

def _build_where_clause(wepp_ids: Optional[list[int]]) -> str: ...

def _resolve_sim_day_column(path: Path) -> str: ...

def _aggregate_pass(con: Any, pass_path: Path, where_clause: str) -> Any: ...

def _aggregate_wat(con: Any, wat_path: Path, where_clause: str) -> Any: ...

def _safe_depth(volume: Any, area: Any) -> Any: ...

def _compute_baseflow(percolation_mm: Any, baseflow_opts: Any) -> Tuple[Any, Any, Any]: ...

def _prepare_paths(interchange_dir: Path | str) -> _QueryTargets: ...

def _finalise_table(df: Any) -> Any: ...

def run_totalwatsed3(
    interchange_dir: Path | str,
    baseflow_opts: Any,
    wepp_ids: Optional[Sequence[int]] = ...,
    *,
    ash_dir: Path | str | None = ...,
    ash_area_lookup: Optional[Mapping[int, float]] = ...,
) -> Path: ...
