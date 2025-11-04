import importlib
import logging
import sys
import types
from contextlib import contextmanager
from pathlib import Path

import pytest


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
    sys.modules.setdefault("utm", types.ModuleType("utm"))
    if "deprecated" not in sys.modules:
        deprecated_stub = types.ModuleType("deprecated")

        def _deprecated(*d_args, **d_kwargs):
            if d_args and callable(d_args[0]) and not d_kwargs:
                return d_args[0]

            def _decorator(func):
                return func

            return _decorator

        deprecated_stub.deprecated = _deprecated
        sys.modules["deprecated"] = deprecated_stub

    for name in [
        "wepppy.nodb",
        "wepppy.nodb.core",
        "wepppy.nodb.base",
        "wepppy.nodb.mods",
        "wepppy.nodb.mods.omni",
        "wepppy.export",
        "wepppy.export.gpkg_export",
    ]:
        sys.modules.pop(name, None)

    repo_root = Path(__file__).resolve().parents[3]
    nodb_path = repo_root / "wepppy" / "nodb"
    mods_path = nodb_path / "mods"
    omni_path = mods_path / "omni"

    _ensure_package("wepppy", repo_root / "wepppy")
    _ensure_package("wepppy.nodb", nodb_path)
    _ensure_package("wepppy.nodb.mods", mods_path)
    _ensure_package("wepppy.nodb.mods.omni", omni_path)

    export_stub = types.ModuleType("wepppy.export")
    export_stub.__path__ = []
    sys.modules["wepppy.export"] = export_stub

    gpkg_stub = types.ModuleType("wepppy.export.gpkg_export")

    def _gpkg_extract_objective_parameter(*args, **kwargs):
        return None

    gpkg_stub.gpkg_extract_objective_parameter = _gpkg_extract_objective_parameter
    gpkg_stub.__all__ = ["gpkg_extract_objective_parameter"]
    sys.modules["wepppy.export.gpkg_export"] = gpkg_stub
    export_stub.gpkg_export = gpkg_stub

    core_stub = types.ModuleType("wepppy.nodb.core")

    def _clear_cache_stub(*args, **kwargs):
        return []

    def _clear_locks_stub(*args, **kwargs):
        return None

    class _Ron:
        def __init__(self, *args, **kwargs):
            pass

    core_stub.clear_nodb_file_cache = _clear_cache_stub
    core_stub.clear_locks = _clear_locks_stub
    core_stub.Ron = _Ron
    core_stub.__all__ = ["clear_nodb_file_cache", "clear_locks", "Ron"]
    sys.modules["wepppy.nodb.core"] = core_stub

    base_stub = types.ModuleType("wepppy.nodb.base")

    class _NoDbBase:
        def __init__(self, *args, **kwargs):
            pass

        @contextmanager
        def locked(self):
            yield

    def _nodb_setter(func):
        return func

    base_stub.NoDbBase = _NoDbBase
    base_stub.nodb_setter = _nodb_setter
    base_stub.__all__ = ["NoDbBase", "nodb_setter"]
    sys.modules["wepppy.nodb.base"] = base_stub

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
        sys.modules["pyproj"] = pyproj_stub

    if "osgeo" not in sys.modules:
        gdal_stub = types.ModuleType("osgeo.gdal")

        def _use_exceptions():
            return None

        gdal_stub.UseExceptions = _use_exceptions

        osr_stub = types.ModuleType("osgeo.osr")
        ogr_stub = types.ModuleType("osgeo.ogr")
        osgeo_stub = types.ModuleType("osgeo")
        osgeo_stub.gdal = gdal_stub
        osgeo_stub.osr = osr_stub
        osgeo_stub.ogr = ogr_stub
        sys.modules["osgeo"] = osgeo_stub
        sys.modules["osgeo.gdal"] = gdal_stub
        sys.modules["osgeo.osr"] = osr_stub
        sys.modules["osgeo.ogr"] = ogr_stub

    if "rasterio" not in sys.modules:
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

        rasterio_stub = types.ModuleType("rasterio")
        rasterio_stub.warp = warp_stub
        sys.modules["rasterio"] = rasterio_stub
        sys.modules["rasterio.warp"] = warp_stub

    return importlib.import_module("wepppy.nodb.mods.omni.omni")


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
