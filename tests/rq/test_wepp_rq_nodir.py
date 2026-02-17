from __future__ import annotations

from types import SimpleNamespace

import pytest

import wepppy.rq.wepp_rq as wepp_rq

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


def test_prep_slopes_uses_watershed_mutation_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_job_context(monkeypatch)
    calls: list[tuple[object, ...]] = []

    class DummyWepp:
        def _prep_slopes(self, translator, clip_hillslopes, clip_hillslope_length):
            calls.append(("prep_slopes", translator, clip_hillslopes, clip_hillslope_length))

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_rq.Watershed, "getInstance", lambda wd: _DummyWatershed())

    mutation_calls: list[tuple[str, str]] = []

    def _fake_mutate_root(wd, root, callback, *, purpose="nodir-mutation"):
        mutation_calls.append((root, purpose))
        callback()

    monkeypatch.setattr(wepp_rq, "mutate_root", _fake_mutate_root)

    wepp_rq._prep_slopes_rq("run-1")

    assert mutation_calls == [("watershed", "prep-slopes-rq")]
    assert calls == [("prep_slopes", "translator", True, 42.0)]


def test_run_flowpaths_uses_watershed_mutation_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_job_context(monkeypatch)
    calls: list[str] = []

    class DummyWepp:
        def prep_and_run_flowpaths(self):
            calls.append("flowpaths")

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())

    mutation_calls: list[tuple[str, str]] = []

    def _fake_mutate_root(wd, root, callback, *, purpose="nodir-mutation"):
        mutation_calls.append((root, purpose))
        callback()

    monkeypatch.setattr(wepp_rq, "mutate_root", _fake_mutate_root)

    wepp_rq._run_flowpaths_rq("run-1")

    assert mutation_calls == [("watershed", "run-flowpaths-rq")]
    assert calls == ["flowpaths"]


def test_prep_multi_ofe_uses_all_required_nodir_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_job_context(monkeypatch)
    calls: list[tuple[str, object]] = []

    class DummyWepp:
        def _prep_multi_ofe(self, translator):
            calls.append(("prep_multi_ofe", translator))

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_rq.Watershed, "getInstance", lambda wd: _DummyWatershed())

    mutation_calls: list[tuple[tuple[str, ...], str]] = []

    def _fake_mutate_roots(wd, roots, callback, *, purpose="nodir-mutation"):
        mutation_calls.append((tuple(roots), purpose))
        callback()

    monkeypatch.setattr(wepp_rq, "mutate_roots", _fake_mutate_roots)

    wepp_rq._prep_multi_ofe_rq("run-1")

    assert mutation_calls == [(("climate", "landuse", "soils", "watershed"), "prep-multi-ofe-rq")]
    assert calls == [("prep_multi_ofe", "translator")]


def test_prep_managements_uses_all_required_nodir_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_job_context(monkeypatch)
    calls: list[tuple[str, object]] = []

    class DummyWepp:
        def _prep_managements(self, translator):
            calls.append(("prep_managements", translator))

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_rq.Watershed, "getInstance", lambda wd: _DummyWatershed())

    mutation_calls: list[tuple[tuple[str, ...], str]] = []

    def _fake_mutate_roots(wd, roots, callback, *, purpose="nodir-mutation"):
        mutation_calls.append((tuple(roots), purpose))
        callback()

    monkeypatch.setattr(wepp_rq, "mutate_roots", _fake_mutate_roots)

    wepp_rq._prep_managements_rq("run-1")

    assert mutation_calls == [(("climate", "landuse", "soils", "watershed"), "prep-managements-rq")]
    assert calls == [("prep_managements", "translator")]


def test_prep_remaining_uses_climate_and_watershed_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_job_context(monkeypatch)
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

    mutation_calls: list[tuple[tuple[str, ...], str]] = []

    def _fake_mutate_roots(wd, roots, callback, *, purpose="nodir-mutation"):
        mutation_calls.append((tuple(roots), purpose))
        callback()

    monkeypatch.setattr(wepp_rq, "mutate_roots", _fake_mutate_roots)

    wepp_rq._prep_remaining_rq("run-1")

    assert mutation_calls == [(("climate", "watershed"), "prep-remaining-rq")]
    assert calls[0] == ("make_hillslope_runs", "translator", False)
    assert ("prep_phosphorus",) in calls


def test_prep_watershed_uses_all_required_nodir_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_job_context(monkeypatch)
    calls: list[str] = []

    class DummyWepp:
        def prep_watershed(self):
            calls.append("prep_watershed")

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())

    mutation_calls: list[tuple[tuple[str, ...], str]] = []

    def _fake_mutate_roots(wd, roots, callback, *, purpose="nodir-mutation"):
        mutation_calls.append((tuple(roots), purpose))
        callback()

    monkeypatch.setattr(wepp_rq, "mutate_roots", _fake_mutate_roots)

    wepp_rq._prep_watershed_rq("run-1")

    assert mutation_calls == [(("climate", "landuse", "soils", "watershed"), "prep-watershed-rq")]
    assert calls == ["prep_watershed"]


def test_prep_soils_uses_soils_and_watershed_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_job_context(monkeypatch)
    calls: list[tuple[str, object]] = []

    class DummyWepp:
        def _prep_soils(self, translator):
            calls.append(("prep_soils", translator))

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_rq.Watershed, "getInstance", lambda wd: _DummyWatershed())

    mutation_calls: list[tuple[tuple[str, ...], str]] = []

    def _fake_mutate_roots(wd, roots, callback, *, purpose="nodir-mutation"):
        mutation_calls.append((tuple(roots), purpose))
        callback()

    monkeypatch.setattr(wepp_rq, "mutate_roots", _fake_mutate_roots)

    wepp_rq._prep_soils_rq("run-1")

    assert mutation_calls == [(("soils", "watershed"), "prep-soils-rq")]
    assert calls == [("prep_soils", "translator")]


def test_prep_climates_uses_climate_and_watershed_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_job_context(monkeypatch)
    calls: list[tuple[str, object]] = []

    class DummyWepp:
        def _prep_climates(self, translator):
            calls.append(("prep_climates", translator))

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_rq.Watershed, "getInstance", lambda wd: _DummyWatershed())

    mutation_calls: list[tuple[tuple[str, ...], str]] = []

    def _fake_mutate_roots(wd, roots, callback, *, purpose="nodir-mutation"):
        mutation_calls.append((tuple(roots), purpose))
        callback()

    monkeypatch.setattr(wepp_rq, "mutate_roots", _fake_mutate_roots)

    wepp_rq._prep_climates_rq("run-1")

    assert mutation_calls == [(("climate", "watershed"), "prep-climates-rq")]
    assert calls == [("prep_climates", "translator")]
