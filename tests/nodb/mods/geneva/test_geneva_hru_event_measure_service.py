from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from wepppy.nodb.mods.geneva.collaborators.artifact_io import GenevaArtifactIO
from wepppy.nodb.mods.geneva.collaborators.hru_event_measure_service import (
    HRU_EVENT_MEASURE_ARTIFACT_RELPATH,
    HRU_EVENT_MEASURE_DATASET_PATH,
    GenevaHruEventMeasureService,
)
from wepppy.nodb.mods.geneva.errors import GenevaKernelError, GenevaValidationError


pytestmark = pytest.mark.unit


def _geneva_stub(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        wd=str(tmp_path),
        artifact_io=GenevaArtifactIO(),
    )


def _write_legend(geneva: SimpleNamespace, *, hru_id: str = "hru_1", hru_value: int = 1) -> None:
    geneva.artifact_io.write_json(
        geneva.wd,
        "hru_map_legend.json",
        {
            "schema_version": 1,
            "hru_map_relpath": "hru_map.tif",
            "nodata_value": 0,
            "mapping_status": "complete",
            "active_cell_count": 1,
            "mapped_cell_count": 1,
            "unmapped_cell_count": 0,
            "unresolved_component_count": 0,
            "unresolved_component_samples": [],
            "rows": [
                {
                    "hru_value": hru_value,
                    "hru_id": hru_id,
                    "landuse_class": 42,
                    "hsg_group": "B",
                    "burn_severity_class": "unburned",
                    "hydrophobic_class": False,
                    "is_water": False,
                    "collapsed_from_hru_ids": [],
                }
            ],
        },
    )


def test_materialize_from_batch_writes_contract_rows(tmp_path: Path) -> None:
    service = GenevaHruEventMeasureService()
    geneva = _geneva_stub(tmp_path)
    _write_legend(geneva)

    meta = service.materialize_from_batch(
        geneva,
        available_cells=[
            {
                "storm_id": "cligen_30m_10y",
                "datasource_id": "cligen_freq",
                "duration_minutes": 30,
                "ari_years": 10,
                "distribution_type": "neh4_type_b",
            }
        ],
        storm_results=[
            {
                "storm_id": "cligen_30m_10y",
                "status": "completed",
                "hru_excess": [
                    {
                        "hru_id": "hru_1",
                        "area_m2": 900.0,
                        "cumulative_excess_mm": [0.0, 4.0],
                        "peak_runoff_m3_s": 1.8,
                    }
                ],
            }
        ],
    )

    assert meta["path"] == "geneva/hru_event_measure_rows.parquet"
    assert meta["row_count"] == 3

    rows = geneva.artifact_io.read_records_parquet(geneva.wd, HRU_EVENT_MEASURE_ARTIFACT_RELPATH)
    assert len(rows) == 3
    measure_ids = sorted(str(row["measure_id"]) for row in rows)
    assert measure_ids == ["hru_peak_runoff", "runoff_depth", "runoff_volume"]
    assert {str(row["unit"]) for row in rows} == {"mm", "m3", "m3_s"}
    assert all(str(row["storm_id"]) == "cligen_30m_10y" for row in rows)
    assert all(str(row["hru_id"]) == "hru_1" for row in rows)
    assert all(int(row["hru_value"]) == 1 for row in rows)


def test_materialize_from_batch_validates_hru_crosswalk(tmp_path: Path) -> None:
    service = GenevaHruEventMeasureService()
    geneva = _geneva_stub(tmp_path)
    _write_legend(geneva, hru_id="hru_x", hru_value=3)

    with pytest.raises(GenevaKernelError) as exc_info:
        service.materialize_from_batch(
            geneva,
            available_cells=[
                {
                    "storm_id": "cligen_30m_10y",
                    "datasource_id": "cligen_freq",
                    "duration_minutes": 30,
                    "ari_years": 10,
                    "distribution_type": "neh4_type_b",
                }
            ],
            storm_results=[
                {
                    "storm_id": "cligen_30m_10y",
                    "status": "completed",
                    "hru_excess": [
                        {
                            "hru_id": "hru_1",
                            "area_m2": 900.0,
                            "cumulative_excess_mm": [0.0, 4.0],
                            "peak_runoff_m3_s": 1.8,
                        }
                    ],
                }
            ],
        )

    assert exc_info.value.code == "contract_violation"


def test_query_rows_returns_legacy_unavailable_when_artifact_missing(tmp_path: Path) -> None:
    service = GenevaHruEventMeasureService()
    geneva = _geneva_stub(tmp_path)

    payload = service.query_rows(
        geneva,
        storm_id="cligen_30m_10y",
        measure_id="runoff_depth",
    )

    assert payload["availability"]["status"] == "unavailable"
    assert payload["availability"]["reason_code"] == "legacy_hru_event_measures_missing"
    assert payload["records"] == []
    assert payload["row_count"] == 0


def test_query_rows_accepts_hru_peak_runoff_measure_id(tmp_path: Path) -> None:
    service = GenevaHruEventMeasureService()
    geneva = _geneva_stub(tmp_path)

    payload = service.query_rows(
        geneva,
        storm_id="cligen_30m_10y",
        measure_id="hru_peak_runoff",
    )

    assert payload["availability"]["status"] == "unavailable"
    assert payload["filters"]["measure_id"] == "hru_peak_runoff"


def test_query_rows_rejects_peak_discharge_scope(tmp_path: Path) -> None:
    service = GenevaHruEventMeasureService()
    geneva = _geneva_stub(tmp_path)

    with pytest.raises(GenevaValidationError) as exc_info:
        service.query_rows(
            geneva,
            storm_id="cligen_30m_10y",
            measure_id="peak_discharge",
        )

    assert exc_info.value.code == "unsupported_measure_scope"


def test_query_rows_rejects_blank_storm_id(tmp_path: Path) -> None:
    service = GenevaHruEventMeasureService()
    geneva = _geneva_stub(tmp_path)

    with pytest.raises(GenevaValidationError) as exc_info:
        service.query_rows(
            geneva,
            storm_id="  ",
            measure_id="runoff_depth",
        )

    assert exc_info.value.code == "invalid_input"


def test_query_rows_uses_query_engine_style_filters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GenevaHruEventMeasureService()
    geneva = _geneva_stub(tmp_path)
    _write_legend(geneva)
    geneva.artifact_io.write_records_parquet(
        geneva.wd,
        HRU_EVENT_MEASURE_ARTIFACT_RELPATH,
        [
            {
                "schema_version": 1,
                "storm_id": "cligen_30m_10y",
                "datasource_id": "cligen_freq",
                "duration_minutes": 30,
                "ari_years": 10,
                "distribution_type": "neh4_type_b",
                "hru_id": "hru_1",
                "hru_value": 1,
                "measure_id": "runoff_depth",
                "value": 4.0,
                "unit": "mm",
            }
        ],
    )

    captured_payloads: list[dict[str, Any]] = []

    class _Catalog:
        def has(self, path: str) -> bool:
            return path == HRU_EVENT_MEASURE_DATASET_PATH

    context = SimpleNamespace(catalog=_Catalog())

    monkeypatch.setattr(
        "wepppy.nodb.mods.geneva.collaborators.hru_event_measure_service.update_catalog_entry",
        lambda _wd, _asset_path: None,
    )
    monkeypatch.setattr(
        "wepppy.nodb.mods.geneva.collaborators.hru_event_measure_service.resolve_run_context",
        lambda *_args, **_kwargs: context,
    )

    def _fake_run_query(_context: Any, query_request: Any):
        captured_payloads.append(
            {
                "datasets": [spec.path for spec in query_request.dataset_specs],
                "filters": list(query_request.filters or []),
                "columns": list(query_request.columns or []),
                "order_by": list(query_request.order_by or []),
            }
        )
        return SimpleNamespace(
            records=[
                {
                    "schema_version": 1,
                    "storm_id": "cligen_30m_10y",
                    "datasource_id": "cligen_freq",
                    "duration_minutes": 30,
                    "ari_years": 10,
                    "distribution_type": "neh4_type_b",
                    "hru_id": "hru_1",
                    "hru_value": 1,
                    "measure_id": "runoff_depth",
                    "value": 4.0,
                    "unit": "mm",
                }
            ],
            schema=[{"name": "hru_id", "type": "VARCHAR"}],
            row_count=1,
            formatted=None,
            sql=None,
        )

    monkeypatch.setattr(
        "wepppy.nodb.mods.geneva.collaborators.hru_event_measure_service.run_query",
        _fake_run_query,
    )

    payload = service.query_rows(
        geneva,
        storm_id="cligen_30m_10y",
        measure_id="runoff_depth",
        include_schema=True,
        limit=200,
    )

    assert payload["availability"]["status"] == "available"
    assert payload["row_count"] == 1
    assert payload["records"][0]["hru_id"] == "hru_1"
    assert captured_payloads == [
        {
            "datasets": [HRU_EVENT_MEASURE_DATASET_PATH],
            "filters": [
                {"column": "storm_id", "operator": "=", "value": "cligen_30m_10y"},
                {"column": "measure_id", "operator": "=", "value": "runoff_depth"},
            ],
            "columns": [
                "schema_version",
                "storm_id",
                "datasource_id",
                "duration_minutes",
                "ari_years",
                "distribution_type",
                "hru_id",
                "hru_value",
                "measure_id",
                "value",
                "unit",
            ],
            "order_by": ["hru_value", "hru_id"],
        }
    ]


def test_query_rows_rejects_crosswalk_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GenevaHruEventMeasureService()
    geneva = _geneva_stub(tmp_path)
    _write_legend(geneva, hru_id="hru_1", hru_value=7)
    geneva.artifact_io.write_records_parquet(geneva.wd, HRU_EVENT_MEASURE_ARTIFACT_RELPATH, [])

    class _Catalog:
        def has(self, _path: str) -> bool:
            return True

    context = SimpleNamespace(catalog=_Catalog())
    monkeypatch.setattr(
        "wepppy.nodb.mods.geneva.collaborators.hru_event_measure_service.update_catalog_entry",
        lambda _wd, _asset_path: None,
    )
    monkeypatch.setattr(
        "wepppy.nodb.mods.geneva.collaborators.hru_event_measure_service.resolve_run_context",
        lambda *_args, **_kwargs: context,
    )
    monkeypatch.setattr(
        "wepppy.nodb.mods.geneva.collaborators.hru_event_measure_service.run_query",
        lambda *_args, **_kwargs: SimpleNamespace(
            records=[
                {
                    "schema_version": 1,
                    "storm_id": "cligen_30m_10y",
                    "datasource_id": "cligen_freq",
                    "duration_minutes": 30,
                    "ari_years": 10,
                    "distribution_type": "neh4_type_b",
                    "hru_id": "hru_1",
                    "hru_value": 1,
                    "measure_id": "runoff_depth",
                    "value": 4.0,
                    "unit": "mm",
                }
            ],
            schema=None,
            row_count=1,
            formatted=None,
            sql=None,
        ),
    )

    with pytest.raises(GenevaKernelError) as exc_info:
        service.query_rows(
            geneva,
            storm_id="cligen_30m_10y",
            measure_id="runoff_depth",
        )

    assert exc_info.value.code == "contract_violation"
