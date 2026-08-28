from __future__ import annotations

from types import SimpleNamespace

import pytest

from wepppy.microservices.rq_engine.auth import AuthError
from wepppy.rq import project_config_update_rq as update_rq

pytestmark = pytest.mark.unit


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
