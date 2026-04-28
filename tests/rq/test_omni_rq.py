from __future__ import annotations

import logging
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.factories.singleton import singleton_factory
from wepppy.runtime_paths.errors import NoDirError

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
    event_log: list[str] = []

    def _resolve(wd: str, root: str, view: str = "effective"):
        event_log.append(root)
        preflight_calls.append((wd, root, view))

    monkeypatch.setattr(
        omni_rq,
        "clear_nodb_file_cache",
        lambda runid, *, pup_relpath: event_log.append(f"clear:{pup_relpath}"),
    )
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
    assert event_log == [
        "climate",
        "watershed",
        "landuse",
        "soils",
        "clear:omni.nodb",
    ]

    omni_instance = omni_cls.getInstance(run_wd)
    assert omni_instance.run_calls == 1

    prep_instance = redis_cls.getInstance(run_wd)
    assert omni_rq.TaskEnum.run_omni_scenarios in prep_instance.timestamps

    assert any("TRIGGER omni OMNI_SCENARIO_RUN_TASK_COMPLETED" in message for _, message in published)


def test_run_omni_scenarios_rq_rejects_mixed_soils_without_recovery(
    omni_rq_environment,
) -> None:
    _redis_cls, omni_cls, published, base_path = omni_rq_environment

    run_wd = base_path / "demo"
    run_wd.mkdir(parents=True, exist_ok=True)
    (run_wd / "soils").mkdir()
    (run_wd / "soils.nodir").write_bytes(b"placeholder archive")

    with pytest.raises(NoDirError) as exc_info:
        omni_rq.run_omni_scenarios_rq("demo")

    assert exc_info.value.code == "NODIR_MIXED_STATE"
    assert "mixed state" in exc_info.value.message
    assert (run_wd / "soils.nodir").exists()
    assert (run_wd / "soils").exists()
    assert not any("Recovered mixed NoDir roots" in message for _, message in published)

    omni_instance = omni_cls.getInstance(str(run_wd))
    assert omni_instance.run_calls == 0


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


def test_run_omni_scenarios_rq_concurrency_uses_helper_outputs_for_dependency_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(omni_rq.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))

    parent_job = SimpleNamespace(id="job-31", meta={}, saves=0)

    def _save() -> None:
        parent_job.saves += 1

    parent_job.save = _save  # type: ignore[attr-defined]

    monkeypatch.setattr(omni_rq, "get_current_job", lambda: parent_job)
    monkeypatch.setattr(omni_rq, "get_wd", lambda runid: str(tmp_path / runid))
    monkeypatch.setattr(omni_rq, "nodir_resolve", lambda wd, root, view="effective": None)
    monkeypatch.setattr(omni_rq, "_hash_file_sha1", lambda path: f"sha:{path}")

    class _RedisCtx:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(omni_rq.redis, "Redis", lambda **kwargs: _RedisCtx(**kwargs))
    monkeypatch.setattr(omni_rq, "redis_connection_kwargs", lambda db: {"db": int(db)})

    enqueue_calls: list[dict] = []

    class _QueueStub:
        def __init__(self, name: str, connection=None) -> None:
            assert name == "batch"
            self.connection = connection

        def enqueue_call(self, func, args=(), kwargs=None, timeout=None, depends_on=None):
            job = SimpleNamespace(id=f"child-{len(enqueue_calls) + 1}")
            enqueue_calls.append(
                {
                    "func": func,
                    "args": args,
                    "kwargs": kwargs or {},
                    "timeout": timeout,
                    "depends_on": depends_on,
                    "job": job,
                }
            )
            return job

    monkeypatch.setattr(omni_rq, "Queue", _QueueStub)

    class OmniStub:
        _instances: dict[str, "OmniStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.logger = logging.getLogger("tests.rq.omni.scenarios.concurrency")
            self.use_rq_job_pool_concurrency = True
            self.scenario_dependency_tree: dict[str, dict] = {}
            self.scenario_run_state: list[dict] = []
            self.scenarios = [
                {"type": "uniform_low"},
                {"type": "mulch", "base_scenario": "uniform_low"},
            ]
            self.base_scenario = omni_rq.OmniScenario.Undisturbed
            self.helper_calls: list[tuple[str, object]] = []

        @classmethod
        def getInstance(cls, wd: str) -> "OmniStub":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def _scenario_dependency_target(self, scenario_enum, scenario_payload):
            self.helper_calls.append(("dependency_target", scenario_enum))
            if scenario_enum == omni_rq.OmniScenario.Mulch:
                return scenario_payload.get("base_scenario")
            return "undisturbed"

        def _loss_pw0_path_for_scenario(self, scenario_name):
            self.helper_calls.append(("loss_path", scenario_name))
            return f"/dep/{scenario_name}/loss_pw0.txt"

        def _scenario_signature(self, scenario_payload):
            self.helper_calls.append(("signature", dict(scenario_payload)))
            return f"sig:{scenario_payload['type']}"

        def _normalize_scenario_key(self, scenario_name):
            self.helper_calls.append(("normalize_key", scenario_name))
            return f"key:{scenario_name}"

    monkeypatch.setattr(omni_rq, "Omni", OmniStub)

    result = omni_rq.run_omni_scenarios_rq("demo")

    run_wd = str(tmp_path / "demo")
    omni = OmniStub.getInstance(run_wd)

    assert result.id == "child-4"
    assert len(enqueue_calls) == 4

    stage1 = enqueue_calls[0]
    assert stage1["func"] is omni_rq.run_omni_scenario_rq
    assert stage1["args"][0] == "demo"
    assert stage1["kwargs"]["dependency_target"] == "key:undisturbed"
    assert stage1["kwargs"]["dependency_path"] == "/dep/undisturbed/loss_pw0.txt"
    assert stage1["kwargs"]["signature"] == "sig:uniform_low"

    stage2 = enqueue_calls[1]
    assert stage2["func"] is omni_rq.run_omni_scenario_rq
    assert stage2["kwargs"]["dependency_target"] == "key:uniform_low"
    assert stage2["kwargs"]["dependency_path"] == "/dep/uniform_low/loss_pw0.txt"
    assert stage2["kwargs"]["signature"] == "sig:mulch"
    assert isinstance(stage2["depends_on"], list)
    assert stage2["depends_on"][0].id == stage1["job"].id

    compile_job = enqueue_calls[2]
    assert compile_job["func"] is omni_rq._compile_hillslope_summaries_rq
    assert isinstance(compile_job["depends_on"], list)
    assert compile_job["depends_on"][0].id == stage2["job"].id

    finalize_job = enqueue_calls[3]
    assert finalize_job["func"] is omni_rq._finalize_omni_scenarios_rq
    assert isinstance(finalize_job["depends_on"], list)
    assert finalize_job["depends_on"][0].id == compile_job["job"].id

    assert any(kind == "dependency_target" for kind, _ in omni.helper_calls)
    assert any(kind == "loss_path" for kind, _ in omni.helper_calls)
    assert any(kind == "signature" for kind, _ in omni.helper_calls)
    assert any(kind == "normalize_key" for kind, _ in omni.helper_calls)
    assert parent_job.saves == 4
    assert any("COMPLETED run_omni_scenarios_rq(demo)" in message for _, message in published)


def test_run_omni_scenario_rq_updates_dependency_state_with_supplied_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(omni_rq.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))
    monkeypatch.setattr(omni_rq, "get_current_job", lambda: SimpleNamespace(id="job-41"))
    monkeypatch.setattr(omni_rq, "get_wd", lambda runid: str(tmp_path / runid))
    monkeypatch.setattr(omni_rq, "_hash_file_sha1", lambda path: "sha-new")
    call_order: list[str] = []
    monkeypatch.setattr(
        omni_rq,
        "clear_nodb_file_cache",
        lambda runid, *, pup_relpath: call_order.append(f"clear:{pup_relpath}"),
    )

    update_calls: list[tuple[dict, dict]] = []
    monkeypatch.setattr(
        omni_rq,
        "_update_dependency_state",
        lambda omni, scenario_name, dependency_entry, run_state_entry: update_calls.append(
            (dependency_entry, run_state_entry)
        ),
    )

    class OmniStub:
        _instances: dict[str, "OmniStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.run_payloads: list[dict] = []

        @classmethod
        def getInstance(cls, wd: str) -> "OmniStub":
            call_order.append("get_instance")
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def run_omni_scenario(self, payload: dict) -> None:
            self.run_payloads.append(payload)

    monkeypatch.setattr(omni_rq, "Omni", OmniStub)

    status, elapsed = omni_rq.run_omni_scenario_rq(
        "demo",
        {"type": "uniform_low"},
        dependency_target="undisturbed",
        dependency_path="/tmp/loss_pw0.txt",
        signature="sig-1",
    )

    run_wd = str(tmp_path / "demo")
    omni = OmniStub.getInstance(run_wd)

    assert status is True
    assert elapsed >= 0.0
    assert call_order[:2] == ["clear:omni.nodb", "get_instance"]
    assert omni.run_payloads[0]["type"] == omni_rq.OmniScenario.UniformLow
    assert update_calls
    dependency_entry, run_state_entry = update_calls[0]
    assert dependency_entry["dependency_target"] == "undisturbed"
    assert dependency_entry["dependency_path"] == "/tmp/loss_pw0.txt"
    assert dependency_entry["dependency_sha1"] == "sha-new"
    assert run_state_entry["scenario"] == "uniform_low"
    assert run_state_entry["reason"] == "dependency_changed"
    assert any("COMPLETED run_omni_scenario_rq(demo)" in message for _, message in published)


def test_run_omni_scenario_rq_derives_dependency_metadata_from_helpers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(omni_rq.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))
    monkeypatch.setattr(omni_rq, "get_current_job", lambda: SimpleNamespace(id="job-42"))
    monkeypatch.setattr(omni_rq, "get_wd", lambda runid: str(tmp_path / runid))
    monkeypatch.setattr(omni_rq, "_hash_file_sha1", lambda path: f"sha:{path}")

    update_calls: list[tuple[dict, dict]] = []
    monkeypatch.setattr(
        omni_rq,
        "_update_dependency_state",
        lambda omni, scenario_name, dependency_entry, run_state_entry: update_calls.append(
            (dependency_entry, run_state_entry)
        ),
    )

    class OmniStub:
        _instances: dict[str, "OmniStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.calls: list[tuple[str, object]] = []

        @classmethod
        def getInstance(cls, wd: str) -> "OmniStub":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def _scenario_dependency_target(self, scenario_enum, scenario_payload):
            self.calls.append(("dependency_target", scenario_enum))
            return "undisturbed"

        def _normalize_scenario_key(self, value):
            self.calls.append(("normalize_scenario_key", value))
            return f"key:{value}"

        def _loss_pw0_path_for_scenario(self, value):
            self.calls.append(("loss_path", value))
            return f"/dep/{value}/loss_pw0.txt"

        def _scenario_signature(self, scenario_payload):
            self.calls.append(("signature", dict(scenario_payload)))
            return "sig:uniform_low"

        def run_omni_scenario(self, payload: dict) -> None:
            self.calls.append(("run", payload["type"]))

    monkeypatch.setattr(omni_rq, "Omni", OmniStub)

    status, elapsed = omni_rq.run_omni_scenario_rq("demo", {"type": "uniform_low"})

    run_wd = str(tmp_path / "demo")
    omni = OmniStub.getInstance(run_wd)

    assert status is True
    assert elapsed >= 0.0
    assert update_calls
    dependency_entry, run_state_entry = update_calls[0]
    assert dependency_entry["dependency_target"] == "key:undisturbed"
    assert dependency_entry["dependency_path"] == "/dep/undisturbed/loss_pw0.txt"
    assert dependency_entry["dependency_sha1"] == "sha:/dep/undisturbed/loss_pw0.txt"
    assert dependency_entry["signature"] == "sig:uniform_low"
    assert run_state_entry["scenario"] == "uniform_low"
    assert run_state_entry["dependency_target"] == "key:undisturbed"
    assert run_state_entry["dependency_path"] == "/dep/undisturbed/loss_pw0.txt"
    assert any(kind == "dependency_target" for kind, _ in omni.calls)
    assert any(kind == "normalize_scenario_key" for kind, _ in omni.calls)
    assert any(kind == "loss_path" for kind, _ in omni.calls)
    assert any(kind == "signature" for kind, _ in omni.calls)
    assert any(kind == "run" for kind, _ in omni.calls)
    assert any("COMPLETED run_omni_scenario_rq(demo)" in message for _, message in published)


def test_run_omni_contrast_rq_emits_trigger_and_passes_job_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(omni_rq.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))
    monkeypatch.setattr(omni_rq, "get_current_job", lambda: SimpleNamespace(id="job-52"))
    monkeypatch.setattr(omni_rq, "get_wd", lambda runid: str(tmp_path / runid))
    call_order: list[str] = []
    monkeypatch.setattr(
        omni_rq,
        "clear_nodb_file_cache",
        lambda runid, *, pup_relpath: call_order.append(f"clear:{pup_relpath}"),
    )

    class OmniStub:
        _instances: dict[str, "OmniStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.contrast_names = ["c1"]
            self.calls: list[tuple[int, str]] = []

        @classmethod
        def getInstance(cls, wd: str) -> "OmniStub":
            call_order.append("get_instance")
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def run_omni_contrast(self, contrast_id: int, *, rq_job_id: str | None = None) -> None:
            self.calls.append((contrast_id, rq_job_id or ""))

    monkeypatch.setattr(omni_rq, "Omni", OmniStub)

    status, elapsed = omni_rq.run_omni_contrast_rq("demo", 1)

    run_wd = str(tmp_path / "demo")
    omni = OmniStub.getInstance(run_wd)
    assert status is True
    assert elapsed >= 0.0
    assert call_order[:2] == ["clear:omni.nodb", "get_instance"]
    assert omni.calls == [(1, "job-52")]
    assert any("TRIGGER omni_contrasts OMNI_CONTRAST_RUN_TASK_COMPLETED" in message for _, message in published)


def test_run_omni_contrasts_rq_clears_dependency_tree_when_no_contrasts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(omni_rq.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))
    monkeypatch.setattr(omni_rq, "get_current_job", lambda: SimpleNamespace(id="job-61", meta={}, save=lambda: None))
    monkeypatch.setattr(omni_rq, "get_wd", lambda runid: str(tmp_path / runid))
    call_order: list[str] = []
    monkeypatch.setattr(
        omni_rq,
        "clear_nodb_file_cache",
        lambda runid, *, pup_relpath: call_order.append(f"clear:{pup_relpath}"),
    )

    class OmniStub:
        _instances: dict[str, "OmniStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.logger = logging.getLogger("tests.rq.omni.contrasts")
            self.contrast_names: list[str] = []
            self.contrast_dependency_tree = {"stale": {"dep": "x"}}
            self.cleaned_ids: list[list[int]] = []

        @classmethod
        def getInstance(cls, wd: str) -> "OmniStub":
            call_order.append("get_instance")
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def _clean_stale_contrast_runs(self, active_ids):
            self.cleaned_ids.append(list(active_ids))

    monkeypatch.setattr(omni_rq, "Omni", OmniStub)

    result = omni_rq.run_omni_contrasts_rq("demo")

    run_wd = str(tmp_path / "demo")
    omni = OmniStub.getInstance(run_wd)

    assert result is None
    assert call_order[:2] == ["clear:omni.nodb", "get_instance"]
    assert omni.contrast_dependency_tree == {}
    assert omni.cleaned_ids == [[]]
    assert any("TRIGGER omni_contrasts END_BROADCAST" in message for _, message in published)


def test_delete_omni_contrasts_rq_clears_scoped_cache_before_hydration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    published: list[tuple[str, str]] = []
    call_order: list[str] = []

    monkeypatch.setattr(omni_rq.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))
    monkeypatch.setattr(omni_rq, "get_current_job", lambda: SimpleNamespace(id="job-65"))
    monkeypatch.setattr(omni_rq, "get_wd", lambda runid: str(tmp_path / runid))
    monkeypatch.setattr(
        omni_rq,
        "clear_nodb_file_cache",
        lambda runid, *, pup_relpath: call_order.append(f"clear:{pup_relpath}"),
    )

    class OmniStub:
        _instances: dict[str, "OmniStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.clear_calls = 0

        @classmethod
        def getInstance(cls, wd: str) -> "OmniStub":
            call_order.append("get_instance")
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def clear_contrasts(self) -> None:
            self.clear_calls += 1

    monkeypatch.setattr(omni_rq, "Omni", OmniStub)
    monkeypatch.setattr(
        omni_rq.RedisPrep,
        "getInstance",
        lambda _wd: SimpleNamespace(remove_timestamp=lambda _task: None),
    )

    omni_rq.delete_omni_contrasts_rq("demo")

    run_wd = str(tmp_path / "demo")
    omni = OmniStub.getInstance(run_wd)
    assert call_order[:2] == ["clear:omni.nodb", "get_instance"]
    assert omni.clear_calls == 1
    assert any("TRIGGER omni_contrasts END_BROADCAST" in message for _, message in published)


def test_run_omni_contrasts_rq_landuse_skip_prunes_dependency_entries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(omni_rq.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))
    monkeypatch.setattr(omni_rq, "get_current_job", lambda: SimpleNamespace(id="job-62", meta={}, save=lambda: None))
    monkeypatch.setattr(omni_rq, "get_wd", lambda runid: str(tmp_path / runid))

    class OmniStub:
        _instances: dict[str, "OmniStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.logger = logging.getLogger("tests.rq.omni.contrasts.landuse")
            self.contrast_names = [
                "undisturbed,1__to__mulch",
                "undisturbed,2__to__mulch",
                None,
            ]
            self.contrast_dependency_tree = {
                "undisturbed,1__to__mulch": {"signature": "old-a"},
                "stale,3__to__mulch": {"signature": "old-b"},
            }
            self.cleaned_stale_ids: list[list[int]] = []
            self.cleaned_contrast_ids: list[int] = []
            self.landuse_cache_ids: list[int] = []
            self.status_calls: list[int] = []
            self.sidecar_paths = {
                2: str(tmp_path / "demo" / "_pups" / "omni" / "contrasts" / "2" / "sidecar.json"),
            }

        @classmethod
        def getInstance(cls, wd: str) -> "OmniStub":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def _contrast_landuse_skip_reason(self, contrast_id, contrast_name, *, landuse_cache=None):
            self.landuse_cache_ids.append(id(landuse_cache))
            if contrast_id == 1:
                return "landuse_unchanged"
            return None

        def _clean_contrast_run(self, contrast_id: int) -> None:
            self.cleaned_contrast_ids.append(contrast_id)

        def _contrast_sidecar_path(self, contrast_id: int) -> str:
            return self.sidecar_paths.get(int(contrast_id), "")

        def _contrast_run_status(self, contrast_id: int, contrast_name: str) -> str:
            self.status_calls.append(int(contrast_id))
            return "up_to_date"

        def _clean_stale_contrast_runs(self, active_ids):
            self.cleaned_stale_ids.append(list(active_ids))

    monkeypatch.setattr(omni_rq, "Omni", OmniStub)

    sidecar_path = tmp_path / "demo" / "_pups" / "omni" / "contrasts" / "2" / "sidecar.json"
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text("{}", encoding="ascii")

    result = omni_rq.run_omni_contrasts_rq("demo")

    run_wd = str(tmp_path / "demo")
    omni = OmniStub.getInstance(run_wd)

    assert result is None
    assert omni.cleaned_contrast_ids == [1]
    assert omni.cleaned_stale_ids == [[1, 2]]
    assert omni.status_calls == [2]
    assert len(set(omni.landuse_cache_ids)) == 1
    assert omni.contrast_dependency_tree == {}
    assert any("TRIGGER omni_contrasts END_BROADCAST" in message for _, message in published)


def test_run_omni_contrasts_rq_reruns_hillslopes_for_deduped_scenarios_when_delete_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        omni_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    parent_job = SimpleNamespace(id="job-63", meta={}, saves=0)

    def _save() -> None:
        parent_job.saves += 1

    parent_job.save = _save  # type: ignore[attr-defined]
    monkeypatch.setattr(omni_rq, "get_current_job", lambda: parent_job)
    monkeypatch.setattr(omni_rq, "get_wd", lambda runid: str(tmp_path / runid))

    class _RedisCtx:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(omni_rq.redis, "Redis", lambda **kwargs: _RedisCtx(**kwargs))
    monkeypatch.setattr(omni_rq, "redis_connection_kwargs", lambda db: {"db": int(db)})

    events: list[tuple[object, ...]] = []
    enqueue_calls: list[dict[str, object]] = []

    class _QueueStub:
        def __init__(self, name: str, connection=None) -> None:
            assert name == "batch"
            self.connection = connection

        def enqueue_call(self, func, args=(), kwargs=None, timeout=None, depends_on=None):
            job = SimpleNamespace(id=f"child-{len(enqueue_calls) + 1}")
            enqueue_calls.append(
                {
                    "func": func,
                    "args": args,
                    "kwargs": kwargs or {},
                    "timeout": timeout,
                    "depends_on": depends_on,
                    "job": job,
                }
            )
            events.append(("enqueue", func.__name__))
            return job

    monkeypatch.setattr(omni_rq, "Queue", _QueueStub)
    monkeypatch.setattr(
        omni_rq,
        "_validate_contrast_hillslope_rerun_inputs",
        lambda **_kwargs: None,
    )

    class _WeppInstance:
        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.runs_dir = os.path.join(wd, "wepp", "runs")

        def run_hillslopes(self, **kwargs) -> None:
            events.append(("rerun", self.wd, kwargs))

    class _WeppStub:
        @staticmethod
        def getInstance(wd: str) -> _WeppInstance:
            return _WeppInstance(wd)

    monkeypatch.setattr(omni_rq, "Wepp", _WeppStub)

    class OmniStub:
        _instances: dict[str, "OmniStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.logger = logging.getLogger("tests.rq.omni.contrasts.rerun")
            self.delete_after_interchange = True
            self.base_scenario = "undisturbed"
            self.contrast_names = [
                "undisturbed,1__to__mulch",
                "undisturbed,2__to__mulch",
            ]
            self.contrast_dependency_tree: dict[str, dict[str, str]] = {}
            self.contrast_batch_size = 2
            self.rq_job_pool_max_worker_per_scenario_task = 7
            self.sidecar_paths = {
                1: str(tmp_path / "demo" / "_pups" / "omni" / "contrasts" / "1" / "sidecar.json"),
                2: str(tmp_path / "demo" / "_pups" / "omni" / "contrasts" / "2" / "sidecar.json"),
            }
            self.cleaned_stale_ids: list[list[int]] = []

        @classmethod
        def getInstance(cls, wd: str) -> "OmniStub":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def _contrast_landuse_skip_reason(self, *_args, **_kwargs):
            return None

        def _clean_contrast_run(self, _contrast_id: int) -> None:
            return None

        def _contrast_sidecar_path(self, contrast_id: int) -> str:
            return self.sidecar_paths[int(contrast_id)]

        def _contrast_run_status(self, _contrast_id: int, _contrast_name: str) -> str:
            return "needs_run"

        def _clean_stale_contrast_runs(self, active_ids):
            self.cleaned_stale_ids.append(list(active_ids))

        def _contrast_scenario_keys(self, _contrast_name: str) -> tuple[str, str]:
            return "undisturbed", "mulch"

        def _normalize_scenario_key(self, value):
            return str(value)

    monkeypatch.setattr(omni_rq, "Omni", OmniStub)

    sidecar_1 = tmp_path / "demo" / "_pups" / "omni" / "contrasts" / "1" / "sidecar.json"
    sidecar_2 = tmp_path / "demo" / "_pups" / "omni" / "contrasts" / "2" / "sidecar.json"
    sidecar_1.parent.mkdir(parents=True, exist_ok=True)
    sidecar_2.parent.mkdir(parents=True, exist_ok=True)
    sidecar_1.write_text("{}", encoding="ascii")
    sidecar_2.write_text("{}", encoding="ascii")
    (tmp_path / "demo" / "_pups" / "omni" / "scenarios" / "mulch").mkdir(parents=True, exist_ok=True)

    result = omni_rq.run_omni_contrasts_rq("demo")

    run_wd = str(tmp_path / "demo")
    mulch_wd = str(tmp_path / "demo" / "_pups" / "omni" / "scenarios" / "mulch")
    expected_rerun_paths = {
        run_wd,
        mulch_wd,
    }
    rerun_events = [
        (item[1], item[2])
        for item in events
        if item[0] == "rerun"
    ]
    enqueue_event_positions = [idx for idx, item in enumerate(events) if item[0] == "enqueue"]
    rerun_event_positions = [idx for idx, item in enumerate(events) if item[0] == "rerun"]
    rerun_paths = [wd for wd, _kwargs in rerun_events]
    rerun_kwargs_by_wd = {wd: kwargs for wd, kwargs in rerun_events}
    expected_scenario_relpath = os.path.relpath(
        os.path.join(run_wd, "wepp", "runs"),
        os.path.join(mulch_wd, "wepp", "runs"),
    )
    if not expected_scenario_relpath.endswith("/"):
        expected_scenario_relpath += "/"

    assert result.id == "child-3"
    assert set(rerun_paths) == expected_rerun_paths
    assert len(rerun_paths) == 2
    assert rerun_event_positions
    assert enqueue_event_positions
    assert max(rerun_event_positions) < min(enqueue_event_positions)
    assert rerun_kwargs_by_wd[run_wd]["cli_relpath"] == ""
    assert rerun_kwargs_by_wd[run_wd]["slp_relpath"] == ""
    assert rerun_kwargs_by_wd[mulch_wd]["cli_relpath"] == expected_scenario_relpath
    assert rerun_kwargs_by_wd[mulch_wd]["slp_relpath"] == expected_scenario_relpath
    assert rerun_kwargs_by_wd[mulch_wd]["man_relpath"] == ""
    assert rerun_kwargs_by_wd[mulch_wd]["sol_relpath"] == ""
    assert rerun_kwargs_by_wd[run_wd]["max_workers"] == 7
    assert rerun_kwargs_by_wd[mulch_wd]["max_workers"] == 7
    assert any("rerunning_hillslopes scenarios=mulch,undisturbed" in message for _, message in published)


def test_run_omni_contrasts_rq_does_not_rerun_hillslopes_when_delete_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        omni_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    parent_job = SimpleNamespace(id="job-64", meta={}, saves=0)

    def _save() -> None:
        parent_job.saves += 1

    parent_job.save = _save  # type: ignore[attr-defined]
    monkeypatch.setattr(omni_rq, "get_current_job", lambda: parent_job)
    monkeypatch.setattr(omni_rq, "get_wd", lambda runid: str(tmp_path / runid))

    class _RedisCtx:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(omni_rq.redis, "Redis", lambda **kwargs: _RedisCtx(**kwargs))
    monkeypatch.setattr(omni_rq, "redis_connection_kwargs", lambda db: {"db": int(db)})

    enqueue_calls: list[dict[str, object]] = []

    class _QueueStub:
        def __init__(self, name: str, connection=None) -> None:
            assert name == "batch"
            self.connection = connection

        def enqueue_call(self, func, args=(), kwargs=None, timeout=None, depends_on=None):
            job = SimpleNamespace(id=f"child-{len(enqueue_calls) + 1}")
            enqueue_calls.append(
                {
                    "func": func,
                    "args": args,
                    "kwargs": kwargs or {},
                    "timeout": timeout,
                    "depends_on": depends_on,
                    "job": job,
                }
            )
            return job

    monkeypatch.setattr(omni_rq, "Queue", _QueueStub)

    class _WeppStub:
        @staticmethod
        def getInstance(_wd: str):
            raise AssertionError("Wepp.getInstance should not be called when delete_after_interchange is disabled")

    monkeypatch.setattr(omni_rq, "Wepp", _WeppStub)

    class OmniStub:
        _instances: dict[str, "OmniStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.logger = logging.getLogger("tests.rq.omni.contrasts.no-rerun")
            self.delete_after_interchange = False
            self.base_scenario = "undisturbed"
            self.contrast_names = ["undisturbed,1__to__mulch"]
            self.contrast_dependency_tree: dict[str, dict[str, str]] = {}
            self.contrast_batch_size = 1
            self.sidecar_paths = {
                1: str(tmp_path / "demo" / "_pups" / "omni" / "contrasts" / "1" / "sidecar.json"),
            }
            self.cleaned_stale_ids: list[list[int]] = []

        @classmethod
        def getInstance(cls, wd: str) -> "OmniStub":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def _contrast_landuse_skip_reason(self, *_args, **_kwargs):
            return None

        def _clean_contrast_run(self, _contrast_id: int) -> None:
            return None

        def _contrast_sidecar_path(self, contrast_id: int) -> str:
            return self.sidecar_paths[int(contrast_id)]

        def _contrast_run_status(self, _contrast_id: int, _contrast_name: str) -> str:
            return "needs_run"

        def _clean_stale_contrast_runs(self, active_ids):
            self.cleaned_stale_ids.append(list(active_ids))

        def _contrast_scenario_keys(self, _contrast_name: str) -> tuple[str, str]:
            return "undisturbed", "mulch"

        def _normalize_scenario_key(self, value):
            return str(value)

    monkeypatch.setattr(omni_rq, "Omni", OmniStub)

    sidecar = tmp_path / "demo" / "_pups" / "omni" / "contrasts" / "1" / "sidecar.json"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text("{}", encoding="ascii")

    result = omni_rq.run_omni_contrasts_rq("demo")

    assert result.id == "child-2"
    assert len(enqueue_calls) == 2
    assert not any("rerunning_hillslopes" in message for _, message in published)


def test_validate_contrast_hillslope_rerun_inputs_allows_base_cli_slp_relpaths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        omni_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    base_runs_dir = tmp_path / "base" / "wepp" / "runs"
    scenario_runs_dir = tmp_path / "scenario" / "wepp" / "runs"
    base_runs_dir.mkdir(parents=True, exist_ok=True)
    scenario_runs_dir.mkdir(parents=True, exist_ok=True)

    (base_runs_dir / "p1.cli").write_text("", encoding="ascii")
    (base_runs_dir / "p1.slp").write_text("", encoding="ascii")
    (scenario_runs_dir / "p1.man").write_text("", encoding="ascii")
    (scenario_runs_dir / "p1.sol").write_text("", encoding="ascii")

    class _TranslatorStub:
        @staticmethod
        def wepp(*, top: int) -> int:
            return top

    class _WatershedStub:
        _subs_summary = [1]

        @staticmethod
        def translator_factory() -> _TranslatorStub:
            return _TranslatorStub()

    wepp = SimpleNamespace(
        runs_dir=str(scenario_runs_dir),
        watershed_instance=_WatershedStub(),
    )
    relpath_to_base_runs = omni_rq._hillslope_input_relpath_to_base_runs(
        str(base_runs_dir),
        str(scenario_runs_dir),
    )

    omni_rq._validate_contrast_hillslope_rerun_inputs(
        wepp=wepp,
        scenario_key="mulch",
        man_relpath="",
        cli_relpath=relpath_to_base_runs,
        slp_relpath=relpath_to_base_runs,
        sol_relpath="",
        status_channel="demo:omni",
        job_id="job-70",
    )

    assert published == []


def test_validate_contrast_hillslope_rerun_inputs_reports_missing_local_man_sol(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        omni_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    base_runs_dir = tmp_path / "base" / "wepp" / "runs"
    scenario_runs_dir = tmp_path / "scenario" / "wepp" / "runs"
    base_runs_dir.mkdir(parents=True, exist_ok=True)
    scenario_runs_dir.mkdir(parents=True, exist_ok=True)

    (base_runs_dir / "p1.cli").write_text("", encoding="ascii")
    (base_runs_dir / "p1.slp").write_text("", encoding="ascii")

    class _TranslatorStub:
        @staticmethod
        def wepp(*, top: int) -> int:
            return top

    class _WatershedStub:
        _subs_summary = [1]

        @staticmethod
        def translator_factory() -> _TranslatorStub:
            return _TranslatorStub()

    wepp = SimpleNamespace(
        runs_dir=str(scenario_runs_dir),
        watershed_instance=_WatershedStub(),
    )
    relpath_to_base_runs = omni_rq._hillslope_input_relpath_to_base_runs(
        str(base_runs_dir),
        str(scenario_runs_dir),
    )

    with pytest.raises(FileNotFoundError) as exc_info:
        omni_rq._validate_contrast_hillslope_rerun_inputs(
            wepp=wepp,
            scenario_key="mulch",
            man_relpath="",
            cli_relpath=relpath_to_base_runs,
            slp_relpath=relpath_to_base_runs,
            sol_relpath="",
            status_channel="demo:omni",
            job_id="job-71",
        )

    error_text = str(exc_info.value)
    assert "scenario=mulch" in error_text
    assert "man=1" in error_text
    assert "sol=1" in error_text
    assert any("missing_hillslope_inputs" in message for _channel, message in published)
    assert any("counts=man=1, sol=1" in message for _channel, message in published)


def test_finalize_omni_scenarios_rq_timestamps_and_triggers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(omni_rq.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))
    monkeypatch.setattr(omni_rq, "get_current_job", lambda: SimpleNamespace(id="job-71"))
    monkeypatch.setattr(omni_rq, "get_wd", lambda runid: str(tmp_path / runid))

    class PrepStub:
        def __init__(self) -> None:
            self.timestamps: list[object] = []

        def timestamp(self, task) -> None:
            self.timestamps.append(task)

    prep = PrepStub()
    monkeypatch.setattr(omni_rq.RedisPrep, "getInstance", lambda wd: prep)
    monkeypatch.setattr(omni_rq, "send_discord_message", lambda message: None)

    omni_rq._finalize_omni_scenarios_rq("demo")

    assert prep.timestamps == [omni_rq.TaskEnum.run_omni_scenarios]
    assert any("TRIGGER omni OMNI_SCENARIO_RUN_TASK_COMPLETED" in message for _, message in published)
    assert any("TRIGGER omni END_BROADCAST" in message for _, message in published)
