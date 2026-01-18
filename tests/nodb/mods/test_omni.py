import importlib
import json
import logging
import sys
import types
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import pytest

pytestmark = pytest.mark.unit


@contextmanager
def _noop_lock():
    yield


def _ensure_package(name: str, path: Path | None):
    if name in sys.modules:
        return sys.modules[name]
    module = types.ModuleType(name)
    if path is not None:
        module.__path__ = [str(path)]
    sys.modules[name] = module
    return module


@pytest.fixture(scope="module")
def omni_module():
    inserted: list[str] = []

    def _install(name: str, module: types.ModuleType) -> None:
        if name not in sys.modules:
            sys.modules[name] = module
            inserted.append(name)

    _install("utm", types.ModuleType("utm"))

    if "deprecated" not in sys.modules:
        deprecated_stub = types.ModuleType("deprecated")

        def _deprecated(*d_args, **d_kwargs):
            if d_args and callable(d_args[0]) and not d_kwargs:
                return d_args[0]

            def _decorator(func):
                return func

            return _decorator

        deprecated_stub.deprecated = _deprecated
        _install("deprecated", deprecated_stub)

    if "pyproj" not in sys.modules:
        class _DummyCRS:
            def __init__(self, value):
                self.value = value

        class _DummyTransformer:
            def transform(self, x, y):
                return x, y

        def _from_crs(*args, **kwargs):
            return _DummyTransformer()

        pyproj_stub = types.ModuleType("pyproj")
        pyproj_stub.CRS = _DummyCRS
        pyproj_stub.Transformer = types.SimpleNamespace(from_crs=_from_crs)
        _install("pyproj", pyproj_stub)

    if "osgeo.gdal" not in sys.modules:
        gdal_stub = types.ModuleType("osgeo.gdal")

        def _use_exceptions():
            return None

        gdal_stub.UseExceptions = _use_exceptions
        _install("osgeo.gdal", gdal_stub)

    if "osgeo.osr" not in sys.modules:
        _install("osgeo.osr", types.ModuleType("osgeo.osr"))

    if "osgeo.ogr" not in sys.modules:
        _install("osgeo.ogr", types.ModuleType("osgeo.ogr"))

    if "osgeo" not in sys.modules:
        osgeo_stub = types.ModuleType("osgeo")
        osgeo_stub.gdal = sys.modules["osgeo.gdal"]
        osgeo_stub.osr = sys.modules["osgeo.osr"]
        osgeo_stub.ogr = sys.modules["osgeo.ogr"]
        _install("osgeo", osgeo_stub)

    if "rasterio.warp" not in sys.modules:
        warp_stub = types.ModuleType("rasterio.warp")

        def _reproject(*args, **kwargs):
            return None

        class _Resampling:
            bilinear = "bilinear"
            nearest = "nearest"

        def _calculate_default_transform(*args, **kwargs):
            return (None, None, None)

        warp_stub.reproject = _reproject
        warp_stub.Resampling = _Resampling
        warp_stub.calculate_default_transform = _calculate_default_transform
        _install("rasterio.warp", warp_stub)

    if "rasterio" not in sys.modules:
        rasterio_stub = types.ModuleType("rasterio")
        if "rasterio.warp" in sys.modules:
            rasterio_stub.warp = sys.modules["rasterio.warp"]
        _install("rasterio", rasterio_stub)

    module = importlib.import_module("wepppy.nodb.mods.omni.omni")

    try:
        yield module
    finally:
        for name in reversed(inserted):
            sys.modules.pop(name, None)


def test_omni_scenario_parse_roundtrip(omni_module):
    scenario = omni_module.OmniScenario.parse("mulch")
    assert scenario is omni_module.OmniScenario.Mulch
    assert str(scenario) == "mulch"


def test_omni_scenario_parse_rejects_invalid(omni_module):
    with pytest.raises(KeyError):
        omni_module.OmniScenario.parse("unknown_scenario")


def test_omni_scenario_equality_supports_int_and_str(omni_module):
    thinning = omni_module.OmniScenario.Thinning
    assert thinning == thinning.value
    assert thinning == "thinning"
    assert thinning != "mulch"
    assert thinning != 999


def test_clear_cache_and_locks_invokes_dependencies(monkeypatch, omni_module):
    calls = []

    def fake_clear_cache(runid, pup_relpath=None):
        calls.append(("cache", runid, pup_relpath))
        return ["entry"]

    def fake_clear_locks(runid, pup_relpath=None):
        calls.append(("locks", runid, pup_relpath))

    test_logger = logging.getLogger("tests.omni.cache_calls")

    monkeypatch.setattr(omni_module, "clear_nodb_file_cache", fake_clear_cache)
    monkeypatch.setattr(omni_module, "clear_locks", fake_clear_locks)
    monkeypatch.setattr(omni_module, "LOGGER", test_logger)

    omni_module._clear_nodb_cache_and_locks("run-123", pup_relpath="scope")

    assert calls == [
        ("cache", "run-123", "scope"),
        ("locks", "run-123", "scope"),
    ]


def test_clear_cache_and_locks_handles_runtime_errors(monkeypatch, omni_module, caplog):
    def fake_clear_cache(runid, pup_relpath=None):
        raise RuntimeError("Redis NoDb cache client is unavailable")

    def fake_clear_locks(runid, pup_relpath=None):
        raise RuntimeError("Redis lock client is unavailable")

    test_logger = logging.getLogger("tests.omni.cache_errors")

    monkeypatch.setattr(omni_module, "clear_nodb_file_cache", fake_clear_cache)
    monkeypatch.setattr(omni_module, "clear_locks", fake_clear_locks)
    monkeypatch.setattr(omni_module, "LOGGER", test_logger)

    with caplog.at_level(logging.DEBUG, logger=test_logger.name):
        omni_module._clear_nodb_cache_and_locks("run-456", pup_relpath="scope")

    assert "Redis NoDb cache unavailable" in caplog.text
    assert "Redis lock client unavailable" in caplog.text


def test_contrast_sidecar_roundtrip(tmp_path, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)

    contrast = {
        10: "/tmp/contrast/H10",
        "11": "/tmp/contrast/H11"
    }

    sidecar_path = omni._write_contrast_sidecar(1, contrast)
    with open(sidecar_path, "r", encoding="ascii") as fp:
        contents = fp.read()

    assert "\t" in contents

    loaded = omni._load_contrast_sidecar(1)
    assert loaded == {
        "10": "/tmp/contrast/H10",
        "11": "/tmp/contrast/H11"
    }


def test_clear_contrasts_removes_runs_and_sidecars(tmp_path, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni._contrast_names = ["existing"]
    omni._contrasts = [{"1": "/tmp/H1"}]
    omni._contrast_dependency_tree = {"existing": {"signature": "sig"}}

    sidecar_dir = tmp_path / "omni" / "contrasts"
    sidecar_dir.mkdir(parents=True)
    (sidecar_dir / "contrast_00001.tsv").write_text("1\t/tmp/H1\n", encoding="ascii")

    contrasts_dir = tmp_path / "_pups" / "omni" / "contrasts"
    (contrasts_dir / "_uploads").mkdir(parents=True)
    (contrasts_dir / "1").mkdir(parents=True)
    (contrasts_dir / "2").mkdir(parents=True)

    omni.clear_contrasts()

    assert omni._contrasts is None
    assert omni._contrast_names is None
    assert omni._contrast_dependency_tree == {}
    assert not sidecar_dir.exists()
    assert (contrasts_dir / "_uploads").exists()
    assert not (contrasts_dir / "1").exists()
    assert not (contrasts_dir / "2").exists()


def test_build_contrasts_report_normalizes_control_scenario(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.build_contrasts")
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 1.0
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None
    omni._contrast_scenario = None
    omni._control_scenario = None
    omni._contrast_names = []
    omni._contrasts = None
    omni._contrast_dependency_tree = {}
    omni.locked = _noop_lock

    class DummyTranslator:
        top2wepp = {10: 20}

    class DummyWatershed:
        def translator_factory(self):
            return DummyTranslator()

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False
    )
    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(
        omni_module.Omni,
        "get_objective_parameter_from_gpkg",
        lambda self, objective_parameter, scenario=None: (
            [omni_module.ObjectiveParameter("10", "20", 5.0)],
            5.0,
        ),
    )

    omni._build_contrasts()

    report_path = tmp_path / "_pups" / "omni" / "contrasts" / "build_report.ndjson"
    assert report_path.exists()

    payload = json.loads(report_path.read_text().splitlines()[0])
    assert payload["control_scenario"] == str(omni_module.OmniScenario.Undisturbed)
    assert payload["contrast_id"] == 1


def test_build_contrasts_applies_advanced_filters(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_filters")
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 1.0
    omni._contrast_hillslope_limit = 1
    omni._contrast_hill_min_slope = 30.0
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = [2, 3]
    omni._contrast_select_topaz_ids = [102, 103]
    omni._contrast_selection_mode = "cumulative"
    omni._contrast_scenario = None
    omni._control_scenario = "uniform_high"
    omni._contrast_names = []
    omni._contrasts = None
    omni._contrast_dependency_tree = {}
    omni.locked = _noop_lock

    class DummyTranslator:
        top2wepp = {101: 201, 102: 202, 103: 203}

    class DummyWatershed:
        def translator_factory(self):
            return DummyTranslator()

        def hillslope_slope(self, topaz_id):
            return {"101": 0.2, "102": 0.4, "103": 0.6}[str(topaz_id)]

    class DummyLanduse:
        def identify_burn_class(self, topaz_id):
            return {"101": "Low", "102": "Moderate", "103": "High"}[str(topaz_id)]

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())
    import wepppy.nodb.core as nodb_core
    monkeypatch.setattr(nodb_core.Landuse, "getInstance", lambda wd: DummyLanduse())
    monkeypatch.setattr(
        omni_module.Omni,
        "get_objective_parameter_from_gpkg",
        lambda self, objective_parameter, scenario=None: (
            [
                omni_module.ObjectiveParameter("101", "201", 10.0),
                omni_module.ObjectiveParameter("102", "202", 9.0),
                omni_module.ObjectiveParameter("103", "203", 8.0),
            ],
            27.0,
        ),
    )

    omni._build_contrasts()

    assert omni._contrast_names == ["uniform_high,102__to__undisturbed"]


def test_build_contrasts_ignores_filters_when_not_cumulative(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_filters")
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 1.0
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = 0.3
    omni._contrast_hill_max_slope = 0.5
    omni._contrast_select_burn_severities = [3]
    omni._contrast_select_topaz_ids = [101]
    omni._contrast_selection_mode = "user_defined_areas"
    omni._contrast_scenario = None
    omni._control_scenario = "uniform_high"
    omni._contrast_names = []
    omni._contrasts = None
    omni._contrast_dependency_tree = {}
    omni.locked = _noop_lock

    class DummyTranslator:
        top2wepp = {101: 201, 102: 202}

    class DummyWatershed:
        def translator_factory(self):
            return DummyTranslator()

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(
        omni_module.Omni,
        "get_objective_parameter_from_gpkg",
        lambda self, objective_parameter, scenario=None: (
            [
                omni_module.ObjectiveParameter("101", "201", 6.0),
                omni_module.ObjectiveParameter("102", "202", 4.0),
            ],
            10.0,
        ),
    )

    omni._build_contrasts()

    assert omni._contrast_names == [
        "uniform_high,101__to__undisturbed",
        "uniform_high,102__to__undisturbed",
    ]


def test_run_omni_contrasts_reruns_all_when_clean_slate(monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = "/tmp/run-123"
    omni.logger = logging.getLogger("tests.omni.run_contrasts")
    omni.locked = _noop_lock
    omni._contrast_names = [
        "None,10__to__undisturbed",
        "None,20__to__undisturbed",
    ]
    omni._contrast_dependency_tree = {
        "None,10__to__undisturbed": {
            "signature": "sig",
            "dependencies": {"undisturbed": {"sha1": "hash"}},
        }
    }

    monkeypatch.setattr(omni, "_clean_contrast_runs", lambda: None)
    monkeypatch.setattr(omni, "_load_contrast_sidecar", lambda contrast_id: {"1": f"/tmp/H{contrast_id}"})
    monkeypatch.setattr(omni, "_contrast_dependencies", lambda name: {"undisturbed": {"sha1": "hash"}})
    monkeypatch.setattr(omni, "_contrast_signature", lambda name, payload: "sig")
    monkeypatch.setattr(omni, "_post_omni_run", lambda wd, name: None)

    calls = []

    def fake_run(contrast_id, contrast_name, contrasts, wd, runid):
        calls.append((contrast_id, contrast_name))
        return f"{wd}/_pups/omni/contrasts/{contrast_id}"

    monkeypatch.setattr(omni_module, "_run_contrast", fake_run)

    omni.run_omni_contrasts()

    assert len(calls) == 2
    assert calls[0][0] == "1"
    assert calls[1][0] == "2"
    assert set(omni.contrast_dependency_tree.keys()) == set(omni._contrast_names)


def test_contrasts_report_reads_contrast_outputs_from_pups(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrasts_report")
    omni._contrast_names = ["None,10__to__undisturbed"]

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False
    )

    contrast_path = tmp_path / "_pups" / "omni" / "contrasts" / "1" / "wepp" / "output" / "interchange" / "loss_pw0.out.parquet"
    contrast_path.parent.mkdir(parents=True, exist_ok=True)
    contrast_path.touch()

    control_path = tmp_path / "wepp" / "output" / "interchange" / "loss_pw0.out.parquet"
    control_path.parent.mkdir(parents=True, exist_ok=True)
    control_path.touch()

    read_calls = []

    def fake_read_parquet(path, *args, **kwargs):
        read_calls.append(str(path))
        if str(path) == str(contrast_path):
            return pd.DataFrame({
                "key": ["Avg. Ann. water discharge from outlet"],
                "value": [1.0],
                "units": ["m^3/yr"]
            })
        return pd.DataFrame({
            "key": ["Avg. Ann. water discharge from outlet"],
            "value": [2.0],
            "units": ["m^3/yr"]
        })

    monkeypatch.setattr(omni_module.pd, "read_parquet", fake_read_parquet)
    monkeypatch.setattr(
        omni_module.pd.DataFrame,
        "to_parquet",
        lambda self, *args, **kwargs: None
    )

    df = omni.contrasts_report()

    assert str(contrast_path) in read_calls
    assert str(control_path) in read_calls
    assert df["control-contrast_v"].iloc[0] == 1.0
