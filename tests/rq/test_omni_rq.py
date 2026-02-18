from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.factories.singleton import singleton_factory
from wepppy.nodir.errors import NoDirError

import wepppy.rq.omni_rq as omni_rq

pytestmark = pytest.mark.unit


@pytest.fixture()
def omni_rq_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    published = []
    monkeypatch.setattr(omni_rq.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))
    monkeypatch.setattr(omni_rq, "get_current_job", lambda: SimpleNamespace(id="job-19"))
    monkeypatch.setattr(omni_rq, "get_wd", lambda runid: str(tmp_path / runid))

    redis_prep_cls = singleton_factory(
        "RedisPrepOmniStub",
        attrs={"timestamps": []},
        methods={"timestamp": lambda self, key: self.timestamps.append(key)},
    )
    redis_prep_cls.reset_instances()
    monkeypatch.setattr(omni_rq, "RedisPrep", redis_prep_cls)

    omni_cls = singleton_factory(
        "OmniRqStub",
        attrs={
            "use_rq_job_pool_concurrency": False,
            "run_calls": 0,
        },
        methods={
            "run_omni_scenarios": lambda self: setattr(self, "run_calls", self.run_calls + 1),
        },
    )
    omni_cls.reset_instances()
    monkeypatch.setattr(omni_rq, "Omni", omni_cls)

    return redis_prep_cls, omni_cls, published, tmp_path


def test_run_omni_scenarios_rq_preflights_roots_before_execution(
    omni_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
):
    redis_cls, omni_cls, published, base_path = omni_rq_environment

    preflight_calls = []

    def _resolve(wd: str, root: str, view: str = "effective"):
        preflight_calls.append((wd, root, view))

    monkeypatch.setattr(omni_rq, "nodir_resolve", _resolve)

    result = omni_rq.run_omni_scenarios_rq("demo")

    assert result is None

    run_wd = str(base_path / "demo")
    assert preflight_calls == [
        (run_wd, "climate", "effective"),
        (run_wd, "watershed", "effective"),
        (run_wd, "landuse", "effective"),
        (run_wd, "soils", "effective"),
    ]

    omni_instance = omni_cls.getInstance(run_wd)
    assert omni_instance.run_calls == 1

    prep_instance = redis_cls.getInstance(run_wd)
    assert omni_rq.TaskEnum.run_omni_scenarios in prep_instance.timestamps

    assert any("TRIGGER omni OMNI_SCENARIO_RUN_TASK_COMPLETED" in message for _, message in published)


def test_run_omni_scenarios_rq_stops_on_nodir_preflight_error(
    omni_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
):
    _redis_cls, omni_cls, published, base_path = omni_rq_environment

    def _raise_on_landuse(wd: str, root: str, view: str = "effective"):
        if root == "landuse":
            raise NoDirError(http_status=409, code="NODIR_MIXED_STATE", message="mixed root state")
        return None

    monkeypatch.setattr(omni_rq, "nodir_resolve", _raise_on_landuse)

    with pytest.raises(NoDirError) as exc_info:
        omni_rq.run_omni_scenarios_rq("demo")

    assert exc_info.value.code == "NODIR_MIXED_STATE"

    run_wd = str(base_path / "demo")
    if run_wd in omni_cls._instances:
        omni_instance = omni_cls.getInstance(run_wd)
        assert omni_instance.run_calls == 0

    assert any("EXCEPTION run_omni_scenarios_rq(demo)" in message for _, message in published)
