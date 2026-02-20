from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path

import pytest

import wepppy.nodb.core.wepp as wepp_module
from wepppy.nodb.core.wepp import Wepp

pytestmark = pytest.mark.unit


def _new_detached_wepp(tmp_path: Path, logger_name: str) -> Wepp:
    wepp = Wepp.__new__(Wepp)
    wepp.wd = str(tmp_path)
    wepp.logger = logging.getLogger(logger_name)
    wepp._logger = wepp.logger
    return wepp


def test_parse_inputs_delegates_to_input_parser_inside_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _new_detached_wepp(tmp_path, "tests.wepp.facade.parse_inputs")
    events: list[object] = []

    @contextmanager
    def _fake_locked():
        events.append("lock-enter")
        yield
        events.append("lock-exit")

    def _fake_parse(instance: Wepp, kwds: dict[str, object]) -> None:
        events.append(("parse", instance, kwds))

    wepp.locked = _fake_locked  # type: ignore[assignment]
    monkeypatch.setattr(wepp_module._WEPP_INPUT_PARSER, "parse", _fake_parse)

    payload = {"dtchr_override": "120"}
    wepp.parse_inputs(payload)

    assert events[0] == "lock-enter"
    assert events[1] == ("parse", wepp, payload)
    assert events[2] == "lock-exit"


def test_prep_hillslopes_delegates_to_prep_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _new_detached_wepp(tmp_path, "tests.wepp.facade.prep_hillslopes")
    captured: dict[str, object] = {}

    def _fake_prep_hillslopes(instance: Wepp, **kwargs: object) -> None:
        captured["instance"] = instance
        captured["kwargs"] = kwargs

    monkeypatch.setattr(wepp_module._WEPP_PREP_SERVICE, "prep_hillslopes", _fake_prep_hillslopes)

    wepp.prep_hillslopes(frost=True, man_relpath="m")

    assert captured["instance"] is wepp
    assert captured["kwargs"] == {
        "frost": True,
        "baseflow": None,
        "wepp_ui": None,
        "pmet": None,
        "snow": None,
        "man_relpath": "m",
        "cli_relpath": "",
        "slp_relpath": "",
        "sol_relpath": "",
        "max_workers": None,
    }


def test_prep_internal_wrappers_delegate_to_prep_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _new_detached_wepp(tmp_path, "tests.wepp.facade.prep_wrappers")
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        wepp_module._WEPP_PREP_SERVICE,
        "prep_managements",
        lambda instance, translator: calls.append(("prep_managements", translator)),
    )
    monkeypatch.setattr(
        wepp_module._WEPP_PREP_SERVICE,
        "prep_soils",
        lambda instance, translator, max_workers=None: calls.append(("prep_soils", max_workers)),
    )
    monkeypatch.setattr(
        wepp_module._WEPP_PREP_SERVICE,
        "prep_climates",
        lambda instance, translator: calls.append(("prep_climates", translator)),
    )
    monkeypatch.setattr(
        wepp_module._WEPP_PREP_SERVICE,
        "prep_climates_ss_batch",
        lambda instance, translator: calls.append(("prep_climates_ss_batch", translator)),
    )
    monkeypatch.setattr(
        wepp_module._WEPP_PREP_SERVICE,
        "make_hillslope_runs",
        lambda instance, translator, **kwargs: calls.append(("make_hillslope_runs", kwargs["reveg"])),
    )

    translator = object()
    wepp._prep_managements(translator)
    wepp._prep_soils(translator, max_workers=3)
    wepp._prep_climates(translator)
    wepp._prep_climates_ss_batch(translator)
    wepp._make_hillslope_runs(translator, reveg=True)

    assert calls == [
        ("prep_managements", translator),
        ("prep_soils", 3),
        ("prep_climates", translator),
        ("prep_climates_ss_batch", translator),
        ("make_hillslope_runs", True),
    ]


def test_prep_and_run_wrappers_delegate_to_run_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _new_detached_wepp(tmp_path, "tests.wepp.facade.run_wrappers")
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        wepp_module._WEPP_RUN_SERVICE,
        "prep_and_run_flowpaths",
        lambda instance, clean_after_run=True: calls.append(("prep_and_run_flowpaths", clean_after_run)),
    )
    monkeypatch.setattr(
        wepp_module._WEPP_RUN_SERVICE,
        "run_hillslopes",
        lambda instance, **kwargs: calls.append(("run_hillslopes", kwargs["max_workers"])),
    )
    monkeypatch.setattr(
        wepp_module._WEPP_RUN_SERVICE,
        "run_watershed",
        lambda instance: calls.append(("run_watershed", None)),
    )

    wepp.prep_and_run_flowpaths(clean_after_run=False)
    wepp.run_hillslopes(max_workers=7)
    wepp.run_watershed()

    assert calls == [
        ("prep_and_run_flowpaths", False),
        ("run_hillslopes", 7),
        ("run_watershed", None),
    ]


def test_prep_watershed_delegates_to_prep_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _new_detached_wepp(tmp_path, "tests.wepp.facade.prep_watershed")
    captured: dict[str, object] = {}

    def _fake_prep_watershed(instance: Wepp, **kwargs: object) -> None:
        captured["instance"] = instance
        captured["kwargs"] = kwargs

    monkeypatch.setattr(wepp_module._WEPP_PREP_SERVICE, "prep_watershed", _fake_prep_watershed)

    wepp.prep_watershed(erodibility=0.3, critical_shear=2.5)

    assert captured["instance"] is wepp
    assert captured["kwargs"]["erodibility"] == 0.3
    assert captured["kwargs"]["critical_shear"] == 2.5


def test_postprocess_wrappers_delegate_to_postprocess_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _new_detached_wepp(tmp_path, "tests.wepp.facade.postprocess")

    monkeypatch.setattr(
        wepp_module._WEPP_POSTPROCESS_SERVICE,
        "report_return_periods",
        lambda instance, **kwargs: {"rp": kwargs["method"]},
    )
    monkeypatch.setattr(
        wepp_module._WEPP_POSTPROCESS_SERVICE,
        "query_sub_val",
        lambda instance, measure: {"sub": {"value": measure}},
    )
    monkeypatch.setattr(
        wepp_module._WEPP_POSTPROCESS_SERVICE,
        "query_chn_val",
        lambda instance, measure: {"chn": {"value": measure}},
    )

    assert wepp.report_return_periods(method="cta") == {"rp": "cta"}
    assert wepp.query_sub_val("Runoff") == {"sub": {"value": "Runoff"}}
    assert wepp.query_chn_val("Peak Discharge") == {"chn": {"value": "Peak Discharge"}}


def test_bootstrap_wrappers_delegate_to_bootstrap_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _new_detached_wepp(tmp_path, "tests.wepp.facade.bootstrap")
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        wepp_module._WEPP_BOOTSTRAP_SERVICE,
        "run_git",
        lambda instance, args: calls.append(("run_git", tuple(args))) or "git-result",
    )
    monkeypatch.setattr(
        wepp_module._WEPP_BOOTSTRAP_SERVICE,
        "mint_bootstrap_jwt",
        lambda instance, user_email, user_id, expires_seconds: (
            calls.append(("mint_bootstrap_jwt", expires_seconds)) or "url"
        ),
    )

    assert wepp._run_git(["status"]) == "git-result"
    assert wepp.mint_bootstrap_jwt("user@example.com", "7") == "url"
    assert calls == [
        ("run_git", ("status",)),
        ("mint_bootstrap_jwt", wepp_module.BOOTSTRAP_JWT_EXPIRES_SECONDS),
    ]


def test_bootstrap_wrappers_delegate_remaining_methods_to_bootstrap_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _new_detached_wepp(tmp_path, "tests.wepp.facade.bootstrap.remaining")
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        wepp_module._WEPP_BOOTSTRAP_SERVICE,
        "load_bootstrap_push_log",
        lambda instance: calls.append(("load_bootstrap_push_log", instance)) or {"abc": "user@example.com"},
    )
    monkeypatch.setattr(
        wepp_module._WEPP_BOOTSTRAP_SERVICE,
        "write_bootstrap_gitignore",
        lambda instance: calls.append(("write_bootstrap_gitignore", instance)),
    )
    monkeypatch.setattr(
        wepp_module._WEPP_BOOTSTRAP_SERVICE,
        "install_bootstrap_hook",
        lambda instance: calls.append(("install_bootstrap_hook", instance)),
    )
    monkeypatch.setattr(
        wepp_module._WEPP_BOOTSTRAP_SERVICE,
        "init_bootstrap",
        lambda instance: calls.append(("init_bootstrap", instance)),
    )
    monkeypatch.setattr(
        wepp_module._WEPP_BOOTSTRAP_SERVICE,
        "get_bootstrap_commits",
        lambda instance: calls.append(("get_bootstrap_commits", instance)) or [{"sha": "deadbeef"}],
    )
    monkeypatch.setattr(
        wepp_module._WEPP_BOOTSTRAP_SERVICE,
        "checkout_bootstrap_commit",
        lambda instance, sha: calls.append(("checkout_bootstrap_commit", sha)) or True,
    )
    monkeypatch.setattr(
        wepp_module._WEPP_BOOTSTRAP_SERVICE,
        "get_bootstrap_current_ref",
        lambda instance: calls.append(("get_bootstrap_current_ref", instance)) or "main",
    )
    monkeypatch.setattr(
        wepp_module._WEPP_BOOTSTRAP_SERVICE,
        "ensure_bootstrap_main",
        lambda instance: calls.append(("ensure_bootstrap_main", instance)),
    )
    monkeypatch.setattr(
        wepp_module._WEPP_BOOTSTRAP_SERVICE,
        "bootstrap_commit_inputs",
        lambda instance, stage: calls.append(("bootstrap_commit_inputs", stage)) or "cafebabe",
    )
    monkeypatch.setattr(
        wepp_module._WEPP_BOOTSTRAP_SERVICE,
        "disable_bootstrap",
        lambda instance: calls.append(("disable_bootstrap", instance)),
    )

    assert wepp._load_bootstrap_push_log() == {"abc": "user@example.com"}
    wepp._write_bootstrap_gitignore()
    wepp._install_bootstrap_hook()
    wepp.init_bootstrap()
    assert wepp.get_bootstrap_commits() == [{"sha": "deadbeef"}]
    assert wepp.checkout_bootstrap_commit("deadbeef") is True
    assert wepp.get_bootstrap_current_ref() == "main"
    wepp.ensure_bootstrap_main()
    assert wepp.bootstrap_commit_inputs("prep wepp") == "cafebabe"
    wepp.disable_bootstrap()

    assert calls == [
        ("load_bootstrap_push_log", wepp),
        ("write_bootstrap_gitignore", wepp),
        ("install_bootstrap_hook", wepp),
        ("init_bootstrap", wepp),
        ("get_bootstrap_commits", wepp),
        ("checkout_bootstrap_commit", "deadbeef"),
        ("get_bootstrap_current_ref", wepp),
        ("ensure_bootstrap_main", wepp),
        ("bootstrap_commit_inputs", "prep wepp"),
        ("disable_bootstrap", wepp),
    ]
