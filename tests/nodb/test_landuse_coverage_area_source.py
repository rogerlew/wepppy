from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from wepppy.nodb.core.landuse import Landuse

pytestmark = pytest.mark.unit


def test_build_managements_uses_watershed_hillslope_area_for_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(wd)
    landuse._mapping = "test-mapping"
    landuse.domlc_d = {"11": "forest", "12": "range"}
    landuse.managements = None
    landuse.locked = lambda: nullcontext()
    landuse.dump_landuse_parquet = lambda: None
    landuse.trigger = lambda *_args, **_kwargs: None

    map_stub = SimpleNamespace(cellsize=30.0)

    hillslope_area_calls: list[str] = []

    class _WatershedStub:
        subwta = str(wd / "watershed" / "subwta.tif")

        @staticmethod
        def hillslope_area(topaz_id: str) -> float:
            topaz_id = str(topaz_id)
            hillslope_area_calls.append(topaz_id)
            return {"11": 6.0, "12": 4.0}[topaz_id]

    monkeypatch.setattr(
        Landuse,
        "ron_instance",
        property(lambda _self: map_stub),
    )
    monkeypatch.setattr(
        Landuse,
        "watershed_instance",
        property(lambda _self: _WatershedStub()),
    )
    monkeypatch.setattr(
        Landuse,
        "wepp_instance",
        property(lambda _self: SimpleNamespace(_multi_ofe=False)),
    )

    def _fake_read_raster(_path: str, dtype: type[np.int32]):
        # Deliberately mismatched from hillslope_area() to ensure coverage no longer
        # comes from subwta pixel counts for this path.
        subwta = np.array([[11, 11, 11, 11, 11, 11, 11, 11, 11, 12]], dtype=dtype)
        return subwta, None, None

    monkeypatch.setattr("wepppy.nodb.core.landuse.read_raster", _fake_read_raster)

    class _ManagementSummaryStub:
        def __init__(self) -> None:
            self.area = 0.0
            self.pct_coverage = 0.0

    monkeypatch.setattr(
        "wepppy.nodb.core.landuse.get_management_summary",
        lambda *_args, **_kwargs: _ManagementSummaryStub(),
    )

    landuse.build_managements()

    assert hillslope_area_calls == ["11", "12"]
    assert landuse.managements["forest"].area == pytest.approx(6.0)
    assert landuse.managements["range"].area == pytest.approx(4.0)
    assert landuse.managements["forest"].pct_coverage == pytest.approx(60.0)
    assert landuse.managements["range"].pct_coverage == pytest.approx(40.0)
