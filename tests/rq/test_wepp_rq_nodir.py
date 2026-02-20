from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

import wepppy.rq.wepp_rq as wepp_rq
from wepppy.nodir.errors import NoDirError

pytestmark = pytest.mark.unit


def _stub_job_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wepp_rq, "get_current_job", lambda: SimpleNamespace(id="job-1"))
    monkeypatch.setattr(wepp_rq, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(wepp_rq.StatusMessenger, "publish", lambda channel, message: None)


class _DummyWatershed:
    clip_hillslopes = True
    clip_hillslope_length = 42.0

    def translator_factory(self):
        return "translator"


def _assert_no_mutate_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    def _should_not_mutate(*_args, **_kwargs):
        raise AssertionError("read-only stage should not call mutate_roots")

    monkeypatch.setattr(wepp_rq, "mutate_roots", _should_not_mutate, raising=False)


def test_recover_mixed_nodir_roots_discards_dir_and_keeps_archive(tmp_path) -> None:
    wd = tmp_path
    mixed_root = wd / "watershed"
    (mixed_root / "slope_files" / "hillslopes").mkdir(parents=True, exist_ok=True)
    (mixed_root / "slope_files" / "hillslopes" / "hill_22.slp").write_text("partial\n", encoding="utf-8")
    (wd / "watershed.nodir").write_text("archive", encoding="utf-8")

    # Non-mixed roots should be ignored.
    (wd / "climate").mkdir(parents=True, exist_ok=True)
    (wd / "soils.nodir").write_text("archive", encoding="utf-8")

    recovered = wepp_rq._recover_mixed_nodir_roots(str(wd))

    assert recovered == ("watershed",)
    assert not mixed_root.exists()
    assert (wd / "watershed.nodir").exists()


def test_prep_slopes_calls_wepp_directly_without_mutation_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_job_context(monkeypatch)
    _assert_no_mutate_roots(monkeypatch)
    calls: list[tuple[object, ...]] = []

    class DummyWepp:
        def _prep_slopes(self, translator, clip_hillslopes, clip_hillslope_length):
            calls.append(("prep_slopes", translator, clip_hillslopes, clip_hillslope_length))

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_rq.Watershed, "getInstance", lambda wd: _DummyWatershed())

    wepp_rq._prep_slopes_rq("run-1")

    assert calls == [("prep_slopes", "translator", True, 42.0)]


def test_prep_slopes_legacy_wepp_rq_patch_points_remain_compatible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, ...]] = []

    monkeypatch.setattr(wepp_rq, "get_current_job", lambda: SimpleNamespace(id="job-1"))
    monkeypatch.setattr(wepp_rq, "get_wd", lambda _runid: "/tmp/run")
    monkeypatch.setattr(wepp_rq.StatusMessenger, "publish", lambda _channel, _message: None)
    monkeypatch.setattr(wepp_rq, "resolve", lambda _wd, _rel, view="effective": None)

    class DummyWepp:
        def _prep_slopes(self, translator, clip_hillslopes, clip_hillslope_length):
            calls.append(("prep_slopes", translator, clip_hillslopes, clip_hillslope_length))

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda _wd: DummyWepp())
    monkeypatch.setattr(wepp_rq.Watershed, "getInstance", lambda _wd: _DummyWatershed())

    wepp_rq._prep_slopes_rq("run-1")

    assert calls == [("prep_slopes", "translator", True, 42.0)]


def test_run_flowpaths_calls_wepp_directly_without_mutation_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_job_context(monkeypatch)
    _assert_no_mutate_roots(monkeypatch)
    calls: list[str] = []

    class DummyWepp:
        def prep_and_run_flowpaths(self):
            calls.append("flowpaths")

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())

    wepp_rq._run_flowpaths_rq("run-1")

    assert calls == ["flowpaths"]


def test_prep_multi_ofe_calls_wepp_directly_without_mutation_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_job_context(monkeypatch)
    _assert_no_mutate_roots(monkeypatch)
    calls: list[tuple[str, object]] = []

    class DummyWepp:
        def _prep_multi_ofe(self, translator):
            calls.append(("prep_multi_ofe", translator))

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_rq.Watershed, "getInstance", lambda wd: _DummyWatershed())

    wepp_rq._prep_multi_ofe_rq("run-1")

    assert calls == [("prep_multi_ofe", "translator")]


def test_prep_managements_calls_wepp_directly_without_mutation_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_job_context(monkeypatch)
    _assert_no_mutate_roots(monkeypatch)
    calls: list[tuple[str, object]] = []

    class DummyWepp:
        def _prep_managements(self, translator):
            calls.append(("prep_managements", translator))

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_rq.Watershed, "getInstance", lambda wd: _DummyWatershed())

    wepp_rq._prep_managements_rq("run-1")

    assert calls == [("prep_managements", "translator")]


def test_prep_soils_calls_wepp_directly_without_mutation_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_job_context(monkeypatch)
    _assert_no_mutate_roots(monkeypatch)
    calls: list[tuple[str, object]] = []

    class DummyWepp:
        def _prep_soils(self, translator):
            calls.append(("prep_soils", translator))

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_rq.Watershed, "getInstance", lambda wd: _DummyWatershed())

    wepp_rq._prep_soils_rq("run-1")

    assert calls == [("prep_soils", "translator")]


def test_prep_climates_calls_wepp_directly_without_mutation_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_job_context(monkeypatch)
    _assert_no_mutate_roots(monkeypatch)
    calls: list[tuple[str, object]] = []

    class DummyWepp:
        def _prep_climates(self, translator):
            calls.append(("prep_climates", translator))

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_rq.Watershed, "getInstance", lambda wd: _DummyWatershed())

    wepp_rq._prep_climates_rq("run-1")

    assert calls == [("prep_climates", "translator")]


def test_prep_remaining_calls_wepp_directly_without_mutation_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_job_context(monkeypatch)
    _assert_no_mutate_roots(monkeypatch)
    calls: list[tuple[object, ...]] = []

    class DummyWepp:
        wd = "/tmp/run"
        run_frost = False
        run_baseflow = False
        run_wepp_ui = False
        run_pmet = False
        run_snow = False

        def _make_hillslope_runs(self, translator, reveg=False):
            calls.append(("make_hillslope_runs", translator, reveg))

        def _remove_frost(self):
            calls.append(("remove_frost",))

        def _prep_phosphorus(self):
            calls.append(("prep_phosphorus",))

        def _remove_baseflow(self):
            calls.append(("remove_baseflow",))

        def _remove_wepp_ui(self):
            calls.append(("remove_wepp_ui",))

        def _remove_pmet(self):
            calls.append(("remove_pmet",))

        def _remove_snow(self):
            calls.append(("remove_snow",))

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_rq.Watershed, "getInstance", lambda wd: _DummyWatershed())
    monkeypatch.setattr(wepp_rq.Disturbed, "getInstance", lambda wd, allow_nonexistent=False: None)

    wepp_rq._prep_remaining_rq("run-1")

    assert calls[0] == ("make_hillslope_runs", "translator", False)
    assert ("prep_phosphorus",) in calls


def test_prep_watershed_calls_wepp_directly_without_mutation_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_job_context(monkeypatch)
    _assert_no_mutate_roots(monkeypatch)
    calls: list[str] = []

    class DummyWepp:
        def prep_watershed(self):
            calls.append("prep_watershed")

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())

    wepp_rq._prep_watershed_rq("run-1")

    assert calls == ["prep_watershed"]


def test_prep_slopes_wraps_call_in_projection_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_job_context(monkeypatch)
    _assert_no_mutate_roots(monkeypatch)

    stage_state = {"active": False}
    lifecycle: list[tuple[str, str]] = []

    @contextmanager
    def _projection_ctx(_wd: str, root: str, *, mode: str, purpose: str):
        assert mode == "read"
        lifecycle.append(("enter", root))
        stage_state["active"] = True
        try:
            yield SimpleNamespace(mount_path=f"/tmp/run/{root}")
        finally:
            lifecycle.append(("exit", root))
            stage_state["active"] = False

    class DummyWepp:
        def _prep_slopes(self, translator, clip_hillslopes, clip_hillslope_length):
            assert stage_state["active"]
            assert translator == "translator"
            assert clip_hillslopes is True
            assert clip_hillslope_length == 42.0

    monkeypatch.setattr(wepp_rq, "resolve", lambda wd, rel, view="effective": object() if rel == "watershed" and view == "archive" else None)
    monkeypatch.setattr(wepp_rq, "with_root_projection", _projection_ctx)
    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_rq.Watershed, "getInstance", lambda wd: _DummyWatershed())

    wepp_rq._prep_slopes_rq("run-1")

    assert lifecycle == [("enter", "watershed"), ("exit", "watershed")]


def test_run_flowpaths_releases_projection_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_job_context(monkeypatch)
    _assert_no_mutate_roots(monkeypatch)

    stage_state = {"active": False}
    lifecycle: list[tuple[str, str]] = []

    @contextmanager
    def _projection_ctx(_wd: str, root: str, *, mode: str, purpose: str):
        assert mode == "read"
        lifecycle.append(("enter", root))
        stage_state["active"] = True
        try:
            yield SimpleNamespace(mount_path=f"/tmp/run/{root}")
        finally:
            lifecycle.append(("exit", root))
            stage_state["active"] = False

    class DummyWepp:
        def prep_and_run_flowpaths(self):
            assert stage_state["active"]
            raise RuntimeError("flowpath failure")

    monkeypatch.setattr(wepp_rq, "resolve", lambda wd, rel, view="effective": object() if rel == "watershed" and view == "archive" else None)
    monkeypatch.setattr(wepp_rq, "with_root_projection", _projection_ctx)
    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())

    with pytest.raises(RuntimeError, match="flowpath failure"):
        wepp_rq._run_flowpaths_rq("run-1")

    assert lifecycle == [("enter", "watershed"), ("exit", "watershed")]
    assert stage_state["active"] is False


def test_stage_projection_wrapper_raises_mixed_state_when_unmanaged_root_exists(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wepp_rq, "get_current_job", lambda: SimpleNamespace(id="job-1"))
    monkeypatch.setattr(wepp_rq, "get_wd", lambda runid: str(tmp_path))
    monkeypatch.setattr(wepp_rq.StatusMessenger, "publish", lambda channel, message: None)
    _assert_no_mutate_roots(monkeypatch)

    (tmp_path / "watershed").mkdir(parents=True, exist_ok=True)
    (tmp_path / "watershed.nodir").write_text("archive", encoding="utf-8")

    def _fail_projection(*_args, **_kwargs):
        raise AssertionError("with_root_projection should not run for unmanaged mixed state")

    class DummyWepp:
        def _prep_slopes(self, translator, clip_hillslopes, clip_hillslope_length):
            raise AssertionError("wepp stage should not execute when mixed state is detected")

    monkeypatch.setattr(wepp_rq, "resolve", lambda wd, rel, view="effective": object() if rel == "watershed" and view == "archive" else None)
    monkeypatch.setattr(wepp_rq, "with_root_projection", _fail_projection)
    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_rq.Watershed, "getInstance", lambda wd: _DummyWatershed())

    with pytest.raises(NoDirError) as exc:
        wepp_rq._prep_slopes_rq("run-1")

    assert exc.value.http_status == 409
    assert exc.value.code == "NODIR_MIXED_STATE"


def test_prep_watershed_projection_wrapper_raises_mixed_state_when_unmanaged_root_exists(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wepp_rq, "get_current_job", lambda: SimpleNamespace(id="job-1"))
    monkeypatch.setattr(wepp_rq, "get_wd", lambda runid: str(tmp_path))
    monkeypatch.setattr(wepp_rq.StatusMessenger, "publish", lambda channel, message: None)
    _assert_no_mutate_roots(monkeypatch)

    (tmp_path / "watershed").mkdir(parents=True, exist_ok=True)
    (tmp_path / "watershed.nodir").write_text("archive", encoding="utf-8")

    def _fail_projection(*_args, **_kwargs):
        raise AssertionError("with_root_projection should not run for unmanaged mixed state")

    class DummyWepp:
        def prep_watershed(self):
            raise AssertionError("prep_watershed should not execute when mixed state is detected")

    monkeypatch.setattr(wepp_rq, "resolve", lambda wd, rel, view="effective": object() if rel == "watershed" and view == "archive" else None)
    monkeypatch.setattr(wepp_rq, "with_root_projection", _fail_projection)
    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())

    with pytest.raises(NoDirError) as exc:
        wepp_rq._prep_watershed_rq("run-1")

    assert exc.value.http_status == 409
    assert exc.value.code == "NODIR_MIXED_STATE"
