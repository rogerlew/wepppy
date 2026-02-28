from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.factories.singleton import singleton_factory
from wepppy.runtime_paths.errors import NoDirError

pytestmark = pytest.mark.unit


@pytest.fixture()
def ash_rq_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    import wepppy.rq.project_rq as project

    published = []
    run_total_calls = []

    monkeypatch.setattr(project.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))
    monkeypatch.setattr(project, "get_current_job", lambda: SimpleNamespace(id="job-88"))
    monkeypatch.setattr(project, "get_wd", lambda runid: str(tmp_path / runid))
    monkeypatch.setattr(project, "run_totalwatsed3", lambda *args, **kwargs: run_total_calls.append((args, kwargs)))

    redis_prep_cls = singleton_factory(
        "RedisPrepAshStub",
        attrs={"timestamps": []},
        methods={"timestamp": lambda self, key: self.timestamps.append(key)},
    )
    redis_prep_cls.reset_instances()
    monkeypatch.setattr(project, "RedisPrep", redis_prep_cls)

    ash_cls = singleton_factory(
        "AshStub",
        attrs={"calls": []},
        methods={
            "run_ash": (
                lambda self, fire_date, white_depth, black_depth: self.calls.append(
                    (fire_date, white_depth, black_depth)
                )
            )
        },
    )
    ash_cls.reset_instances()
    monkeypatch.setattr(project, "Ash", ash_cls)

    wepp_cls = singleton_factory(
        "WeppStub",
        attrs={"wepp_interchange_dir": "/tmp/wepp/interchange", "baseflow_opts": object()},
        methods={},
    )
    wepp_cls.reset_instances()
    monkeypatch.setattr(project, "Wepp", wepp_cls)

    return project, ash_cls, wepp_cls, redis_prep_cls, published, run_total_calls, tmp_path


def test_run_ash_rq_preflights_roots_before_execution(ash_rq_environment, monkeypatch: pytest.MonkeyPatch):
    project, ash_cls, _wepp_cls, redis_cls, published, run_total_calls, base_path = ash_rq_environment

    preflight_calls = []

    def _resolve(wd: str, root: str, view: str = "effective"):
        preflight_calls.append((wd, root, view))
        return None

    monkeypatch.setattr(project, "nodir_resolve", _resolve)

    project.run_ash_rq("demo", "8/4", 3.0, 5.0)

    run_wd = str(base_path / "demo")
    assert preflight_calls == [
        (run_wd, "climate", "effective"),
        (run_wd, "landuse", "effective"),
        (run_wd, "watershed", "effective"),
        (run_wd, "climate", "effective"),
        (run_wd, "landuse", "effective"),
        (run_wd, "watershed", "effective"),
    ]

    ash_instance = ash_cls.getInstance(run_wd)
    assert ash_instance.calls == [("8/4", 3.0, 5.0)]

    assert len(run_total_calls) == 1
    args, kwargs = run_total_calls[0]
    assert args == ("/tmp/wepp/interchange",)
    assert "baseflow_opts" in kwargs

    prep_instance = redis_cls.getInstance(run_wd)
    assert project.TaskEnum.run_watar in prep_instance.timestamps

    assert any("TRIGGER   ash ASH_RUN_TASK_COMPLETED" in message for _, message in published)


def test_run_ash_rq_stops_on_nodir_preflight_error(ash_rq_environment, monkeypatch: pytest.MonkeyPatch):
    project, ash_cls, _wepp_cls, _redis_cls, published, run_total_calls, base_path = ash_rq_environment

    def _raise_on_watershed(wd: str, root: str, view: str = "effective"):
        if root == "watershed":
            raise NoDirError(http_status=409, code="NODIR_MIXED_STATE", message="mixed root state")
        return None

    monkeypatch.setattr(project, "nodir_resolve", _raise_on_watershed)

    with pytest.raises(NoDirError) as exc_info:
        project.run_ash_rq("demo", "8/4", 3.0, 5.0)

    assert exc_info.value.code == "NODIR_MIXED_STATE"
    assert run_total_calls == []

    run_wd = str(base_path / "demo")
    if run_wd in ash_cls._instances:
        ash_instance = ash_cls.getInstance(run_wd)
        assert ash_instance.calls == []

    assert any("EXCEPTION run_ash_rq(demo)" in message for _, message in published)


def test_run_ash_rq_rejects_archive_form_roots(ash_rq_environment, monkeypatch: pytest.MonkeyPatch):
    project, ash_cls, _wepp_cls, _redis_cls, published, run_total_calls, base_path = ash_rq_environment

    monkeypatch.setattr(
        project,
        "nodir_resolve",
        lambda _wd, _root, view="effective": SimpleNamespace(form="archive"),
    )

    with pytest.raises(NoDirError) as exc_info:
        project.run_ash_rq("demo", "8/4", 3.0, 5.0)

    assert exc_info.value.code == "NODIR_ARCHIVE_ACTIVE"
    assert run_total_calls == []

    run_wd = str(base_path / "demo")
    if run_wd in ash_cls._instances:
        ash_instance = ash_cls.getInstance(run_wd)
        assert ash_instance.calls == []

    assert any("EXCEPTION run_ash_rq(demo)" in message for _, message in published)
