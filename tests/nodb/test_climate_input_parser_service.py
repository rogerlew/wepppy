from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from wepppy.nodb.core.climate import CLIMATE_MAX_YEARS, ClimateMode, ClimateSpatialMode
from wepppy.nodb.core.climate_input_parser import ClimateInputParsingService

pytestmark = pytest.mark.unit


class _DummyClimate:
    def __init__(self) -> None:
        self.events: list[object] = []
        self._catalog: dict[str, object] = {}
        self._catalog_id = None
        self._climate_mode = ClimateMode.Undefined
        self._climate_spatialmode = ClimateSpatialMode.Single
        self._input_years = None
        self._orig_cli_fn = None
        self._climate_daily_temp_ds = None
        self._precip_scaling_mode = None
        self._precip_scale_factor = None
        self._precip_monthly_scale_factors = None
        self._precip_scaling_reference = None
        self._precip_scale_factor_map = None
        self._observed_start_year = ""
        self._observed_end_year = ""
        self._future_start_year = ""
        self._future_end_year = ""

    @contextmanager
    def locked(self):
        self.events.append("lock-enter")
        yield
        self.events.append("lock-exit")

    def _resolve_catalog_dataset(self, catalog_id: str):
        return self._catalog.get(catalog_id)

    def set_observed_pars(self, **kwds):
        self.events.append(("observed", kwds))

    def set_future_pars(self, **kwds):
        self.events.append(("future", kwds))

    def set_single_storm_pars(self, **kwds):
        self.events.append(("single-storm", kwds["ss_storm_date"]))


def _payload() -> dict[str, str]:
    return {
        "input_years": "50",
        "observed_start_year": "1981",
        "observed_end_year": "2020",
        "future_start_year": "2030",
        "future_end_year": "2040",
        "ss_storm_date": "4 15 01",
        "ss_design_storm_amount_inches": "6.3",
        "ss_duration_of_storm_in_hours": "6.0",
        "ss_time_to_peak_intensity_pct": "40",
        "ss_max_intensity_inches_per_hour": "3.0",
        "ss_batch": "",
        "climate_daily_temp_ds": "null",
        "precip_scaling_mode": "0",
    }


def test_parse_inputs_catalog_sets_mode_and_spatial_mode() -> None:
    parser = ClimateInputParsingService()
    climate = _DummyClimate()
    climate._catalog["prism_stochastic"] = SimpleNamespace(
        catalog_id="prism_stochastic",
        climate_mode=int(ClimateMode.PRISM),
        spatial_modes=[int(ClimateSpatialMode.Single), int(ClimateSpatialMode.Multiple)],
        default_spatial_mode=int(ClimateSpatialMode.Multiple),
    )

    payload = _payload()
    payload["climate_catalog_id"] = "prism_stochastic"
    payload["climate_spatialmode"] = str(int(ClimateSpatialMode.Multiple))

    parser.parse_inputs(climate, payload)

    assert climate._catalog_id == "prism_stochastic"
    assert climate._climate_mode == ClimateMode.PRISM
    assert climate._climate_spatialmode == ClimateSpatialMode.Multiple
    assert climate._input_years == 50


def test_parse_inputs_rejects_invalid_catalog_spatial_mode() -> None:
    parser = ClimateInputParsingService()
    climate = _DummyClimate()
    climate._catalog["prism_stochastic"] = SimpleNamespace(
        catalog_id="prism_stochastic",
        climate_mode=int(ClimateMode.PRISM),
        spatial_modes=[int(ClimateSpatialMode.Single)],
        default_spatial_mode=int(ClimateSpatialMode.Single),
    )

    payload = _payload()
    payload["climate_catalog_id"] = "prism_stochastic"
    payload["climate_spatialmode"] = str(int(ClimateSpatialMode.MultipleInterpolated))

    with pytest.raises(ValueError):
        parser.parse_inputs(climate, payload)


def test_parse_inputs_vanilla_checks_input_year_bounds() -> None:
    parser = ClimateInputParsingService()
    climate = _DummyClimate()
    payload = _payload()
    payload["climate_mode"] = str(int(ClimateMode.Vanilla))
    payload["input_years"] = str(CLIMATE_MAX_YEARS + 1)

    with pytest.raises(AssertionError):
        parser.parse_inputs(climate, payload)


def test_parse_inputs_rejects_deprecated_single_storm_modes() -> None:
    parser = ClimateInputParsingService()
    climate = _DummyClimate()
    payload = _payload()
    payload["climate_mode"] = str(int(ClimateMode.SingleStorm))
    payload["climate_spatialmode"] = str(int(ClimateSpatialMode.Multiple))

    with pytest.raises(
        ValueError,
        match="Single-storm climate modes are deprecated and unsupported",
    ):
        parser.parse_inputs(climate, payload)


def test_parse_inputs_keeps_lock_scope_around_core_parsing_only() -> None:
    parser = ClimateInputParsingService()
    climate = _DummyClimate()
    payload = _payload()
    payload["climate_mode"] = str(int(ClimateMode.Vanilla))

    parser.parse_inputs(climate, payload)

    assert climate.events[0] == "lock-enter"
    assert climate.events[1] == "lock-exit"
    assert climate.events[2][0] == "observed"
    assert all(not (isinstance(event, tuple) and event[0] == "future") for event in climate.events)


def test_parse_inputs_prism_mode_allows_missing_future_year_bounds() -> None:
    parser = ClimateInputParsingService()
    climate = _DummyClimate()
    payload = _payload()
    payload["climate_mode"] = str(int(ClimateMode.PRISM))
    payload.pop("future_start_year")
    payload.pop("future_end_year")

    parser.parse_inputs(climate, payload)

    observed_events = [event for event in climate.events if isinstance(event, tuple) and event[0] == "observed"]
    future_events = [event for event in climate.events if isinstance(event, tuple) and event[0] == "future"]
    assert observed_events
    assert future_events == []


def test_parse_inputs_future_mode_requires_future_year_bounds() -> None:
    parser = ClimateInputParsingService()
    climate = _DummyClimate()
    payload = _payload()
    payload["climate_mode"] = str(int(ClimateMode.Future))
    payload.pop("future_end_year")

    with pytest.raises(ValueError, match="future_end_year"):
        parser.parse_inputs(climate, payload)


def test_parse_inputs_future_mode_validation_failure_does_not_mutate_observed_year_bounds() -> None:
    parser = ClimateInputParsingService()
    climate = _DummyClimate()
    climate._observed_start_year = 1995
    climate._observed_end_year = 2005

    payload = _payload()
    payload["climate_mode"] = str(int(ClimateMode.Future))
    payload.pop("future_end_year")

    with pytest.raises(ValueError, match="future_end_year"):
        parser.parse_inputs(climate, payload)

    assert climate._observed_start_year == 1995
    assert climate._observed_end_year == 2005


def test_parse_inputs_future_mode_clears_stale_observed_year_bounds() -> None:
    parser = ClimateInputParsingService()
    climate = _DummyClimate()
    climate._observed_start_year = 1990
    climate._observed_end_year = 2020

    payload = _payload()
    payload["climate_mode"] = str(int(ClimateMode.Future))
    payload.pop("observed_start_year")
    payload.pop("observed_end_year")

    parser.parse_inputs(climate, payload)

    assert climate._observed_start_year == ""
    assert climate._observed_end_year == ""


def test_parse_inputs_future_mode_ignores_and_clears_observed_year_fields() -> None:
    parser = ClimateInputParsingService()
    climate = _DummyClimate()
    climate._observed_start_year = 1990
    climate._observed_end_year = 2020

    payload = _payload()
    payload["climate_mode"] = str(int(ClimateMode.Future))

    parser.parse_inputs(climate, payload)

    assert climate._observed_start_year == ""
    assert climate._observed_end_year == ""


def test_parse_inputs_non_future_mode_clears_stale_future_year_bounds() -> None:
    parser = ClimateInputParsingService()
    climate = _DummyClimate()
    climate._future_start_year = 2030
    climate._future_end_year = 2040

    payload = _payload()
    payload["climate_mode"] = str(int(ClimateMode.PRISM))
    payload.pop("future_start_year")
    payload.pop("future_end_year")

    parser.parse_inputs(climate, payload)

    assert climate._future_start_year == ""
    assert climate._future_end_year == ""


def test_parse_inputs_non_future_mode_ignores_future_year_fields_when_provided() -> None:
    parser = ClimateInputParsingService()
    climate = _DummyClimate()
    climate._future_start_year = 2030
    climate._future_end_year = 2040

    payload = _payload()
    payload["climate_mode"] = str(int(ClimateMode.PRISM))

    parser.parse_inputs(climate, payload)

    assert climate._future_start_year == ""
    assert climate._future_end_year == ""
