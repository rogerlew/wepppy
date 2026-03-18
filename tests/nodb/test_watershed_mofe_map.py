from __future__ import annotations

import logging
from contextlib import nullcontext
from pathlib import Path

import numpy as np
import pytest

from wepppy.nodb.core import watershed_mixins as watershed_mixins_module


class _DummyWatershed(watershed_mixins_module.WatershedOperationsMixin):
    class_name = "DummyWatershed"

    def __init__(self, wat_dir: Path) -> None:
        self.wat_dir = str(wat_dir)
        self.subwta = str(wat_dir / "subwta.tif")
        self.discha = str(wat_dir / "discha.tif")
        self.logger = logging.getLogger("tests.nodb.test_watershed_mofe_map")
        self._mofe_target_length = 50.0
        self._mofe_buffer = False
        self._mofe_buffer_length = 15.0
        self._mofe_max_ofes = 19
        self._subs_summary = {"171": {"fname": "hill_171.slp"}}

    def locked(self):
        return nullcontext()

    @property
    def subs_summary(self):
        return self._subs_summary


@pytest.mark.unit
def test_build_mofe_map_repairs_non_contiguous_ids(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    watershed = _DummyWatershed(tmp_path)
    subwta = np.array([[171, 171, 171, 171]], dtype=np.int32)
    discha = np.array([[5, 5, 5, 5]], dtype=np.int32)

    def _fake_read_raster(path: str, dtype: np.dtype[np.int32] = np.int32):  # noqa: ARG001
        if path == watershed.subwta:
            return subwta, (0.0, 1.0, 0.0, 0.0, 0.0, -1.0), "+proj=longlat"
        if path == watershed.discha:
            return discha, (0.0, 1.0, 0.0, 0.0, 0.0, -1.0), "+proj=longlat"
        raise AssertionError(path)

    monkeypatch.setattr(watershed_mixins_module, "read_raster", _fake_read_raster)
    monkeypatch.setattr(
        watershed_mixins_module,
        "mofe_distance_fractions",
        lambda _path: np.array([0.0, 0.34, 0.67, 1.0], dtype=np.float64),
    )

    sink: dict[str, np.ndarray] = {}

    class _FakeBand:
        def WriteArray(self, values: np.ndarray) -> None:
            sink["values"] = np.array(values, copy=True)

    class _FakeDataset:
        def SetProjection(self, _wkt: str) -> None:
            return None

        def SetGeoTransform(self, _transform) -> None:
            return None

        def GetRasterBand(self, _index: int) -> _FakeBand:
            return _FakeBand()

    class _FakeDriver:
        def Create(self, path: str, _num_cols: int, _num_rows: int, _bands: int, _dtype: int) -> _FakeDataset:
            Path(path).touch()
            return _FakeDataset()

    class _FakeSpatialReference:
        def ImportFromProj4(self, _proj4: str) -> None:
            return None

        def ExportToWkt(self) -> str:
            return "WKT"

    monkeypatch.setattr(watershed_mixins_module.gdal, "GetDriverByName", lambda _name: _FakeDriver())
    monkeypatch.setattr(watershed_mixins_module.osr, "SpatialReference", _FakeSpatialReference)

    watershed._build_mofe_map()

    repaired_map = sink["values"].T
    repaired_ids = {int(value) for value in np.unique(repaired_map[subwta == 171])}
    assert repaired_ids == {1, 2, 3}


@pytest.mark.unit
def test_build_multiple_ofe_caps_segments_by_hillslope_cells(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    watershed = _DummyWatershed(tmp_path)
    subwta = np.array([[171, 171], [0, 0]], dtype=np.int32)
    recorded: dict[str, int] = {}

    monkeypatch.setattr(
        watershed_mixins_module,
        "read_raster",
        lambda _path, dtype=np.int32: (subwta, None, None),  # noqa: ARG005
    )

    class _FakeSlopeFile:
        def __init__(self, _fname: str) -> None:
            return None

        def segmented_multiple_ofe(self, **kwargs) -> int:
            recorded["max_ofes"] = int(kwargs["max_ofes"])
            return int(kwargs["max_ofes"])

    monkeypatch.setattr(watershed_mixins_module, "SlopeFile", _FakeSlopeFile)
    monkeypatch.setattr(watershed, "_build_mofe_map", lambda: None)

    watershed._build_multiple_ofe()

    assert recorded["max_ofes"] == 2
    assert watershed.mofe_nsegments == {"171": 2}
