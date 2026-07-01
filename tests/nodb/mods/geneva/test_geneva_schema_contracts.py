from __future__ import annotations

import pytest

from wepppy.nodb.mods.geneva.schemas import (
    GENEVA_DISTRIBUTION_IDS,
    config_from_mapping,
    normalize_frequency_panel_payload,
    parse_run_batch_request,
)
from wepppy.nodb.mods.geneva.collaborators.frequency_panel_service import (
    GenevaFrequencyPanelService,
    _normalize_cligen_text_for_kernel,
    _normalize_noaa_text_for_kernel,
)


pytestmark = pytest.mark.unit


def test_config_schema_rejects_non_boolean_and_string_hsg_code() -> None:
    with pytest.raises(ValueError, match="enabled must be boolean"):
        config_from_mapping({"enabled": "true"})

    with pytest.raises(ValueError, match="default_hsg_code must be an integer when provided"):
        config_from_mapping({"default_hsg_code": "2"})


def test_run_batch_schema_rejects_unknown_datasource_id() -> None:
    with pytest.raises(ValueError, match="datasource_id must be one of"):
        parse_run_batch_request(
            {
                "schema_version": 1,
                "event_filter": {
                    "datasource_ids": ["unsupported_source"],
                },
                "hyetograph": {
                    "distribution_type": "neh4_type_b",
                    "time_step_minutes": 1.0,
                },
                "runoff_model": {
                    "timing_method": "kirpich",
                },
            },
            default_lambda_mode="0.20",
            default_uh_method="scs_triangular",
        )


def test_run_batch_schema_accepts_all_closed_storm_shapes_and_defaults_missing() -> None:
    for distribution_type in GENEVA_DISTRIBUTION_IDS:
        request = parse_run_batch_request(
            {
                "schema_version": 1,
                "hyetograph": {
                    "distribution_type": distribution_type,
                    "time_step_minutes": 1.0,
                },
                "runoff_model": {
                    "timing_method": "kirpich",
                },
            },
            default_lambda_mode="0.20",
            default_uh_method="scs_triangular",
        )
        assert request.hyetograph.distribution_type == distribution_type

    defaulted = parse_run_batch_request(
        {
            "schema_version": 1,
            "runoff_model": {
                "timing_method": "kirpich",
            },
        },
        default_lambda_mode="0.20",
        default_uh_method="scs_triangular",
    )
    assert defaulted.hyetograph.distribution_type == "neh4_type_b"


def test_run_batch_schema_rejects_unsupported_storm_shape() -> None:
    with pytest.raises(ValueError, match="distribution_type must be one of"):
        parse_run_batch_request(
            {
                "schema_version": 1,
                "hyetograph": {
                    "distribution_type": "custom_breakpoint",
                    "time_step_minutes": 1.0,
                },
                "runoff_model": {
                    "timing_method": "kirpich",
                },
            },
            default_lambda_mode="0.20",
            default_uh_method="scs_triangular",
        )


def test_frequency_panel_schema_enforces_reason_code_invariants() -> None:
    with pytest.raises(ValueError, match="reason_code must be null when availability=available"):
        normalize_frequency_panel_payload(
            {
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
                        "availability": "available",
                        "reason_code": "source_missing",
                    }
                ],
            }
        )


def test_frequency_panel_schema_rejects_non_positive_available_depth_and_intensity() -> None:
    with pytest.raises(
        ValueError,
        match="available cells must include positive depth_mm and intensity_mm_per_hr",
    ):
        normalize_frequency_panel_payload(
            {
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
                        "depth_mm": 0.0,
                        "intensity_mm_per_hr": 0.0,
                        "availability": "available",
                        "reason_code": None,
                    }
                ],
            }
        )


def test_cligen_normalization_maps_precipitation_depth_label_for_kernel() -> None:
    source_text = (
        "PRECIPITATION FREQUENCY ESTIMATES\n"
        "by metric for ARI (years):, 1,2,5\n"
        "Precipitation depth (mm):, 12.1,15.0,20.2\n"
        "Storm duration (hours):, 0.5,1.0,2.0\n"
        "10-min intensity (mm/hour):, 20.0,30.0,40.0\n"
        "15-min intensity (mm/hour):, 18.0,28.0,38.0\n"
    )
    normalized = _normalize_cligen_text_for_kernel(source_text)
    assert normalized is not None
    assert "Storm depth (mm):, 12.1,15.0,20.2" in normalized
    assert "Precipitation depth (mm):" not in normalized
    assert "10-min intensity (mm/hour):, 20.0,30.0,40.0" in normalized
    assert "15-min intensity (mm/hour):, 18.0,28.0,38.0" in normalized


def test_cligen_normalization_noops_when_kernel_row_already_present() -> None:
    source_text = (
        "PRECIPITATION FREQUENCY ESTIMATES\n"
        "by metric for ARI (years):, 1,2\n"
        "Storm depth (mm):, 8.0,10.5\n"
        "Storm duration (hours):, 0.5,1.0\n"
    )
    assert _normalize_cligen_text_for_kernel(source_text) is None


def test_noaa_normalization_omits_non_positive_intensity_rows_for_kernel() -> None:
    source_text = (
        "Point precipitation frequency estimates (millimeters/hour)\n"
        "NOAA Atlas 14 Volume 12 Version 2\n"
        "\n"
        "PRECIPITATION FREQUENCY ESTIMATES\n"
        "by duration for ARI (years):, 1,2,5\n"
        "24-hr:, 1,2,3\n"
        "7-day:, 0,0,1\n"
        "10-day:, 0,0,0\n"
        "\n"
        "Date/time (GMT): Tue Jun 30 23:27:55 2026\n"
        "pyRunTime: 0.77\n"
    )

    normalized = _normalize_noaa_text_for_kernel(source_text)

    assert normalized is not None
    assert "24-hr:, 1,2,3" in normalized
    assert "7-day:" not in normalized
    assert "10-day:" not in normalized
    assert "Date/time (GMT): Tue Jun 30 23:27:55 2026" in normalized


def test_noaa_normalization_noops_when_frequency_rows_are_positive() -> None:
    source_text = (
        "PRECIPITATION FREQUENCY ESTIMATES\n"
        "by duration for ARI (years):, 1,2\n"
        "24-hr:, 1,2\n"
        "2-day:, 1,1\n"
    )
    assert _normalize_noaa_text_for_kernel(source_text) is None


def test_frequency_panel_default_durations_include_cligen_15_minute_intensity() -> None:
    request = GenevaFrequencyPanelService().normalize_request({})
    assert request["durations_minutes"] == [5, 10, 15, 30, 60, 120, 180, 360, 720, 1440]


def test_frequency_panel_schema_rejects_string_null_reason_code() -> None:
    with pytest.raises(ValueError, match='reason_code must be null, not string \"null\"'):
        normalize_frequency_panel_payload(
            {
                "schema_version": 1,
                "datasource_ids": ["noaa14_pds"],
                "durations_minutes": [30],
                "ari_years": [10],
                "distribution_type": "neh4_type_b",
                "cells": [
                    {
                        "storm_id": "noaa14_30m_10y",
                        "datasource_id": "noaa14_pds",
                        "duration_minutes": 30,
                        "ari_years": 10,
                        "depth_mm": None,
                        "intensity_mm_per_hr": None,
                        "availability": "unavailable",
                        "reason_code": "null",
                    }
                ],
            }
        )
