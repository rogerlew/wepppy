from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.rq.culvert_rq as culvert_rq

pytestmark = pytest.mark.unit


def test_require_directory_root_rejects_archive_form(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        culvert_rq,
        "nodir_resolve",
        lambda _wd, _root, view="effective": SimpleNamespace(form="archive"),
    )

    with pytest.raises(culvert_rq.NoDirError) as exc_info:
        culvert_rq._require_directory_root("/tmp/run", "watershed")

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

    monkeypatch.setattr(culvert_rq, "nodir_resolve", _resolve)
    monkeypatch.setattr(culvert_rq, "nodir_maintenance_lock", _lock)

    callback_calls: list[str] = []
    result = culvert_rq._run_with_directory_root_lock(
        "/tmp/run",
        "watershed",
        lambda: callback_calls.append("called") or "ok",
        purpose="culvert-unit",
    )

    assert result == "ok"
    assert callback_calls == ["called"]
    assert resolve_calls == [
        ("watershed", "effective"),
        ("watershed", "effective"),
    ]
    assert lock_events == [
        ("enter", "watershed", "culvert-unit"),
        ("exit", "watershed", "culvert-unit"),
    ]


def test_process_culvert_run_fails_before_mutation_when_directory_guard_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_wd = tmp_path / "run"
    run_wd.mkdir(parents=True, exist_ok=True)

    class WatershedStub:
        def _ensure_wbt(self):
            raise AssertionError("watershed mutation should not execute")

    class LanduseStub:
        def clean(self) -> None:
            raise AssertionError("landuse mutation should not execute")

    class SoilsStub:
        def clean(self) -> None:
            raise AssertionError("soils mutation should not execute")

    class ClimateStub:
        def build(self) -> None:
            raise AssertionError("climate build should not execute")

    class WeppStub:
        def clean(self) -> None:
            raise AssertionError("wepp should not execute")

    monkeypatch.setattr(culvert_rq.Watershed, "getInstance", lambda _wd: WatershedStub())
    monkeypatch.setattr(culvert_rq.Landuse, "getInstance", lambda _wd: LanduseStub())
    monkeypatch.setattr(culvert_rq.Soils, "getInstance", lambda _wd: SoilsStub())
    monkeypatch.setattr(culvert_rq.Climate, "getInstance", lambda _wd: ClimateStub())
    monkeypatch.setattr(culvert_rq.Wepp, "getInstance", lambda _wd: WeppStub())
    guard_calls: list[str] = []

    def _raise_for_watershed(_wd: str, root: str) -> None:
        guard_calls.append(root)
        if root == "watershed":
            raise culvert_rq.NoDirError(
                http_status=409,
                code="NODIR_ARCHIVE_ACTIVE",
                message="archive-backed",
            )

    metadata_calls: list[tuple[str, dict[str, object]]] = []

    monkeypatch.setattr(culvert_rq, "_require_directory_root", _raise_for_watershed)
    monkeypatch.setattr(
        culvert_rq,
        "_write_run_metadata",
        lambda _path, metadata: metadata_calls.append((str(_path), metadata)),
    )
    monkeypatch.setattr(culvert_rq, "skeletonize_run", lambda *_args, **_kwargs: None)

    status = culvert_rq._process_culvert_run(
        culvert_batch_uuid="batch-1",
        run_id="001",
        run_wd=run_wd,
        watershed_feature=SimpleNamespace(),
        run_config="disturbed9002",
        wepppy_version="test",
        nlcd_db_override=None,
        minimum_watershed_area_m2=None,
    )

    assert status == "failed"
    assert guard_calls == ["watershed"]
    assert len(metadata_calls) == 1
    assert metadata_calls[0][1]["status"] == "failed"


def test_process_culvert_run_forces_delete_after_interchange_off_for_culverts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_wd = tmp_path / "run"
    run_wd.mkdir(parents=True, exist_ok=True)
    batch_root = tmp_path / "batch"
    (batch_root / "landuse").mkdir(parents=True, exist_ok=True)
    (batch_root / "soils").mkdir(parents=True, exist_ok=True)
    (batch_root / "landuse" / "nlcd.tif").write_text("x", encoding="utf-8")
    (batch_root / "soils" / "ssurgo.tif").write_text("x", encoding="utf-8")

    class WatershedStub:
        pass

    class LanduseStub:
        pass

    class SoilsStub:
        pass

    class ClimateStub:
        def build(self) -> None:
            return None

    class WeppStub:
        def __init__(self) -> None:
            self.delete_after_interchange = True

        def clean(self) -> None:
            return None

        def prep_hillslopes(self) -> None:
            return None

        def run_hillslopes(self) -> None:
            return None

        def prep_watershed(self) -> None:
            return None

        def run_watershed(self) -> None:
            return None

    wepp_stub = WeppStub()
    metadata_calls: list[dict[str, object]] = []
    watershed_interchange_calls: list[bool] = []

    monkeypatch.setattr(culvert_rq.Watershed, "getInstance", lambda _wd: WatershedStub())
    monkeypatch.setattr(culvert_rq.Landuse, "getInstance", lambda _wd: LanduseStub())
    monkeypatch.setattr(culvert_rq.Soils, "getInstance", lambda _wd: SoilsStub())
    monkeypatch.setattr(culvert_rq.Climate, "getInstance", lambda _wd: ClimateStub())
    monkeypatch.setattr(culvert_rq.Wepp, "getInstance", lambda _wd: wepp_stub)
    monkeypatch.setattr(culvert_rq, "_resolve_batch_root", lambda _uuid: batch_root)
    monkeypatch.setattr(
        culvert_rq,
        "_run_with_directory_root_lock",
        lambda _wd, _root, _callback, *, purpose: None,
    )
    monkeypatch.setattr(
        culvert_rq,
        "_run_with_directory_roots_lock",
        lambda _wd, _roots, _callback, *, purpose: None,
    )
    monkeypatch.setattr(culvert_rq, "ensure_hillslope_interchange", lambda *_a, **_k: None)
    monkeypatch.setattr(culvert_rq, "ensure_totalwatsed3", lambda *_a, **_k: None)
    monkeypatch.setattr(
        culvert_rq,
        "ensure_watershed_interchange",
        lambda wepp, *_a, **_k: watershed_interchange_calls.append(
            bool(getattr(wepp, "delete_after_interchange", None))
        ),
    )
    monkeypatch.setattr(culvert_rq, "activate_query_engine_for_run", lambda *_a, **_k: None)
    monkeypatch.setattr(
        culvert_rq,
        "_write_run_metadata",
        lambda _path, metadata: metadata_calls.append(metadata),
    )
    monkeypatch.setattr(culvert_rq, "skeletonize_run", lambda *_args, **_kwargs: None)

    status = culvert_rq._process_culvert_run(
        culvert_batch_uuid="batch-1",
        run_id="001",
        run_wd=run_wd,
        watershed_feature=SimpleNamespace(),
        run_config="culvert.cfg",
        wepppy_version="test",
        nlcd_db_override=None,
        minimum_watershed_area_m2=None,
    )

    assert status == "success"
    assert wepp_stub.delete_after_interchange is False
    assert watershed_interchange_calls == [False]
    assert len(metadata_calls) == 1
    assert metadata_calls[0]["status"] == "success"
