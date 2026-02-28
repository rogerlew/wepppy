from __future__ import annotations

from contextlib import contextmanager
import shutil
from types import SimpleNamespace

import pytest

import wepppy.rq.land_and_soil_rq as land_and_soil_rq

pytestmark = pytest.mark.unit


def test_require_directory_root_rejects_archive_form(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        land_and_soil_rq,
        "nodir_resolve",
        lambda _wd, _root, view="effective": SimpleNamespace(form="archive"),
    )

    with pytest.raises(land_and_soil_rq.NoDirError) as exc_info:
        land_and_soil_rq._require_directory_root("/tmp/run", "landuse")

    assert exc_info.value.code == "NODIR_ARCHIVE_ACTIVE"


def test_run_with_directory_root_lock_executes_callback_for_directory_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolve_calls: list[tuple[str, str]] = []
    lock_events: list[tuple[str, str, str]] = []

    def _resolve(_wd: str, root: str, view: str = "effective"):
        resolve_calls.append((root, view))
        return SimpleNamespace(form="dir")

    @contextmanager
    def _lock(_wd: str, root: str, *, purpose: str):
        lock_events.append(("enter", root, purpose))
        yield
        lock_events.append(("exit", root, purpose))

    monkeypatch.setattr(land_and_soil_rq, "nodir_resolve", _resolve)
    monkeypatch.setattr(land_and_soil_rq, "nodir_maintenance_lock", _lock)

    callback_calls: list[str] = []
    result = land_and_soil_rq._run_with_directory_root_lock(
        "/tmp/run",
        "landuse",
        lambda: callback_calls.append("called") or "ok",
        purpose="unit-land-soil",
    )

    assert result == "ok"
    assert callback_calls == ["called"]
    assert resolve_calls == [
        ("landuse", "effective"),
        ("landuse", "effective"),
    ]
    assert lock_events == [
        ("enter", "landuse", "unit-land-soil"),
        ("exit", "landuse", "unit-land-soil"),
    ]


def test_land_and_soil_rq_aborts_before_landuse_build_on_archive_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = "unit-nodir-guard"
    target_wd = land_and_soil_rq.Path("/wc1/land_and_soil_rq") / job_id

    monkeypatch.setattr(land_and_soil_rq, "get_current_job", lambda: SimpleNamespace(id=job_id))
    monkeypatch.setattr(land_and_soil_rq.StatusMessenger, "publish", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        land_and_soil_rq,
        "nodir_resolve",
        lambda _wd, _root, view="effective": SimpleNamespace(form="archive"),
    )

    class RonStub:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

        def set_map(self, *_args, **_kwargs) -> None:
            return None

    class LanduseStub:
        mode = None
        nlcd_db = None

        def build(self) -> None:
            raise AssertionError("landuse.build should not be called")

    class SoilsStub:
        mode = None
        ssurgo_db = None

        def build(self) -> None:
            raise AssertionError("soils.build should not be called")

    monkeypatch.setattr(land_and_soil_rq, "Ron", RonStub)
    monkeypatch.setattr(land_and_soil_rq.Landuse, "getInstance", lambda _wd: LanduseStub())
    monkeypatch.setattr(land_and_soil_rq.Soils, "getInstance", lambda _wd: SoilsStub())

    try:
        with pytest.raises(land_and_soil_rq.NoDirError) as exc_info:
            land_and_soil_rq.land_and_soil_rq(
                runid="demo",
                extent=(0.0, 0.0, 1.0, 1.0),
                cfg="disturbed9002",
                nlcd_db=None,
                ssurgo_db=None,
            )
        assert exc_info.value.code == "NODIR_ARCHIVE_ACTIVE"
    finally:
        shutil.rmtree(target_wd, ignore_errors=True)


def test_land_and_soil_rq_aborts_on_soils_guard_after_landuse_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = "unit-nodir-soils-guard"
    target_wd = land_and_soil_rq.Path("/wc1/land_and_soil_rq") / job_id

    monkeypatch.setattr(land_and_soil_rq, "get_current_job", lambda: SimpleNamespace(id=job_id))
    monkeypatch.setattr(land_and_soil_rq.StatusMessenger, "publish", lambda *_args, **_kwargs: None)

    def _resolve(_wd: str, root: str, view: str = "effective"):
        if root == "soils":
            return SimpleNamespace(form="archive")
        return SimpleNamespace(form="dir")

    monkeypatch.setattr(land_and_soil_rq, "nodir_resolve", _resolve)

    class RonStub:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

        def set_map(self, *_args, **_kwargs) -> None:
            return None

    class LanduseStub:
        mode = None
        nlcd_db = None

        def __init__(self) -> None:
            self.build_calls = 0

        def build(self) -> None:
            self.build_calls += 1

    class SoilsStub:
        mode = None
        ssurgo_db = None

        def build(self) -> None:
            raise AssertionError("soils.build should not be called")

    landuse_stub = LanduseStub()
    monkeypatch.setattr(land_and_soil_rq, "Ron", RonStub)
    monkeypatch.setattr(land_and_soil_rq.Landuse, "getInstance", lambda _wd: landuse_stub)
    monkeypatch.setattr(land_and_soil_rq.Soils, "getInstance", lambda _wd: SoilsStub())

    try:
        with pytest.raises(land_and_soil_rq.NoDirError) as exc_info:
            land_and_soil_rq.land_and_soil_rq(
                runid="demo",
                extent=(0.0, 0.0, 1.0, 1.0),
                cfg="disturbed9002",
                nlcd_db=None,
                ssurgo_db=None,
            )
        assert exc_info.value.code == "NODIR_ARCHIVE_ACTIVE"
        assert landuse_stub.build_calls == 1
    finally:
        shutil.rmtree(target_wd, ignore_errors=True)
