import importlib
import json
import logging
import sys
import types
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.unit


@contextmanager
def _noop_lock():
    yield


class Rect:
    def __init__(self, xmin, ymin, xmax, ymax):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax

    @property
    def bounds(self):
        return (self.xmin, self.ymin, self.xmax, self.ymax)

    @property
    def area(self):
        return max(0.0, self.xmax - self.xmin) * max(0.0, self.ymax - self.ymin)

    @property
    def is_empty(self):
        return self.area == 0.0

    def intersection(self, other):
        xmin = max(self.xmin, other.xmin)
        ymin = max(self.ymin, other.ymin)
        xmax = min(self.xmax, other.xmax)
        ymax = min(self.ymax, other.ymax)
        if xmin >= xmax or ymin >= ymax:
            return Rect(0.0, 0.0, 0.0, 0.0)
        return Rect(xmin, ymin, xmax, ymax)


class DummyRow(dict):
    @property
    def geometry(self):
        return self.get("geometry")


class DummySpatialIndex:
    def __init__(self, rows):
        self._rows = rows

    def intersection(self, bounds):
        results = []
        for idx, row in enumerate(self._rows):
            geom = row.get("geometry")
            if geom is None:
                continue
            left, bottom, right, top = bounds
            g_left, g_bottom, g_right, g_top = geom.bounds
            if right <= g_left or g_right <= left or top <= g_bottom or g_top <= bottom:
                continue
            results.append(idx)
        return results


class DummyGeoDataFrame:
    def __init__(self, rows, crs=None):
        self._rows = [DummyRow(row) for row in rows]
        self.crs = crs
        self.columns = list(rows[0].keys()) if rows else []

    def __len__(self):
        return len(self._rows)

    @property
    def empty(self):
        return not self._rows

    def iterrows(self):
        for idx, row in enumerate(self._rows):
            yield idx, row

    def set_crs(self, epsg=None, crs=None):
        if crs is not None:
            self.crs = crs
        elif epsg is not None:
            self.crs = f"EPSG:{epsg}"
        return self

    def to_crs(self, crs):
        self.crs = crs
        return self

    @property
    def sindex(self):
        return DummySpatialIndex(self._rows)


def _stub_user_defined_geodata(
    monkeypatch,
    omni_module,
    tmp_path,
    *,
    hillslope_rows,
    user_rows,
    hillslope_crs="EPSG:32611",
    user_crs=None,
    top2wepp=None,
    srid="32611",
):
    hillslope_path = tmp_path / "subwta.geojson"
    user_geojson_path = tmp_path / "areas.geojson"
    hillslope_path.write_text("{}", encoding="ascii")
    user_geojson_path.write_text("{}", encoding="ascii")

    hillslope_gdf = DummyGeoDataFrame(hillslope_rows, crs=hillslope_crs)
    user_gdf = DummyGeoDataFrame(user_rows, crs=user_crs)

    geopandas_stub = types.ModuleType("geopandas")
    geopandas_stub.read_file = lambda path: hillslope_gdf if str(path) == str(hillslope_path) else user_gdf
    monkeypatch.setitem(sys.modules, "geopandas", geopandas_stub)

    if top2wepp is None:
        top2wepp = {}
        for idx, row in enumerate(hillslope_rows, start=1):
            topaz_id = row.get("TopazID")
            if topaz_id not in (None, ""):
                top2wepp[str(topaz_id)] = str(idx)

    mapping = {str(k): str(v) for k, v in top2wepp.items()}

    class DummyTranslator:
        pass

    DummyTranslator.top2wepp = mapping

    class DummyWatershed:
        def __init__(self, subwta_utm_shp):
            self.subwta_utm_shp = subwta_utm_shp

        def translator_factory(self):
            return DummyTranslator()

    class DummyRon:
        pass

    DummyRon.srid = srid

    monkeypatch.setattr(
        omni_module.Watershed,
        "getInstance",
        lambda wd: DummyWatershed(str(hillslope_path)),
    )
    monkeypatch.setattr(omni_module.Ron, "getInstance", lambda wd: DummyRon())
    monkeypatch.setattr(omni_module.NoDbBase, "has_sbs", property(lambda self: False))

    return user_geojson_path


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
    report_path = contrasts_dir / "build_report.ndjson"
    report_path.write_text("{}", encoding="ascii")
    contrasts_report = tmp_path / "omni" / "contrasts.out.parquet"
    contrasts_report.parent.mkdir(parents=True, exist_ok=True)
    contrasts_report.write_text("placeholder", encoding="ascii")

    omni.clear_contrasts()

    assert omni._contrasts is None
    assert omni._contrast_names is None
    assert omni._contrast_dependency_tree == {}
    assert not sidecar_dir.exists()
    assert not report_path.exists()
    assert not contrasts_report.exists()
    assert (contrasts_dir / "_uploads").exists()
    assert not (contrasts_dir / "1").exists()
    assert not (contrasts_dir / "2").exists()


def test_user_defined_areas_contrast_builds_sidecars_with_overlap(tmp_path, omni_module, monkeypatch):
    hillslope_rows = [
        {"TopazID": "10", "geometry": Rect(0.0, 0.0, 10.0, 10.0)},
        {"TopazID": "20", "geometry": Rect(10.0, 0.0, 20.0, 10.0)},
    ]
    user_rows = [
        {"name": "Alpha", "geometry": Rect(0.0, 0.0, 6.0, 10.0)},
        {"name": None, "geometry": Rect(5.0, 0.0, 15.0, 10.0)},
        {"name": "Gamma", "geometry": Rect(30.0, 0.0, 40.0, 10.0)},
    ]
    user_geojson_path = _stub_user_defined_geodata(
        monkeypatch,
        omni_module,
        tmp_path,
        hillslope_rows=hillslope_rows,
        user_rows=user_rows,
    )

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.user_defined")
    omni._contrast_selection_mode = "user_defined_areas"
    omni._contrast_geojson_path = str(user_geojson_path)
    omni._contrast_geojson_name_key = "name"
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
    ]
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 0.8
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None
    omni._control_scenario = "uniform_low"
    omni._contrast_scenario = "mulch"

    omni._build_contrasts()

    assert omni.contrast_names == [
        "uniform_low,1__to__mulch",
        "uniform_low,2__to__mulch",
        None,
    ]
    assert omni._contrast_labels == {1: "Alpha", 2: "2", 3: "Gamma"}

    def _read_sidecar(path):
        contents = {}
        with open(path, "r", encoding="ascii") as fp:
            for line in fp:
                topaz_id, _, wepp_path = line.strip().partition("\t")
                contents[topaz_id] = wepp_path
        return contents

    contrast1 = _read_sidecar(omni._contrast_sidecar_path(1))
    contrast2 = _read_sidecar(omni._contrast_sidecar_path(2))

    assert contrast1["10"].endswith("/_pups/omni/scenarios/mulch/wepp/output/H1")
    assert contrast1["20"].endswith("/_pups/omni/scenarios/uniform_low/wepp/output/H2")
    assert contrast2["10"].endswith("/_pups/omni/scenarios/mulch/wepp/output/H1")
    assert contrast2["20"].endswith("/_pups/omni/scenarios/mulch/wepp/output/H2")
    assert not Path(omni._contrast_sidecar_path(3)).exists()


def test_user_defined_contrast_pairs_expand_and_skip_duplicates(tmp_path, omni_module, monkeypatch):
    hillslope_rows = [
        {"TopazID": "10", "geometry": Rect(0.0, 0.0, 10.0, 10.0)},
        {"TopazID": "20", "geometry": Rect(10.0, 0.0, 20.0, 10.0)},
    ]
    user_rows = [
        {"name": "Alpha", "geometry": Rect(0.0, 0.0, 10.0, 10.0)},
        {"name": "Beta", "geometry": Rect(10.0, 0.0, 20.0, 10.0)},
    ]
    user_geojson_path = _stub_user_defined_geodata(
        monkeypatch,
        omni_module,
        tmp_path,
        hillslope_rows=hillslope_rows,
        user_rows=user_rows,
    )

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.user_defined_pairs")
    omni._contrast_selection_mode = "user_defined_areas"
    omni._contrast_geojson_path = str(user_geojson_path)
    omni._contrast_geojson_name_key = "name"
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        {"control_scenario": "uniform_low", "contrast_scenario": "thinning"},
    ]
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 0.8
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None
    omni._control_scenario = None
    omni._contrast_scenario = None

    omni._build_contrasts()

    names = [name for name in omni.contrast_names or [] if name]
    assert len(names) == 4
    assert Counter(omni._contrast_labels.values()) == Counter({"Alpha": 2, "Beta": 2})


def test_user_defined_contrast_ids_stable_on_rebuild(tmp_path, omni_module, monkeypatch):
    hillslope_rows = [
        {"TopazID": "10", "geometry": Rect(0.0, 0.0, 10.0, 10.0)},
    ]
    user_rows = [
        {"name": "Alpha", "geometry": Rect(0.0, 0.0, 10.0, 10.0)},
    ]
    user_geojson_path = _stub_user_defined_geodata(
        monkeypatch,
        omni_module,
        tmp_path,
        hillslope_rows=hillslope_rows,
        user_rows=user_rows,
    )

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.user_defined_ids")
    omni._contrast_selection_mode = "user_defined_areas"
    omni._contrast_geojson_path = str(user_geojson_path)
    omni._contrast_geojson_name_key = "name"
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
    ]
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 0.8
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None
    omni._control_scenario = None
    omni._contrast_scenario = None

    omni._build_contrasts()
    first_names = list(omni.contrast_names or [])
    assert first_names == ["uniform_low,1__to__mulch"]

    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        {"control_scenario": "uniform_low", "contrast_scenario": "thinning"},
    ]
    omni._build_contrasts()

    assert omni.contrast_names[0] == first_names[0]
    assert omni.contrast_names[1] == "uniform_low,2__to__thinning"


def test_user_defined_hillslope_group_ids_stable_on_rebuild(tmp_path, omni_module, monkeypatch):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.hillslope_groups_ids")
    omni._contrast_selection_mode = "user_defined_hillslope_groups"
    omni._contrast_hillslope_groups = "11 12\n13"
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
    ]
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None

    class DummyTranslator:
        top2wepp = {11: 1, 12: 2, 13: 3}

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

    omni._build_contrasts()

    first_names = list(omni.contrast_names or [])
    assert first_names == ["uniform_low,1__to__mulch", "uniform_low,2__to__mulch"]

    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        {"control_scenario": "uniform_low", "contrast_scenario": "thinning"},
    ]
    omni._build_contrasts()

    assert omni.contrast_names[0] == first_names[0]
    assert omni.contrast_names[1] == first_names[1]
    assert omni.contrast_names[2] == "uniform_low,3__to__thinning"
    assert omni.contrast_names[3] == "uniform_low,4__to__thinning"


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
    omni._contrast_selection_mode = "objective"
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


def _install_json_to_wgs_stub(monkeypatch):
    support_stub = types.ModuleType("wepppy.topo.watershed_abstraction.support")

    def _json_to_wgs(src_fn, s_srs=None):
        src_path = Path(src_fn)
        dst_path = src_path.with_suffix(".WGS.geojson")
        dst_path.write_text(src_path.read_text(encoding="ascii"), encoding="ascii")
        return str(dst_path)

    support_stub.json_to_wgs = _json_to_wgs

    wa_stub = types.ModuleType("wepppy.topo.watershed_abstraction")
    wa_stub.__path__ = []
    wa_stub.support = support_stub

    monkeypatch.setitem(sys.modules, "wepppy.topo.watershed_abstraction", wa_stub)
    monkeypatch.setitem(sys.modules, "wepppy.topo.watershed_abstraction.support", support_stub)


def _install_shapely_shape_stub(monkeypatch):
    shapely_stub = types.ModuleType("shapely")
    shapely_geometry_stub = types.ModuleType("shapely.geometry")
    shapely_ops_stub = types.ModuleType("shapely.ops")

    class DummyShape:
        def __init__(self, geom):
            self.__geo_interface__ = geom
            self.is_empty = False

    shapely_geometry_stub.shape = lambda geom: DummyShape(geom)
    shapely_ops_stub.unary_union = lambda geoms: geoms[0] if geoms else None

    monkeypatch.setitem(sys.modules, "shapely", shapely_stub)
    monkeypatch.setitem(sys.modules, "shapely.geometry", shapely_geometry_stub)
    monkeypatch.setitem(sys.modules, "shapely.ops", shapely_ops_stub)


def test_build_contrast_ids_geojson_cumulative(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_ids")
    omni.locked = _noop_lock
    omni._contrast_selection_mode = "cumulative"

    report_path = Path(omni._contrast_build_report_path())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({"topaz_id": 101}) + "\n", encoding="ascii")

    hillslope_path = tmp_path / "subwta.wgs.geojson"
    hillslope_path.write_text("{}", encoding="ascii")
    hillslope_rows = [{"TopazID": "101", "geometry": Rect(0.0, 0.0, 1.0, 1.0)}]
    hillslope_gdf = DummyGeoDataFrame(hillslope_rows, crs="EPSG:4326")

    geopandas_stub = types.ModuleType("geopandas")
    geopandas_stub.read_file = lambda path: hillslope_gdf
    monkeypatch.setitem(sys.modules, "geopandas", geopandas_stub)

    shapely_stub = types.ModuleType("shapely")
    shapely_geometry_stub = types.ModuleType("shapely.geometry")
    shapely_ops_stub = types.ModuleType("shapely.ops")
    shapely_geometry_stub.mapping = lambda geom: {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
    }
    shapely_ops_stub.unary_union = lambda geoms: geoms[0] if geoms else None
    monkeypatch.setitem(sys.modules, "shapely", shapely_stub)
    monkeypatch.setitem(sys.modules, "shapely.geometry", shapely_geometry_stub)
    monkeypatch.setitem(sys.modules, "shapely.ops", shapely_ops_stub)

    class DummyWatershed:
        subwta_shp = str(hillslope_path)

    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())

    output_path = omni._build_contrast_ids_geojson()

    payload = json.loads(Path(output_path).read_text(encoding="ascii"))
    assert payload["type"] == "FeatureCollection"
    assert payload["features"]
    assert payload["features"][0]["properties"]["contrast_label"] == "101"


def test_build_contrast_ids_geojson_user_defined_areas(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_ids.user_defined")
    omni.locked = _noop_lock
    omni._contrast_selection_mode = "user_defined_areas"

    report_path = Path(omni._contrast_build_report_path())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        {
            "selection_mode": "user_defined_areas",
            "feature_index": 1,
            "topaz_ids": ["8122", "8123"],
        },
        {
            "selection_mode": "user_defined_areas",
            "feature_index": 1,
            "topaz_ids": ["8122", "8123"],
        },
        {
            "selection_mode": "user_defined_areas",
            "feature_index": 2,
            "topaz_ids": ["8201", "8202"],
        },
    ]
    report_path.write_text(
        "\n".join(json.dumps(entry) for entry in entries) + "\n",
        encoding="ascii",
    )

    subwta_path = tmp_path / "dem" / "wbt" / "subwta.tif"
    subwta_path.parent.mkdir(parents=True, exist_ok=True)
    subwta_path.write_text("", encoding="ascii")

    class DummyWatershed:
        subwta = str(subwta_path)

    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())

    data = np.ma.array([[8122, 8201], [8123, 8202]], mask=False)

    class DummyDataset:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, *args, **kwargs):
            return data

        @property
        def transform(self):
            return "transform"

        @property
        def crs(self):
            return "EPSG:32611"

    def _shapes(*args, **kwargs):
        return [
            (
                {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [0.0, 0.0],
                            [1.0, 0.0],
                            [1.0, 1.0],
                            [0.0, 1.0],
                            [0.0, 0.0],
                        ]
                    ],
                },
                1,
            )
        ]

    rasterio_stub = sys.modules.get("rasterio")
    if rasterio_stub is None:
        rasterio_stub = types.ModuleType("rasterio")
        sys.modules["rasterio"] = rasterio_stub
    if not hasattr(rasterio_stub, "__path__"):
        rasterio_stub.__path__ = []
    monkeypatch.setattr(rasterio_stub, "open", lambda *args, **kwargs: DummyDataset())

    features_stub = types.ModuleType("rasterio.features")
    features_stub.shapes = _shapes
    monkeypatch.setitem(sys.modules, "rasterio.features", features_stub)
    rasterio_stub.features = features_stub

    _install_shapely_shape_stub(monkeypatch)
    _install_json_to_wgs_stub(monkeypatch)

    output_path = omni._build_contrast_ids_geojson()

    utm_path = output_path.replace(".wgs.geojson", ".utm.geojson")
    assert Path(utm_path).exists()

    payload = json.loads(Path(output_path).read_text(encoding="ascii"))
    labels = [feature["properties"]["contrast_label"] for feature in payload["features"]]
    assert labels == ["1", "2"]
    for feature in payload["features"]:
        assert feature["properties"]["label"] == feature["properties"]["contrast_label"]
        assert feature["properties"]["selection_mode"] == "user_defined_areas"


def test_build_contrast_ids_geojson_user_defined_hillslope_groups(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_ids.hillslope_groups")
    omni.locked = _noop_lock
    omni._contrast_selection_mode = "user_defined_hillslope_groups"

    report_path = Path(omni._contrast_build_report_path())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        {
            "selection_mode": "user_defined_hillslope_groups",
            "group_index": 2,
            "topaz_ids": ["101", "102"],
        },
        {
            "selection_mode": "user_defined_hillslope_groups",
            "group_index": 1,
            "topaz_ids": ["103"],
        },
    ]
    report_path.write_text(
        "\n".join(json.dumps(entry) for entry in entries) + "\n",
        encoding="ascii",
    )

    hillslope_path = tmp_path / "subwta.wgs.geojson"
    hillslope_path.write_text("{}", encoding="ascii")
    hillslope_rows = [
        {"TopazID": "101", "geometry": Rect(0.0, 0.0, 1.0, 1.0)},
        {"TopazID": "102", "geometry": Rect(1.0, 0.0, 2.0, 1.0)},
        {"TopazID": "103", "geometry": Rect(2.0, 0.0, 3.0, 1.0)},
    ]
    hillslope_gdf = DummyGeoDataFrame(hillslope_rows, crs="EPSG:4326")

    geopandas_stub = types.ModuleType("geopandas")
    geopandas_stub.read_file = lambda path: hillslope_gdf
    monkeypatch.setitem(sys.modules, "geopandas", geopandas_stub)

    shapely_stub = types.ModuleType("shapely")
    shapely_geometry_stub = types.ModuleType("shapely.geometry")
    shapely_ops_stub = types.ModuleType("shapely.ops")
    shapely_geometry_stub.mapping = lambda geom: {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
    }
    shapely_ops_stub.unary_union = lambda geoms: geoms[0] if geoms else None
    monkeypatch.setitem(sys.modules, "shapely", shapely_stub)
    monkeypatch.setitem(sys.modules, "shapely.geometry", shapely_geometry_stub)
    monkeypatch.setitem(sys.modules, "shapely.ops", shapely_ops_stub)

    class DummyWatershed:
        subwta_shp = str(hillslope_path)

    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())

    output_path = omni._build_contrast_ids_geojson()

    payload = json.loads(Path(output_path).read_text(encoding="ascii"))
    labels = [feature["properties"]["contrast_label"] for feature in payload["features"]]
    assert labels == ["1", "2"]
    for feature in payload["features"]:
        assert feature["properties"]["selection_mode"] == "user_defined_hillslope_groups"
        assert feature["properties"]["label"] == feature["properties"]["contrast_label"]
        assert "group_index" in feature["properties"]


def test_build_contrast_ids_geojson_stream_order(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_ids.stream_order")
    omni.locked = _noop_lock
    omni._contrast_selection_mode = "stream_order"
    omni._contrast_order_reduction_passes = 1

    report_path = Path(omni._contrast_build_report_path())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        {
            "selection_mode": "stream_order",
            "subcatchments_group": 220,
            "n_hillslopes": 8,
        },
        {
            "selection_mode": "stream_order",
            "subcatchments_group": 220,
            "n_hillslopes": 8,
        },
        {
            "selection_mode": "stream_order",
            "subcatchments_group": 230,
            "n_hillslopes": 6,
        },
        {
            "selection_mode": "stream_order",
            "subcatchments_group": 240,
            "n_hillslopes": 0,
            "status": "skipped",
        },
    ]
    report_path.write_text(
        "\n".join(json.dumps(entry) for entry in entries) + "\n",
        encoding="ascii",
    )

    wbt_dir = tmp_path / "dem" / "wbt"
    wbt_dir.mkdir(parents=True, exist_ok=True)
    subwta_pruned_path = wbt_dir / "subwta.strahler_pruned_1.tif"
    subwta_pruned_path.write_text("", encoding="ascii")

    class DummyWatershed:
        wbt_wd = str(wbt_dir)

    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())

    data = np.ma.array([[22, 23], [0, 0]], mask=False)

    class DummyDataset:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, *args, **kwargs):
            return data

        @property
        def transform(self):
            return "transform"

        @property
        def crs(self):
            return "EPSG:32611"

    def _shapes(*args, **kwargs):
        return [
            (
                {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [0.0, 0.0],
                            [1.0, 0.0],
                            [1.0, 1.0],
                            [0.0, 1.0],
                            [0.0, 0.0],
                        ]
                    ],
                },
                22,
            ),
            (
                {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [2.0, 2.0],
                            [3.0, 2.0],
                            [3.0, 3.0],
                            [2.0, 3.0],
                            [2.0, 2.0],
                        ]
                    ],
                },
                23,
            ),
        ]

    rasterio_stub = sys.modules.get("rasterio")
    if rasterio_stub is None:
        rasterio_stub = types.ModuleType("rasterio")
        sys.modules["rasterio"] = rasterio_stub
    if not hasattr(rasterio_stub, "__path__"):
        rasterio_stub.__path__ = []
    monkeypatch.setattr(rasterio_stub, "open", lambda *args, **kwargs: DummyDataset())

    features_stub = types.ModuleType("rasterio.features")
    features_stub.shapes = _shapes
    monkeypatch.setitem(sys.modules, "rasterio.features", features_stub)
    rasterio_stub.features = features_stub

    _install_shapely_shape_stub(monkeypatch)
    _install_json_to_wgs_stub(monkeypatch)

    output_path = omni._build_contrast_ids_geojson()

    utm_path = output_path.replace(".wgs.geojson", ".utm.geojson")
    assert Path(utm_path).exists()

    payload = json.loads(Path(output_path).read_text(encoding="ascii"))
    labels = [feature["properties"]["contrast_label"] for feature in payload["features"]]
    assert labels == ["220", "230"]
    for feature in payload["features"]:
        assert feature["properties"]["selection_mode"] == "stream_order"
        assert "subcatchments_group" in feature["properties"]


def test_build_contrasts_clamps_hillslope_limit(tmp_path, monkeypatch, omni_module, caplog):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_cap")
    omni.locked = _noop_lock
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 1.0
    omni._contrast_hillslope_limit = 150
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None
    omni._contrast_selection_mode = "cumulative"
    omni._contrast_scenario = None
    omni._control_scenario = None
    omni._contrast_names = []
    omni._contrasts = None
    omni._contrast_dependency_tree = {}

    class DummyTranslator:
        top2wepp = {i: i for i in range(1, 121)}

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

    obj_params = [
        omni_module.ObjectiveParameter(str(i), str(i), 1.0) for i in range(1, 121)
    ]
    monkeypatch.setattr(
        omni_module.Omni,
        "get_objective_parameter_from_gpkg",
        lambda self, objective_parameter, scenario=None: (obj_params, 120.0),
    )

    with caplog.at_level(logging.WARNING, logger=omni.logger.name):
        omni._build_contrasts()

    assert len(omni._contrast_names) == 100
    assert "capped at 100" in caplog.text


def test_build_contrasts_caps_when_no_limit(tmp_path, monkeypatch, omni_module, caplog):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_cap_default")
    omni.locked = _noop_lock
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 1.0
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None
    omni._contrast_selection_mode = "cumulative"
    omni._contrast_scenario = None
    omni._control_scenario = None
    omni._contrast_names = []
    omni._contrasts = None
    omni._contrast_dependency_tree = {}

    class DummyTranslator:
        top2wepp = {i: i for i in range(1, 151)}

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

    obj_params = [
        omni_module.ObjectiveParameter(str(i), str(i), 1.0) for i in range(1, 151)
    ]
    monkeypatch.setattr(
        omni_module.Omni,
        "get_objective_parameter_from_gpkg",
        lambda self, objective_parameter, scenario=None: (obj_params, 150.0),
    )

    with caplog.at_level(logging.WARNING, logger=omni.logger.name):
        omni._build_contrasts()

    assert len(omni._contrast_names) == 100
    assert "Contrast selection reached cap of 100 hillslopes" in caplog.text


def test_run_omni_contrasts_skips_up_to_date(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.run_contrasts")
    omni.locked = _noop_lock
    omni._contrast_names = ["None,10__to__undisturbed"]
    omni._contrast_dependency_tree = {}

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    sidecar_path = Path(omni._contrast_sidecar_path(1))
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text("10\t/tmp/H10\n", encoding="ascii")

    readme_path = tmp_path / "_pups" / "omni" / "contrasts" / "1" / "wepp" / "output" / "interchange" / "README.md"
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text("ok", encoding="ascii")

    redisprep_path = tmp_path / "redisprep.dump"
    snapshot = {"timestamps:run_wepp_watershed": 123}
    redisprep_path.write_text(json.dumps(snapshot), encoding="ascii")

    omni._contrast_dependency_tree = {
        "None,10__to__undisturbed": {
            "dependencies": {},
            "sidecar_sha1": omni_module._hash_file_sha1(str(sidecar_path)),
            "control_redisprep": snapshot,
            "contrast_redisprep": snapshot,
            "last_run": 1.0,
        }
    }

    calls = []

    def fake_run(contrast_id, contrast_name, contrasts, wd, runid, control_key, contrast_key):
        calls.append((contrast_id, contrast_name))
        return f"{wd}/_pups/omni/contrasts/{contrast_id}"

    monkeypatch.setattr(omni_module, "_run_contrast", fake_run)
    monkeypatch.setattr(omni, "_post_omni_run", lambda wd, name: None)

    omni.run_omni_contrasts()

    assert calls == []


def test_run_omni_contrasts_runs_when_readme_missing(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.run_contrasts_missing_readme")
    omni.locked = _noop_lock
    contrast_name = "uniform_low,10__to__mulch"
    omni._contrast_names = [contrast_name]
    omni._contrast_dependency_tree = {}

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(
        omni_module,
        "_resolve_base_scenario_key",
        lambda wd: str(omni_module.OmniScenario.Undisturbed),
    )

    sidecar_path = Path(omni._contrast_sidecar_path(1))
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text("10\t/tmp/H10\n", encoding="ascii")

    redisprep_path = tmp_path / "redisprep.dump"
    snapshot = {"timestamps:run_wepp_watershed": 456}
    redisprep_path.write_text(json.dumps(snapshot), encoding="ascii")

    calls = []

    def fake_run(contrast_id, contrast_name, contrasts, wd, runid, control_key, contrast_key):
        calls.append((contrast_id, contrast_name))
        contrast_dir = Path(wd) / "_pups" / "omni" / "contrasts" / contrast_id
        (contrast_dir / "wepp" / "output" / "interchange").mkdir(parents=True, exist_ok=True)
        return str(contrast_dir)

    monkeypatch.setattr(omni_module, "_run_contrast", fake_run)
    monkeypatch.setattr(omni, "_post_omni_run", lambda wd, name: None)

    omni.run_omni_contrasts()

    assert calls
    assert calls[0][0] == "1"
    assert contrast_name in omni.contrast_dependency_tree


def test_run_omni_contrasts_runs_when_sidecar_changes(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.run_contrasts_sidecar")
    omni.locked = _noop_lock
    omni._contrast_names = ["uniform_low,10__to__mulch"]

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(
        omni_module,
        "_resolve_base_scenario_key",
        lambda wd: str(omni_module.OmniScenario.Undisturbed),
    )

    sidecar_path = Path(omni._contrast_sidecar_path(1))
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text("10\t/tmp/H10\n", encoding="ascii")

    readme_path = tmp_path / "_pups" / "omni" / "contrasts" / "1" / "wepp" / "output" / "interchange" / "README.md"
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text("ok", encoding="ascii")

    redisprep_path = tmp_path / "redisprep.dump"
    snapshot = {"timestamps:run_wepp_watershed": 789}
    redisprep_path.write_text(json.dumps(snapshot), encoding="ascii")

    omni._contrast_dependency_tree = {
        "None,10__to__undisturbed": {
            "dependencies": {},
            "sidecar_sha1": "stale",
            "control_redisprep": snapshot,
            "contrast_redisprep": snapshot,
            "last_run": 1.0,
        }
    }

    calls = []

    def fake_run(contrast_id, contrast_name, contrasts, wd, runid, control_key, contrast_key):
        calls.append((contrast_id, contrast_name))
        contrast_dir = Path(wd) / "_pups" / "omni" / "contrasts" / contrast_id
        (contrast_dir / "wepp" / "output" / "interchange").mkdir(parents=True, exist_ok=True)
        return str(contrast_dir)

    monkeypatch.setattr(omni_module, "_run_contrast", fake_run)
    monkeypatch.setattr(omni, "_post_omni_run", lambda wd, name: None)

    omni.run_omni_contrasts()

    assert calls
    assert calls[0][0] == "1"


def test_contrast_run_status_needs_run_when_redisprep_missing_watershed_timestamp(
    tmp_path, monkeypatch, omni_module
):
    monkeypatch.setattr(omni_module.NoDbBase, "has_sbs", property(lambda self: False))
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.redisprep_missing")

    contrast_name = "None,10__to__undisturbed"
    sidecar_path = Path(omni._contrast_sidecar_path(1))
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text("10\t/tmp/H1\n", encoding="ascii")
    readme_path = Path(omni._contrast_run_readme_path(1))
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text("done", encoding="ascii")

    redisprep_path = tmp_path / "redisprep.dump"
    redisprep_path.write_text(
        json.dumps({"timestamps:run_wepp_hillslopes": 123}),
        encoding="utf-8",
    )

    omni._contrast_dependency_tree = {
        contrast_name: {
            "sidecar_sha1": omni_module._hash_file_sha1(str(sidecar_path)),
            "control_redisprep": {"timestamps:run_wepp_watershed": 123},
            "contrast_redisprep": {"timestamps:run_wepp_watershed": 123},
        }
    }

    assert omni._contrast_run_status(1, contrast_name) == "needs_run"


def test_run_omni_contrasts_cleans_stale_runs(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.run_contrasts_stale")
    omni.locked = _noop_lock
    omni._contrast_names = ["None,10__to__undisturbed"]
    omni._contrast_dependency_tree = {}

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    contrasts_root = tmp_path / "_pups" / "omni" / "contrasts"
    (contrasts_root / "1").mkdir(parents=True, exist_ok=True)
    (contrasts_root / "2").mkdir(parents=True, exist_ok=True)
    (contrasts_root / "_uploads").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(omni, "_contrast_run_status", lambda contrast_id, name: "up_to_date")
    monkeypatch.setattr(omni_module, "_run_contrast", lambda *args, **kwargs: None)
    monkeypatch.setattr(omni, "_post_omni_run", lambda wd, name: None)

    omni.run_omni_contrasts()

    assert (contrasts_root / "1").exists()
    assert not (contrasts_root / "2").exists()
    assert (contrasts_root / "_uploads").exists()


def test_build_contrasts_dry_run_report_cumulative_statuses(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.dry_run_cumulative")
    omni.locked = _noop_lock
    monkeypatch.setattr(omni, "_contrast_landuse_skip_reason", lambda *args, **kwargs: None)

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    def fake_build_contrasts(*args, **kwargs):
        omni._contrast_selection_mode = "cumulative"
        omni._contrast_names = [
            "None,10__to__undisturbed",
            "None,20__to__undisturbed",
        ]
        sidecar1 = Path(omni._contrast_sidecar_path(1))
        sidecar1.parent.mkdir(parents=True, exist_ok=True)
        sidecar1.write_text("10\t/tmp/H10\n", encoding="ascii")
        sidecar2 = Path(omni._contrast_sidecar_path(2))
        sidecar2.write_text("20\t/tmp/H20\n", encoding="ascii")

        snapshot = {"timestamps:run_wepp_watershed": 123}
        (tmp_path / "redisprep.dump").write_text(json.dumps(snapshot), encoding="ascii")

        readme_path = Path(omni._contrast_run_readme_path(1))
        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text("ok", encoding="ascii")

        omni._contrast_dependency_tree = {
            "None,10__to__undisturbed": {
                "dependencies": {},
                "sidecar_sha1": omni_module._hash_file_sha1(str(sidecar1)),
                "control_redisprep": snapshot,
                "contrast_redisprep": snapshot,
                "last_run": 1.0,
            }
        }

    monkeypatch.setattr(omni, "build_contrasts", fake_build_contrasts)

    report = omni.build_contrasts_dry_run_report(
        control_scenario_def={"type": "uniform_low"},
        contrast_scenario_def={"type": "mulch"},
        contrast_pairs=[{"control_scenario": "uniform_low", "contrast_scenario": "mulch"}],
    )

    assert report["selection_mode"] == "cumulative"
    assert report["items"][0]["run_status"] == "up_to_date"
    assert report["items"][1]["run_status"] == "needs_run"
    assert report["items"][0]["topaz_id"] == "10"
    assert report["items"][1]["topaz_id"] == "20"


def test_build_contrasts_dry_run_report_user_defined(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.dry_run_user_defined")
    omni.locked = _noop_lock
    monkeypatch.setattr(omni, "_contrast_landuse_skip_reason", lambda *args, **kwargs: None)

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    def fake_build_contrasts(*args, **kwargs):
        omni._contrast_selection_mode = "user_defined_areas"
        omni._control_scenario = None
        omni._contrast_scenario = None
        omni._contrast_names = [
            None,
            "None,2__to__undisturbed",
        ]
        omni._contrast_labels = {1: "A1", 2: "A2"}

        report_path = Path(omni._contrast_build_report_path())
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_lines = [
            {
                "contrast_id": 1,
                "control_scenario": "undisturbed",
                "contrast_scenario": "undisturbed",
                "selection_mode": "user_defined_areas",
                "area_label": "A1",
                "n_hillslopes": 0,
                "topaz_ids": [],
                "status": "skipped",
            },
            {
                "contrast_id": 2,
                "control_scenario": "undisturbed",
                "contrast_scenario": "undisturbed",
                "selection_mode": "user_defined_areas",
                "area_label": "A2",
                "n_hillslopes": 2,
                "topaz_ids": ["10", "11"],
            },
        ]
        report_path.write_text(
            "\n".join(json.dumps(line) for line in report_lines) + "\n",
            encoding="ascii",
        )

        sidecar2 = Path(omni._contrast_sidecar_path(2))
        sidecar2.parent.mkdir(parents=True, exist_ok=True)
        sidecar2.write_text("10\t/tmp/H10\n", encoding="ascii")

        snapshot = {"timestamps:run_wepp_watershed": 456}
        (tmp_path / "redisprep.dump").write_text(json.dumps(snapshot), encoding="ascii")

        readme_path = Path(omni._contrast_run_readme_path(2))
        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text("ok", encoding="ascii")

        omni._contrast_dependency_tree = {
            "None,2__to__undisturbed": {
                "dependencies": {},
                "sidecar_sha1": omni_module._hash_file_sha1(str(sidecar2)),
                "control_redisprep": snapshot,
                "contrast_redisprep": snapshot,
                "last_run": 1.0,
            }
        }

    monkeypatch.setattr(omni, "build_contrasts", fake_build_contrasts)

    report = omni.build_contrasts_dry_run_report(
        control_scenario_def={"type": "uniform_low"},
        contrast_scenario_def={"type": "mulch"},
    )

    assert report["selection_mode"] == "user_defined_areas"
    assert report["items"][0]["run_status"] == "skipped"
    assert report["items"][0]["skip_status"]["reason"] == "no_hillslopes"
    assert report["items"][1]["run_status"] == "up_to_date"
    assert report["items"][1]["skip_status"]["skipped"] is False


def test_contrasts_report_reads_contrast_outputs_from_pups(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrasts_report")
    omni._contrast_names = ["None,10__to__undisturbed"]
    omni._contrast_selection_mode = "cumulative"

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


def test_stream_order_contrasts_grouping_and_skip(tmp_path, omni_module, monkeypatch):
    wbt_dir = tmp_path / "dem" / "wbt"
    wbt_dir.mkdir(parents=True)

    for stem in ("flovec", "netful", "relief", "chnjnt", "bound", "subwta"):
        (wbt_dir / f"{stem}.tif").write_text("", encoding="ascii")
    (wbt_dir / "outlet.geojson").write_text("{}", encoding="ascii")

    (wbt_dir / "netful.strahler.tif").write_text("", encoding="ascii")
    (wbt_dir / "netful.pruned_1.tif").write_text("", encoding="ascii")
    (wbt_dir / "netful.strahler_pruned_1.tif").write_text("", encoding="ascii")
    (wbt_dir / "chnjnt.strahler_pruned_1.tif").write_text("", encoding="ascii")
    (wbt_dir / "subwta.strahler_pruned_1.tif").write_text("", encoding="ascii")
    (wbt_dir / "netw.strahler_pruned_1.tsv").write_text("", encoding="ascii")

    class DummyDataset:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, *args, **kwargs):
            return np.ma.array([[1, 2, 3]], mask=False)

    rasterio_stub = sys.modules.get("rasterio")
    if rasterio_stub is None:
        rasterio_stub = types.ModuleType("rasterio")
        sys.modules["rasterio"] = rasterio_stub
    monkeypatch.setattr(rasterio_stub, "open", lambda *args, **kwargs: DummyDataset())

    _ensure_package("wepppyo3", tmp_path)
    rc_stub = types.ModuleType("wepppyo3.raster_characteristics")
    rc_stub.identify_mode_single_raster_key = lambda **kwargs: {"10": 2, "20": 1, "30": 1}
    monkeypatch.setitem(sys.modules, "wepppyo3.raster_characteristics", rc_stub)
    sys.modules["wepppyo3"].raster_characteristics = rc_stub

    class DummyTranslator:
        top2wepp = {"10": "1", "20": "2", "30": "3"}

    class DummyWatershed:
        delineation_backend_is_wbt = True
        wbt_wd = str(wbt_dir)

        def translator_factory(self):
            return DummyTranslator()

    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(
        omni_module,
        "_resolve_base_scenario_key",
        lambda wd: str(omni_module.OmniScenario.Undisturbed),
    )

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.stream_order")
    omni._contrast_selection_mode = "stream_order"
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        {"control_scenario": "uniform_low", "contrast_scenario": "thinning"},
    ]
    omni._contrast_order_reduction_passes = 1

    omni._build_contrasts()

    assert omni.contrast_names[:4] == [
        "uniform_low,1__to__mulch",
        "uniform_low,2__to__thinning",
        "uniform_low,3__to__mulch",
        "uniform_low,4__to__thinning",
    ]
    assert omni.contrast_names[4:] == [None, None]

    sidecar_path = omni._contrast_sidecar_path(1)
    sidecar = {}
    with open(sidecar_path, "r", encoding="ascii") as handle:
        for line in handle:
            topaz_id, _, wepp_path = line.strip().partition("\t")
            sidecar[topaz_id] = wepp_path

    assert sidecar["20"].endswith("/_pups/omni/scenarios/mulch/wepp/output/H2")
    assert sidecar["30"].endswith("/_pups/omni/scenarios/mulch/wepp/output/H3")
    assert sidecar["10"].endswith("/_pups/omni/scenarios/uniform_low/wepp/output/H1")

    report = omni.contrast_status_report()
    report_index = {item["contrast_id"]: item for item in report["items"]}
    assert report_index[1]["subcatchments_group"] == 10
    assert report_index[3]["subcatchments_group"] == 20
    assert report_index[5]["subcatchments_group"] == 30
    skipped = next(item for item in report["items"] if item["contrast_id"] == 5)
    assert skipped["run_status"] == "skipped"
    assert skipped["skip_status"]["reason"] == "no_hillslopes"
