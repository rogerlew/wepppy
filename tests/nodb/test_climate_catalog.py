import types
import textwrap

import pytest

pytest.importorskip("rasterio", reason="rasterio required for climate catalog tests")

from wepppy.nodb.locales.climate_catalog import available_climate_datasets, get_climate_dataset
from wepppy.nodb.core.climate import Climate, ClimateMode, ClimateSpatialMode


def test_available_climate_datasets_default_locale():
    datasets = available_climate_datasets(["us"], [])
    catalog_ids = {dataset.catalog_id for dataset in datasets}
    # Baseline options should always be present.
    assert "vanilla_cligen" in catalog_ids
    assert "prism_stochastic" in catalog_ids
    assert "user_defined_cli" in catalog_ids
    # EU-specific entries should not appear when locale is US.
    assert "eobs_modified" not in catalog_ids


def test_available_climate_datasets_ghcn_only_locale():
    datasets = available_climate_datasets(["au"], [])
    catalog_ids = {dataset.catalog_id for dataset in datasets}
    # Only Vanilla + single-storm style options should remain for GHCN-only locales.
    assert catalog_ids == {
        "vanilla_cligen",
        "single_storm",
        "single_storm_batch",
        "user_defined_cli",
    }


def test_available_climate_datasets_include_hidden():
    exposed = available_climate_datasets(["us"], [])
    hidden = available_climate_datasets(["us"], [], include_hidden=True)

    exposed_ids = {dataset.catalog_id for dataset in exposed}
    hidden_ids = {dataset.catalog_id for dataset in hidden}

    assert "observed_db" not in exposed_ids
    assert "future_db" not in exposed_ids
    assert {"observed_db", "future_db"} <= hidden_ids


@pytest.fixture
def climate_factory(tmp_path, monkeypatch, request):
    stub_map: dict[int, types.SimpleNamespace] = {}

    class _RedisStub:
        def __init__(self) -> None:
            self._store = {}
            self._hash = {}

        def set(self, key, value, nx=False, ex=None):
            if nx and key in self._store:
                return False
            self._store[key] = value
            return True

        def get(self, key):
            return self._store.get(key)

        def delete(self, key):
            self._store.pop(key, None)

        def hset(self, name, key, value):
            self._hash.setdefault(name, {})[key] = value
            return 1

        def hget(self, name, key):
            return self._hash.get(name, {}).get(key)

    monkeypatch.setattr("wepppy.nodb.base.redis_lock_client", _RedisStub(), raising=False)

    def _patched_ron_instance(self):
        stub = stub_map.get(id(self))
        if stub is None:
            locales = tuple(self.config_get_list('general', 'locales') or ())
            stub = types.SimpleNamespace(mods=[], _locales=list(locales))
            stub_map[id(self)] = stub
        return stub

    monkeypatch.setattr(Climate, 'ron_instance', property(_patched_ron_instance))

    created = []

    def _create(locales=('us',), mods=None):
        run_dir = tmp_path / f'run_{len(created)}'
        run_dir.mkdir()
        cfg_path = run_dir / '0.cfg'
        cfg_text = textwrap.dedent(
            f"""
            [general]
            name = "test"
            cellsize = 30
            locales = {list(locales)}

            [unitizer]
            is_english = true

            [nodb]
            mods = {list(mods or [])}

            [climate]
            cligen_db = "ghcn"
            observed_clis_wc = None
            future_clis_wc = None
            use_gridmet_wind_when_applicable = true
            """
        ).strip()
        cfg_path.write_text(cfg_text + "\n", encoding="utf-8")

        climate = Climate(str(run_dir), '0.cfg')
        stub = types.SimpleNamespace(mods=list(mods or []), _locales=list(locales))
        stub_map[id(climate)] = stub
        created.append(climate)
        return climate

    def _finalize():
        for climate in created:
            listener = getattr(climate, '_queue_listener', None)
            if listener is not None:
                try:
                    listener.stop()
                except Exception:
                    pass

    request.addfinalizer(_finalize)
    return _create


def _baseline_form() -> dict[str, str]:
    return {
        "input_years": "50",
        "observed_start_year": "1980",
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


def test_parse_inputs_sets_catalog_id_and_mode(climate_factory):
    climate = climate_factory(locales=('us',))
    form = _baseline_form()
    form["climate_catalog_id"] = "prism_stochastic"
    form["climate_spatialmode"] = "1"

    climate.parse_inputs(form)

    assert climate.catalog_id == "prism_stochastic"
    assert climate.climate_mode == ClimateMode.PRISM
    assert climate.climate_spatialmode == ClimateSpatialMode.Multiple
    assert climate.input_years == 50


def test_parse_inputs_rejects_invalid_spatial_mode(climate_factory):
    climate = climate_factory(locales=('us',))
    form = _baseline_form()
    form["climate_catalog_id"] = "prism_stochastic"
    # MultipleInterpolated (2) is not supported for PRISM stochastic dataset.
    form["climate_spatialmode"] = "2"

    with pytest.raises(ValueError):
        climate.parse_inputs(form)
