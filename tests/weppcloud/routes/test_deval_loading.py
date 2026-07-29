from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask
from werkzeug.exceptions import Forbidden, NotFound

deval_module = import_module("wepppy.weppcloud.routes.weppcloudr")
cap_guard = import_module("wepppy.weppcloud.utils.cap_guard")
run_context_module = import_module("wepppy.weppcloud.routes._run_context")

pytestmark = pytest.mark.routes


class _RedisContext:
    def __init__(self, **_kwargs: object) -> None:
        pass

    def __enter__(self) -> object:
        return object()

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


@pytest.mark.parametrize(
    ("skip_cache", "file_exists", "job_status", "expected"),
    [
        (False, True, "finished", ("job-1", "finished")),
        (False, False, "started", ("job-1", "started")),
        (True, True, "queued", ("job-1", "queued")),
    ],
)
def test_determine_job_retains_cached_or_active_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    skip_cache: bool,
    file_exists: bool,
    job_status: str,
    expected: tuple[str, str],
) -> None:
    ctx = SimpleNamespace(
        active_root=tmp_path,
        run_root=tmp_path,
        config="cfg",
        pup_relpath=None,
    )
    prep = SimpleNamespace(get_rq_job_id=lambda _key: "job-1")
    output = tmp_path / "export" / "WEPPcloudR" / "deval_run-1.htm"
    if file_exists:
        output.parent.mkdir(parents=True)
        output.write_text("cached", encoding="utf-8")

    monkeypatch.setattr(deval_module, "_resolve_prep", lambda _ctx: prep)
    monkeypatch.setattr(deval_module.redis, "Redis", _RedisContext)
    monkeypatch.setattr(deval_module, "redis_connection_kwargs", lambda *_args: {})
    monkeypatch.setattr(
        deval_module,
        "_lookup_job_status",
        lambda _conn, _job_id, _runid, _config, _active_root: job_status,
    )
    monkeypatch.setattr(
        deval_module,
        "_enqueue_deval_job",
        lambda *_args, **_kwargs: pytest.fail("unexpected enqueue"),
    )

    assert deval_module._determine_job(
        ctx,
        "run-1",
        "cfg",
        skip_cache=skip_cache,
    ) == expected


def test_determine_job_enqueues_when_cache_and_active_job_are_absent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ctx = SimpleNamespace(
        active_root=tmp_path,
        run_root=tmp_path,
        config="cfg",
        pup_relpath=None,
    )
    monkeypatch.setattr(deval_module, "_resolve_prep", lambda _ctx: None)
    monkeypatch.setattr(deval_module.redis, "Redis", _RedisContext)
    monkeypatch.setattr(deval_module, "redis_connection_kwargs", lambda *_args: {})
    monkeypatch.setattr(
        deval_module,
        "_enqueue_deval_job",
        lambda _ctx, runid, config, *, skip_cache: (
            f"{runid}:{config}:{skip_cache}",
            "queued",
        ),
    )

    assert deval_module._determine_job(
        ctx,
        "run-1",
        "cfg",
        skip_cache=False,
    ) == ("run-1:cfg:False", "queued")


def test_deval_tracking_uses_parent_prep_and_lossless_pup_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requested: list[str] = []
    monkeypatch.setattr(
        deval_module.RedisPrep,
        "tryGetInstance",
        lambda path: requested.append(path) or SimpleNamespace(run_id=Path(path).name),
    )
    contexts = [
        SimpleNamespace(
            run_root=tmp_path / parent,
            active_root=tmp_path / parent / "_pups" / "omni" / "scenarios" / "shared",
            config="cfg/a",
            pup_relpath="omni/scenarios/shared",
        )
        for parent in ("parent-a", "parent-b")
    ]

    preps = [deval_module._resolve_prep(ctx) for ctx in contexts]

    assert requested == [str(ctx.run_root) for ctx in contexts]
    assert [prep.run_id for prep in preps] == ["parent-a", "parent-b"]
    assert deval_module._deval_job_key(contexts[0]) == (
        "deval_details:cfg%2Fa:omni%2Fscenarios%2Fshared"
    )


def test_determine_job_replaces_foreign_tracked_job(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ctx = SimpleNamespace(
        active_root=tmp_path / "_pups" / "shared",
        run_root=tmp_path,
        config="cfg",
        pup_relpath="shared",
    )
    prep = SimpleNamespace(get_rq_job_id=lambda _key: "foreign-job")
    cleared: list[tuple[object, str]] = []
    monkeypatch.setattr(deval_module, "_resolve_prep", lambda _ctx: prep)
    monkeypatch.setattr(deval_module.redis, "Redis", _RedisContext)
    monkeypatch.setattr(deval_module, "redis_connection_kwargs", lambda *_args: {})
    monkeypatch.setattr(
        deval_module,
        "_lookup_job_status",
        lambda *_args: "foreign",
    )
    monkeypatch.setattr(
        deval_module,
        "_clear_tracked_job",
        lambda owner, key: cleared.append((owner, key)),
    )
    monkeypatch.setattr(
        deval_module,
        "_enqueue_deval_job",
        lambda *_args, **_kwargs: ("replacement-job", "queued"),
    )

    assert deval_module._determine_job(
        ctx,
        "run-1",
        "cfg",
        skip_cache=False,
    ) == ("replacement-job", "queued")
    assert cleared == [(prep, "deval_details:cfg:shared")]


@pytest.mark.parametrize(
    ("func_name", "args", "expected"),
    [
        (
            "wepppy.rq.weppcloudr_rq.render_deval_details_rq",
            ("run-1", "cfg", "/runs/run-1"),
            "started",
        ),
        (
            "wepppy.rq.weppcloudr_rq.render_deval_details_rq",
            ("other-run", "cfg", "/runs/other-run"),
            "foreign",
        ),
        (
            "wepppy.rq.weppcloudr_rq.render_deval_details_rq",
            ("run-1", "other-cfg", "/runs/run-1"),
            "foreign",
        ),
        (
            "wepppy.rq.weppcloudr_rq.render_deval_details_rq",
            ("run-1", "cfg", "/runs/other-run"),
            "foreign",
        ),
        (
            "wepppy.rq.other.run",
            ("run-1", "cfg", "/runs/run-1"),
            "foreign",
        ),
    ],
)
def test_lookup_job_status_validates_job_ownership(
    monkeypatch: pytest.MonkeyPatch,
    func_name: str,
    args: tuple[str, str, str],
    expected: str,
) -> None:
    job = SimpleNamespace(
        func_name=func_name,
        args=args,
        get_status=lambda: "started",
    )
    monkeypatch.setattr(
        deval_module.Job,
        "fetch",
        lambda _job_id, connection: job,
    )

    assert deval_module._lookup_job_status(
        object(),
        "job-1",
        "run-1",
        "cfg",
        Path("/runs/run-1"),
    ) == expected


def test_pup_validation_error_does_not_disclose_paths(tmp_path: Path) -> None:
    run_root = tmp_path / "private-run"
    run_root.mkdir()
    app = Flask(__name__)

    with app.test_request_context("/"):
        with pytest.raises(NotFound) as exc_info:
            run_context_module._validate_pup_root(run_root, "../../secret")

    assert exc_info.value.description == "Unknown pup project"
    assert str(run_root) not in exc_info.value.description
    assert "secret" not in exc_info.value.description


def test_enqueue_deval_job_passes_exact_active_root_and_options(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    ctx = SimpleNamespace(
        active_root=tmp_path / "active",
        run_root=tmp_path,
        config="cfg",
        pup_relpath="pup-a",
    )

    class _Queue:
        def __init__(self, *, connection: object) -> None:
            captured["connection"] = connection

        def enqueue_call(self, **kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(id="job-new")

    monkeypatch.setattr(deval_module, "_resolve_prep", lambda _ctx: None)
    monkeypatch.setattr(deval_module.redis, "Redis", _RedisContext)
    monkeypatch.setattr(deval_module, "redis_connection_kwargs", lambda *_args: {})
    monkeypatch.setattr(deval_module, "Queue", _Queue)

    app = Flask(__name__)
    app.config.update(
        WEPPCLOUDR_CONTAINER="renderer",
        WEPPCLOUDR_COMMAND_TIMEOUT=120,
        WEPPCLOUDR_JOB_TIMEOUT=180,
    )
    with app.app_context():
        result = deval_module._enqueue_deval_job(
            ctx,
            "run-1",
            "cfg",
            skip_cache=True,
        )

    assert result == ("job-new", "queued")
    assert captured["func"] is deval_module.render_deval_details_rq
    assert captured["args"] == ("run-1", "cfg", str(ctx.active_root))
    assert captured["kwargs"] == {
        "skip_cache": True,
        "container_name": "renderer",
        "timeout": 120,
    }
    assert captured["timeout"] == 180


def test_deval_route_authorizes_before_interchange_or_enqueue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ctx = SimpleNamespace(
        active_root=tmp_path,
        run_root=tmp_path,
        config="cfg",
        pup_relpath=None,
    )
    monkeypatch.setattr(deval_module, "load_run_context", lambda *_args: ctx)
    monkeypatch.setattr(
        deval_module,
        "authorize",
        lambda *_args: (_ for _ in ()).throw(Forbidden()),
    )
    monkeypatch.setattr(
        deval_module,
        "_ensure_interchange",
        lambda _ctx: pytest.fail("interchange must not run"),
    )
    monkeypatch.setattr(
        deval_module,
        "_determine_job",
        lambda *_args, **_kwargs: pytest.fail("enqueue must not run"),
    )

    app = Flask(__name__)
    with app.test_request_context("/runs/run-1/cfg/report/deval_details"):
        with pytest.raises(Forbidden):
            deval_module.deval_details.__wrapped__("run-1", "cfg")


def test_deval_route_requires_cap_before_authorization_for_anonymous_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        cap_guard,
        "current_user",
        SimpleNamespace(is_authenticated=False),
    )
    monkeypatch.setattr(cap_guard, "_cap_session_valid", lambda _ttl: False)
    monkeypatch.setattr(
        cap_guard,
        "cap_gate_response",
        lambda **kwargs: captured.update(kwargs) or "cap-gate",
    )
    monkeypatch.setattr(
        deval_module,
        "authorize",
        lambda *_args: pytest.fail("authorization must wait for CAP"),
    )

    app = Flask(__name__)
    app.secret_key = "test"
    with app.test_request_context("/runs/run-1/cfg/report/deval_details"):
        response = deval_module.deval_details("run-1", "cfg")

    assert response == "cap-gate"
    assert captured["reason"] == "Complete verification to view report details."


def test_deval_route_authenticated_cap_bypass_still_authorizes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cap_guard,
        "current_user",
        SimpleNamespace(is_authenticated=True),
    )
    monkeypatch.setattr(
        deval_module,
        "authorize",
        lambda *_args: (_ for _ in ()).throw(Forbidden()),
    )

    app = Flask(__name__)
    with app.test_request_context("/runs/run-1/cfg/report/deval_details"):
        with pytest.raises(Forbidden):
            deval_module.deval_details("run-1", "cfg")


def test_deval_registered_route_caps_before_filesystem_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cap_guard,
        "current_user",
        SimpleNamespace(is_authenticated=False),
    )
    monkeypatch.setattr(cap_guard, "_cap_session_valid", lambda _ttl: False)
    monkeypatch.setattr(cap_guard, "cap_gate_response", lambda **_kwargs: "cap-gate")
    monkeypatch.setattr(
        deval_module,
        "load_run_context",
        lambda *_args: pytest.fail("filesystem context must wait for CAP"),
    )

    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(deval_module.weppcloudr_bp)

    response = app.test_client().get("/runs/missing/cfg/report/deval_details")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "cap-gate"


def test_deval_route_rejects_symlinked_report_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    active_root = tmp_path / "run"
    outside = tmp_path / "outside"
    (active_root / "export").mkdir(parents=True)
    outside.mkdir()
    (active_root / "export" / "WEPPcloudR").symlink_to(outside, target_is_directory=True)
    ctx = SimpleNamespace(
        active_root=active_root,
        run_root=active_root,
        config="cfg",
        pup_relpath=None,
    )
    monkeypatch.setattr(deval_module, "authorize", lambda *_args: None)
    monkeypatch.setattr(deval_module, "load_run_context", lambda *_args: ctx)
    monkeypatch.setattr(deval_module, "_ensure_interchange", lambda _ctx: None)

    app = Flask(__name__)
    with app.test_request_context("/runs/run-1/cfg/report/deval_details"):
        with pytest.raises(NotFound, match="DEVAL report path is invalid"):
            deval_module.deval_details.__wrapped__("run-1", "cfg")


def test_deval_route_serves_cached_report_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ctx = SimpleNamespace(
        active_root=tmp_path,
        run_root=tmp_path,
        config="cfg",
        pup_relpath=None,
    )
    output = tmp_path / "export" / "WEPPcloudR" / "deval_run-1.htm"
    output.parent.mkdir(parents=True)
    output.write_text("<h1>cached report</h1>", encoding="utf-8")
    monkeypatch.setattr(deval_module, "load_run_context", lambda *_args: ctx)
    monkeypatch.setattr(deval_module, "authorize", lambda *_args: None)
    monkeypatch.setattr(deval_module, "_ensure_interchange", lambda _ctx: None)
    monkeypatch.setattr(
        deval_module,
        "_determine_job",
        lambda *_args, **_kwargs: ("job-old", "finished"),
    )

    app = Flask(__name__)
    with app.test_request_context("/runs/run-1/cfg/report/deval_details"):
        response = deval_module.deval_details.__wrapped__("run-1", "cfg")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "<h1>cached report</h1>"
    assert response.headers["X-Report-Cache"] == "hit"
    assert response.headers["Cache-Control"] == "no-store, max-age=0, must-revalidate"


def test_deval_route_renders_loading_context_and_preserves_pup_refresh(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    ctx = SimpleNamespace(
        active_root=tmp_path / "_pups" / "pup-a",
        run_root=tmp_path,
        config="cfg",
        pup_relpath="pup-a",
    )
    monkeypatch.setattr(deval_module, "load_run_context", lambda *_args: ctx)
    monkeypatch.setattr(deval_module, "authorize", lambda *_args: None)
    monkeypatch.setattr(deval_module, "_ensure_interchange", lambda _ctx: None)
    monkeypatch.setattr(
        deval_module,
        "_determine_job",
        lambda *_args, **_kwargs: ("job-1", "queued"),
    )
    monkeypatch.setattr(
        deval_module,
        "url_for_run",
        lambda endpoint, **kwargs: f"/{endpoint}?pup={kwargs.get('pup', '')}",
    )
    monkeypatch.setattr(
        deval_module,
        "url_for",
        lambda endpoint, **kwargs: f"/{endpoint}/{kwargs['job_id']}",
    )
    monkeypatch.setattr(
        deval_module,
        "render_template",
        lambda template, **context: captured.update(context) or template,
    )

    app = Flask(__name__)
    with app.test_request_context(
        "/runs/run-1/cfg/report/deval_details?no-cache=1&pup=pup-a"
    ):
        response = deval_module.deval_details.__wrapped__("run-1", "cfg")

    assert response.status_code == 202
    assert response.headers["Cache-Control"] == "no-store, max-age=0, must-revalidate"
    assert captured == {
        "runid": "run-1",
        "config": "cfg",
        "job_id": "job-1",
        "job_status": "queued",
        "job_dashboard_url": "/rq_job_dashboard.job_dashboard_route/job-1",
        "refresh_url": "/weppcloud.deval_details?pup=pup-a",
        "skip_cache": True,
    }
