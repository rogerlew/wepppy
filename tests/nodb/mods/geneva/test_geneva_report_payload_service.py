from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.mods.geneva.collaborators.artifact_io import GenevaArtifactIO
from wepppy.nodb.mods.geneva.collaborators.report_payload_service import GenevaReportPayloadService
from wepppy.nodb.mods.geneva.errors import GenevaValidationError


pytestmark = pytest.mark.unit


def _write_storm_summary(
    artifact_io: GenevaArtifactIO,
    wd: str,
    storm_id: str,
    *,
    peak_discharge: float,
    time_to_peak: float,
    runoff_volume: float,
    runoff_depth: float,
    distribution_type: str = "neh4_type_b",
    uniform_rainfall_assumed: bool | None = None,
    include_hyetograph_section: bool = True,
) -> None:
    assumptions = {
        "storm_distribution_assumption": distribution_type,
        "distribution_type": distribution_type,
    }
    if uniform_rainfall_assumed is not None:
        assumptions["uniform_rainfall_assumed"] = uniform_rainfall_assumed

    payload = {
        "storm_id": storm_id,
        "status": "completed",
        "summary_metrics": {
            "peak_discharge": peak_discharge,
            "time_to_peak": time_to_peak,
            "runoff_volume": runoff_volume,
            "runoff_depth": runoff_depth,
        },
        "assumptions": assumptions,
    }
    if include_hyetograph_section:
        payload["hyetograph"] = {"distribution_type": distribution_type}

    artifact_io.write_json(wd, f"storms/{storm_id}/summary.json", payload)


def test_build_summary_payload_shapes_chart_and_event_table(tmp_path: Path) -> None:
    artifact_io = GenevaArtifactIO()
    wd = str(tmp_path)

    panel_payload = {
        "schema_version": 1,
        "datasource_ids": ["cligen_freq", "noaa14_pds"],
        "durations_minutes": [30, 60],
        "ari_years": [10, 25],
        "distribution_type": "neh4_type_b",
        "cells": [
            {
                "storm_id": "cligen_30m_10y",
                "datasource_id": "cligen_freq",
                "duration_minutes": 30,
                "ari_years": 10,
                "depth_mm": 20.0,
                "intensity_mm_per_hr": 40.0,
                "distribution_type": "neh4_type_b",
                "availability": "available",
                "reason_code": None,
            },
            {
                "storm_id": "noaa14_60m_25y",
                "datasource_id": "noaa14_pds",
                "duration_minutes": 60,
                "ari_years": 25,
                "depth_mm": 50.0,
                "intensity_mm_per_hr": 50.0,
                "distribution_type": "neh4_type_b",
                "availability": "available",
                "reason_code": None,
            },
            {
                "storm_id": "noaa14_30m_10y",
                "datasource_id": "noaa14_pds",
                "duration_minutes": 30,
                "ari_years": 10,
                "depth_mm": None,
                "intensity_mm_per_hr": None,
                "distribution_type": "neh4_type_b",
                "availability": "unavailable",
                "reason_code": "source_missing",
            },
        ],
        "warnings": [{"code": "source_missing", "storm_id": "noaa14_30m_10y"}],
    }

    _write_storm_summary(
        artifact_io,
        wd,
        "cligen_30m_10y",
        peak_discharge=1.2,
        time_to_peak=5.0,
        runoff_volume=100.0,
        runoff_depth=4.0,
    )
    _write_storm_summary(
        artifact_io,
        wd,
        "noaa14_60m_25y",
        peak_discharge=3.4,
        time_to_peak=8.0,
        runoff_volume=220.0,
        runoff_depth=7.5,
    )

    geneva_stub = SimpleNamespace(
        wd=wd,
        artifact_io=artifact_io,
        frequency_panel_service=SimpleNamespace(get_frequency_panel=lambda _geneva: panel_payload),
        _warnings=[{"code": "watershed_large"}],
    )

    service = GenevaReportPayloadService()
    payload = service.build_summary_payload(
        geneva_stub,
        datasource_id="all",
        measure="peak_discharge",
    )

    assert payload["schema_version"] == 1
    assert payload["filters"]["datasource_id"] == "all"
    assert payload["filters"]["ari_years"] == [10, 25]
    assert payload["filters"]["measure"] == "peak_discharge"
    assert payload["filter_options"]["datasource_ids"] == ["all", "cligen_freq", "noaa14_pds"]
    assert payload["filter_options"]["measures"] == ["peak_discharge", "runoff_depth", "runoff_volume"]
    assert payload["filter_options"]["ari_years"] == [10, 25]
    assert payload["filter_options"]["duration_minutes"] == [30, 60]
    assert payload["selected_storm_id"] == "cligen_30m_10y"
    assert payload["assumptions"]["storm_distribution_assumption"] == "neh4_type_b"
    assert payload["assumptions"]["uniform_rainfall_assumed"] is False
    assert payload["chart"]["x_axis"] == "intensity_mm_per_hr"
    assert payload["chart"]["y_axis"] == "selected_measure"
    assert payload["chart"]["series_grouping"] == "ari_years"
    assert payload["chart"]["marker_grouping"] == "duration_minutes"
    assert len(payload["event_table"]) == 3
    first_row = payload["event_table"][0]
    second_row = payload["event_table"][1]
    third_row = payload["event_table"][2]
    assert first_row["storm_id"] == "cligen_30m_10y"
    assert first_row["status"] == "completed"
    assert first_row["peak_discharge"] == {"value": 1.2, "unit": "m3_s"}
    assert first_row["runoff_volume"] == {"value": 100.0, "unit": "m3"}
    assert first_row["runoff_depth"] == {"value": 4.0, "unit": "mm"}
    assert first_row["time_to_peak_minutes"] == 5.0
    assert second_row["storm_id"] == "noaa14_30m_10y"
    assert second_row["status"] == "unavailable"
    assert second_row["peak_discharge"] == {"value": None, "unit": "m3_s"}
    assert second_row["runoff_volume"] == {"value": None, "unit": "m3"}
    assert second_row["runoff_depth"] == {"value": None, "unit": "mm"}
    assert third_row["storm_id"] == "noaa14_60m_25y"
    assert third_row["status"] == "completed"
    first_point = payload["chart"]["series"][0]["points"][0]
    assert first_point["storm_id"] == "cligen_30m_10y"
    assert first_point["marker_label"] == "30m"
    assert first_point["intensity_mm_per_hr"] == 40.0
    assert first_point["measure_value"] == 1.2
    assert payload["warnings"] == [{"code": "watershed_large"}, {"code": "source_missing", "storm_id": "noaa14_30m_10y"}]
    assert payload["errors"] == []

    filtered = service.build_summary_payload(
        geneva_stub,
        datasource_id="cligen_freq",
        ari_years=[10],
        measure="runoff_depth",
    )
    assert filtered["filters"]["datasource_id"] == "cligen_freq"
    assert filtered["filters"]["ari_years"] == [10]
    assert filtered["filters"]["measure"] == "runoff_depth"
    assert filtered["selected_storm_id"] == "cligen_30m_10y"
    assert len(filtered["event_table"]) == 1
    assert filtered["event_table"][0]["storm_id"] == "cligen_30m_10y"
    assert filtered["event_table"][0]["runoff_depth"] == {"value": 4.0, "unit": "mm"}
    filtered_point = filtered["chart"]["series"][0]["points"][0]
    assert filtered_point["measure_value"] == 4.0


def test_build_summary_payload_rejects_invalid_filters(tmp_path: Path) -> None:
    artifact_io = GenevaArtifactIO()
    wd = str(tmp_path)
    panel_payload = {
        "schema_version": 1,
        "datasource_ids": ["cligen_freq"],
        "durations_minutes": [30],
        "ari_years": [10],
        "distribution_type": "neh4_type_b",
        "cells": [],
        "warnings": [],
    }
    geneva_stub = SimpleNamespace(
        wd=wd,
        artifact_io=artifact_io,
        frequency_panel_service=SimpleNamespace(get_frequency_panel=lambda _geneva: panel_payload),
        _warnings=[],
    )
    service = GenevaReportPayloadService()

    with pytest.raises(GenevaValidationError, match="datasource_id must be one of all, cligen_freq, noaa14_pds"):
        service.build_summary_payload(geneva_stub, datasource_id="bad_source")

    with pytest.raises(GenevaValidationError, match="measure must be one of"):
        service.build_summary_payload(geneva_stub, measure="unsupported_measure")


def test_build_summary_payload_uses_run_summary_status_over_stale_summary_artifacts(
    tmp_path: Path,
) -> None:
    artifact_io = GenevaArtifactIO()
    wd = str(tmp_path)
    panel_payload = {
        "schema_version": 1,
        "datasource_ids": ["cligen_freq", "noaa14_pds"],
        "durations_minutes": [30, 60],
        "ari_years": [10],
        "distribution_type": "neh4_type_b",
        "cells": [
            {
                "storm_id": "cligen_30m_10y",
                "datasource_id": "cligen_freq",
                "duration_minutes": 30,
                "ari_years": 10,
                "depth_mm": 20.0,
                "intensity_mm_per_hr": 40.0,
                "distribution_type": "neh4_type_b",
                "availability": "available",
                "reason_code": None,
            },
            {
                "storm_id": "noaa14_60m_10y",
                "datasource_id": "noaa14_pds",
                "duration_minutes": 60,
                "ari_years": 10,
                "depth_mm": 30.0,
                "intensity_mm_per_hr": 30.0,
                "distribution_type": "neh4_type_b",
                "availability": "available",
                "reason_code": None,
            },
        ],
        "warnings": [],
    }

    _write_storm_summary(
        artifact_io,
        wd,
        "cligen_30m_10y",
        peak_discharge=2.0,
        time_to_peak=4.0,
        runoff_volume=110.0,
        runoff_depth=5.0,
    )
    _write_storm_summary(
        artifact_io,
        wd,
        "noaa14_60m_10y",
        peak_discharge=9.9,
        time_to_peak=11.0,
        runoff_volume=999.0,
        runoff_depth=12.0,
    )

    geneva_stub = SimpleNamespace(
        wd=wd,
        artifact_io=artifact_io,
        frequency_panel_service=SimpleNamespace(get_frequency_panel=lambda _geneva: panel_payload),
        _run_summary={
            "completed_storm_ids": ["cligen_30m_10y"],
            "failed_storm_ids": ["noaa14_60m_10y"],
            "warnings": [{"storm_id": "noaa14_60m_10y", "code": "source_missing"}],
            "errors": [{"storm_id": "noaa14_60m_10y", "message": "kernel failed"}],
        },
        _warnings=[{"code": "upstream_warning", "debug_trace": "internal detail"}],
        _errors=[{"code": "batch_error", "details": {"sensitive": True}}],
    )

    service = GenevaReportPayloadService()
    payload = service.build_summary_payload(geneva_stub, measure="peak_discharge")

    assert payload["selected_storm_id"] == "cligen_30m_10y"
    assert len(payload["event_table"]) == 2

    completed_row = next(row for row in payload["event_table"] if row["storm_id"] == "cligen_30m_10y")
    failed_row = next(row for row in payload["event_table"] if row["storm_id"] == "noaa14_60m_10y")

    assert completed_row["status"] == "completed"
    assert completed_row["peak_discharge"] == {"value": 2.0, "unit": "m3_s"}

    # Failed status must come from run summary, and stale summary metrics are suppressed.
    assert failed_row["status"] == "failed"
    assert failed_row["peak_discharge"] == {"value": None, "unit": "m3_s"}
    assert failed_row["warning_count"] == 1
    assert failed_row["error_count"] == 1

    chart_points = [
        point["storm_id"]
        for series in payload["chart"]["series"]
        for point in series.get("points", [])
    ]
    assert chart_points == ["cligen_30m_10y"]

    # Summary payload sanitizes free-form/internal warning/error fields.
    assert payload["warnings"] == [{"code": "upstream_warning"}]
    assert payload["errors"] == [{"code": "batch_error"}]


def test_build_summary_payload_ignores_completed_summary_when_shape_mismatches_panel(
    tmp_path: Path,
) -> None:
    artifact_io = GenevaArtifactIO()
    wd = str(tmp_path)
    panel_payload = {
        "schema_version": 1,
        "datasource_ids": ["cligen_freq"],
        "durations_minutes": [60],
        "ari_years": [10],
        "distribution_type": "uniform",
        "cells": [
            {
                "storm_id": "cligen_60m_10y",
                "datasource_id": "cligen_freq",
                "duration_minutes": 60,
                "ari_years": 10,
                "depth_mm": 20.0,
                "intensity_mm_per_hr": 20.0,
                "distribution_type": "uniform",
                "availability": "available",
                "reason_code": None,
            }
        ],
        "warnings": [],
    }

    _write_storm_summary(
        artifact_io,
        wd,
        "cligen_60m_10y",
        peak_discharge=9.9,
        time_to_peak=11.0,
        runoff_volume=999.0,
        runoff_depth=12.0,
        distribution_type="type_ii",
    )

    geneva_stub = SimpleNamespace(
        wd=wd,
        artifact_io=artifact_io,
        frequency_panel_service=SimpleNamespace(get_frequency_panel=lambda _geneva: panel_payload),
        _run_summary={
            "completed_storm_ids": ["cligen_60m_10y"],
            "failed_storm_ids": [],
            "warnings": [],
            "errors": [],
        },
        _warnings=[],
        _errors=[],
    )

    service = GenevaReportPayloadService()
    payload = service.build_summary_payload(geneva_stub)

    row = payload["event_table"][0]
    assert row["status"] == "unavailable"
    assert row["distribution_type"] == "uniform"
    assert row["peak_discharge"] == {"value": None, "unit": "m3_s"}


def test_build_summary_payload_preserves_watershed_warning_severity_fields(tmp_path: Path) -> None:
    artifact_io = GenevaArtifactIO()
    wd = str(tmp_path)
    panel_payload = {
        "schema_version": 1,
        "datasource_ids": ["cligen_freq"],
        "durations_minutes": [30],
        "ari_years": [10],
        "distribution_type": "neh4_type_b",
        "cells": [],
        "warnings": [],
    }
    geneva_stub = SimpleNamespace(
        wd=wd,
        artifact_io=artifact_io,
        frequency_panel_service=SimpleNamespace(get_frequency_panel=lambda _geneva: panel_payload),
        _warnings=[
            {
                "code": "point_rainfall_assumption",
                "severity": "warning",
                "message": "Point rainfall assumption may under-represent watershed-scale variability.",
                "wsarea_km2": 30.0,
                "threshold_km2": 25.0,
                "thresholds_km2": {"warning": 25.0, "severe": 100.0, "extreme": 250.0},
                "arf_method": "constant_1.0",
                "arf_value": 1.0,
                "uniform_rainfall_assumed": True,
                "debug_trace": "internal detail",
            }
        ],
        _errors=[],
    )

    service = GenevaReportPayloadService()
    payload = service.build_summary_payload(geneva_stub)

    assert payload["warnings"] == [
        {
            "code": "point_rainfall_assumption",
            "severity": "warning",
            "message": "Point rainfall assumption may under-represent watershed-scale variability.",
            "wsarea_km2": 30.0,
            "threshold_km2": 25.0,
            "thresholds_km2": {"warning": 25.0, "severe": 100.0, "extreme": 250.0},
            "arf_method": "constant_1.0",
            "arf_value": 1.0,
            "uniform_rainfall_assumed": True,
        }
    ]


def test_build_summary_payload_surfaces_legacy_uniform_interim_warning(tmp_path: Path) -> None:
    artifact_io = GenevaArtifactIO()
    wd = str(tmp_path)
    panel_payload = {
        "schema_version": 1,
        "datasource_ids": ["cligen_freq"],
        "durations_minutes": [30],
        "ari_years": [10],
        "distribution_type": "neh4_type_b",
        "cells": [
            {
                "storm_id": "cligen_30m_10y",
                "datasource_id": "cligen_freq",
                "duration_minutes": 30,
                "ari_years": 10,
                "depth_mm": 20.0,
                "intensity_mm_per_hr": 40.0,
                "distribution_type": "neh4_type_b",
                "availability": "available",
                "reason_code": None,
            }
        ],
        "warnings": [],
    }

    _write_storm_summary(
        artifact_io,
        wd,
        "cligen_30m_10y",
        peak_discharge=1.2,
        time_to_peak=5.0,
        runoff_volume=100.0,
        runoff_depth=4.0,
        distribution_type="neh4_type_b",
        uniform_rainfall_assumed=True,
        include_hyetograph_section=False,
    )

    geneva_stub = SimpleNamespace(
        wd=wd,
        artifact_io=artifact_io,
        frequency_panel_service=SimpleNamespace(get_frequency_panel=lambda _geneva: panel_payload),
        _warnings=[],
        _errors=[],
    )

    payload = GenevaReportPayloadService().build_summary_payload(geneva_stub)
    assert payload["assumptions"]["legacy_uniform_interim_artifact_count"] == 1
    assert "stale_artifact_policy" in payload["assumptions"]
    assert payload["warnings"] == [
        {
            "code": "legacy_uniform_interim_artifacts",
            "message": payload["assumptions"]["stale_artifact_policy"],
            "legacy_uniform_interim_artifact_count": 1,
        }
    ]
