import errno
import os
import importlib
import json
import logging
import time
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


def test_apply_contrast_output_triggers_creates_and_removes_files(tmp_path, omni_module):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    created = {"chan": 0}

    class DummyWepp:
        def __init__(self, runs_dir):
            self.runs_dir = str(runs_dir)
            self.logger = logging.getLogger("tests.omni.output_triggers")

        def _prep_channel_input(self):
            created["chan"] += 1
            (Path(self.runs_dir) / "chan.inp").write_text("chan", encoding="ascii")

    wepp = DummyWepp(runs_dir)

    omni_module._apply_contrast_output_triggers(
        wepp,
        {"chan_out": True, "tcr_out": True},
    )

    assert (runs_dir / "chan.inp").exists()
    assert (runs_dir / "tc.txt").exists()
    assert created["chan"] == 1

    omni_module._apply_contrast_output_triggers(
        wepp,
        {"chan_out": False, "tcr_out": False},
    )

    assert not (runs_dir / "chan.inp").exists()
    assert not (runs_dir / "tc.txt").exists()


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


def test_run_omni_scenario_prescribed_fire_requires_treatment_key(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    run_dir = tmp_path / "run-omni-prescribed-fire"
    run_dir.mkdir()
    omni.wd = str(run_dir)
    omni.logger = logging.getLogger("tests.omni.prescribed_fire")

    scenario_dir = tmp_path / "_pups" / "omni" / "scenarios" / "prescribed_fire"
    scenario_dir.mkdir(parents=True)

    monkeypatch.setattr(omni_module, "_omni_clone", lambda *args, **kwargs: str(scenario_dir))
    monkeypatch.setattr(omni_module.NoDbBase, "has_sbs", property(lambda self: False), raising=False)

    class DummyDisturbed:
        has_sbs = False

    class DummyLanduse:
        pass

    class DummySoils:
        def build(self, max_workers=None):
            return None

    class DummyTreatments:
        @property
        def treatments_lookup(self):
            return {}

    import wepppy.nodb.core as nodb_core
    import wepppy.nodb.mods.disturbed as disturbed_mod
    import wepppy.nodb.mods.treatments as treatments_mod

    monkeypatch.setattr(disturbed_mod.Disturbed, "getInstance", lambda wd: DummyDisturbed())
    monkeypatch.setattr(nodb_core.Landuse, "getInstance", lambda wd: DummyLanduse())
    monkeypatch.setattr(nodb_core.Soils, "getInstance", lambda wd: DummySoils())
    monkeypatch.setattr(treatments_mod.Treatments, "getInstance", lambda wd: DummyTreatments())

    with pytest.raises(ValueError, match="prescribed_fire"):
        omni.run_omni_scenario({"type": "prescribed_fire"})


def test_run_omni_scenario_undisturbed_allows_base_without_sbs(
    tmp_path,
    monkeypatch,
    omni_module,
):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    run_dir = tmp_path / "_base"
    run_dir.mkdir()
    scenario_dir = run_dir / "_pups" / "omni" / "scenarios" / "undisturbed"
    scenario_dir.mkdir(parents=True)
    (run_dir / "wepp" / "runs").mkdir(parents=True, exist_ok=True)
    (scenario_dir / "wepp" / "runs").mkdir(parents=True, exist_ok=True)
    (scenario_dir / "wepp" / "output").mkdir(parents=True, exist_ok=True)

    omni.wd = str(run_dir)
    omni.logger = logging.getLogger("tests.omni.undisturbed_base")

    monkeypatch.setattr(omni_module, "_omni_clone", lambda *args, **kwargs: str(scenario_dir))
    monkeypatch.setattr(omni_module, "run_wepp_hillslope_interchange", lambda *args, **kwargs: None)
    monkeypatch.setattr(omni_module, "_post_watershed_run_cleanup", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        omni_module.Omni,
        "delete_after_interchange",
        property(lambda self: False),
        raising=False,
    )
    monkeypatch.setattr(omni_module.NoDbBase, "has_sbs", property(lambda self: False), raising=False)

    remove_calls = {"count": 0}

    class DummyDisturbed:
        has_sbs = False

        def remove_sbs(self) -> None:
            remove_calls["count"] += 1

    class DummyLanduse:
        def build(self) -> None:
            return None

        def build_managements(self) -> None:
            return None

    class DummySoils:
        def build(self, max_workers=None) -> None:
            return None

    class DummyWepp:
        def __init__(self, wd: str) -> None:
            self.runs_dir = str(Path(wd) / "wepp" / "runs")
            self.output_dir = str(Path(wd) / "wepp" / "output")

        def prep_hillslopes(self, **kwargs) -> None:
            return None

        def run_hillslopes(self, **kwargs) -> None:
            return None

        def prep_watershed(self) -> None:
            return None

        def run_watershed(self) -> None:
            return None

    class DummyClimate:
        observed_start_year = None
        future_start_year = None

    import wepppy.nodb.core as nodb_core
    import wepppy.nodb.mods.disturbed as disturbed_mod

    monkeypatch.setattr(disturbed_mod.Disturbed, "getInstance", lambda wd: DummyDisturbed())
    monkeypatch.setattr(nodb_core.Landuse, "getInstance", lambda wd: DummyLanduse())
    monkeypatch.setattr(nodb_core.Soils, "getInstance", lambda wd: DummySoils())
    monkeypatch.setattr(nodb_core.Wepp, "getInstance", lambda wd: DummyWepp(wd))
    monkeypatch.setattr(nodb_core.Climate, "getInstance", lambda wd: DummyClimate())

    scenario_wd, scenario_name = omni.run_omni_scenario({"type": "undisturbed"})

    assert Path(scenario_wd) == scenario_dir
    assert scenario_name == "undisturbed"
    assert remove_calls["count"] == 1


def test_run_omni_scenario_undisturbed_requires_sbs_outside_base(
    tmp_path,
    monkeypatch,
    omni_module,
):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    run_dir = tmp_path / "run-omni-undisturbed"
    run_dir.mkdir()
    scenario_dir = run_dir / "_pups" / "omni" / "scenarios" / "undisturbed"
    scenario_dir.mkdir(parents=True)

    omni.wd = str(run_dir)
    omni.logger = logging.getLogger("tests.omni.undisturbed_requires_sbs")

    monkeypatch.setattr(omni_module, "_omni_clone", lambda *args, **kwargs: str(scenario_dir))
    monkeypatch.setattr(omni_module.NoDbBase, "has_sbs", property(lambda self: False), raising=False)

    class DummyDisturbed:
        has_sbs = False

        def remove_sbs(self) -> None:
            return None

    class DummyLanduse:
        def build(self) -> None:
            return None

        def build_managements(self) -> None:
            return None

    class DummySoils:
        def build(self, max_workers=None) -> None:
            return None

    import wepppy.nodb.core as nodb_core
    import wepppy.nodb.mods.disturbed as disturbed_mod

    monkeypatch.setattr(disturbed_mod.Disturbed, "getInstance", lambda wd: DummyDisturbed())
    monkeypatch.setattr(nodb_core.Landuse, "getInstance", lambda wd: DummyLanduse())
    monkeypatch.setattr(nodb_core.Soils, "getInstance", lambda wd: DummySoils())

    with pytest.raises(Exception, match="Undisturbed scenario requires a base scenario with sbs"):
        omni.run_omni_scenario({"type": "undisturbed"})


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


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_omni_clone_links_nodir_shared_inputs(tmp_path: Path, omni_module) -> None:
    base_wd = tmp_path / "run"
    base_wd.mkdir()
    (base_wd / "dem").mkdir()
    (base_wd / "climate.nodir").write_text("climate", encoding="utf-8")
    (base_wd / "watershed.nodir").write_text("watershed", encoding="utf-8")
    (base_wd / "climate.wepp_cli.parquet").write_text("climate-sidecar", encoding="utf-8")
    (base_wd / "watershed.hillslopes.parquet").write_text("hillslope-sidecar", encoding="utf-8")
    (base_wd / "watershed.channels.parquet").write_text("channel-sidecar", encoding="utf-8")

    scenario_def = {"type": "dummy"}
    scenario_wd = Path(omni_module._omni_clone(scenario_def, str(base_wd), runid="run-123"))

    assert (scenario_wd / "dem").is_symlink()
    assert os.readlink(scenario_wd / "dem") == str(base_wd / "dem")
    assert (scenario_wd / "climate.nodir").is_symlink()
    assert os.readlink(scenario_wd / "climate.nodir") == str(base_wd / "climate.nodir")
    assert (scenario_wd / "watershed.nodir").is_symlink()
    assert os.readlink(scenario_wd / "watershed.nodir") == str(base_wd / "watershed.nodir")
    assert (scenario_wd / "climate.wepp_cli.parquet").is_symlink()
    assert os.readlink(scenario_wd / "climate.wepp_cli.parquet") == str(base_wd / "climate.wepp_cli.parquet")
    assert (scenario_wd / "watershed.hillslopes.parquet").is_symlink()
    assert os.readlink(scenario_wd / "watershed.hillslopes.parquet") == str(base_wd / "watershed.hillslopes.parquet")
    assert (scenario_wd / "watershed.channels.parquet").is_symlink()
    assert os.readlink(scenario_wd / "watershed.channels.parquet") == str(base_wd / "watershed.channels.parquet")


def test_omni_clone_survives_enotempty_on_existing_workspace_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    omni_module,
) -> None:
    import wepppy.nodb.mods.omni.omni_clone_contrast_service as clone_service_mod

    base_wd = tmp_path / "run"
    base_wd.mkdir()
    (base_wd / "dem").mkdir()
    (base_wd / "climate").mkdir()
    (base_wd / "watershed").mkdir()

    existing_wd = base_wd / "_pups" / "omni" / "scenarios" / "dummy"
    (existing_wd / "wepp" / "runs").mkdir(parents=True)
    (existing_wd / "wepp" / "runs" / "old.run").write_text("old", encoding="ascii")

    monkeypatch.setattr(omni_module, "nodir_resolve", lambda *args, **kwargs: None)

    real_rmtree = clone_service_mod.shutil.rmtree
    calls = {"enotempty_raised": 0}

    def _flaky_rmtree(path: str | Path, *args: object, **kwargs: object) -> None:
        path_obj = Path(path)
        if path_obj.name.startswith("dummy.stale.") and calls["enotempty_raised"] == 0:
            calls["enotempty_raised"] += 1
            raise OSError(errno.ENOTEMPTY, "Directory not empty", str(path_obj))
        real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(clone_service_mod.shutil, "rmtree", _flaky_rmtree)

    scenario_wd = Path(omni_module._omni_clone({"type": "dummy"}, str(base_wd), runid="run-123"))

    assert calls["enotempty_raised"] == 1
    assert scenario_wd.is_dir()
    stale_dirs = list((base_wd / "_pups" / "omni" / "scenarios").glob("dummy.stale.*"))
    assert stale_dirs == []


def test_omni_clone_logs_directory_copy_permission_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    omni_module,
    caplog: pytest.LogCaptureFixture,
) -> None:
    base_wd = tmp_path / "run"
    source_dir = base_wd / "problem-dir"
    nested_dir = source_dir / "nested"
    nested_dir.mkdir(parents=True)

    monkeypatch.setattr(omni_module, "nodir_resolve", lambda *args, **kwargs: None)

    original_walk = omni_module.os.walk

    def _walk_with_permission_error(path: str):
        if str(path) == str(source_dir):
            raise PermissionError("blocked")
        return original_walk(path)

    monkeypatch.setattr(omni_module.os, "walk", _walk_with_permission_error)

    with caplog.at_level(logging.WARNING, logger=omni_module.LOGGER.name):
        scenario_wd = Path(omni_module._omni_clone({"type": "dummy"}, str(base_wd), runid="run-123"))

    assert scenario_wd.exists()
    assert "Permission denied while creating Omni clone directory tree" in caplog.text


def test_omni_clone_logs_directory_copy_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    omni_module,
    caplog: pytest.LogCaptureFixture,
) -> None:
    base_wd = tmp_path / "run"
    source_dir = base_wd / "problem-dir"
    nested_dir = source_dir / "nested"
    nested_dir.mkdir(parents=True)

    monkeypatch.setattr(omni_module, "nodir_resolve", lambda *args, **kwargs: None)

    original_walk = omni_module.os.walk

    def _walk_with_oserror(path: str):
        if str(path) == str(source_dir):
            raise OSError("boom")
        return original_walk(path)

    monkeypatch.setattr(omni_module.os, "walk", _walk_with_oserror)

    with caplog.at_level(logging.WARNING, logger=omni_module.LOGGER.name):
        scenario_wd = Path(omni_module._omni_clone({"type": "dummy"}, str(base_wd), runid="run-123"))

    assert scenario_wd.exists()
    assert "Error creating Omni clone directory tree" in caplog.text


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


def test_clear_contrasts_propagates_non_oserror_from_report_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    omni_module,
) -> None:
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni._contrast_names = ["existing"]
    omni._contrasts = [{"1": "/tmp/H1"}]
    omni._contrast_dependency_tree = {}

    report_path = Path(omni._contrast_build_report_path())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("{}", encoding="ascii")

    original_remove = omni_module.os.remove

    def _remove_with_non_oserror(path: str) -> None:
        if path == str(report_path):
            raise ValueError("simulated-remove-error")
        original_remove(path)

    monkeypatch.setattr(omni_module.os, "remove", _remove_with_non_oserror)

    with pytest.raises(ValueError, match="simulated-remove-error"):
        omni.clear_contrasts()


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


def test_user_defined_areas_contrast_limit_enforced(tmp_path, omni_module, monkeypatch):
    hillslope_rows = [
        {"TopazID": "10", "geometry": Rect(0.0, 0.0, 10.0, 10.0)},
    ]
    user_rows = [
        {"name": f"Area {idx}", "geometry": Rect(0.0, 0.0, 10.0, 10.0)}
        for idx in range(101)
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
    omni.logger = logging.getLogger("tests.omni.user_defined_limit")
    omni._contrast_selection_mode = "user_defined_areas"
    omni._contrast_geojson_path = str(user_geojson_path)
    omni._contrast_geojson_name_key = "name"
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        {"control_scenario": "uniform_low", "contrast_scenario": "thinning"},
    ]
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None

    with pytest.raises(ValueError) as excinfo:
        omni._build_contrasts()

    assert "limited to 200" in str(excinfo.value)


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


def test_user_defined_hillslope_groups_contrast_limit_enforced(tmp_path, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.hillslope_group_limit")
    omni._contrast_selection_mode = "user_defined_hillslope_groups"
    omni._contrast_hillslope_groups = "\n".join(["11"] * 101)
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        {"control_scenario": "uniform_low", "contrast_scenario": "thinning"},
    ]
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None

    with pytest.raises(ValueError) as excinfo:
        omni._build_contrasts()

    assert "limited to 200" in str(excinfo.value)


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


def test_build_contrasts_raises_value_error_when_no_soil_data(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.no_soil_data")
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 1.0
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None
    omni._contrast_selection_mode = "cumulative"
    omni._control_scenario = "uniform_high"
    omni._contrast_scenario = None
    omni._contrast_names = []
    omni._contrasts = None
    omni._contrast_dependency_tree = {}
    omni.locked = _noop_lock

    class DummyTranslator:
        top2wepp = {101: 201}

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
        lambda self, objective_parameter, scenario=None: ([], 0.0),
    )

    with pytest.raises(ValueError, match="No soil erosion data found!"):
        omni._build_contrasts()


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


def test_run_omni_scenarios_delegates_to_run_orchestration_service(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    captured: dict[str, object] = {}

    def _fake_run(instance):
        captured["instance"] = instance

    monkeypatch.setattr(omni_module._OMNI_RUN_ORCHESTRATION_SERVICE, "run_omni_scenarios", _fake_run)

    omni.run_omni_scenarios()

    assert captured["instance"] is omni


def test_build_contrasts_stream_order_delegates_to_contrast_build_service(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    captured: dict[str, object] = {}

    def _fake_build(instance):
        captured["instance"] = instance

    monkeypatch.setattr(
        omni_module._OMNI_CONTRAST_BUILD_SERVICE,
        "build_contrasts_stream_order",
        _fake_build,
    )

    omni._build_contrasts_stream_order()

    assert captured["instance"] is omni


def test_build_contrasts_user_defined_areas_delegates_to_contrast_build_service(
    tmp_path,
    monkeypatch,
    omni_module,
):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    captured: dict[str, object] = {}

    def _fake_build(instance):
        captured["instance"] = instance

    monkeypatch.setattr(
        omni_module._OMNI_CONTRAST_BUILD_SERVICE,
        "build_contrasts_user_defined_areas",
        _fake_build,
    )

    omni._build_contrasts_user_defined_areas()

    assert captured["instance"] is omni


def test_run_omni_contrasts_delegates_to_run_orchestration_service(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    captured: dict[str, object] = {}

    def _fake_run(instance):
        captured["instance"] = instance

    monkeypatch.setattr(omni_module._OMNI_RUN_ORCHESTRATION_SERVICE, "run_omni_contrasts", _fake_run)

    omni.run_omni_contrasts()

    assert captured["instance"] is omni


def test_run_omni_contrast_delegates_to_run_orchestration_service(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    captured: dict[str, object] = {}

    def _fake_run(instance, contrast_id, *, rq_job_id=None):
        captured["instance"] = instance
        captured["contrast_id"] = contrast_id
        captured["rq_job_id"] = rq_job_id
        return str(tmp_path / "_pups" / "omni" / "contrasts" / str(contrast_id))

    monkeypatch.setattr(omni_module._OMNI_RUN_ORCHESTRATION_SERVICE, "run_omni_contrast", _fake_run)

    result = omni.run_omni_contrast(3, rq_job_id="job-123")

    assert captured == {"instance": omni, "contrast_id": 3, "rq_job_id": "job-123"}
    assert result.endswith("/_pups/omni/contrasts/3")


def test_run_omni_scenarios_raises_runtime_error_when_no_scenarios(tmp_path, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.run_scenarios.empty")
    omni._scenarios = []

    with pytest.raises(RuntimeError, match="No scenarios to run"):
        omni.run_omni_scenarios()


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

    def fake_run(contrast_id, contrast_name, contrasts, wd, runid, control_key, contrast_key, **_kwargs):
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

    def fake_run(contrast_id, contrast_name, contrasts, wd, runid, control_key, contrast_key, **_kwargs):
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

    def fake_run(contrast_id, contrast_name, contrasts, wd, runid, control_key, contrast_key, **_kwargs):
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


def test_contrast_run_status_needs_run_when_order_reduction_passes_change(
    tmp_path,
    monkeypatch,
    omni_module,
):
    monkeypatch.setattr(omni_module.NoDbBase, "has_sbs", property(lambda self: False))
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.order_reduction_status")
    omni._contrast_selection_mode = "stream_order"
    omni._contrast_order_reduction_passes = 2

    contrast_name = "None,10__to__undisturbed"
    sidecar_path = Path(omni._contrast_sidecar_path(1))
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text("10\t/tmp/H1\n", encoding="ascii")
    readme_path = Path(omni._contrast_run_readme_path(1))
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text("done", encoding="ascii")

    snapshot = {"timestamps:run_wepp_watershed": 123}
    (tmp_path / "redisprep.dump").write_text(json.dumps(snapshot), encoding="utf-8")

    omni._contrast_dependency_tree = {
        contrast_name: {
            "sidecar_sha1": omni_module._hash_file_sha1(str(sidecar_path)),
            "control_redisprep": snapshot,
            "contrast_redisprep": snapshot,
            "order_reduction_passes": 1,
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


def test_stream_order_contrast_limit_enforced(tmp_path, omni_module, monkeypatch):
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
            return np.ma.array([list(range(1, 226))], mask=False)

    rasterio_stub = sys.modules.get("rasterio")
    if rasterio_stub is None:
        rasterio_stub = types.ModuleType("rasterio")
        sys.modules["rasterio"] = rasterio_stub
    monkeypatch.setattr(rasterio_stub, "open", lambda *args, **kwargs: DummyDataset())

    _ensure_package("wepppyo3", tmp_path)
    rc_stub = types.ModuleType("wepppyo3.raster_characteristics")
    rc_stub.identify_mode_single_raster_key = lambda **kwargs: {"10": 1}
    monkeypatch.setitem(sys.modules, "wepppyo3.raster_characteristics", rc_stub)
    sys.modules["wepppyo3"].raster_characteristics = rc_stub

    class DummyTranslator:
        top2wepp = {"10": "1"}

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
    omni.logger = logging.getLogger("tests.omni.stream_order_limit")
    omni._contrast_selection_mode = "stream_order"
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
    ]
    omni._contrast_order_reduction_passes = 1

    with pytest.raises(ValueError) as excinfo:
        omni._build_contrasts()

    assert "limited to 200" in str(excinfo.value)


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


@pytest.mark.parametrize(
    ("build_subcatchments_ts", "expect_prune", "expect_wbt"),
    [
        (10_000_000_000.0, True, True),
        (0.0, False, False),
    ],
)
def test_build_contrasts_stream_order_stale_rebuild_decisions(
    tmp_path,
    omni_module,
    monkeypatch,
    build_subcatchments_ts,
    expect_prune,
    expect_wbt,
):
    wbt_dir = tmp_path / "dem" / "wbt"
    wbt_dir.mkdir(parents=True)

    required = {}
    for stem in ("flovec", "netful", "relief", "chnjnt", "bound", "subwta"):
        path = wbt_dir / f"{stem}.tif"
        path.write_text("", encoding="ascii")
        required[stem] = path
    (wbt_dir / "outlet.geojson").write_text("{}", encoding="ascii")

    strahler_path = wbt_dir / "netful.strahler.tif"
    pruned_streams_path = wbt_dir / "netful.pruned_1.tif"
    order_pruned_path = wbt_dir / "netful.strahler_pruned_1.tif"
    chnjnt_pruned_path = wbt_dir / "chnjnt.strahler_pruned_1.tif"
    subwta_pruned_path = wbt_dir / "subwta.strahler_pruned_1.tif"
    netw_pruned_path = wbt_dir / "netw.strahler_pruned_1.tsv"
    for path in (
        strahler_path,
        pruned_streams_path,
        order_pruned_path,
        chnjnt_pruned_path,
        subwta_pruned_path,
        netw_pruned_path,
    ):
        path.write_text("", encoding="ascii")

    now = time.time()
    for path in (
        strahler_path,
        pruned_streams_path,
        order_pruned_path,
        chnjnt_pruned_path,
        subwta_pruned_path,
        netw_pruned_path,
    ):
        os.utime(path, (now, now))

    class DummyDataset:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, *args, **kwargs):
            return np.ma.array([[1]], mask=False)

    rasterio_stub = sys.modules.get("rasterio")
    if rasterio_stub is None:
        rasterio_stub = types.ModuleType("rasterio")
        sys.modules["rasterio"] = rasterio_stub
    monkeypatch.setattr(rasterio_stub, "open", lambda *args, **kwargs: DummyDataset())

    _ensure_package("wepppyo3", tmp_path)
    rc_stub = types.ModuleType("wepppyo3.raster_characteristics")
    rc_stub.identify_mode_single_raster_key = lambda **kwargs: {"10": 1}
    monkeypatch.setitem(sys.modules, "wepppyo3.raster_characteristics", rc_stub)
    sys.modules["wepppyo3"].raster_characteristics = rc_stub

    class DummyTranslator:
        top2wepp = {"10": "1"}

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

    prune_calls = []

    def _fake_prune(*args, **kwargs):
        prune_calls.append((args, kwargs))
        strahler_path.write_text("", encoding="ascii")
        pruned_streams_path.write_text("", encoding="ascii")
        os.utime(strahler_path, None)
        os.utime(pruned_streams_path, None)

    monkeypatch.setattr(omni_module, "_prune_stream_order", _fake_prune)

    wbt_calls = {"strahler_stream_order": 0, "stream_junction_identifier": 0, "hillslopes_topaz": 0}

    class DummyWhiteboxTools:
        def __init__(self, *args, **kwargs) -> None:
            self._working_dir = str(wbt_dir)

        def set_working_dir(self, working_dir: str) -> None:
            self._working_dir = working_dir

        def strahler_stream_order(self, **kwargs):
            wbt_calls["strahler_stream_order"] += 1
            Path(kwargs["output"]).write_text("", encoding="ascii")
            return 0

        def stream_junction_identifier(self, **kwargs):
            wbt_calls["stream_junction_identifier"] += 1
            Path(kwargs["output"]).write_text("", encoding="ascii")
            return 0

        def hillslopes_topaz(self, **kwargs):
            wbt_calls["hillslopes_topaz"] += 1
            Path(kwargs["subwta"]).write_text("", encoding="ascii")
            Path(kwargs["netw"]).write_text("", encoding="ascii")
            return 0

    whitebox_tools_stub = types.ModuleType("whitebox_tools")
    whitebox_tools_stub.WhiteboxTools = DummyWhiteboxTools
    monkeypatch.setitem(sys.modules, "whitebox_tools", whitebox_tools_stub)

    class DummyPrep:
        def __getitem__(self, key):
            return build_subcatchments_ts

    monkeypatch.setattr(omni_module.RedisPrep, "getInstance", lambda wd: DummyPrep())

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.stream_order_rebuild")
    omni._contrast_selection_mode = "stream_order"
    omni._contrast_pairs = [{"control_scenario": "uniform_low", "contrast_scenario": "mulch"}]
    omni._contrast_order_reduction_passes = 1

    omni._build_contrasts()

    assert bool(prune_calls) is expect_prune
    assert bool(wbt_calls["hillslopes_topaz"]) is expect_wbt
    assert bool(wbt_calls["strahler_stream_order"]) is expect_wbt
    assert bool(wbt_calls["stream_junction_identifier"]) is expect_wbt


def test_omni_clone_copies_soils_from_archive_source(tmp_path: Path, omni_module, monkeypatch):
    base_wd = tmp_path / "run"
    base_wd.mkdir()
    (base_wd / "dem").mkdir()
    (base_wd / "climate").mkdir()
    (base_wd / "watershed").mkdir()
    (base_wd / "soils.nodir").write_text("archive", encoding="ascii")
    (base_wd / "landuse.nodir").write_text("archive", encoding="ascii")
    (base_wd / "soils.parquet").write_text("soils-sidecar", encoding="ascii")
    (base_wd / "landuse.parquet").write_text("landuse-sidecar", encoding="ascii")

    projected_soils = tmp_path / "projected-soils"
    projected_soils.mkdir()
    (projected_soils / "soils.parquet").write_text("soils", encoding="ascii")

    def _resolve(wd: str, rel: str, view: str = "effective"):
        if wd == str(base_wd) and rel in {"soils", "landuse"}:
            return types.SimpleNamespace(form="archive")
        return None

    @contextmanager
    def _projection(wd: str, root: str, *, mode: str, purpose: str):
        assert wd == str(base_wd)
        assert root == "soils"
        assert mode == "read"
        yield types.SimpleNamespace(mount_path=str(projected_soils))

    monkeypatch.setattr(omni_module, "nodir_resolve", _resolve)
    monkeypatch.setattr(omni_module, "with_root_projection", _projection)

    scenario_wd = Path(omni_module._omni_clone({"type": "dummy"}, str(base_wd), runid="run-123"))

    assert (scenario_wd / "soils").is_dir()
    assert (scenario_wd / "soils" / "soils.parquet").read_text(encoding="ascii") == "soils"
    assert (scenario_wd / "soils.parquet").read_text(encoding="ascii") == "soils-sidecar"
    assert not (scenario_wd / "soils.parquet").is_symlink()
    assert (scenario_wd / "landuse.parquet").read_text(encoding="ascii") == "landuse-sidecar"
    assert not (scenario_wd / "landuse.parquet").is_symlink()


def test_omni_clone_copies_soils_from_directory_source(tmp_path: Path, omni_module, monkeypatch):
    base_wd = tmp_path / "run"
    base_wd.mkdir()
    (base_wd / "dem").mkdir()
    (base_wd / "climate").mkdir()
    (base_wd / "watershed").mkdir()
    soils_src = base_wd / "soils"
    soils_src.mkdir()
    (soils_src / "763002.sol").write_text("soil-data", encoding="ascii")
    (base_wd / "soils.parquet").write_text("soils-sidecar", encoding="ascii")

    def _resolve(wd: str, rel: str, view: str = "effective"):
        if wd == str(base_wd) and rel == "soils":
            return types.SimpleNamespace(
                form="dir",
                dir_path=str(base_wd),
                inner_path="soils",
            )
        return None

    monkeypatch.setattr(omni_module, "nodir_resolve", _resolve)

    scenario_wd = Path(omni_module._omni_clone({"type": "dummy"}, str(base_wd), runid="run-123"))

    assert (scenario_wd / "soils").is_dir()
    assert (scenario_wd / "soils" / "763002.sol").read_text(encoding="ascii") == "soil-data"
    assert (scenario_wd / "soils.parquet").read_text(encoding="ascii") == "soils-sidecar"
    assert not (scenario_wd / "soils.parquet").is_symlink()


def test_omni_clone_copies_landuse_from_directory_source(tmp_path: Path, omni_module, monkeypatch):
    base_wd = tmp_path / "run"
    base_wd.mkdir()
    (base_wd / "dem").mkdir()
    (base_wd / "climate").mkdir()
    (base_wd / "watershed").mkdir()
    landuse_src = base_wd / "landuse"
    landuse_src.mkdir()
    (landuse_src / "custom.man").write_text("management-data", encoding="ascii")
    (base_wd / "landuse.parquet").write_text("landuse-sidecar", encoding="ascii")

    def _resolve(wd: str, rel: str, view: str = "effective"):
        if wd == str(base_wd) and rel == "landuse":
            return types.SimpleNamespace(
                form="dir",
                dir_path=str(base_wd),
                inner_path="landuse",
            )
        return None

    monkeypatch.setattr(omni_module, "nodir_resolve", _resolve)

    scenario_wd = Path(omni_module._omni_clone({"type": "dummy"}, str(base_wd), runid="run-123"))

    assert (scenario_wd / "landuse").is_dir()
    assert (scenario_wd / "landuse" / "custom.man").read_text(encoding="ascii") == "management-data"
    assert (scenario_wd / "landuse.parquet").read_text(encoding="ascii") == "landuse-sidecar"
    assert not (scenario_wd / "landuse.parquet").is_symlink()


def test_omni_clone_sibling_copies_archive_landuse_and_soils(tmp_path: Path, omni_module, monkeypatch):
    parent_wd = tmp_path / "run"
    new_wd = parent_wd / "_pups" / "omni" / "scenarios" / "target"
    sibling_wd = parent_wd / "_pups" / "omni" / "scenarios" / "sibling"
    new_wd.mkdir(parents=True)
    sibling_wd.mkdir(parents=True)

    for name in ("disturbed", "landuse", "soils"):
        (new_wd / f"{name}.nodb").write_text(json.dumps({"wd": str(new_wd)}), encoding="ascii")
        (sibling_wd / f"{name}.nodb").write_text(json.dumps({"wd": str(sibling_wd)}), encoding="ascii")

    for dirname in ("disturbed", "landuse", "soils"):
        (new_wd / dirname).mkdir()
        (new_wd / dirname / "old.txt").write_text("old", encoding="ascii")
    (new_wd / "landuse.parquet").write_text("old-landuse-sidecar", encoding="ascii")
    (new_wd / "soils.parquet").write_text("old-soils-sidecar", encoding="ascii")

    (sibling_wd / "disturbed").mkdir()
    (sibling_wd / "disturbed" / "disturbed.txt").write_text("disturbed", encoding="ascii")
    (sibling_wd / "landuse.nodir").write_text("landuse", encoding="ascii")
    (sibling_wd / "soils.nodir").write_text("soils", encoding="ascii")
    (sibling_wd / "landuse.parquet").write_text("landuse-sidecar", encoding="ascii")
    (sibling_wd / "soils.parquet").write_text("soils-sidecar", encoding="ascii")

    projected_landuse = tmp_path / "projected-landuse"
    projected_soils = tmp_path / "projected-soils"
    projected_landuse.mkdir()
    projected_soils.mkdir()
    (projected_landuse / "landuse.txt").write_text("landuse", encoding="ascii")
    (projected_soils / "soils.txt").write_text("soils", encoding="ascii")

    monkeypatch.setattr(omni_module, "copy_version_for_clone", lambda src, dst: None)
    monkeypatch.setattr(omni_module, "_clear_nodb_cache_and_locks", lambda runid, pup_relpath=None: None)

    def _resolve(wd: str, rel: str, view: str = "effective"):
        if Path(wd).resolve() == sibling_wd.resolve() and rel in {"landuse", "soils"}:
            return types.SimpleNamespace(form="archive")
        return None

    @contextmanager
    def _projection(wd: str, root: str, *, mode: str, purpose: str):
        assert Path(wd).resolve() == sibling_wd.resolve()
        assert mode == "read"
        if root == "landuse":
            yield types.SimpleNamespace(mount_path=str(projected_landuse))
            return
        if root == "soils":
            yield types.SimpleNamespace(mount_path=str(projected_soils))
            return
        raise AssertionError(root)

    monkeypatch.setattr(omni_module, "nodir_resolve", _resolve)
    monkeypatch.setattr(omni_module, "with_root_projection", _projection)

    omni_module._omni_clone_sibling(str(new_wd), "sibling", runid="run-123", parent_wd=str(parent_wd))

    assert (new_wd / "disturbed" / "disturbed.txt").read_text(encoding="ascii") == "disturbed"
    assert (new_wd / "landuse" / "landuse.txt").read_text(encoding="ascii") == "landuse"
    assert (new_wd / "soils" / "soils.txt").read_text(encoding="ascii") == "soils"
    assert (new_wd / "landuse.parquet").read_text(encoding="ascii") == "landuse-sidecar"
    assert not (new_wd / "landuse.parquet").is_symlink()
    assert (new_wd / "soils.parquet").read_text(encoding="ascii") == "soils-sidecar"
    assert not (new_wd / "soils.parquet").is_symlink()

    for name in ("disturbed", "landuse", "soils"):
        payload = json.loads((new_wd / f"{name}.nodb").read_text(encoding="ascii"))
        assert payload["wd"] == str(new_wd)


def test_run_contrast_copies_archive_landuse_and_soils(tmp_path: Path, omni_module, monkeypatch):
    wd = tmp_path / "run"
    (wd / "climate").mkdir(parents=True)
    (wd / "watershed").mkdir(parents=True)
    (wd / "wepp" / "runs").mkdir(parents=True)
    (wd / "wepp" / "output").mkdir(parents=True)
    (wd / "wepp" / "runs" / "H1.run").write_text("run", encoding="ascii")

    (wd / "landuse.nodir").write_text("landuse", encoding="ascii")
    (wd / "soils.nodir").write_text("soils", encoding="ascii")
    (wd / "climate.wepp_cli.parquet").write_text("climate-sidecar", encoding="ascii")
    (wd / "watershed.hillslopes.parquet").write_text("hillslope-sidecar", encoding="ascii")
    (wd / "watershed.channels.parquet").write_text("channel-sidecar", encoding="ascii")

    projected_landuse = tmp_path / "contrast-projected-landuse"
    projected_soils = tmp_path / "contrast-projected-soils"
    projected_landuse.mkdir()
    projected_soils.mkdir()
    (projected_landuse / "landuse.txt").write_text("landuse", encoding="ascii")
    (projected_soils / "soils.txt").write_text("soils", encoding="ascii")

    monkeypatch.setattr(omni_module, "copy_version_for_clone", lambda src, dst: None)
    monkeypatch.setattr(omni_module, "_clear_nodb_cache_and_locks", lambda runid, pup_relpath=None: None)
    monkeypatch.setattr(omni_module, "_resolve_base_scenario_key", lambda wd: "undisturbed")
    monkeypatch.setattr(omni_module, "pick_existing_parquet_path", lambda *_args, **_kwargs: "/tmp/mock.parquet")
    monkeypatch.setattr(omni_module, "_merge_contrast_parquet", lambda **kwargs: None)
    monkeypatch.setattr(omni_module, "_apply_contrast_output_triggers", lambda *args, **kwargs: None)
    monkeypatch.setattr(omni_module, "_post_watershed_run_cleanup", lambda *args, **kwargs: None)

    def _resolve(wd_path: str, rel: str, view: str = "effective"):
        if wd_path == str(wd) and rel in {"landuse", "soils"}:
            return types.SimpleNamespace(form="archive")
        return None

    @contextmanager
    def _projection(wd_path: str, root: str, *, mode: str, purpose: str):
        assert wd_path == str(wd)
        assert mode == "read"
        if root == "landuse":
            yield types.SimpleNamespace(mount_path=str(projected_landuse))
            return
        if root == "soils":
            yield types.SimpleNamespace(mount_path=str(projected_soils))
            return
        raise AssertionError(root)

    monkeypatch.setattr(omni_module, "nodir_resolve", _resolve)
    monkeypatch.setattr(omni_module, "with_root_projection", _projection)

    class DummyWepp:
        def __init__(self, run_wd: str):
            self.runs_dir = str(Path(run_wd) / "wepp" / "runs")
            self.output_dir = str(Path(run_wd) / "wepp" / "output")
            self.baseflow_opts = object()
            self.wepp_interchange_dir = str(Path(run_wd) / "wepp" / "output" / "interchange")
            self.wepp_bin = None

        def clean(self):
            Path(self.runs_dir).mkdir(parents=True, exist_ok=True)
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        def make_watershed_run(self, **kwargs):
            return None

        def run_watershed(self):
            return None

        def report_loss(self):
            return None

    import wepppy.nodb.core as nodb_core

    monkeypatch.setattr(nodb_core.Wepp, "getInstance", lambda run_wd: DummyWepp(run_wd))

    new_wd = Path(
        omni_module._run_contrast(
            contrast_id="1",
            contrast_name="demo",
            contrasts={10: str(wd / "wepp" / "output" / "H1")},
            wd=str(wd),
            runid="run-123",
            control_scenario_key="undisturbed",
            contrast_scenario_key="undisturbed",
        )
    )

    assert (new_wd / "landuse" / "landuse.txt").read_text(encoding="ascii") == "landuse"
    assert (new_wd / "soils" / "soils.txt").read_text(encoding="ascii") == "soils"
    assert (new_wd / "climate.wepp_cli.parquet").is_symlink()
    assert os.readlink(new_wd / "climate.wepp_cli.parquet") == str(wd / "climate.wepp_cli.parquet")
    assert (new_wd / "watershed.hillslopes.parquet").is_symlink()
    assert os.readlink(new_wd / "watershed.hillslopes.parquet") == str(wd / "watershed.hillslopes.parquet")
    assert (new_wd / "watershed.channels.parquet").is_symlink()
    assert os.readlink(new_wd / "watershed.channels.parquet") == str(wd / "watershed.channels.parquet")


def test_run_contrast_copies_directory_landuse_and_soils(tmp_path: Path, omni_module, monkeypatch):
    wd = tmp_path / "run"
    (wd / "climate").mkdir(parents=True)
    (wd / "watershed").mkdir(parents=True)
    (wd / "wepp" / "runs").mkdir(parents=True)
    (wd / "wepp" / "output").mkdir(parents=True)
    (wd / "wepp" / "runs" / "H1.run").write_text("run", encoding="ascii")

    landuse_src = wd / "landuse"
    soils_src = wd / "soils"
    landuse_src.mkdir()
    soils_src.mkdir()
    (landuse_src / "landuse.txt").write_text("landuse", encoding="ascii")
    (soils_src / "soils.txt").write_text("soils", encoding="ascii")
    (wd / "landuse.parquet").write_text("landuse-sidecar", encoding="ascii")
    (wd / "soils.parquet").write_text("soils-sidecar", encoding="ascii")

    monkeypatch.setattr(omni_module, "copy_version_for_clone", lambda src, dst: None)
    monkeypatch.setattr(omni_module, "_clear_nodb_cache_and_locks", lambda runid, pup_relpath=None: None)
    monkeypatch.setattr(omni_module, "_resolve_base_scenario_key", lambda wd: "undisturbed")
    monkeypatch.setattr(omni_module, "pick_existing_parquet_path", lambda *_args, **_kwargs: "/tmp/mock.parquet")
    monkeypatch.setattr(omni_module, "_merge_contrast_parquet", lambda **kwargs: None)
    monkeypatch.setattr(omni_module, "_apply_contrast_output_triggers", lambda *args, **kwargs: None)
    monkeypatch.setattr(omni_module, "_post_watershed_run_cleanup", lambda *args, **kwargs: None)

    def _resolve(wd_path: str, rel: str, view: str = "effective"):
        if wd_path == str(wd) and rel in {"landuse", "soils"}:
            return types.SimpleNamespace(
                form="dir",
                dir_path=str(wd),
                inner_path=rel,
            )
        return None

    monkeypatch.setattr(omni_module, "nodir_resolve", _resolve)

    class DummyWepp:
        def __init__(self, run_wd: str):
            self.runs_dir = str(Path(run_wd) / "wepp" / "runs")
            self.output_dir = str(Path(run_wd) / "wepp" / "output")
            self.baseflow_opts = object()
            self.wepp_interchange_dir = str(Path(run_wd) / "wepp" / "output" / "interchange")
            self.wepp_bin = None

        def clean(self):
            Path(self.runs_dir).mkdir(parents=True, exist_ok=True)
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        def make_watershed_run(self, **kwargs):
            return None

        def run_watershed(self):
            return None

        def report_loss(self):
            return None

    import wepppy.nodb.core as nodb_core

    monkeypatch.setattr(nodb_core.Wepp, "getInstance", lambda run_wd: DummyWepp(run_wd))

    new_wd = Path(
        omni_module._run_contrast(
            contrast_id="1",
            contrast_name="demo",
            contrasts={10: str(wd / "wepp" / "output" / "H1")},
            wd=str(wd),
            runid="run-123",
            control_scenario_key="undisturbed",
            contrast_scenario_key="undisturbed",
        )
    )

    assert (new_wd / "landuse" / "landuse.txt").read_text(encoding="ascii") == "landuse"
    assert (new_wd / "soils" / "soils.txt").read_text(encoding="ascii") == "soils"
    assert (new_wd / "landuse.parquet").read_text(encoding="ascii") == "landuse-sidecar"
    assert not (new_wd / "landuse.parquet").is_symlink()
    assert (new_wd / "soils.parquet").read_text(encoding="ascii") == "soils-sidecar"
    assert not (new_wd / "soils.parquet").is_symlink()


def test_run_contrast_rewrites_legacy_omni_prefix_when_pass_dat_exists(
    tmp_path: Path,
    omni_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    (wd / "climate").mkdir(parents=True)
    (wd / "watershed").mkdir(parents=True)
    (wd / "wepp" / "runs").mkdir(parents=True)
    (wd / "wepp" / "output").mkdir(parents=True)

    monkeypatch.setattr(omni_module, "copy_version_for_clone", lambda src, dst: None)
    monkeypatch.setattr(omni_module, "_clear_nodb_cache_and_locks", lambda runid, pup_relpath=None: None)
    monkeypatch.setattr(omni_module, "nodir_resolve", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(omni_module, "_resolve_base_scenario_key", lambda wd: "undisturbed")
    monkeypatch.setattr(omni_module, "_resolve_contrast_scenario_wd", lambda wd, *_args, **_kwargs: wd)
    monkeypatch.setattr(omni_module, "_contrast_topaz_ids_from_mapping", lambda mapping, _wd: list(mapping.keys()))

    landuse_parquet = tmp_path / "landuse.parquet"
    soils_parquet = tmp_path / "soils.parquet"
    landuse_parquet.write_text("landuse", encoding="ascii")
    soils_parquet.write_text("soils", encoding="ascii")

    def _pick_parquet(_wd: str, rel: str):
        if rel.startswith("landuse/"):
            return landuse_parquet
        if rel.startswith("soils/"):
            return soils_parquet
        raise AssertionError(rel)

    monkeypatch.setattr(omni_module, "pick_existing_parquet_path", _pick_parquet)
    monkeypatch.setattr(omni_module, "_merge_contrast_parquet", lambda **_kwargs: None)
    monkeypatch.setattr(omni_module, "_apply_contrast_output_triggers", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(omni_module, "_post_watershed_run_cleanup", lambda *_args, **_kwargs: None)

    old_path = str(wd / "omni" / "scenarios" / "uniform_low" / "wepp" / "output" / "H1")
    candidate = str(wd / "_pups" / "omni" / "scenarios" / "uniform_low" / "wepp" / "output" / "H1")
    Path(candidate).parent.mkdir(parents=True, exist_ok=True)
    Path(f"{candidate}.pass.dat").write_text("pass", encoding="ascii")

    captured: dict[str, object] = {}

    class DummyWepp:
        def __init__(self, run_wd: str):
            self.runs_dir = str(Path(run_wd) / "wepp" / "runs")
            self.output_dir = str(Path(run_wd) / "wepp" / "output")
            self.wepp_bin = None

        def clean(self):
            Path(self.runs_dir).mkdir(parents=True, exist_ok=True)
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        def make_watershed_run(self, *, wepp_id_paths, output_options):
            captured["wepp_id_paths"] = list(wepp_id_paths)
            captured["output_options"] = dict(output_options)

        def run_watershed(self):
            return None

        def report_loss(self):
            return None

    import wepppy.nodb.core as nodb_core

    monkeypatch.setattr(nodb_core.Wepp, "getInstance", lambda run_wd: DummyWepp(run_wd))

    omni_module._run_contrast(
        contrast_id="1",
        contrast_name="demo",
        contrasts={10: old_path},
        wd=str(wd),
        runid="run-123",
        control_scenario_key="uniform_low",
        contrast_scenario_key="uniform_low",
        output_options={},
    )

    assert captured["wepp_id_paths"] == [candidate]


def test_omni_clone_sibling_rejects_path_traversal(tmp_path: Path, omni_module):
    parent_wd = tmp_path / "run"
    new_wd = parent_wd / "_pups" / "omni" / "scenarios" / "target"
    new_wd.mkdir(parents=True)

    with pytest.raises(ValueError, match="Invalid sibling scenario key"):
        omni_module._omni_clone_sibling(
            str(new_wd),
            "../escape",
            runid="run-123",
            parent_wd=str(parent_wd),
        )


def test_run_contrast_retries_archive_projection_lock_contention(
    tmp_path: Path,
    omni_module,
    monkeypatch,
):
    from wepppy.nodir.errors import nodir_locked

    wd = tmp_path / "run"
    (wd / "climate").mkdir(parents=True)
    (wd / "watershed").mkdir(parents=True)
    (wd / "wepp" / "runs").mkdir(parents=True)
    (wd / "wepp" / "output").mkdir(parents=True)
    (wd / "wepp" / "runs" / "H1.run").write_text("run", encoding="ascii")

    (wd / "landuse.nodir").write_text("landuse", encoding="ascii")
    (wd / "soils.nodir").write_text("soils", encoding="ascii")

    projected_landuse = tmp_path / "retry-projected-landuse"
    projected_soils = tmp_path / "retry-projected-soils"
    projected_landuse.mkdir()
    projected_soils.mkdir()
    (projected_landuse / "landuse.txt").write_text("landuse", encoding="ascii")
    (projected_soils / "soils.txt").write_text("soils", encoding="ascii")

    monkeypatch.setattr(omni_module, "copy_version_for_clone", lambda src, dst: None)
    monkeypatch.setattr(omni_module, "_clear_nodb_cache_and_locks", lambda runid, pup_relpath=None: None)
    monkeypatch.setattr(omni_module, "_resolve_base_scenario_key", lambda wd: "undisturbed")
    monkeypatch.setattr(omni_module, "pick_existing_parquet_path", lambda *_args, **_kwargs: "/tmp/mock.parquet")
    monkeypatch.setattr(omni_module, "_merge_contrast_parquet", lambda **kwargs: None)
    monkeypatch.setattr(omni_module, "_apply_contrast_output_triggers", lambda *args, **kwargs: None)
    monkeypatch.setattr(omni_module, "_post_watershed_run_cleanup", lambda *args, **kwargs: None)
    monkeypatch.setattr(omni_module, "sleep", lambda _seconds: None)

    def _resolve(wd_path: str, rel: str, view: str = "effective"):
        if wd_path == str(wd) and rel in {"landuse", "soils"}:
            return types.SimpleNamespace(form="archive")
        return None

    projection_failures = {"landuse": 1, "soils": 1}

    @contextmanager
    def _projection(wd_path: str, root: str, *, mode: str, purpose: str):
        assert wd_path == str(wd)
        assert mode == "read"
        if projection_failures[root] > 0:
            projection_failures[root] -= 1
            raise nodir_locked("NoDir projection lock is currently held")
        if root == "landuse":
            yield types.SimpleNamespace(mount_path=str(projected_landuse))
            return
        if root == "soils":
            yield types.SimpleNamespace(mount_path=str(projected_soils))
            return
        raise AssertionError(root)

    monkeypatch.setattr(omni_module, "nodir_resolve", _resolve)
    monkeypatch.setattr(omni_module, "with_root_projection", _projection)

    class DummyWepp:
        def __init__(self, run_wd: str):
            self.runs_dir = str(Path(run_wd) / "wepp" / "runs")
            self.output_dir = str(Path(run_wd) / "wepp" / "output")
            self.baseflow_opts = object()
            self.wepp_interchange_dir = str(Path(run_wd) / "wepp" / "output" / "interchange")
            self.wepp_bin = None

        def clean(self):
            Path(self.runs_dir).mkdir(parents=True, exist_ok=True)
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        def make_watershed_run(self, **kwargs):
            return None

        def run_watershed(self):
            return None

        def report_loss(self):
            return None

    import wepppy.nodb.core as nodb_core

    monkeypatch.setattr(nodb_core.Wepp, "getInstance", lambda run_wd: DummyWepp(run_wd))

    new_wd = Path(
        omni_module._run_contrast(
            contrast_id="1",
            contrast_name="demo",
            contrasts={10: str(wd / "wepp" / "output" / "H1")},
            wd=str(wd),
            runid="run-123",
            control_scenario_key="undisturbed",
            contrast_scenario_key="undisturbed",
        )
    )

    assert projection_failures == {"landuse": 0, "soils": 0}
    assert (new_wd / "landuse" / "landuse.txt").read_text(encoding="ascii") == "landuse"
    assert (new_wd / "soils" / "soils.txt").read_text(encoding="ascii") == "soils"
