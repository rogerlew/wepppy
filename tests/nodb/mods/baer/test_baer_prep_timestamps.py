from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest

import wepppy.nodb.mods.baer.baer as baer_module
from wepppy.nodb.mods.baer.baer import Baer

pytestmark = [pytest.mark.nodb, pytest.mark.unit]


@contextmanager
def _null_context() -> None:
    yield


class _PrepRecorder:
    def __init__(self) -> None:
        self.timestamps: list[object] = []
        self.has_sbs: bool | None = None

    def timestamp(self, task: object) -> None:
        self.timestamps.append(task)


def test_modify_burn_class_updates_landuse_and_sbs_timestamps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baer = Baer.__new__(Baer)
    baer.wd = str(tmp_path)
    baer._breaks = [0, 1, 2, 3]
    baer._nodata_vals = None

    prep = _PrepRecorder()

    monkeypatch.setattr(Baer, "locked", lambda self, validate_on_success=True: _null_context())
    monkeypatch.setattr(Baer, "write_color_table", lambda self: None)
    monkeypatch.setattr(Baer, "build_color_map", lambda self: None)
    monkeypatch.setattr(
        baer_module.RedisPrep,
        "getInstance",
        staticmethod(lambda _wd: prep),
    )

    baer.modify_burn_class([0, 1, 2, 3], None)

    assert prep.timestamps == [
        baer_module.TaskEnum.landuse_map,
        baer_module.TaskEnum.init_sbs_map,
    ]
    assert prep.has_sbs is True
