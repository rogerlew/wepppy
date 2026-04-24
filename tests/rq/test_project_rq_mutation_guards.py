from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.rq.project_rq as project_rq
from wepppy.runtime_paths.errors import NoDirError

pytestmark = pytest.mark.unit


def _stub_rq_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    run_wd = tmp_path / "run"
    run_wd.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(project_rq, "get_wd", lambda _runid: str(run_wd))
    monkeypatch.setattr(project_rq, "get_current_job", lambda: SimpleNamespace(id="job-guard"))
    monkeypatch.setattr(project_rq.StatusMessenger, "publish", lambda *_args, **_kwargs: None)
    archive_roots: set[str] = set()
    call_roots: list[str] = []

    def _set_archive_roots(*roots: str) -> None:
        archive_roots.clear()
        archive_roots.update(roots)

    def _resolve(_wd: str, root: str, view: str = "effective"):
        call_roots.append(root)
        if root in archive_roots:
            raise NoDirError(
                http_status=409,
                code="NODIR_ARCHIVE_RETIRED",
                message=f"{root}.nodir exists but archive-backed runtime access is retired",
            )
        return SimpleNamespace(form="dir")

    monkeypatch.setattr(project_rq, "nodir_resolve", _resolve)
    return run_wd, _set_archive_roots, call_roots


def test_build_channels_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("watershed")
    monkeypatch.setattr(
        project_rq.Watershed,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Watershed should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.build_channels_rq(
            "demo",
            csa=10.0,
            mcl=50.0,
            stream_pruning_method=None,
            wbt_fill_or_breach=None,
            wbt_blc_dist=None,
        )

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["watershed"]


def test_build_landuse_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("landuse")
    monkeypatch.setattr(
        project_rq.Landuse,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Landuse should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.build_landuse_rq("demo")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["landuse"]


def test_modify_landuse_mapping_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("landuse")
    monkeypatch.setattr(
        project_rq.Landuse,
        "getInstance",
        lambda _wd, ignore_lock=False: (_ for _ in ()).throw(
            AssertionError("Landuse should not be loaded when root is archive-backed")
        ),
    )

    class DummyPrep:
        def get_rq_job_id(self, key: str):
            return "job-guard"

    monkeypatch.setattr(project_rq.RedisPrep, "getInstance", lambda _wd: DummyPrep())

    with pytest.raises(NoDirError) as exc_info:
        project_rq.modify_landuse_mapping_rq("demo", "44", "71")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["landuse"]


def test_modify_landuse_mapping_rq_publishes_trigger_and_mutates_landuse(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, _set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )
    monkeypatch.setattr(project_rq, "get_current_job", lambda: SimpleNamespace(id="job-latest"))

    class DummyPrep:
        def get_rq_job_id(self, key: str):
            return "job-latest"

    monkeypatch.setattr(project_rq.RedisPrep, "getInstance", lambda _wd: DummyPrep())
    cleared_cache: list[tuple[str, str | None]] = []
    monkeypatch.setattr(
        project_rq,
        "clear_nodb_file_cache",
        lambda runid, pup_relpath=None: cleared_cache.append((runid, pup_relpath)),
    )

    class DummyLanduse:
        def __init__(self):
            self.calls: list[tuple[str, str]] = []

        def modify_mapping(self, dom: str, newdom: str) -> None:
            self.calls.append((dom, newdom))

    landuse = DummyLanduse()

    def _get_landuse(_wd: str, ignore_lock: bool = False):
        assert ignore_lock is True
        assert cleared_cache == [("demo", "landuse.nodb")]
        return landuse

    monkeypatch.setattr(
        project_rq.Landuse,
        "getInstance",
        _get_landuse,
    )
    monkeypatch.setattr(
        project_rq.Landuse,
        "load_detached",
        lambda _wd, allow_nonexistent=True: (_ for _ in ()).throw(
            AssertionError("modify_landuse_mapping_rq should not use load_detached")
        ),
    )

    project_rq.modify_landuse_mapping_rq("demo", "44", "71")

    assert cleared_cache == [("demo", "landuse.nodb")]
    assert landuse.calls == [("44", "71")]
    assert call_roots == ["landuse", "landuse"]
    assert any("LANDUSE_MODIFY_MAPPING_TASK_COMPLETED" in message for _channel, message in published)


def test_modify_landuse_mapping_rq_skips_stale_job_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, _set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )
    monkeypatch.setattr(project_rq, "get_current_job", lambda: SimpleNamespace(id="job-stale"))

    class DummyPrep:
        def get_rq_job_id(self, key: str):
            return "job-latest"

    monkeypatch.setattr(project_rq.RedisPrep, "getInstance", lambda _wd: DummyPrep())
    monkeypatch.setattr(
        project_rq.Landuse,
        "getInstance",
        lambda _wd, ignore_lock=False: (_ for _ in ()).throw(
            AssertionError("Stale jobs should not mutate landuse")
        ),
    )

    project_rq.modify_landuse_mapping_rq("demo", "44", "71")

    assert call_roots == []
    assert any("SKIPPED" in message for _channel, message in published)
    assert all("LANDUSE_MODIFY_MAPPING_TASK_COMPLETED" not in message for _channel, message in published)


def test_build_treatments_rq_rejects_archive_form_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("landuse", "soils")
    monkeypatch.setattr(
        project_rq.Treatments,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Treatments should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.build_treatments_rq("demo")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["landuse"]


def test_build_climate_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("climate")
    monkeypatch.setattr(
        project_rq.Climate,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Climate should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.build_climate_rq("demo")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["climate"]


def test_build_soils_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("soils")
    monkeypatch.setattr(
        project_rq.Soils,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Soils should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.build_soils_rq("demo")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["soils"]


def test_set_outlet_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("watershed")
    monkeypatch.setattr(
        project_rq.Watershed,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Watershed should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.set_outlet_rq("demo", outlet_lng=-112.0, outlet_lat=44.0)

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["watershed"]


def test_build_subcatchments_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("watershed")
    monkeypatch.setattr(
        project_rq.Watershed,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Watershed should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.build_subcatchments_rq("demo")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["watershed"]


def test_abstract_watershed_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("watershed")
    monkeypatch.setattr(
        project_rq.Watershed,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Watershed should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.abstract_watershed_rq("demo")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["watershed"]


def test_abstract_watershed_rq_repairs_missing_persisted_centroid_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    monkeypatch.setattr(project_rq, "wait_for_path", lambda *_args, **_kwargs: None)

    class _WatershedStub:
        def __init__(self) -> None:
            self.abstract_calls = 0
            self.repair_calls = 0
            self.subwta = "dem/topaz/SUBWTA.ARC"
            self.logger = SimpleNamespace(warning=lambda *_args, **_kwargs: None)

        def abstract_watershed(self) -> None:
            self.abstract_calls += 1

        def require_centroid(self):
            self.repair_calls += 1
            return (-116.2, 43.6)

    watershed = _WatershedStub()
    monkeypatch.setattr(project_rq.Watershed, "getInstance", lambda _wd: watershed)

    persisted_states = [
        SimpleNamespace(centroid=None),
        SimpleNamespace(centroid=(-116.2, 43.6)),
    ]
    monkeypatch.setattr(
        project_rq.Watershed,
        "load_detached",
        lambda _wd, allow_nonexistent=True: persisted_states.pop(0),
    )

    prep_timestamps: list[object] = []

    class _PrepStub:
        def timestamp(self, task):
            prep_timestamps.append(task)

    monkeypatch.setattr(project_rq.RedisPrep, "getInstance", lambda _wd: _PrepStub())

    project_rq.abstract_watershed_rq("demo")

    assert watershed.abstract_calls == 1
    assert watershed.repair_calls == 1
    assert prep_timestamps == [project_rq.TaskEnum.abstract_watershed]


def test_abstract_watershed_rq_fails_when_centroid_still_missing_after_repair(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    monkeypatch.setattr(project_rq, "wait_for_path", lambda *_args, **_kwargs: None)

    class _WatershedStub:
        def __init__(self) -> None:
            self.abstract_calls = 0
            self.repair_calls = 0
            self.subwta = "dem/topaz/SUBWTA.ARC"
            self.logger = SimpleNamespace(warning=lambda *_args, **_kwargs: None)

        def abstract_watershed(self) -> None:
            self.abstract_calls += 1

        def require_centroid(self):
            self.repair_calls += 1
            return (-116.2, 43.6)

    watershed = _WatershedStub()
    monkeypatch.setattr(project_rq.Watershed, "getInstance", lambda _wd: watershed)
    monkeypatch.setattr(
        project_rq.Watershed,
        "load_detached",
        lambda _wd, allow_nonexistent=True: SimpleNamespace(centroid=None),
    )

    with pytest.raises(project_rq.WatershedCentroidStateError):
        project_rq.abstract_watershed_rq("demo")

    assert watershed.abstract_calls == 1
    assert watershed.repair_calls == 1


def test_upload_cli_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("climate")
    monkeypatch.setattr(
        project_rq.Climate,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Climate should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.upload_cli_rq("demo", "my.cli")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["climate"]


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

    monkeypatch.setattr(project_rq, "nodir_resolve", _resolve)
    monkeypatch.setattr(project_rq, "nodir_maintenance_lock", _lock)

    callback_calls: list[str] = []
    result = project_rq._run_with_directory_root_lock(
        "/tmp/run",
        "watershed",
        lambda: callback_calls.append("called") or "ok",
        purpose="unit-root-lock",
    )

    assert result == "ok"
    assert callback_calls == ["called"]
    assert resolve_calls == [
        ("watershed", "effective"),
        ("watershed", "effective"),
    ]
    assert lock_events == [
        ("enter", "watershed", "unit-root-lock"),
        ("exit", "watershed", "unit-root-lock"),
    ]


def test_run_with_directory_root_lock_retries_nodir_locked_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_rq, "DIRECTORY_ROOT_LOCK_RETRY_ATTEMPTS", 3)
    monkeypatch.setattr(project_rq, "DIRECTORY_ROOT_LOCK_RETRY_SECONDS", 0.0)
    monkeypatch.setattr(project_rq, "nodir_resolve", lambda _wd, _root, view="effective": SimpleNamespace(form="dir"))

    attempts = {"count": 0}

    @contextmanager
    def _lock(_wd: str, _root: str, *, purpose: str):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise NoDirError(http_status=503, code="NODIR_LOCKED", message=f"busy ({purpose})")
        yield

    monkeypatch.setattr(project_rq, "nodir_maintenance_lock", _lock)

    callback_calls: list[str] = []
    result = project_rq._run_with_directory_root_lock(
        "/tmp/run",
        "watershed",
        lambda: callback_calls.append("called") or "ok",
        purpose="unit-root-lock-retry",
    )

    assert result == "ok"
    assert callback_calls == ["called"]
    assert attempts["count"] == 2


def test_run_with_directory_root_lock_does_not_retry_non_lock_nodir_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_rq, "DIRECTORY_ROOT_LOCK_RETRY_ATTEMPTS", 3)
    monkeypatch.setattr(project_rq, "DIRECTORY_ROOT_LOCK_RETRY_SECONDS", 0.0)
    monkeypatch.setattr(project_rq, "nodir_resolve", lambda _wd, _root, view="effective": SimpleNamespace(form="dir"))

    attempts = {"count": 0}

    @contextmanager
    def _lock(_wd: str, _root: str, *, purpose: str):
        attempts["count"] += 1
        raise NoDirError(
            http_status=409,
            code="NODIR_ARCHIVE_RETIRED",
            message=f"archive-backed ({purpose})",
        )
        yield

    monkeypatch.setattr(project_rq, "nodir_maintenance_lock", _lock)

    with pytest.raises(NoDirError) as exc_info:
        project_rq._run_with_directory_root_lock(
            "/tmp/run",
            "watershed",
            lambda: "ok",
            purpose="unit-root-lock-no-retry",
        )

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert attempts["count"] == 1


def test_run_with_directory_roots_lock_sorts_lock_order_and_rechecks_roots(
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

    monkeypatch.setattr(project_rq, "nodir_resolve", _resolve)
    monkeypatch.setattr(project_rq, "nodir_maintenance_lock", _lock)

    callback_calls: list[str] = []
    result = project_rq._run_with_directory_roots_lock(
        "/tmp/run",
        ("soils", "landuse", "soils"),
        lambda: callback_calls.append("called") or "ok",
        purpose="unit-roots-lock",
    )

    assert result == "ok"
    assert callback_calls == ["called"]
    assert resolve_calls == [
        ("landuse", "effective"),
        ("soils", "effective"),
        ("landuse", "effective"),
        ("soils", "effective"),
    ]
    assert lock_events == [
        ("enter", "landuse", "unit-roots-lock/landuse"),
        ("enter", "soils", "unit-roots-lock/soils"),
        ("exit", "soils", "unit-roots-lock/soils"),
        ("exit", "landuse", "unit-roots-lock/landuse"),
    ]


def test_run_with_directory_roots_lock_retries_nodir_locked_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_rq, "DIRECTORY_ROOT_LOCK_RETRY_ATTEMPTS", 3)
    monkeypatch.setattr(project_rq, "DIRECTORY_ROOT_LOCK_RETRY_SECONDS", 0.0)
    monkeypatch.setattr(project_rq, "nodir_resolve", lambda _wd, _root, view="effective": SimpleNamespace(form="dir"))

    lock_events: list[tuple[str, str]] = []
    contention_emitted = {"value": False}

    @contextmanager
    def _lock(_wd: str, root: str, *, purpose: str):
        lock_events.append((root, purpose))
        if not contention_emitted["value"]:
            contention_emitted["value"] = True
            raise NoDirError(http_status=503, code="NODIR_LOCKED", message="busy")
        yield

    monkeypatch.setattr(project_rq, "nodir_maintenance_lock", _lock)

    callback_calls: list[str] = []
    result = project_rq._run_with_directory_roots_lock(
        "/tmp/run",
        ("soils", "landuse"),
        lambda: callback_calls.append("called") or "ok",
        purpose="unit-roots-lock-retry",
    )

    assert result == "ok"
    assert callback_calls == ["called"]
    assert lock_events == [
        ("landuse", "unit-roots-lock-retry/landuse"),
        ("landuse", "unit-roots-lock-retry/landuse"),
        ("soils", "unit-roots-lock-retry/soils"),
    ]
