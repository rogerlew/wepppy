from __future__ import annotations

from types import SimpleNamespace

import pytest

from wepppy.nodb.core.watershed import Watershed


@pytest.mark.unit
def test_watershed_dem_fn_delegates_to_ron(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = "/wc1/runs/demo/dem/dem.tif"
    monkeypatch.setattr(
        Watershed,
        "ron_instance",
        property(lambda _self: SimpleNamespace(dem_fn=expected)),
    )

    watershed = Watershed.__new__(Watershed)

    assert watershed.dem_fn == expected


@pytest.mark.unit
def test_watershed_wsarea_falls_back_to_component_areas_when_missing() -> None:
    watershed = Watershed.__new__(Watershed)
    watershed._wsarea = None
    watershed._sub_area = 12.0
    watershed._chn_area = 3.5

    assert watershed.wsarea == pytest.approx(15.5)
