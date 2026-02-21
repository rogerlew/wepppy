from __future__ import annotations

import logging
import sys
import types
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pytest

import wepppy.nodb.mods.omni.omni as omni_module
from wepppy.nodb.mods.omni.omni_contrast_build_service import OmniContrastBuildService

pytestmark = pytest.mark.unit


@contextmanager
def _noop_lock():
    yield


class Rect:
    def __init__(self, xmin: float, ymin: float, xmax: float, ymax: float):
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
        left, bottom, right, top = bounds
        results = []
        for idx, row in enumerate(self._rows):
            geom = row.get("geometry")
            if geom is None:
                continue
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

    @property
    def empty(self):
        return not self._rows

    def __len__(self):
        return len(self._rows)

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


def _ensure_package(name: str, path: Path | None):
    if name in sys.modules:
        return sys.modules[name]
    module = types.ModuleType(name)
    if path is not None:
        module.__path__ = [str(path)]
    sys.modules[name] = module
    return module


def _stub_user_defined_geodata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    hillslope_rows,
    user_rows,
) -> Path:
    hillslope_path = tmp_path / "subwta.geojson"
    user_geojson_path = tmp_path / "areas.geojson"
    hillslope_path.write_text("{}", encoding="ascii")
    user_geojson_path.write_text("{}", encoding="ascii")

    hillslope_gdf = DummyGeoDataFrame(hillslope_rows, crs="EPSG:32611")
    user_gdf = DummyGeoDataFrame(user_rows, crs=None)

    geopandas_stub = types.ModuleType("geopandas")
    geopandas_stub.read_file = lambda path: hillslope_gdf if str(path) == str(hillslope_path) else user_gdf
    monkeypatch.setitem(sys.modules, "geopandas", geopandas_stub)

    class DummyTranslator:
        top2wepp = {"10": "1", "20": "2"}

    class DummyWatershed:
        subwta_utm_shp = str(hillslope_path)

        def translator_factory(self):
            return DummyTranslator()

    class DummyRon:
        srid = "32611"

    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(omni_module.Ron, "getInstance", lambda wd: DummyRon())
    monkeypatch.setattr(omni_module.NoDbBase, "has_sbs", property(lambda self: False))
    return user_geojson_path


def test_build_contrasts_stream_order_service_groups_hillslopes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = OmniContrastBuildService()
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

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.contrast_build_service.stream_order")
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        {"control_scenario": "uniform_low", "contrast_scenario": "thinning"},
    ]
    omni._contrast_order_reduction_passes = 1

    service.build_contrasts_stream_order(omni)

    assert omni.contrast_names[:4] == [
        "uniform_low,1__to__mulch",
        "uniform_low,2__to__thinning",
        "uniform_low,3__to__mulch",
        "uniform_low,4__to__thinning",
    ]
    assert omni.contrast_names[4:] == [None, None]


def test_build_contrasts_user_defined_areas_service_builds_sidecars(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniContrastBuildService()
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
        tmp_path,
        hillslope_rows=hillslope_rows,
        user_rows=user_rows,
    )

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.contrast_build_service.user_defined")
    omni._contrast_geojson_path = str(user_geojson_path)
    omni._contrast_geojson_name_key = "name"
    omni._contrast_pairs = [{"control_scenario": "uniform_low", "contrast_scenario": "mulch"}]
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None

    service.build_contrasts_user_defined_areas(omni)

    assert omni.contrast_names == [
        "uniform_low,1__to__mulch",
        "uniform_low,2__to__mulch",
        None,
    ]
    assert omni._contrast_labels == {1: "Alpha", 2: "2", 3: "Gamma"}
    assert Path(omni._contrast_sidecar_path(1)).exists()
    assert Path(omni._contrast_sidecar_path(2)).exists()
    assert not Path(omni._contrast_sidecar_path(3)).exists()
