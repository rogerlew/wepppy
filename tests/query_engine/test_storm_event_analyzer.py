from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.query_engine.catalog import CatalogEntry, DatasetCatalog
from wepppy.query_engine.storm_event_analyzer import (
    STORM_EVENT_DATASETS,
    build_event_filter_payload,
    build_hydrology_metrics_payload,
    build_soil_saturation_payload,
    build_tc_payload,
    resolve_join_strategy,
)
from wepppy.wepp.interchange.versioning import Version, write_version_manifest

pytestmark = pytest.mark.unit


def _build_catalog(root: Path, schemas: dict[str, list[str]]) -> DatasetCatalog:
    entries = []
    for rel_path, fields in schemas.items():
        entries.append(
            CatalogEntry(
                path=rel_path,
                extension=Path(rel_path).suffix or ".parquet",
                size_bytes=0,
                modified="2024-01-01T00:00:00Z",
                schema={
                    "fields": [{"name": name, "type": "int64"} for name in fields],
                },
            )
        )
    return DatasetCatalog(root=root, entries=entries)


def _write_manifest(run_dir: Path, version: Version) -> None:
    interchange_dir = run_dir / "wepp" / "output" / "interchange"
    write_version_manifest(interchange_dir, version=version)


def _base_schemas(include_tc: bool = True) -> dict[str, list[str]]:
    schemas = {
        STORM_EVENT_DATASETS["climate"]: [
            "sim_day_index",
            "year",
            "julian",
            "month",
            "day_of_month",
            "prcp",
            "dur",
            "tp",
            "ip",
            "peak_intensity_10",
            "peak_intensity_15",
            "peak_intensity_30",
            "peak_intensity_60",
        ],
        STORM_EVENT_DATASETS["soil"]: [
            "sim_day_index",
            "year",
            "julian",
            "month",
            "day_of_month",
            "Saturation",
        ],
        STORM_EVENT_DATASETS["water"]: [
            "sim_day_index",
            "year",
            "julian",
            "month",
            "day_of_month",
            "Snow-Water",
        ],
        STORM_EVENT_DATASETS["hillslope_events"]: [
            "sim_day_index",
            "year",
            "julian",
            "month",
            "day_of_month",
            "wepp_id",
            "Precip",
        ],
        STORM_EVENT_DATASETS["outlet_events"]: [
            "sim_day_index",
            "year",
            "julian",
            "month",
            "day_of_month",
            "runoff_volume",
            "peak_runoff",
            "sediment_yield",
        ],
        STORM_EVENT_DATASETS["hillslopes"]: [
            "wepp_id",
            "area",
        ],
    }
    if include_tc:
        schemas[STORM_EVENT_DATASETS["tc_out"]] = [
            "year",
            "day",
            "Time of Conc (hr)",
        ]
    return schemas


def test_resolve_join_strategy_uses_sim_day_index(tmp_path: Path) -> None:
    _write_manifest(tmp_path, Version(major=1, minor=1))
    catalog = _build_catalog(tmp_path, _base_schemas(include_tc=False))

    strategy = resolve_join_strategy(
        tmp_path,
        catalog,
        dataset_paths=[
            STORM_EVENT_DATASETS["climate"],
            STORM_EVENT_DATASETS["soil"],
        ],
    )

    assert strategy.mode == "sim_day_index"


def test_resolve_join_strategy_falls_back_without_manifest(tmp_path: Path) -> None:
    catalog = _build_catalog(tmp_path, _base_schemas(include_tc=False))

    strategy = resolve_join_strategy(
        tmp_path,
        catalog,
        dataset_paths=[
            STORM_EVENT_DATASETS["climate"],
            STORM_EVENT_DATASETS["soil"],
        ],
    )

    assert strategy.mode == "year_julian"


def test_resolve_join_strategy_raises_when_sim_day_missing(tmp_path: Path) -> None:
    _write_manifest(tmp_path, Version(major=1, minor=1))
    schemas = _base_schemas(include_tc=False)
    schemas[STORM_EVENT_DATASETS["soil"]] = [
        "year",
        "julian",
        "month",
        "day_of_month",
        "Saturation",
    ]
    catalog = _build_catalog(tmp_path, schemas)

    with pytest.raises(KeyError, match="sim_day_index"):
        resolve_join_strategy(
            tmp_path,
            catalog,
            dataset_paths=[
                STORM_EVENT_DATASETS["climate"],
                STORM_EVENT_DATASETS["soil"],
            ],
        )


def test_soil_payload_uses_sim_day_index_t1_join(tmp_path: Path) -> None:
    _write_manifest(tmp_path, Version(major=1, minor=1))
    catalog = _build_catalog(tmp_path, _base_schemas(include_tc=False))

    payload = build_soil_saturation_payload(
        tmp_path,
        catalog,
        intensity=10,
        min_value=1.0,
        max_value=2.0,
    )

    join = payload.join_specs[0]
    assert join.left_on == ["ev.sim_day_index - 1"]
    assert join.right_on == ["sim_day_index"]


def test_soil_payload_uses_julian_fallback_t1_join(tmp_path: Path) -> None:
    catalog = _build_catalog(tmp_path, _base_schemas(include_tc=False))

    payload = build_soil_saturation_payload(
        tmp_path,
        catalog,
        intensity=10,
        min_value=1.0,
        max_value=2.0,
    )

    join = payload.join_specs[0]
    assert "MAKE_DATE(ev.year" in join.left_on[0]
    assert "MAKE_DATE(soil.year" in join.right_on[0]


def test_tc_payload_optional_when_missing(tmp_path: Path) -> None:
    catalog = _build_catalog(tmp_path, _base_schemas(include_tc=False))

    payload = build_tc_payload(tmp_path, catalog)

    assert payload is None


def test_event_filter_payload_includes_intensity_filters(tmp_path: Path) -> None:
    catalog = _build_catalog(tmp_path, _base_schemas(include_tc=False))

    payload = build_event_filter_payload(
        tmp_path,
        catalog,
        intensity="10-min",
        min_value=5.0,
        max_value=7.5,
    )

    ops = [filt["operator"] for filt in payload.filters or []]
    assert ops == [">=", "<="]
    assert payload.order_by[0] == "peak_intensity_10"


def test_hydrology_payload_includes_runoff_coefficient(tmp_path: Path) -> None:
    _write_manifest(tmp_path, Version(major=1, minor=1))
    catalog = _build_catalog(tmp_path, _base_schemas(include_tc=False))

    payload = build_hydrology_metrics_payload(
        tmp_path,
        catalog,
        intensity=30,
        min_value=5.0,
        max_value=7.5,
    )

    aliases = {agg.alias for agg in payload.aggregation_specs}
    assert "runoff_coefficient" in aliases
    assert "precip_volume_m3" in aliases
