from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence, Literal

from .catalog import DatasetCatalog
from .payload import QueryRequest

STORM_EVENT_DATASETS: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class JoinStrategy:
    mode: Literal["sim_day_index", "year_julian"]
    reason: str

    @property
    def uses_sim_day_index(self) -> bool: ...


def resolve_join_strategy(
    run_dir: str | Path,
    catalog: DatasetCatalog,
    *,
    dataset_paths: Sequence[str],
) -> JoinStrategy: ...

def build_event_filter_payload(
    run_dir: str | Path,
    catalog: DatasetCatalog,
    *,
    intensity: int | str,
    min_value: float,
    max_value: float,
    warmup_year: int | None = ...,
) -> QueryRequest: ...

def build_soil_saturation_payload(
    run_dir: str | Path,
    catalog: DatasetCatalog,
    *,
    intensity: int | str | None = ...,
    min_value: float | None = ...,
    max_value: float | None = ...,
    warmup_year: int | None = ...,
) -> QueryRequest: ...

def build_snow_water_payload(
    run_dir: str | Path,
    catalog: DatasetCatalog,
    *,
    intensity: int | str | None = ...,
    min_value: float | None = ...,
    max_value: float | None = ...,
    warmup_year: int | None = ...,
) -> QueryRequest: ...

def build_hydrology_metrics_payload(
    run_dir: str | Path,
    catalog: DatasetCatalog,
    *,
    intensity: int | str | None = ...,
    min_value: float | None = ...,
    max_value: float | None = ...,
    warmup_year: int | None = ...,
) -> QueryRequest: ...

def build_tc_payload(
    run_dir: str | Path,
    catalog: DatasetCatalog,
    *,
    warmup_year: int | None = ...,
) -> QueryRequest | None: ...
