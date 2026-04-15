from __future__ import annotations

import pytest

from wepppy.nodb.mods.geneva.schemas import (
    config_from_mapping,
    normalize_frequency_panel_payload,
    parse_run_batch_request,
)
from wepppy.nodb.mods.geneva.collaborators.frequency_panel_service import _normalize_cligen_text_for_kernel


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


def test_cligen_normalization_maps_precipitation_depth_label_for_kernel() -> None:
    source_text = (
        "PRECIPITATION FREQUENCY ESTIMATES\n"
        "by metric for ARI (years):, 1,2,5\n"
        "Precipitation depth (mm):, 12.1,15.0,20.2\n"
        "Storm duration (hours):, 0.5,1.0,2.0\n"
    )
    normalized = _normalize_cligen_text_for_kernel(source_text)
    assert normalized is not None
    assert "Storm depth (mm):, 12.1,15.0,20.2" in normalized
    assert "Precipitation depth (mm):" not in normalized


def test_cligen_normalization_noops_when_kernel_row_already_present() -> None:
    source_text = (
        "PRECIPITATION FREQUENCY ESTIMATES\n"
        "by metric for ARI (years):, 1,2\n"
        "Storm depth (mm):, 8.0,10.5\n"
        "Storm duration (hours):, 0.5,1.0\n"
    )
    assert _normalize_cligen_text_for_kernel(source_text) is None

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
