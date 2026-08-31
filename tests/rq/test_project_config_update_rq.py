from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace

import pytest

from wepppy.microservices.rq_engine.auth import AuthError
from wepppy.rq import project_config_update_rq as update_rq

pytestmark = pytest.mark.unit


def test_fresh_rq_process_can_resolve_worker_task() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from rq.utils import import_attribute; "
                "task = import_attribute("
                "'wepppy.rq.project_config_update_rq.run_project_config_update_rq'); "
                "assert task.__name__ == 'run_project_config_update_rq'"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_release_active_atomically_preserves_replacement_reservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "release-race"
    key = f"{update_rq.CONFIG_UPDATE_ACTIVE_PREFIX}{runid}"

    class AtomicRedis:
        def __init__(self) -> None:
            self.store = {key: b"replacement-job"}
            self.calls: list[tuple[str, int, str, str]] = []

        def __enter__(self) -> AtomicRedis:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def eval(self, script: str, numkeys: int, script_key: str, expected: str) -> int:
            self.calls.append((script, numkeys, script_key, expected))
            if self.store.get(script_key) == expected.encode("utf-8"):
                del self.store[script_key]
                return 1
            return 0

    client = AtomicRedis()
    monkeypatch.setattr(update_rq.redis, "Redis", lambda **_kwargs: client)

    update_rq._release_active(runid, "expired-job")

    assert client.store[key] == b"replacement-job"
    update_rq._release_active(runid, "replacement-job")
    assert key not in client.store
    assert len(client.calls) == 2
    assert all(call[1:3] == (1, key) for call in client.calls)
    assert all("redis.call('get'" in call[0] for call in client.calls)
    assert all("redis.call('del'" in call[0] for call in client.calls)


def test_worker_reauthorizes_current_actor_before_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    actor = {"token_class": "user", "user_id": 42}
    job = SimpleNamespace(id="job-1", meta={"auth_actor": actor})
    calls: list[tuple] = []
    released: list[tuple[str, str]] = []
    apply_kwargs: dict[str, object] = {}
    result = SimpleNamespace(
        applied=True, sequence=2, prior_digest="a" * 64,
        resulting_digest="b" * 64, additions=(1, 2), recovered=False,
        update_kind="additive",
    )
    monkeypatch.setattr(update_rq, "get_current_job", lambda: job)
    monkeypatch.setenv("RQ_ENGINE_DEPLOYMENT_REVISION", "different-worker-revision")
    monkeypatch.setattr(update_rq, "authorize_run_mutation", lambda current, runid: calls.append((current, runid)))
    monkeypatch.setattr(update_rq, "get_wd", lambda runid: f"/wc1/runs/{runid}")
    def apply(*_args, **kwargs):
        apply_kwargs.update(kwargs)
        return result
    monkeypatch.setattr(update_rq, "apply_project_config_update", apply)
    monkeypatch.setattr(update_rq, "_release_active", lambda runid, job_id: released.append((runid, job_id)))

    payload = update_rq.run_project_config_update_rq(
        "run-1", "config", "pcu1-preview", "route-revision", "new", "option"
    )

    assert calls == [(actor, "run-1")]
    assert payload == {
        "applied": True,
        "recovered": False,
        "sequence": 2,
        "prior_digest": "a" * 64,
        "resulting_digest": "b" * 64,
    }
    assert apply_kwargs["application_revision"] == "route-revision"
    assert released == [("run-1", "job-1")]


def test_worker_authority_loss_prevents_mutation_and_releases_singleflight(monkeypatch: pytest.MonkeyPatch) -> None:
    job = SimpleNamespace(id="job-2", meta={"auth_actor": {"token_class": "user", "user_id": 42}})
    applied: list[bool] = []
    released: list[tuple[str, str]] = []
    monkeypatch.setattr(update_rq, "get_current_job", lambda: job)
    monkeypatch.setattr(
        update_rq,
        "authorize_run_mutation",
        lambda *_args: (_ for _ in ()).throw(AuthError("ownership changed", status_code=403, code="forbidden")),
    )
    monkeypatch.setattr(update_rq, "apply_project_config_update", lambda *_a, **_k: applied.append(True))
    monkeypatch.setattr(update_rq, "_release_active", lambda runid, job_id: released.append((runid, job_id)))

    with pytest.raises(AuthError, match="ownership changed"):
        update_rq.run_project_config_update_rq(
            "run-1", "config", "pcu1-preview", "route-revision", "new", "option"
        )

    assert applied == []
    assert released == [("run-1", "job-2")]
