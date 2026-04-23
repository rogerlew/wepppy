from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.core.watershed_mixins as watershed_mixins_module
from wepppy.nodb.core.watershed import Watershed
from wepppy.nodb.core.watershed import WatershedCentroidStateError


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
