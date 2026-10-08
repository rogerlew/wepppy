from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
import json
import os

import pytest
from flask import Flask, abort as flask_abort
from werkzeug.exceptions import Forbidden

import wepppy.weppcloud.routes.fork_console.fork_console as fork_console_module


pytestmark = pytest.mark.routes


@pytest.mark.parametrize("controller_present", [False, True])
@pytest.mark.parametrize("layout", ["absent", "empty", "populated"])
def test_checked_omni_readiness_optional_state(tmp_path, controller_present, layout):
    if controller_present:
        (tmp_path / "omni.nodb").write_text("{}")
    if layout != "absent":
        for path in ("omni", "_pups/omni/scenarios", "_pups/omni/contrasts"):
            (tmp_path / path).mkdir(parents=True)
        if layout == "populated":
            (tmp_path / "omni/results.csv").write_text("retained")
    (tmp_path / "_pups/unrelated").mkdir(parents=True, exist_ok=True)
    sentinel = tmp_path / "_pups/unrelated/result.txt"
    sentinel.write_text("preserve")

    expected = layout == "empty" or (layout == "absent" and not controller_present)
    assert fork_console_module._checked_omni_destination_ready(str(tmp_path)) is expected
    assert sentinel.read_text() == "preserve"


@pytest.mark.parametrize("controller_present", [False, True])
@pytest.mark.parametrize("path", ["omni", "_pups", "_pups/omni", "_pups/omni/scenarios", "_pups/omni/contrasts"])
@pytest.mark.parametrize("kind", ["file", "symlink", "dangling", "fifo"])
def test_checked_omni_readiness_rejects_unsafe_directories(tmp_path, controller_present, path, kind):
    if controller_present:
        (tmp_path / "omni.nodb").write_text("{}")
    for directory in ("omni", "_pups/omni/scenarios", "_pups/omni/contrasts"):
        if directory == path or directory.startswith(path + "/"):
            continue
        (tmp_path / directory).mkdir(parents=True, exist_ok=True)
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if kind == "file":
        target.write_text("not a directory")
    elif kind == "fifo":
        os.mkfifo(target)
    else:
        outside = tmp_path / "outside"
        if kind == "symlink":
            outside.mkdir()
        target.symlink_to(outside, target_is_directory=True)
    assert fork_console_module._checked_omni_destination_ready(str(tmp_path)) is False


@pytest.mark.parametrize("kind", ["directory", "symlink", "dangling", "fifo"])
def test_checked_omni_readiness_rejects_unsafe_controller(tmp_path, kind):
    target = tmp_path / "omni.nodb"
    if kind == "directory":
        target.mkdir()
    elif kind == "fifo":
        os.mkfifo(target)
    else:
        outside = tmp_path / "outside.nodb"
        if kind == "symlink":
            outside.write_text("{}")
        target.symlink_to(outside)
    assert fork_console_module._checked_omni_destination_ready(str(tmp_path)) is False


@pytest.mark.parametrize("envelope", ["flat", "py/state"])
@pytest.mark.parametrize("scenario_state", ["absent", "empty", "scenario", "contrast", "pairs", "legacy", "child"])
def test_fork_capabilities_omni_read_only(tmp_path, envelope, scenario_state):
    state = {}
    if scenario_state in {"scenario", "contrast", "pairs", "legacy"}:
        key = {"scenario": "_scenarios", "contrast": "_contrast_names", "pairs": "_contrast_pairs", "legacy": "_contrasts"}[scenario_state]
        state[key] = [{"type": "undisturbed"}] if scenario_state != "contrast" else ["contrast-1"]
    if scenario_state not in {"absent", "child"}:
        payload = {"py/state": state} if envelope == "py/state" else state
        (tmp_path / "omni.nodb").write_text(json.dumps(payload))
    if scenario_state == "child":
        (tmp_path / "_pups/omni/contrasts/1").mkdir(parents=True)
    if scenario_state == "empty":
        (tmp_path / "_pups/omni/scenarios").mkdir(parents=True)
    before = {str(p.relative_to(tmp_path)): p.read_bytes() if p.is_file() else None for p in tmp_path.rglob("*")}

    assert fork_console_module._fork_option_availability(str(tmp_path)) == (
        False, scenario_state not in {"absent", "empty"}
    )
    assert not (tmp_path / "nodb.version").exists()
    assert before == {str(p.relative_to(tmp_path)): p.read_bytes() if p.is_file() else None for p in tmp_path.rglob("*")}


@pytest.mark.parametrize("map_state", ["absent", "unset", "missing", "source", "derived", "absolute", "symlink"])
def test_fork_capabilities_sbs(tmp_path, map_state):
    if map_state != "absent":
        map_path = tmp_path / "disturbed/source.tif"
        map_path.parent.mkdir()
        name = str(map_path) if map_state == "absolute" else "source.tif"
        (tmp_path / "disturbed.nodb").write_text(json.dumps({"py/state": {"_disturbed_fn": None if map_state == "unset" else name}}))
        if map_state in {"source", "absolute"}:
            map_path.write_bytes(b"existing map")
        elif map_state == "derived":
            (map_path.parent / "sbs_4class.tif").write_bytes(b"existing derived map")
        elif map_state == "symlink":
            artifact = tmp_path / "retained.tif"
            artifact.write_bytes(b"existing map")
            map_path.symlink_to(artifact)
    assert fork_console_module._fork_option_availability(str(tmp_path)) == (
        map_state in {"source", "derived", "absolute", "symlink"}, False
    )
    assert not (tmp_path / "nodb.version").exists()


@pytest.mark.parametrize("name", ["omni.nodb", "disturbed.nodb"])
@pytest.mark.parametrize("kind", ["symlink", "dangling", "directory", "fifo", "invalid", "envelope", "field"])
def test_fork_capabilities_reject_malformed_metadata(tmp_path, name, kind):
    target = tmp_path / name
    if kind in {"symlink", "dangling"}:
        outside = tmp_path / "outside.nodb"
        if kind == "symlink":
            outside.write_text("{}")
        target.symlink_to(outside)
    elif kind == "directory":
        target.mkdir()
    elif kind == "fifo":
        os.mkfifo(target)
    elif kind == "invalid":
        target.write_text("{invalid")
    elif kind == "envelope":
        target.write_text('{"py/state": []}')
    else:
        target.write_text(json.dumps({"_scenarios": "invalid", "_disturbed_fn": []}))
    with pytest.raises((OSError, ValueError)):
        fork_console_module._fork_option_availability(str(tmp_path))


@pytest.mark.parametrize("has_sbs,has_omni", [(False, False), (False, True), (True, False), (True, True)])
def test_fork_console_query_selections_use_real_source_capabilities(monkeypatch, tmp_path, has_sbs, has_omni):
    if has_sbs:
        (tmp_path / "disturbed").mkdir()
        (tmp_path / "disturbed/sbs.tif").write_bytes(b"existing")
        (tmp_path / "disturbed.nodb").write_text('{"_disturbed_fn": "sbs.tif"}')
    if has_omni:
        (tmp_path / "omni.nodb").write_text('{"_scenarios": [{"type": "undisturbed"}]}')
    monkeypatch.setattr(fork_console_module, "authorize", lambda *args: None)
    monkeypatch.setattr(fork_console_module, "get_wd", lambda *args, **kwargs: str(tmp_path))
    monkeypatch.setattr(fork_console_module, "current_user", SimpleNamespace(is_authenticated=False))
    monkeypatch.setattr(fork_console_module, "render_template", lambda template, **context: context)
    app = Flask(__name__)
    with app.test_request_context("/?undisturbify=true&skip_omni_scenarios_contrasts=true&skip_wepp_runs_output=true"):
        context = fork_console_module.rq_fork_console("source", "cfg")
    assert context["can_undisturbify"] is has_sbs
    assert context["undisturbify"] is has_sbs
    assert context["can_skip_omni"] is has_omni
    assert context["skip_omni_scenarios_contrasts"] is has_omni
    assert context["skip_wepp_runs_output"] is True


@pytest.mark.parametrize("job_args", [(), (True,), (False,)])
def test_fork_readiness_route_accepts_finished_non_omni_destination(monkeypatch, tmp_path, job_args):
    for name in fork_console_module._FORK_DESTINATION_REQUIRED_FILES:
        (tmp_path / name).write_text("{}")
    authorized = []
    monkeypatch.setattr(fork_console_module, "authorize", lambda runid, config: authorized.append(runid))
    monkeypatch.setattr(fork_console_module, "get_wd", lambda *args, **kwargs: str(tmp_path))
    monkeypatch.setattr(fork_console_module, "_fetch_fork_job", lambda job_id: SimpleNamespace(
        func_name="wepppy.rq.project_rq.fork_rq", args=("source", "destination", False, True, *job_args),
        get_status=lambda **kwargs: "finished",
    ))
    monkeypatch.setattr(fork_console_module, "jsonify", lambda body: body)
    assert fork_console_module.fork_destination_readiness("source", "cfg", "job", "destination") == {"ready": True}
    assert authorized == ["source", "destination"]


def test_fork_readiness_missing_root_is_not_ready(tmp_path):
    assert fork_console_module._checked_omni_destination_ready(str(tmp_path / "missing")) is False


def test_fork_readiness_unreadable_directory_is_not_absence(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("requires an unprivileged filesystem identity")
    directory = tmp_path / "omni"
    directory.mkdir(mode=0o000)
    try:
        assert fork_console_module._checked_omni_destination_ready(str(tmp_path)) is False
    finally:
        directory.chmod(0o700)


@pytest.mark.parametrize(
    ("args", "expected_undisturbify", "expected_skip"),
    [
        ({}, False, False),
        ({"undisturbify": "YES", "skip_wepp_runs_output": "1"}, True, True),
        ({"undisturbify": "false", "skip_wepp_runs_output": "off"}, False, False),
    ],
)
def test_fork_console_route_propagates_query_defaults_and_authenticated_token(
    monkeypatch: pytest.MonkeyPatch,
    args: dict[str, str],
    expected_undisturbify: bool,
    expected_skip: bool,
) -> None:
    monkeypatch.setattr(fork_console_module, "authorize", lambda runid, config: None)
    monkeypatch.setattr(fork_console_module, "get_wd", lambda *args, **kwargs: "/source")
    monkeypatch.setattr(fork_console_module, "_fork_option_availability", lambda wd: (True, True))
    monkeypatch.setattr(fork_console_module, "request", SimpleNamespace(args=args))
    monkeypatch.setattr(
        fork_console_module,
        "current_user",
        SimpleNamespace(is_authenticated=True),
    )
    monkeypatch.setattr(
        fork_console_module,
        "current_app",
        SimpleNamespace(
            config={
                "CAP_BASE_URL": "/cap/",
                "CAP_ASSET_BASE_URL": "/cap/assets/",
                "CAP_SITE_KEY": "site-key",
            },
            logger=SimpleNamespace(exception=lambda *args, **kwargs: None),
        ),
    )
    monkeypatch.setattr(fork_console_module, "_issue_rq_engine_token", lambda: "rq-token")
    monkeypatch.setattr(
        fork_console_module,
        "render_template",
        lambda template, **context: {"template": template, **context},
    )

    context = fork_console_module.rq_fork_console("source-run", "cfg")

    assert context == {
        "template": "rq-fork-console.htm",
        "runid": "source-run",
        "config": "cfg",
        "can_undisturbify": True,
        "can_skip_omni": True,
        "undisturbify": expected_undisturbify,
        "skip_wepp_runs_output": expected_skip,
        "skip_omni_scenarios_contrasts": False,
        "cap_base_url": "/cap",
        "cap_asset_base_url": "/cap/assets",
        "cap_site_key": "site-key",
        "rq_engine_token": "rq-token",
    }


def test_fork_console_route_anonymous_context_has_no_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fork_console_module, "authorize", lambda runid, config: None)
    monkeypatch.setattr(fork_console_module, "get_wd", lambda *args, **kwargs: "/source")
    monkeypatch.setattr(fork_console_module, "_fork_option_availability", lambda wd: (False, False))
    monkeypatch.setattr(fork_console_module, "request", SimpleNamespace(args={}))
    monkeypatch.setattr(
        fork_console_module,
        "current_user",
        SimpleNamespace(is_authenticated=False),
    )
    monkeypatch.setattr(
        fork_console_module,
        "current_app",
        SimpleNamespace(
            config={
                "CAP_BASE_URL": "/cap",
                "CAP_ASSET_BASE_URL": "/cap/assets",
                "CAP_SITE_KEY": "site-key",
            },
            logger=SimpleNamespace(exception=lambda *args, **kwargs: None),
        ),
    )
    monkeypatch.setattr(
        fork_console_module,
        "_issue_rq_engine_token",
        lambda: pytest.fail("anonymous route must not mint a bearer token"),
    )
    monkeypatch.setattr(
        fork_console_module,
        "render_template",
        lambda template, **context: context,
    )

    context = fork_console_module.rq_fork_console("public-run", "cfg")

    assert context["rq_engine_token"] is None
    assert context["undisturbify"] is False
    assert context["skip_wepp_runs_output"] is False


def test_fork_destination_readiness_requires_core_nodb_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    authorized: list[tuple[str, str]] = []
    monkeypatch.setattr(
        fork_console_module,
        "authorize",
        lambda runid, config: authorized.append((runid, config)),
    )
    monkeypatch.setattr(
        fork_console_module,
        "get_wd",
        lambda runid, *, prefer_active: str(tmp_path / runid),
    )
    monkeypatch.setattr(
        fork_console_module,
        "_fetch_fork_job",
        lambda job_id: SimpleNamespace(
            func_name="wepppy.rq.project_rq.fork_rq",
            args=("source-run", "destination-run", False, False),
            get_status=lambda *, refresh: "finished",
        ),
    )

    destination = tmp_path / "destination-run"
    destination.mkdir()
    for name in fork_console_module._FORK_DESTINATION_REQUIRED_FILES:
        (destination / name).write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        fork_console_module,
        "jsonify",
        lambda payload: payload,
    )

    response = fork_console_module.fork_destination_readiness(
        "source-run",
        "cfg",
        "fork-job",
        "destination-run",
    )

    assert authorized == [
        ("source-run", "cfg"),
        ("destination-run", "cfg"),
    ]
    assert response == {"ready": True}


def test_fork_destination_readiness_reports_incomplete_destination(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(fork_console_module, "authorize", lambda runid, config: None)
    monkeypatch.setattr(
        fork_console_module,
        "get_wd",
        lambda runid, *, prefer_active: str(tmp_path / runid),
    )
    monkeypatch.setattr(
        fork_console_module,
        "_fetch_fork_job",
        lambda job_id: SimpleNamespace(
            func_name="wepppy.rq.project_rq.fork_rq",
            args=("source-run", "not-visible-yet", False, False),
            get_status=lambda *, refresh: "finished",
        ),
    )
    monkeypatch.setattr(
        fork_console_module,
        "jsonify",
        lambda payload: payload,
    )

    response = fork_console_module.fork_destination_readiness(
        "source-run",
        "cfg",
        "fork-job",
        "not-visible-yet",
    )

    assert response["ready"] is False


@pytest.mark.parametrize(
    ("func_name", "args"),
    [
        ("wepppy.rq.project_rq.not_fork_rq", ("source-run", "requested-destination")),
        ("wepppy.rq.project_rq.fork_rq", ("different-source", "requested-destination")),
        ("wepppy.rq.project_rq.fork_rq", ("source-run", "different-destination")),
    ],
)
def test_fork_destination_readiness_rejects_unrelated_job(
    monkeypatch: pytest.MonkeyPatch,
    func_name: str,
    args: tuple[str, str],
) -> None:
    monkeypatch.setattr(fork_console_module, "authorize", lambda runid, config: None)
    monkeypatch.setattr(
        fork_console_module,
        "_fetch_fork_job",
        lambda job_id: SimpleNamespace(
            func_name=func_name,
            args=(*args, False, False),
            get_status=lambda *, refresh: "finished",
        ),
    )
    monkeypatch.setattr(
        fork_console_module,
        "abort",
        lambda status: (_ for _ in ()).throw(RuntimeError(status)),
    )

    with pytest.raises(RuntimeError, match="404"):
        fork_console_module.fork_destination_readiness(
            "source-run",
            "cfg",
            "fork-job",
            "requested-destination",
        )


def test_fork_destination_readiness_waits_for_finished_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorized: list[tuple[str, str]] = []
    monkeypatch.setattr(
        fork_console_module,
        "authorize",
        lambda runid, config: authorized.append((runid, config)),
    )
    monkeypatch.setattr(
        fork_console_module,
        "_fetch_fork_job",
        lambda job_id: SimpleNamespace(
            func_name="wepppy.rq.project_rq.fork_rq",
            args=("source-run", "destination-run", False, False),
            get_status=lambda *, refresh: "started",
        ),
    )
    monkeypatch.setattr(fork_console_module, "jsonify", lambda payload: payload)

    response = fork_console_module.fork_destination_readiness(
        "source-run",
        "cfg",
        "fork-job",
        "destination-run",
    )

    assert response == {"ready": False}
    assert authorized == [("source-run", "cfg")]


def test_fork_destination_readiness_http_route_enforces_authorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(fork_console_module.fork_bp, url_prefix="/weppcloud")
    monkeypatch.setattr(
        fork_console_module,
        "authorize",
        lambda runid, config: flask_abort(403),
    )
    monkeypatch.setattr(
        fork_console_module,
        "_fetch_fork_job",
        lambda job_id: pytest.fail("authorization must precede job lookup"),
    )

    with pytest.raises(Forbidden):
        app.test_client().get(
            "/weppcloud/runs/source-run/cfg/rq-fork-console/readiness/"
            "fork-job/destination-run"
        )
