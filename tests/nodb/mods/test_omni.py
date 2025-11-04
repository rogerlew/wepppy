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
