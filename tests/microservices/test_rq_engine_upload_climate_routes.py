from pathlib import Path
from types import SimpleNamespace

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import upload_climate_routes
from wepppy.nodb.locales import (
    build_continental_us_capability_graph,
    build_locale_capability_graph,
)
from wepppy.nodb.project_config_capabilities import (
    BuilderRegistryUnavailableError,
    LocaleAuthorityInvalidError,
)
from wepppy.runtime_paths.errors import NoDirError


pytestmark = pytest.mark.microservice


def _binary_revisions(binary_ids: tuple[str, ...]) -> dict[str, str]:
    return {
        binary_id: f"provider-v1:watershed={'a' * 64}:hillslope={'b' * 64}"
        for binary_id in binary_ids
    }


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(upload_climate_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(upload_climate_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(
        upload_climate_routes,
        "resolve_run_capability_authority",
        lambda _config: SimpleNamespace(graph=None),
    )


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "job-123") -> None:
    from wepppy.rq import submission_recovery
    class DummyLock:
        def acquire(self, **kwargs): return True
        def extend(self, *args, **kwargs): return True
        def release(self): return None
    class DummyJob:
        id = job_id

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            self.connection = kwargs["connection"]

        def enqueue_call(self, *args, **kwargs):
            return DummyJob()

    class DummyRedis:
        def lock(self, *args, **kwargs): return DummyLock()
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(upload_climate_routes, "Queue", DummyQueue)
    monkeypatch.setattr(upload_climate_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(submission_recovery, "new_rq_job_id", lambda: job_id)


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def get_rq_job_id(self, key): return None
        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(upload_climate_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


@pytest.mark.parametrize("authority_mode", [None, "stored_v3", "preset_projection", "legacy_builder"])
def test_upload_cli_succeeds_for_compatible_or_user_defined_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    authority_mode: str | None,
) -> None:
    run_dir = tmp_path / "run"
    cli_dir = run_dir / "cli"
    cli_dir.mkdir(parents=True)

    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-77")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(upload_climate_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(upload_climate_routes.Ron, "getInstance", lambda wd: object())

    class DummyClimate:
        def __init__(self, cli_dir: Path) -> None:
            self.cli_dir = str(cli_dir)

    climate = DummyClimate(cli_dir)
    monkeypatch.setattr(upload_climate_routes.Climate, "getInstance", lambda wd: climate)
    if authority_mode is not None:
        graph = build_locale_capability_graph(
            "europe",
            ("wepp_260803",),
            _binary_revisions(("wepp_260803",)),
        )
        monkeypatch.setattr(
            upload_climate_routes,
            "resolve_run_capability_authority",
            lambda _config: SimpleNamespace(mode=authority_mode, graph=graph),
        )
    monkeypatch.setattr(
        upload_climate_routes,
        "mutate_root",
        lambda wd, root, callback, purpose="nodir-mutation": callback(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-cli/",
            files={"input_upload_cli": ("demo.cli", b"data")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-77"


@pytest.mark.parametrize("authority_kind", ["stored_v2", "stored_v3_without_user_defined"])
def test_upload_cli_rejects_graph_without_user_defined_before_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    authority_kind: str,
) -> None:
    run_dir = tmp_path / "run"
    cli_dir = run_dir / "cli"
    cli_dir.mkdir(parents=True)
    _stub_auth(monkeypatch)
    monkeypatch.setattr(upload_climate_routes, "get_wd", lambda _runid: str(run_dir))
    monkeypatch.setattr(upload_climate_routes.Ron, "getInstance", lambda _wd: object())
    climate = SimpleNamespace(cli_dir=str(cli_dir))
    monkeypatch.setattr(upload_climate_routes.Climate, "getInstance", lambda _wd: climate)
    graph = (
        build_continental_us_capability_graph(
            ("wepp_260803",),
            _binary_revisions(("wepp_260803",)),
        )
        if authority_kind == "stored_v2"
        else SimpleNamespace(climate_datasets=("vanilla_cligen", "eobs_modified"))
    )
    monkeypatch.setattr(
        upload_climate_routes,
        "resolve_run_capability_authority",
        lambda _config: SimpleNamespace(mode=authority_kind, graph=graph),
    )
    async def fail_form(_request):
        pytest.fail("multipart form read ran after authority denial")

    monkeypatch.setattr(upload_climate_routes.Request, "form", fail_form)
    monkeypatch.setattr(
        upload_climate_routes,
        "mutate_root",
        lambda *_args, **_kwargs: pytest.fail("upload save ran after authority denial"),
    )
    monkeypatch.setattr(
        upload_climate_routes.RedisPrep,
        "getInstance",
        lambda _wd: pytest.fail("timestamp mutation ran after authority denial"),
    )
    monkeypatch.setattr(
        upload_climate_routes,
        "Queue",
        lambda *_args, **_kwargs: pytest.fail("queue reservation ran after authority denial"),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-cli/",
            files={"input_upload_cli": ("demo.cli", b"data")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_capability"


@pytest.mark.parametrize(
    ("failure", "status", "code"),
    [
        (LocaleAuthorityInvalidError("bad locale"), 409, "locale_authority_invalid"),
        (
            BuilderRegistryUnavailableError("provider unavailable"),
            503,
            "builder_registry_error",
        ),
        (ValueError("partial graph"), 409, "capability_authority_invalid"),
    ],
)
def test_upload_cli_authority_errors_are_diagnostic_and_side_effect_free(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: Exception,
    status: int,
    code: str,
) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "cli").mkdir(parents=True)
    _stub_auth(monkeypatch)
    monkeypatch.setattr(upload_climate_routes, "get_wd", lambda _runid: str(run_dir))
    monkeypatch.setattr(upload_climate_routes.Ron, "getInstance", lambda _wd: object())
    monkeypatch.setattr(
        upload_climate_routes.Climate,
        "getInstance",
        lambda _wd: SimpleNamespace(cli_dir=str(run_dir / "cli")),
    )
    monkeypatch.setattr(
        upload_climate_routes,
        "resolve_run_capability_authority",
        lambda _config: (_ for _ in ()).throw(failure),
    )
    async def fail_form(_request):
        pytest.fail("multipart form read ran after authority failure")

    monkeypatch.setattr(upload_climate_routes.Request, "form", fail_form)
    monkeypatch.setattr(
        upload_climate_routes,
        "mutate_root",
        lambda *_args, **_kwargs: pytest.fail("file mutation ran after authority failure"),
    )
    monkeypatch.setattr(
        upload_climate_routes.RedisPrep,
        "getInstance",
        lambda _wd: pytest.fail("timestamp mutation ran after authority failure"),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-cli/",
            files={"input_upload_cli": ("demo.cli", b"data")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["details"] == str(failure)
    if status == 503:
        assert response.headers["Retry-After"] == "5"


def test_upload_cli_auth_precedes_run_and_capability_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        upload_climate_routes,
        "require_jwt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            upload_climate_routes.AuthError("denied", status_code=403, code="forbidden")
        ),
    )
    monkeypatch.setattr(
        upload_climate_routes,
        "get_wd",
        lambda _runid: pytest.fail("run resolution preceded auth"),
    )
    monkeypatch.setattr(
        upload_climate_routes,
        "resolve_run_capability_authority",
        lambda _config: pytest.fail("capability resolution preceded auth"),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-cli/",
            files={"input_upload_cli": ("demo.cli", b"data")},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_upload_cli_propagates_nodir_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    cli_dir = run_dir / "cli"
    cli_dir.mkdir(parents=True)

    _stub_auth(monkeypatch)
    monkeypatch.setattr(upload_climate_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(upload_climate_routes.Ron, "getInstance", lambda wd: object())

    class DummyClimate:
        def __init__(self, cli_dir: Path) -> None:
            self.cli_dir = str(cli_dir)

    climate = DummyClimate(cli_dir)
    monkeypatch.setattr(upload_climate_routes.Climate, "getInstance", lambda wd: climate)

    def _raise_nodir(wd, root, callback, purpose="nodir-mutation"):
        raise NoDirError(http_status=409, code="NODIR_MIXED_STATE", message="mixed")

    monkeypatch.setattr(upload_climate_routes, "mutate_root", _raise_nodir)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-cli/",
            files={"input_upload_cli": ("demo.cli", b"data")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NODIR_MIXED_STATE"


def test_upload_cli_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    cli_dir = run_dir / "cli"
    cli_dir.mkdir(parents=True)

    _stub_auth(monkeypatch)
    monkeypatch.setattr(upload_climate_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(upload_climate_routes.Ron, "getInstance", lambda wd: object())
    monkeypatch.setattr(
        upload_climate_routes,
        "nodir_resolve",
        lambda _wd, _root, view="effective": SimpleNamespace(form="archive"),
    )

    class DummyClimate:
        def __init__(self, cli_dir: Path) -> None:
            self.cli_dir = str(cli_dir)

    climate = DummyClimate(cli_dir)
    monkeypatch.setattr(upload_climate_routes.Climate, "getInstance", lambda wd: climate)
    monkeypatch.setattr(
        upload_climate_routes,
        "mutate_root",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("mutate_root should not run")),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-cli/",
            files={"input_upload_cli": ("demo.cli", b"data")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NODIR_ARCHIVE_ACTIVE"


def test_upload_cli_rejects_oversize_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    cli_dir = run_dir / "cli"
    cli_dir.mkdir(parents=True)

    _stub_auth(monkeypatch)
    monkeypatch.setattr(upload_climate_routes, "UPLOAD_CLI_MAX_BYTES", 4)
    monkeypatch.setattr(upload_climate_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(upload_climate_routes.Ron, "getInstance", lambda wd: object())
    monkeypatch.setattr(
        upload_climate_routes,
        "mutate_root",
        lambda wd, root, callback, purpose="rq-upload": callback(),
    )

    class DummyClimate:
        def __init__(self, cli_dir: Path) -> None:
            self.cli_dir = str(cli_dir)

    climate = DummyClimate(cli_dir)
    monkeypatch.setattr(upload_climate_routes.Climate, "getInstance", lambda wd: climate)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-cli/",
            files={"input_upload_cli": ("demo.cli", b"abcdef")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["message"] == "File exceeds maximum allowed size"
    assert payload["error"]["details"] == "File exceeds maximum allowed size"
    assert payload["error"]["code"] == "payload_too_large"
    assert payload["error_id"]


def test_upload_cli_requires_file_field(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    cli_dir = run_dir / "cli"
    cli_dir.mkdir(parents=True)

    _stub_auth(monkeypatch)
    monkeypatch.setattr(upload_climate_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(upload_climate_routes.Ron, "getInstance", lambda wd: object())
    monkeypatch.setattr(
        upload_climate_routes,
        "mutate_root",
        lambda wd, root, callback, purpose="rq-upload": callback(),
    )

    class DummyClimate:
        def __init__(self, cli_dir: Path) -> None:
            self.cli_dir = str(cli_dir)

    climate = DummyClimate(cli_dir)
    monkeypatch.setattr(upload_climate_routes.Climate, "getInstance", lambda wd: climate)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-cli/",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "input_upload_cli must be provided"
    assert payload["error"]["details"] == "input_upload_cli must be provided"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error_id"]


def test_upload_cli_500_logs_traceback_with_response_error_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    run_dir = tmp_path / "run"
    cli_dir = run_dir / "cli"
    cli_dir.mkdir(parents=True)

    _stub_auth(monkeypatch)
    monkeypatch.setattr(upload_climate_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(upload_climate_routes.Ron, "getInstance", lambda wd: object())

    class DummyClimate:
        def __init__(self, source_dir: Path) -> None:
            self.cli_dir = str(source_dir)

    monkeypatch.setattr(upload_climate_routes.Climate, "getInstance", lambda wd: DummyClimate(cli_dir))

    def _raise_failure(wd, root, callback, purpose="rq-upload"):
        raise RuntimeError("disk write exploded")

    monkeypatch.setattr(upload_climate_routes, "mutate_root", _raise_failure)
    caplog.set_level("ERROR", logger="wepppy.microservices.rq_engine.responses")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-cli/",
            files={"input_upload_cli": ("demo.cli", b"data")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["message"] == "Could not save file"
    assert payload["error"]["code"] == "internal_error"
    assert payload["error"]["details"]
    assert payload["error_id"]

    correlated_records = [
        record
        for record in caplog.records
        if getattr(record, "error_id", None) == payload["error_id"]
    ]
    assert correlated_records
    assert any("RuntimeError: disk write exploded" in record.getMessage() for record in correlated_records)
