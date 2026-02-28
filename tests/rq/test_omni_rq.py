from __future__ import annotations

import logging
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

    class OmniStub:
        _instances: dict[str, "OmniStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.contrast_names = ["c1"]
            self.calls: list[tuple[int, str]] = []

        @classmethod
        def getInstance(cls, wd: str) -> "OmniStub":
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
    assert omni.contrast_dependency_tree == {}
    assert omni.cleaned_ids == [[]]
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
