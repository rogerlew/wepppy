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
