import types
import textwrap

import pytest

pytest.importorskip("rasterio", reason="rasterio required for climate catalog tests")

from wepppy.nodb.locales.climate_catalog import available_climate_datasets, get_climate_dataset
from wepppy.nodb.core.climate import Climate, ClimateMode, ClimateSpatialMode, ClimateStationMode


def test_available_climate_datasets_default_locale():
    datasets = available_climate_datasets(["us"], [])
    catalog_ids = {dataset.catalog_id for dataset in datasets}
    # Baseline options should always be present.
    assert "vanilla_cligen" in catalog_ids
    assert "prism_stochastic" in catalog_ids
    assert "user_defined_cli" in catalog_ids
    # EU-specific entries should not appear when locale is US.
    assert "eobs_modified" not in catalog_ids


def test_amendment5_climate_datasets_have_builder_support_and_runtime_modes():
    expected = {
        "dep_nexrad": 13,
        "future_cmip5": 3,
        "user_defined_cli": 12,
    }
    for catalog_id, mode in expected.items():
        dataset = get_climate_dataset(catalog_id)
        assert dataset is not None
        assert dataset.support_state == "builder_exposed"
        assert dataset.climate_mode == mode
    user_defined = get_climate_dataset("user_defined_cli")
    assert user_defined is not None
    assert user_defined.station_method_ids == ("user_defined",)
    assert user_defined.upload_behaviour == "upload"


def test_available_climate_datasets_ghcn_only_locale():
    datasets = available_climate_datasets(["au"], [])
    catalog_ids = {dataset.catalog_id for dataset in datasets}
    # Australia keeps its regional AGDC source alongside CLIGEN/storm inputs.
    assert catalog_ids == {
        "agdc",
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

        def eval(self, _script, _numkeys, key, expected):
            if self._store.get(key) != expected:
                return 0
            self._store.pop(key, None)
            return 1

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

    def _create(locales=('us',), mods=None, cligen_db="ghcn"):
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
            cligen_db = "{cligen_db}"
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


@pytest.mark.unit
@pytest.mark.parametrize(
    "settings, expected",
    [
        ({}, None),
        ({"precip_scale_factor_map": '"/maps/generic.tif"'}, "/maps/generic.tif"),
        ({"precip_scale_factor_map": '"/maps/generic.tif"',
          "gridmet_precip_scale_factor_map": '"/maps/gridmet.tif"'}, "/maps/gridmet.tif"),
        ({"precip_scale_factor_map": '"/maps/generic.tif"',
          "gridmet_precip_scale_factor_map": '"/maps/gridmet.tif"',
          "daymet_precip_scale_factor_map": '"/maps/daymet.tif"'}, "/maps/daymet.tif"),
        ({"gridmet_precip_scale_factor_map": '"/maps/gridmet.tif"',
          "daymet_precip_scale_factor_map": "None"}, "/maps/gridmet.tif"),
    ],
)
@pytest.mark.parametrize("persisted", ["missing", None, "", "1.1"])
def test_config_owned_scale_map_persists_and_reloads(climate_factory, settings, expected, persisted):
    import json
    from pathlib import Path

    climate = climate_factory()
    config_path = Path(climate.wd) / "0.cfg"
    with config_path.open("a") as handle:
        for key, value in settings.items():
            handle.write(f"{key} = {value}\n")
    with climate.locked():
        if persisted == "missing":
            del climate._precip_scale_factor_map
        else:
            climate._precip_scale_factor_map = persisted
    assert climate.precip_scale_factor_map == expected

    payload = _baseline_form()
    payload["climate_mode"] = str(int(ClimateMode.Vanilla))
    payload["precip_scale_factor_map"] = "/untrusted/map.tif"
    climate.parse_inputs(payload)

    document = json.loads((Path(climate.wd) / "climate.nodb").read_text())
    assert document["py/state"]["_precip_scale_factor_map"] == expected
    reloaded = Climate.getInstance(climate.wd, ignore_lock=True)
    assert reloaded._precip_scale_factor_map == expected
    assert reloaded.precip_scale_factor_map == expected


@pytest.mark.unit
def test_rq_payload_replay_cannot_replace_configured_scale_map(climate_factory, monkeypatch):
    import json
    import pickle
    from pathlib import Path
    import wepppy.rq.project_rq as project_rq

    climate = climate_factory()
    wd = Path(climate.wd)
    expected = "/configured/daymet_scale.tif"
    with (wd / "0.cfg").open("a") as handle:
        handle.write(f'daymet_precip_scale_factor_map = "{expected}"\n')
    with climate.locked():
        climate._precip_scale_factor_map = expected
    payload = _baseline_form()
    payload.update(climate_mode="0", precip_scale_factor_map="1.1")
    # Reproduce the serialized enqueue-time payload seen by a later worker.
    job = types.SimpleNamespace(id="map-replay", meta=pickle.loads(pickle.dumps({
        "build_payload": payload,
    })))
    monkeypatch.setattr(project_rq, "get_current_job", lambda: job)
    monkeypatch.setattr(project_rq, "get_wd", lambda runid: str(wd))
    monkeypatch.setattr("wepppy.rq.exception_logging.get_wd", lambda runid: str(wd))
    # Production run-id lookup is external RQ plumbing; use the fixture directory.
    monkeypatch.setattr("wepppy.weppcloud.utils.helpers.get_wd", lambda runid: str(wd))
    monkeypatch.setattr(project_rq.StatusMessenger, "publish", lambda *args: None)
    monkeypatch.setattr(project_rq.RedisPrep, "getInstance", lambda wd: types.SimpleNamespace(
        timestamp=lambda task: None,
    ))
    monkeypatch.setattr(project_rq, "_run_with_directory_root_lock",
                        lambda wd, root, operation, **kwargs: operation())
    built = []

    def build(controller):
        built.append(controller.precip_scale_factor_map)
        assert controller._precip_scale_factor_map == expected

    monkeypatch.setattr(Climate, "build", build)
    project_rq.build_climate_rq(climate.runid)

    assert built == [expected]
    assert job.meta["build_payload"]["precip_scale_factor_map"] == "1.1"
    assert json.loads((wd / "climate.nodb").read_text())["py/state"]["_precip_scale_factor_map"] == expected
    reloaded = Climate.getInstance(str(wd), ignore_lock=True)
    assert reloaded._precip_scale_factor_map == reloaded.precip_scale_factor_map == expected


@pytest.mark.unit
def test_missing_map_config_does_not_become_client_map(climate_factory):
    from wepppy.nodb.core.climate import ClimatePrecipScalingMode
    from wepppy.nodb.core.climate_scaling_service import ClimateScalingService

    climate = climate_factory()
    climate._precip_scale_factor_map = "/untrusted/map.tif"
    climate._precip_scaling_mode = ClimatePrecipScalingMode.Spatial
    with pytest.raises(ValueError, match="precip_scale_factor_map is None"):
        ClimateScalingService().validate_scaling_inputs(climate)


@pytest.mark.unit
def test_scale_map_config_io_failure_preserves_disk_and_input_state(climate_factory, monkeypatch):
    from pathlib import Path

    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_READER_ENABLED", "false")
    climate = climate_factory()
    nodb_path = Path(climate.wd) / "climate.nodb"
    before = nodb_path.read_bytes()
    input_years = climate.input_years
    (Path(climate.wd) / "0.cfg").unlink()
    (Path(climate.wd) / "0.cfg").mkdir()
    payload = _baseline_form()
    payload["climate_mode"] = str(int(ClimateMode.Vanilla))
    with pytest.raises(IsADirectoryError):
        climate.parse_inputs(payload)
    assert climate.input_years == input_years
    assert nodb_path.read_bytes() == before


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


def test_tenerife_catalog_restricts_climate_mode_and_spatial_mode(climate_factory):
    climate = climate_factory(locales=("tenerife", "eu"), cligen_db="tenerife_stations.db")

    climate.climate_mode = ClimateMode.Vanilla
    climate.climate_mode = ClimateMode.UserDefined
    climate.climate_spatialmode = ClimateSpatialMode.Single

    with pytest.raises(ValueError, match="only supports Vanilla or User-Defined climate mode"):
        climate.climate_mode = ClimateMode.PRISM

    with pytest.raises(ValueError, match="only supports Single climate spatial mode"):
        climate.climate_spatialmode = ClimateSpatialMode.Multiple


def test_tenerife_catalog_restricts_station_modes_to_auto_and_closest(climate_factory):
    climate = climate_factory(locales=("tenerife", "eu"), cligen_db="tenerife_stations.db")

    climate.climatestation_mode = ClimateStationMode.FindClosestAtRuntime
    climate.climatestation_mode = ClimateStationMode.Closest

    with pytest.raises(ValueError, match="only supports auto and distance-ranking station modes"):
        climate.climatestation_mode = ClimateStationMode.Heuristic

    with pytest.raises(ValueError, match="only supports auto and distance-ranking station modes"):
        climate.find_heuristic_stations()


def test_tenerife_catalog_allows_user_defined_station_mode_for_user_defined_cli(climate_factory):
    climate = climate_factory(locales=("tenerife", "eu"), cligen_db="tenerife_stations.db")
    climate.catalog_id = "user_defined_cli"
    climate.climate_mode = ClimateMode.UserDefined

    climate.climatestation_mode = ClimateStationMode.UserDefined


def test_tenerife_catalog_parse_inputs_rejects_non_vanilla_or_multiple(climate_factory):
    climate = climate_factory(locales=("tenerife", "eu"), cligen_db="tenerife_stations.db")
    form = _baseline_form()
    form["climate_mode"] = str(int(ClimateMode.PRISM))
    form["climate_spatialmode"] = str(int(ClimateSpatialMode.Single))

    with pytest.raises(ValueError, match="only supports Vanilla or User-Defined climate mode"):
        climate.parse_inputs(form)

    form["climate_mode"] = str(int(ClimateMode.Vanilla))
    form["climate_spatialmode"] = str(int(ClimateSpatialMode.Multiple))

    with pytest.raises(ValueError, match="only supports Single climate spatial mode"):
        climate.parse_inputs(form)


def test_tenerife_catalog_parse_inputs_accepts_user_defined_cli(climate_factory):
    climate = climate_factory(locales=("tenerife", "eu"), cligen_db="tenerife_stations.db")
    form = _baseline_form()
    form["climate_catalog_id"] = "user_defined_cli"
    form["climate_spatialmode"] = str(int(ClimateSpatialMode.Single))

    climate.parse_inputs(form)

    assert climate.catalog_id == "user_defined_cli"
    assert climate.climate_mode == ClimateMode.UserDefined
    assert climate.climate_spatialmode == ClimateSpatialMode.Single
