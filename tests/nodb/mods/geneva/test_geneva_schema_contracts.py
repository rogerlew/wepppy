from __future__ import annotations

import pytest

from wepppy.nodb.mods.geneva.schemas import (
    config_from_mapping,
    normalize_frequency_panel_payload,
    parse_run_batch_request,
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
