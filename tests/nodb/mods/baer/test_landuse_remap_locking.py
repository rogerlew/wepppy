from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.mods.baer.baer as baer_module
from wepppy.nodb.mods.baer.baer import Baer
from wepppy.nodb.core.landuse import LanduseMode

pytestmark = [pytest.mark.nodb, pytest.mark.unit]


class _FakeSbs:
    def __init__(self, domlc_d: dict[str, str]) -> None:
        self._domlc_d = dict(domlc_d)

    def build_lcgrid(self, _subwta: str, _mofe_map: object) -> dict[str, str]:
        return dict(self._domlc_d)


class _FakePopen:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        return

    def wait(self) -> int:
        return 0


class _FakeLanduse:
    _instance: "_FakeLanduse | None" = None

    def __init__(self) -> None:
        self.mode = LanduseMode.Gridded
        self.domlc_d = {"101": "original-dom"}
        self._lock_depth = 0
        self.build_managements_maps: list[str | None] = []

    @classmethod
    def getInstance(cls, _wd: str) -> "_FakeLanduse":
        assert cls._instance is not None
        return cls._instance

    @contextmanager
    def locked(self):
        self._lock_depth += 1
        try:
            yield
        finally:
            self._lock_depth -= 1

    def build_managements(self, _map: str | None = None) -> None:
        if self._lock_depth > 0:
            raise AssertionError("build_managements() called while landuse lock was still held")
        self.build_managements_maps.append(_map)


def test_remap_landuse_rebuilds_managements_after_unlock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baer = Baer.__new__(Baer)
    baer.wd = str(tmp_path)
    baer._baer_fn = "input_baer.tif"
    baer._breaks = [0, 1, 2, 3]
    baer._nodata_vals = None

    landuse = _FakeLanduse()
    _FakeLanduse._instance = landuse

    monkeypatch.setattr(baer_module, "Landuse", _FakeLanduse)
    monkeypatch.setattr(
        baer_module,
        "Watershed",
        SimpleNamespace(
            getInstance=lambda _wd: SimpleNamespace(
                subwta="subwta.tif",
                subs_summary={"101": object()},
            )
        ),
    )
    monkeypatch.setattr(
        baer_module,
        "Ron",
        SimpleNamespace(
            getInstance=lambda _wd: SimpleNamespace(
                map=SimpleNamespace(utm_extent=(0, 0, 1, 1), cellsize=1, srid=26911),
                mods=[],
            )
        ),
    )
    monkeypatch.setattr(baer_module, "Popen", _FakePopen)
    monkeypatch.setattr(
        baer_module,
        "_exists",
        lambda path: path == baer.baer_cropped,
    )
    monkeypatch.setattr(baer_module.os, "remove", lambda _path: None)
    monkeypatch.setattr(
        baer_module,
        "SoilBurnSeverityMap",
        lambda *_args, **_kwargs: _FakeSbs({"101": "131", "24": "132"}),
    )
    monkeypatch.setattr(Baer, "_calc_sbs_coverage", lambda self, _sbs: None)

    baer.remap_landuse()

    assert landuse.domlc_d == {"101": "131"}
    assert "24" not in landuse.domlc_d
    assert landuse.build_managements_maps == ["default"]
