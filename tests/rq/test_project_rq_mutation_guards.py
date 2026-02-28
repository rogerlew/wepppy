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
        project_rq.build_channels_rq("demo", csa=10.0, mcl=50.0, wbt_fill_or_breach=None, wbt_blc_dist=None)

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
