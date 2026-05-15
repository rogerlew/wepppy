from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pytest

import wepppy.nodb.core.watershed_mixins as watershed_mixins_module
from wepppy.nodb.core.watershed import (
    OUTLET_LOCATION_CHANNELS_REQUIRED_MESSAGE,
    OUTLET_LOCATION_OUTSIDE_MAP_EXTENT_MESSAGE,
    Watershed,
    WatershedCentroidStateError,
)


class _LookupOnlyWatershed(watershed_mixins_module.WatershedLookupMixin):
    def __init__(self, wd: str) -> None:
        self.wd = wd
        self._centroid = None
        self._sub_area = None
        self._chn_area = None
        self._wsarea = None
        self._subs_summary = None
        self._chns_summary = None
        self._locked = False
        self.dump_calls = 0
        self.logger = SimpleNamespace(warning=lambda *_args, **_kwargs: None)

    @property
    def runid(self) -> str:
        return Path(self.wd).name

    def islocked(self) -> bool:
        return self._locked

    @contextmanager
    def locked(self):
        self._locked = True
        try:
            yield
            self.dump_calls += 1
        finally:
            self._locked = False

    def dump(self) -> None:
        self.dump_calls += 1


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


@pytest.mark.unit
def test_require_centroid_repairs_when_abstraction_artifacts_exist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    watershed = _LookupOnlyWatershed(str(tmp_path / "repairable-run"))

    monkeypatch.setattr(
        watershed_mixins_module,
        "post_abstract_watershed",
        lambda _wd: (12.5, 2.5, (-116.2, 43.6), [10, 11], [20]),
    )

    centroid = watershed.require_centroid()

    assert centroid == pytest.approx((-116.2, 43.6))
    assert watershed._centroid == pytest.approx((-116.2, 43.6))
    assert watershed._wsarea == pytest.approx(15.0)
    assert watershed._subs_summary == {"10": None, "11": None}
    assert watershed._chns_summary == {"20": None}
    assert watershed.dump_calls == 1


@pytest.mark.unit
def test_require_centroid_raises_typed_error_when_artifacts_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    watershed = _LookupOnlyWatershed(str(tmp_path / "missing-artifacts-run"))

    def _raise_missing(_wd: str):
        raise FileNotFoundError("hillslopes.parquet missing")

    monkeypatch.setattr(
        watershed_mixins_module,
        "post_abstract_watershed",
        _raise_missing,
    )

    with pytest.raises(WatershedCentroidStateError) as exc_info:
        watershed.require_centroid()

    message = str(exc_info.value)
    assert "runid=missing-artifacts-run" in message
    assert "centroid missing and repair from watershed abstraction artifacts failed" in message


@pytest.mark.unit
def test_validate_outlet_location_requires_delineated_channels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    watershed = Watershed.__new__(Watershed)

    monkeypatch.setattr(Watershed, "has_channels", property(lambda _self: False))

    with pytest.raises(ValueError, match=OUTLET_LOCATION_CHANNELS_REQUIRED_MESSAGE):
        watershed.validate_outlet_location(-117.5, 46.9)


@pytest.mark.unit
def test_validate_outlet_location_rejects_outside_wbt_extent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    watershed = Watershed.__new__(Watershed)
    watershed.logger = None

    monkeypatch.setattr(Watershed, "has_channels", property(lambda _self: True))
    monkeypatch.setattr(Watershed, "delineation_backend_is_wbt", property(lambda _self: True))

    class DummyWbt:
        @staticmethod
        def lnglat_to_pixel(
            _lng: float,
            _lat: float,
            logger: Optional[SimpleNamespace] = None,
        ) -> tuple[int, int]:
            raise AssertionError((1.0, 2.0))

    watershed._ensure_wbt = lambda: DummyWbt()  # type: ignore[method-assign]

    with pytest.raises(ValueError, match=OUTLET_LOCATION_OUTSIDE_MAP_EXTENT_MESSAGE):
        watershed.validate_outlet_location(-117.5, 46.9)


@pytest.mark.unit
def test_validate_outlet_location_rejects_outside_topaz_extent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    watershed = Watershed.__new__(Watershed)

    monkeypatch.setattr(Watershed, "has_channels", property(lambda _self: True))
    monkeypatch.setattr(Watershed, "delineation_backend_is_wbt", property(lambda _self: False))

    class DummyMap:
        @staticmethod
        def lnglat_to_px(_lng: float, _lat: float) -> tuple[int, int]:
            raise ValueError("latitude out of range")

    class DummyRon:
        map = DummyMap()

    monkeypatch.setattr(Watershed, "ron_instance", property(lambda _self: DummyRon()))

    with pytest.raises(ValueError, match=OUTLET_LOCATION_OUTSIDE_MAP_EXTENT_MESSAGE):
        watershed.validate_outlet_location(-117.5, 95.0)


@pytest.mark.unit
def test_validate_outlet_location_uses_topaz_ron_map_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    watershed = Watershed.__new__(Watershed)
    calls = {"map_lnglat_to_px": 0}

    monkeypatch.setattr(Watershed, "has_channels", property(lambda _self: True))
    monkeypatch.setattr(Watershed, "delineation_backend_is_wbt", property(lambda _self: False))

    class DummyMap:
        @staticmethod
        def lnglat_to_px(_lng: float, _lat: float) -> tuple[int, int]:
            calls["map_lnglat_to_px"] += 1
            return (1, 1)

    class DummyRon:
        map = DummyMap()

    monkeypatch.setattr(Watershed, "ron_instance", property(lambda _self: DummyRon()))

    watershed.validate_outlet_location(-117.5, 46.9)

    assert calls["map_lnglat_to_px"] == 1
