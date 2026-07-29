from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import pytest
from flask import Flask, abort as flask_abort
from werkzeug.exceptions import Forbidden

import wepppy.weppcloud.routes.fork_console.fork_console as fork_console_module


pytestmark = pytest.mark.routes


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
        "undisturbify": expected_undisturbify,
        "skip_wepp_runs_output": expected_skip,
        "cap_base_url": "/cap",
        "cap_asset_base_url": "/cap/assets",
        "cap_site_key": "site-key",
        "rq_engine_token": "rq-token",
    }


def test_fork_console_route_anonymous_context_has_no_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fork_console_module, "authorize", lambda runid, config: None)
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
