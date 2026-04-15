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
) -> None:
    artifact_io.write_json(
        wd,
        f"storms/{storm_id}/summary.json",
        {
            "storm_id": storm_id,
            "status": "completed",
            "summary_metrics": {
                "peak_discharge": peak_discharge,
                "time_to_peak": time_to_peak,
                "runoff_volume": runoff_volume,
                "runoff_depth": runoff_depth,
            },
            "assumptions": {
                "storm_distribution_assumption": "neh4_type_b",
            },
        },
    )


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

    assert payload["filters"]["datasource_id"] == "all"
    assert payload["filters"]["ari_years"] == [10, 25]
    assert payload["filters"]["measure"] == "peak_discharge"
    assert payload["assumptions"]["storm_distribution_assumption"] == "neh4_type_b"
    assert payload["chart"]["x_axis"] == "intensity_mm_per_hr"
    assert payload["chart"]["y_axis"] == "selected_measure"
    assert len(payload["event_table"]) == 2
    assert payload["event_table"][0]["storm_id"] == "cligen_30m_10y"
    assert payload["event_table"][1]["storm_id"] == "noaa14_60m_25y"
    assert payload["warnings"] == [{"code": "watershed_large"}, {"code": "source_missing", "storm_id": "noaa14_30m_10y"}]

    filtered = service.build_summary_payload(
        geneva_stub,
        datasource_id="cligen_freq",
        ari_years=[10],
        measure="runoff_depth",
    )
    assert filtered["filters"]["datasource_id"] == "cligen_freq"
    assert filtered["filters"]["ari_years"] == [10]
    assert filtered["filters"]["measure"] == "runoff_depth"
    assert len(filtered["event_table"]) == 1
    assert filtered["event_table"][0]["storm_id"] == "cligen_30m_10y"


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

    with pytest.raises(GenevaValidationError, match="datasource_id must be one of panel datasource_ids or all"):
        service.build_summary_payload(geneva_stub, datasource_id="noaa14_pds")

    with pytest.raises(GenevaValidationError, match="measure must be one of"):
        service.build_summary_payload(geneva_stub, measure="unsupported_measure")
