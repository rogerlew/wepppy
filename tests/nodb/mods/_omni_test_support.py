"""Shared setup for detached Omni controller tests."""

import sys
import types
from contextlib import contextmanager

import pytest



@pytest.fixture
def omni_module(monkeypatch):
    from wepppy.nodb.mods.omni import omni

    # These detached controllers model legacy runs and bypass NoDb initialization.
    monkeypatch.setattr(
        omni.Omni,
        "config_get_str",
        lambda self, section, option, default=None: default,
    )
    return omni


@contextmanager
def _noop_lock():
    yield


class Rect:
    geom_type = "Polygon"

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
