from __future__ import annotations

import logging
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.core.soils import Soils

pytestmark = pytest.mark.unit


class _StopBuild(Exception):
    """Sentinel used to stop _build_gridded after pre-retrieve assertions."""


def test_build_gridded_creates_soils_dir_before_retrieve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    soils = Soils.__new__(Soils)
    soils.wd = str(wd)
    soils.logger = logging.getLogger("tests.nodb.soils_gridded")
    soils._soils_is_vrt = False
    soils._ssurgo_db = "ssurgo"
    soils._initial_sat = 0.75
    soils._ksflag = True

    soils.locked = lambda: nullcontext()
    soils.timed = lambda _label: nullcontext()
    soils.config_get_int = lambda *_args, **_kwargs: 1
    soils.config_get_str = lambda *_args, **_kwargs: None

    map_stub = SimpleNamespace(extent=(-116.1, 47.0, -116.0, 47.1), cellsize=30.0)
    watershed_stub = SimpleNamespace(subwta=str(wd / "watershed" / "subwta.tif"))

    monkeypatch.setattr(Soils, "ron_instance", property(lambda _self: SimpleNamespace(map=map_stub)))
    monkeypatch.setattr(Soils, "watershed_instance", property(lambda _self: watershed_stub))

    expected_soils_dir = wd / "soils"

    def _fake_wmesque_retrieve(*_args, **_kwargs):
        assert expected_soils_dir.is_dir(), "Soils directory must exist before ssurgo retrieval"
        raise _StopBuild()

    monkeypatch.setattr("wepppy.nodb.core.soils.wmesque_retrieve", _fake_wmesque_retrieve)

    with pytest.raises(_StopBuild):
        soils._build_gridded()

    assert expected_soils_dir.is_dir()
