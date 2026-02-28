from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.factories.singleton import singleton_factory
from wepppy.runtime_paths.errors import NoDirError

pytestmark = pytest.mark.unit


@pytest.fixture()
def debris_flow_rq_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    import wepppy.rq.project_rq as project

    published = []
    monkeypatch.setattr(project.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))
    monkeypatch.setattr(project, "get_current_job", lambda: SimpleNamespace(id="job-77"))
    monkeypatch.setattr(project, "get_wd", lambda runid: str(tmp_path / runid))

    redis_prep_cls = singleton_factory(
        "RedisPrepStub",
        attrs={"timestamps": []},
        methods={"timestamp": lambda self, key: self.timestamps.append(key)},
    )
    redis_prep_cls.reset_instances()
    monkeypatch.setattr(project, "RedisPrep", redis_prep_cls)

    def run_debris_flow(self, cc=None, ll=None, req_datasource=None):
        self.calls.append((cc, ll, req_datasource))
        redis_prep_cls.getInstance(self.wd).timestamp(project.TaskEnum.run_debris)

    debris_flow_cls = singleton_factory(
        "DebrisFlowStub",
        attrs={"calls": []},
        methods={"run_debris_flow": run_debris_flow},
    )
    debris_flow_cls.reset_instances()
    monkeypatch.setattr(project, "DebrisFlow", debris_flow_cls)

    return project, debris_flow_cls, redis_prep_cls, published, tmp_path


def test_run_debris_flow_rq_passes_payload(
    debris_flow_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
):
    project, debris_cls, redis_cls, published, base_path = debris_flow_rq_environment

    preflight_calls = []

    def _resolve(wd: str, root: str, view: str = "effective"):
        preflight_calls.append((wd, root, view))

    monkeypatch.setattr(project, "nodir_resolve", _resolve)

    project.run_debris_flow_rq(
        "demo",
        payload={"clay_pct": 5.1, "liquid_limit": 12.3, "datasource": "Holden"},
    )

    run_wd = str(base_path / "demo")
    assert preflight_calls == [
        (run_wd, "soils", "effective"),
        (run_wd, "watershed", "effective"),
        (run_wd, "soils", "effective"),
        (run_wd, "watershed", "effective"),
    ]

    debris_instance = debris_cls.getInstance(run_wd)
    assert debris_instance.calls == [(5.1, 12.3, "Holden")]

    prep_instance = redis_cls.getInstance(run_wd)
    assert project.TaskEnum.run_debris in prep_instance.timestamps
    assert project.TaskEnum.run_watar in prep_instance.timestamps

    assert any("TRIGGER   debris_flow DEBRIS_FLOW_RUN_TASK_COMPLETED" in message for _, message in published)


def test_run_debris_flow_rq_defaults_to_none(
    debris_flow_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
):
    project, debris_cls, redis_cls, _published, base_path = debris_flow_rq_environment

    monkeypatch.setattr(project, "nodir_resolve", lambda wd, root, view="effective": None)

    project.run_debris_flow_rq("demo")

    debris_instance = debris_cls.getInstance(str(base_path / "demo"))
    assert debris_instance.calls == [(None, None, None)]

    prep_instance = redis_cls.getInstance(str(base_path / "demo"))
    assert project.TaskEnum.run_debris in prep_instance.timestamps
    assert project.TaskEnum.run_watar in prep_instance.timestamps


def test_run_debris_flow_rq_stops_on_nodir_preflight_error(
    debris_flow_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
):
    project, debris_cls, _redis_cls, published, base_path = debris_flow_rq_environment

    def _raise_on_watershed(wd: str, root: str, view: str = "effective"):
        if root == "watershed":
            raise NoDirError(http_status=409, code="NODIR_MIXED_STATE", message="mixed root state")
        return None

    monkeypatch.setattr(project, "nodir_resolve", _raise_on_watershed)

    with pytest.raises(NoDirError) as exc_info:
        project.run_debris_flow_rq("demo")

    assert exc_info.value.code == "NODIR_MIXED_STATE"

    run_wd = str(base_path / "demo")
    if run_wd in debris_cls._instances:
        debris_instance = debris_cls.getInstance(run_wd)
        assert debris_instance.calls == []

    assert any("EXCEPTION run_debris_flow_rq(demo)" in message for _, message in published)


def test_run_debris_flow_rq_rejects_archive_form_roots(
    debris_flow_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
):
    project, debris_cls, _redis_cls, published, base_path = debris_flow_rq_environment
    monkeypatch.setattr(
        project,
        "nodir_resolve",
        lambda _wd, _root, view="effective": SimpleNamespace(form="archive"),
    )

    with pytest.raises(NoDirError) as exc_info:
        project.run_debris_flow_rq("demo")

    assert exc_info.value.code == "NODIR_ARCHIVE_ACTIVE"

    run_wd = str(base_path / "demo")
    if run_wd in debris_cls._instances:
        debris_instance = debris_cls.getInstance(run_wd)
        assert debris_instance.calls == []

    assert any("EXCEPTION run_debris_flow_rq(demo)" in message for _, message in published)
