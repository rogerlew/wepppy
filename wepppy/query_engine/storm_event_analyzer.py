"""Query payload helpers for the Storm Event Analyzer data surface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Mapping, Sequence, Literal

from wepppy.query_engine.catalog import DatasetCatalog
from wepppy.query_engine.payload import QueryRequest
from wepppy.wepp.interchange.versioning import Version, read_version_manifest

__all__ = [
    "JoinStrategy",
    "STORM_EVENT_DATASETS",
    "resolve_join_strategy",
    "build_event_filter_payload",
    "build_soil_saturation_payload",
    "build_snow_water_payload",
    "build_hydrology_metrics_payload",
    "build_tc_payload",
]


STORM_EVENT_DATASETS: Mapping[str, str] = {
    "climate": "climate/wepp_cli.parquet",
    "soil": "wepp/output/interchange/H.soil.parquet",
    "water": "wepp/output/interchange/H.wat.parquet",
    "hillslope_events": "wepp/output/interchange/H.ebe.parquet",
    "outlet_events": "wepp/output/interchange/ebe_pw0.parquet",
    "hillslopes": "watershed/hillslopes.parquet",
    "tc_out": "wepp/output/interchange/tc_out.parquet",
}

INTERCHANGE_SIM_DAY_MIN_VERSION = Version(major=1, minor=1)

_SIMPLE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_CLIMATE_COLUMNS: Mapping[str, Sequence[str]] = {
    "sim_day_index": ("sim_day_index",),
    "year": ("year",),
    "julian": ("julian",),
    "month": ("month", "mo"),
    "day_of_month": ("day_of_month", "da", "day"),
    "depth_mm": ("prcp", "precip_mm", "precip", "precipitation"),
    "duration_hours": ("storm_duration_hours", "storm_duration", "dur"),
    "tp": ("tp",),
    "ip": ("ip",),
    "peak_intensity_10": (
        "peak_intensity_10",
        "10-min Peak Rainfall Intensity (mm/hour)",
        "i10",
    ),
    "peak_intensity_15": (
        "peak_intensity_15",
        "15-min Peak Rainfall Intensity (mm/hour)",
        "i15",
    ),
    "peak_intensity_30": (
        "peak_intensity_30",
        "30-min Peak Rainfall Intensity (mm/hour)",
        "i30",
    ),
    "peak_intensity_60": (
        "peak_intensity_60",
        "60-min Peak Rainfall Intensity (mm/hour)",
        "i60",
    ),
}

_INTENSITY_KEY_MAP: Mapping[str, str] = {
    "10": "peak_intensity_10",
    "10-min": "peak_intensity_10",
    "10min": "peak_intensity_10",
    "15": "peak_intensity_15",
    "15-min": "peak_intensity_15",
    "15min": "peak_intensity_15",
    "30": "peak_intensity_30",
    "30-min": "peak_intensity_30",
    "30min": "peak_intensity_30",
    "60": "peak_intensity_60",
    "60-min": "peak_intensity_60",
    "60min": "peak_intensity_60",
    "peak_intensity_10": "peak_intensity_10",
    "peak_intensity_15": "peak_intensity_15",
    "peak_intensity_30": "peak_intensity_30",
    "peak_intensity_60": "peak_intensity_60",
}


@dataclass(frozen=True, slots=True)
class JoinStrategy:
    """Join strategy for storm event datasets."""

    mode: Literal["sim_day_index", "year_julian"]
    reason: str

    @property
    def uses_sim_day_index(self) -> bool:
        return self.mode == "sim_day_index"


def resolve_join_strategy(
    run_dir: str | Path,
    catalog: DatasetCatalog,
    *,
    dataset_paths: Sequence[str],
) -> JoinStrategy:
    """Determine the join strategy for event datasets based on interchange version."""
    run_path = Path(run_dir).expanduser()
    if not run_path.exists():
        raise FileNotFoundError(run_path)

    for path in dataset_paths:
        _require_dataset(catalog, path)

    version = _read_interchange_version(run_path)
    if version is None or (version.major, version.minor) < (
        INTERCHANGE_SIM_DAY_MIN_VERSION.major,
        INTERCHANGE_SIM_DAY_MIN_VERSION.minor,
    ):
        return JoinStrategy(
            mode="year_julian",
            reason="Interchange version missing or <1.1; use year+julian fallback",
        )

    missing_sim_day = [
        path for path in dataset_paths if not _has_column(catalog, path, "sim_day_index")
    ]
    if missing_sim_day:
        formatted = ", ".join(sorted(missing_sim_day))
        raise KeyError(f"sim_day_index missing from datasets: {formatted}")

    return JoinStrategy(
        mode="sim_day_index",
        reason=f"Interchange version {version} provides absolute sim_day_index",
    )


def build_event_filter_payload(
    run_dir: str | Path,
    catalog: DatasetCatalog,
    *,
    intensity: int | str,
    min_value: float,
    max_value: float,
    warmup_year: int | None = None,
) -> QueryRequest:
    """Build a QueryRequest that filters storms by peak intensity range."""
    climate_path = STORM_EVENT_DATASETS["climate"]
    _require_dataset(catalog, climate_path)

    climate_cols = _resolve_climate_columns(catalog, climate_path)
    intensity_key = _normalize_intensity_key(intensity)
    intensity_column = climate_cols[intensity_key]

    columns = _event_key_columns("ev", climate_cols)
    columns.extend(
        [
            f"{_qualify_column('ev', climate_cols['depth_mm'])} AS depth_mm",
            f"{_qualify_column('ev', climate_cols['duration_hours'])} AS duration_hours",
            f"{_qualify_column('ev', climate_cols['tp'])} AS tp",
            f"{_qualify_column('ev', climate_cols['ip'])} AS ip",
        ]
    )

    for key in ("peak_intensity_10", "peak_intensity_15", "peak_intensity_30", "peak_intensity_60"):
        columns.append(f"{_qualify_column('ev', climate_cols[key])} AS {key}")

    filters = [
        {
            "column": _qualify_column("ev", intensity_column),
            "operator": ">=",
            "value": float(min_value),
        },
        {
            "column": _qualify_column("ev", intensity_column),
            "operator": "<=",
            "value": float(max_value),
        },
    ]

    if warmup_year is not None:
        filters.append(
            {
                "column": _qualify_column("ev", climate_cols["year"]),
                "operator": ">",
                "value": int(warmup_year),
            }
        )

    return QueryRequest(
        datasets=[{"path": climate_path, "alias": "ev"}],
        columns=columns,
        filters=filters,
        order_by=[intensity_key, "sim_day_index"],
    )


def build_soil_saturation_payload(
    run_dir: str | Path,
    catalog: DatasetCatalog,
    *,
    intensity: int | str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    warmup_year: int | None = None,
) -> QueryRequest:
    """Build a QueryRequest that aggregates soil saturation (T-1) across hillslopes."""
    climate_path = STORM_EVENT_DATASETS["climate"]
    soil_path = STORM_EVENT_DATASETS["soil"]

    strategy = resolve_join_strategy(run_dir, catalog, dataset_paths=[climate_path, soil_path])
    climate_cols = _resolve_climate_columns(catalog, climate_path)

    filters = _build_intensity_filters(
        climate_cols,
        intensity=intensity,
        min_value=min_value,
        max_value=max_value,
    )
    if warmup_year is not None:
        filters.append(
            {
                "column": _qualify_column("ev", climate_cols["year"]),
                "operator": ">",
                "value": int(warmup_year),
            }
        )

    return QueryRequest(
        datasets=[
            {"path": climate_path, "alias": "ev"},
            {"path": soil_path, "alias": "soil"},
        ],
        joins=[_t1_join(strategy, left_alias="ev", right_alias="soil", join_type="left")],
        columns=_event_key_columns("ev", climate_cols),
        aggregations=[
            {
                "sql": f"AVG({_qualify_column('soil', 'Saturation')})",
                "alias": "soil_saturation_t1",
            }
        ],
        filters=filters or None,
        group_by=_event_key_group_by("ev", climate_cols),
        order_by=["sim_day_index"],
    )


def build_snow_water_payload(
    run_dir: str | Path,
    catalog: DatasetCatalog,
    *,
    intensity: int | str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    warmup_year: int | None = None,
) -> QueryRequest:
    """Build a QueryRequest that aggregates snow water (T-1) across hillslopes."""
    climate_path = STORM_EVENT_DATASETS["climate"]
    water_path = STORM_EVENT_DATASETS["water"]

    strategy = resolve_join_strategy(run_dir, catalog, dataset_paths=[climate_path, water_path])
    climate_cols = _resolve_climate_columns(catalog, climate_path)

    filters = _build_intensity_filters(
        climate_cols,
        intensity=intensity,
        min_value=min_value,
        max_value=max_value,
    )
    if warmup_year is not None:
        filters.append(
            {
                "column": _qualify_column("ev", climate_cols["year"]),
                "operator": ">",
                "value": int(warmup_year),
            }
        )

    return QueryRequest(
        datasets=[
            {"path": climate_path, "alias": "ev"},
            {"path": water_path, "alias": "wat"},
        ],
        joins=[_t1_join(strategy, left_alias="ev", right_alias="wat", join_type="left")],
        columns=_event_key_columns("ev", climate_cols),
        aggregations=[
            {
                "sql": f"AVG({_qualify_column('wat', 'Snow-Water')})",
                "alias": "snow_water_t1_mm",
            }
        ],
        filters=filters or None,
        group_by=_event_key_group_by("ev", climate_cols),
        order_by=["sim_day_index"],
    )


def build_hydrology_metrics_payload(
    run_dir: str | Path,
    catalog: DatasetCatalog,
    *,
    intensity: int | str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    warmup_year: int | None = None,
) -> QueryRequest:
    """Build a QueryRequest for hydrology metrics + runoff coefficient."""
    climate_path = STORM_EVENT_DATASETS["climate"]
    out_path = STORM_EVENT_DATASETS["outlet_events"]
    hill_events_path = STORM_EVENT_DATASETS["hillslope_events"]
    hills_path = STORM_EVENT_DATASETS["hillslopes"]

    strategy = resolve_join_strategy(
        run_dir,
        catalog,
        dataset_paths=[climate_path, out_path, hill_events_path],
    )
    _require_dataset(catalog, hills_path)

    climate_cols = _resolve_climate_columns(catalog, climate_path)
    hill_area_column = _select_column(catalog, hills_path, ("area", "area_m2"), label="area")

    filters = _build_intensity_filters(
        climate_cols,
        intensity=intensity,
        min_value=min_value,
        max_value=max_value,
    )
    if warmup_year is not None:
        filters.append(
            {
                "column": _qualify_column("ev", climate_cols["year"]),
                "operator": ">",
                "value": int(warmup_year),
            }
        )

    precip_volume_expr = (
        f"SUM({_qualify_column('hebe', 'Precip')} * {_qualify_column('hill', hill_area_column)} / 1000.0)"
    )

    runoff_volume_expr = f"MAX({_qualify_column('out', 'runoff_volume')})"
    peak_runoff_expr = f"MAX({_qualify_column('out', 'peak_runoff')})"
    sediment_yield_expr = f"MAX({_qualify_column('out', 'sediment_yield')})"

    runoff_coeff_expr = f"{runoff_volume_expr} / NULLIF({precip_volume_expr}, 0)"

    return QueryRequest(
        datasets=[
            {"path": climate_path, "alias": "ev"},
            {"path": out_path, "alias": "out"},
            {"path": hill_events_path, "alias": "hebe"},
            {"path": hills_path, "alias": "hill"},
        ],
        joins=[
            _event_join(strategy, left_alias="ev", right_alias="out", join_type="left"),
            _event_join(strategy, left_alias="ev", right_alias="hebe", join_type="left"),
            {
                "left": "hebe",
                "right": "hill",
                "left_on": ["wepp_id"],
                "right_on": ["wepp_id"],
                "type": "left",
            },
        ],
        columns=_event_key_columns("ev", climate_cols),
        aggregations=[
            {"sql": runoff_volume_expr, "alias": "runoff_volume_m3"},
            {"sql": peak_runoff_expr, "alias": "peak_discharge_m3s"},
            {"sql": sediment_yield_expr, "alias": "sediment_yield_kg"},
            {"sql": precip_volume_expr, "alias": "precip_volume_m3"},
            {"sql": runoff_coeff_expr, "alias": "runoff_coefficient"},
        ],
        filters=filters or None,
        group_by=_event_key_group_by("ev", climate_cols),
        order_by=["sim_day_index"],
    )


def build_tc_payload(
    run_dir: str | Path,
    catalog: DatasetCatalog,
    *,
    warmup_year: int | None = None,
) -> QueryRequest | None:
    """Build a Tc lookup payload or return None when tc_out is unavailable."""
    tc_path = STORM_EVENT_DATASETS["tc_out"]
    if not catalog.has(tc_path):
        return None

    climate_path = STORM_EVENT_DATASETS["climate"]
    _require_dataset(catalog, climate_path)

    climate_cols = _resolve_climate_columns(catalog, climate_path)

    filters = []
    if warmup_year is not None:
        filters.append(
            {
                "column": _qualify_column("ev", climate_cols["year"]),
                "operator": ">",
                "value": int(warmup_year),
            }
        )

    return QueryRequest(
        datasets=[
            {"path": climate_path, "alias": "ev"},
            {"path": tc_path, "alias": "tc"},
        ],
        joins=[
            {
                "left": "ev",
                "right": "tc",
                "left_on": [climate_cols["year"], climate_cols["julian"]],
                "right_on": ["year", "day"],
                "type": "left",
            }
        ],
        columns=[
            *_event_key_columns("ev", climate_cols),
            f"{_qualify_column('tc', 'Time of Conc (hr)')} AS tc_hours",
        ],
        filters=filters or None,
        order_by=["sim_day_index"],
    )


def _read_interchange_version(run_path: Path) -> Version | None:
    """Return the interchange version from the canonical output directory."""
    interchange_dir = run_path / "wepp" / "output" / "interchange"
    if not interchange_dir.exists():
        return None
    return read_version_manifest(interchange_dir)


def _require_dataset(catalog: DatasetCatalog, path: str) -> None:
    if not catalog.has(path):
        raise FileNotFoundError(path)


def _catalog_field_names(catalog: DatasetCatalog, path: str) -> set[str]:
    entry = catalog.get(path)
    if entry is None:
        raise FileNotFoundError(path)
    schema = entry.schema
    if not schema or "fields" not in schema:
        raise ValueError(f"Missing schema metadata for {path}")
    fields = schema.get("fields")
    if not isinstance(fields, list):
        raise ValueError(f"Invalid schema metadata for {path}")
    names: set[str] = set()
    for field in fields:
        if isinstance(field, dict):
            name = field.get("name")
            if isinstance(name, str):
                names.add(name)
    return names


def _has_column(catalog: DatasetCatalog, path: str, column: str) -> bool:
    return column in _catalog_field_names(catalog, path)


def _select_column(
    catalog: DatasetCatalog,
    path: str,
    candidates: Iterable[str],
    *,
    label: str,
) -> str:
    available = _catalog_field_names(catalog, path)
    for candidate in candidates:
        if candidate in available:
            return candidate
    candidate_list = ", ".join(candidates)
    raise KeyError(f"Missing {label} column in {path}. Tried: {candidate_list}")


def _resolve_climate_columns(catalog: DatasetCatalog, climate_path: str) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for label, candidates in _CLIMATE_COLUMNS.items():
        resolved[label] = _select_column(catalog, climate_path, candidates, label=label)
    return resolved


def _normalize_intensity_key(value: int | str) -> str:
    key = str(value).strip().lower()
    normalized = _INTENSITY_KEY_MAP.get(key)
    if normalized is None:
        raise KeyError(f"Unsupported intensity selection: {value}")
    return normalized


def _build_intensity_filters(
    climate_cols: Mapping[str, str],
    *,
    intensity: int | str | None,
    min_value: float | None,
    max_value: float | None,
) -> list[dict[str, object]]:
    if intensity is None or min_value is None or max_value is None:
        return []
    intensity_key = _normalize_intensity_key(intensity)
    column = climate_cols[intensity_key]
    return [
        {
            "column": _qualify_column("ev", column),
            "operator": ">=",
            "value": float(min_value),
        },
        {
            "column": _qualify_column("ev", column),
            "operator": "<=",
            "value": float(max_value),
        },
    ]


def _event_key_columns(alias: str, climate_cols: Mapping[str, str]) -> list[str]:
    return [
        f"{_qualify_column(alias, climate_cols['sim_day_index'])} AS sim_day_index",
        f"{_qualify_column(alias, climate_cols['year'])} AS year",
        f"{_qualify_column(alias, climate_cols['julian'])} AS julian",
        f"{_qualify_column(alias, climate_cols['month'])} AS month",
        f"{_qualify_column(alias, climate_cols['day_of_month'])} AS day_of_month",
    ]


def _event_key_group_by(alias: str, climate_cols: Mapping[str, str]) -> list[str]:
    return [
        _qualify_column(alias, climate_cols["sim_day_index"]),
        _qualify_column(alias, climate_cols["year"]),
        _qualify_column(alias, climate_cols["julian"]),
        _qualify_column(alias, climate_cols["month"]),
        _qualify_column(alias, climate_cols["day_of_month"]),
    ]


def _qualify_column(alias: str, column: str) -> str:
    if _SIMPLE_IDENTIFIER_RE.match(column):
        return f"{alias}.{column}"
    escaped = column.replace('"', '""')
    return f'{alias}."{escaped}"'


def _julian_date_expr(alias: str) -> str:
    return f"(MAKE_DATE({alias}.year, 1, 1) + ({alias}.julian - 1))"


def _event_join(strategy: JoinStrategy, *, left_alias: str, right_alias: str, join_type: str) -> dict[str, object]:
    if strategy.uses_sim_day_index:
        left_on = ["sim_day_index"]
        right_on = ["sim_day_index"]
    else:
        left_on = ["year", "julian"]
        right_on = ["year", "julian"]
    return {
        "left": left_alias,
        "right": right_alias,
        "left_on": left_on,
        "right_on": right_on,
        "type": join_type,
    }


def _t1_join(strategy: JoinStrategy, *, left_alias: str, right_alias: str, join_type: str) -> dict[str, object]:
    if strategy.uses_sim_day_index:
        left_on = [f"{left_alias}.sim_day_index - 1"]
        right_on = ["sim_day_index"]
    else:
        left_on = [f"{_julian_date_expr(left_alias)} - 1"]
        right_on = [_julian_date_expr(right_alias)]
    return {
        "left": left_alias,
        "right": right_alias,
        "left_on": left_on,
        "right_on": right_on,
        "type": join_type,
    }
