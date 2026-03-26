from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.rq.features_export_rq as features_export_rq

pytestmark = pytest.mark.unit


class _PrepStub:
    def __init__(self, wd: str) -> None:
        self.wd = wd
        self.removed: list[object] = []
        self.timestamps: list[object] = []

    def remove_timestamp(self, task: object) -> None:
        self.removed.append(task)

    def timestamp(self, task: object) -> None:
        self.timestamps.append(task)


@pytest.fixture()
def features_export_rq_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    published: list[tuple[str, str]] = []
    execution_calls: list[dict[str, object]] = []
    prep_instances: dict[str, _PrepStub] = {}

    class _RedisPrepStub:
        @staticmethod
        def tryGetInstance(wd: str) -> _PrepStub:
            instance = prep_instances.get(wd)
            if instance is None:
                instance = _PrepStub(wd)
                prep_instances[wd] = instance
            return instance

    def _fake_execute_features_export(
        wd: str,
        *,
        runid: str,
        config: str,
        payload: dict[str, object],
        job_id: str,
        force_cache_hit: bool = False,
    ) -> dict[str, object]:
        execution_calls.append(
            {
                "wd": wd,
                "runid": runid,
                "config": config,
                "payload": payload,
                "job_id": job_id,
                "force_cache_hit": force_cache_hit,
            }
        )
        return {
            "artifact_id": "artifact-1",
            "download_url": "/rq-engine/api/runs/run-1/cfg/export/features/job-77/download",
            "cache_hit": force_cache_hit,
            "source_job_id": "job-1" if force_cache_hit else None,
            "manifest_relpath": "export/features/jobs/job-77/manifest.json",
            "warnings": [],
        }

    monkeypatch.setattr(features_export_rq, "RedisPrep", _RedisPrepStub)
    monkeypatch.setattr(features_export_rq, "execute_features_export", _fake_execute_features_export)
    monkeypatch.setattr(features_export_rq, "get_current_job", lambda: SimpleNamespace(id="job-77"))
    monkeypatch.setattr(features_export_rq, "get_wd", lambda runid: str(tmp_path / runid))
    monkeypatch.setattr(
        features_export_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    return {
        "published": published,
        "execution_calls": execution_calls,
        "prep_instances": prep_instances,
        "tmp_path": tmp_path,
    }


def test_run_features_export_rq_executes_full_export_and_timestamps_completion(
    features_export_rq_environment,
) -> None:
    env = features_export_rq_environment

    result = features_export_rq.run_features_export_rq(
        "run-1",
        "cfg",
        {"format": "geopackage"},
    )

    assert result["cache_hit"] is False
    assert env["execution_calls"][0]["force_cache_hit"] is False

    prep = env["prep_instances"][str(env["tmp_path"] / "run-1")]
    assert prep.removed == [features_export_rq.TaskEnum.run_features_export]
    assert prep.timestamps == [features_export_rq.TaskEnum.run_features_export]
    assert any("TRIGGER features_export FEATURES_EXPORT_TASK_COMPLETED" in m for _, m in env["published"])


def test_run_features_export_cache_hit_rq_sets_cache_hit_flag(
    features_export_rq_environment,
) -> None:
    env = features_export_rq_environment

    result = features_export_rq.run_features_export_cache_hit_rq(
        "run-1",
        "cfg",
        {"format": "geopackage"},
    )

    assert result["cache_hit"] is True
    assert env["execution_calls"][0]["force_cache_hit"] is True


def test_run_features_export_rq_rejects_non_object_payload(
    features_export_rq_environment,
) -> None:
    with pytest.raises(ValueError, match="JSON object"):
        features_export_rq.run_features_export_rq("run-1", "cfg", ["not", "an", "object"])  # type: ignore[arg-type]

