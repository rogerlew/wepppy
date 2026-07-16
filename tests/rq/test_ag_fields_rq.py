from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from wepppy.nodb.mods.ag_fields import AgFieldsRunError, PlantFileProcessingError
from wepppy.rq import ag_fields_rq


pytestmark = pytest.mark.unit


@pytest.fixture
def rq_context(monkeypatch: pytest.MonkeyPatch):
    events: list[tuple[str, object]] = []
    published: list[tuple[str, str]] = []
    controller_box: dict[str, object] = {}

    monkeypatch.setattr(ag_fields_rq, "get_current_job", lambda: SimpleNamespace(id="job-17"))
    monkeypatch.setattr(ag_fields_rq, "get_wd", lambda runid: events.append(("get_wd", runid)) or "/runs/demo")
    monkeypatch.setattr(
        ag_fields_rq,
        "clear_nodb_file_cache",
        lambda runid, pup_relpath: events.append(("clear", (runid, pup_relpath))),
    )
    monkeypatch.setattr(
        ag_fields_rq.AgFields,
        "getInstance",
        lambda wd: events.append(("hydrate", wd)) or controller_box["controller"],
    )
    monkeypatch.setattr(
        ag_fields_rq.RedisPrep,
        "getInstance",
        lambda wd: SimpleNamespace(
            remove_timestamp=lambda task: events.append(("preflight-remove", task)),
            timestamp=lambda task: events.append(("preflight-stamp", task)),
        ),
    )
    monkeypatch.setattr(
        ag_fields_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )
    return events, published, controller_box


def test_build_subfields_rq_orders_chain_and_guards_hydration(rq_context) -> None:
    events, published, controller_box = rq_context

    class DummyAgFields:
        field_n = 2
        sub_field_n = 5
        sub_field_fp_n = 1

        def rasterize_field_boundaries_geojson(self) -> None:
            events.append(("stage", "rasterize"))

        def periodot_abstract_sub_fields(self, minimum_area: float) -> None:
            events.append(("stage", ("abstract", minimum_area)))

        def polygonize_sub_fields(self) -> None:
            events.append(("stage", "polygonize"))

    controller_box["controller"] = DummyAgFields()

    result = ag_fields_rq.build_ag_fields_subfields_rq("demo", 25.0)

    assert events == [
        ("get_wd", "demo"),
        ("preflight-remove", ag_fields_rq.TaskEnum.run_ag_fields),
        ("clear", ("demo", "ag_fields.nodb")),
        ("hydrate", "/runs/demo"),
        ("stage", "rasterize"),
        ("stage", ("abstract", 25.0)),
        ("stage", "polygonize"),
    ]
    assert result == {"field_n": 2, "sub_field_n": 5, "sub_field_fp_n": 1}
    assert any("AGFIELDS_BUILD_SUBFIELDS_TASK_COMPLETED" in message for _, message in published)


def test_plant_db_rq_returns_inventory_summary(rq_context) -> None:
    _events, published, controller_box = rq_context
    summary = {
        "valid_files": ["corn.man"],
        "invalid_files": [{"filename": "bad.man", "error": "bad format"}],
        "files": [],
        "replaced": [],
    }
    controller_box["controller"] = SimpleNamespace(
        handle_plant_file_db_upload=lambda filename: summary if filename == "plants.zip" else None
    )

    assert ag_fields_rq.process_ag_fields_plant_db_rq("demo", "plants.zip") == summary
    result_message = next(message for _, message in published if "RESULT_JSON" in message)
    assert json.loads(result_message.split("RESULT_JSON ", 1)[1]) == summary


def test_plant_db_rq_failure_names_aborting_file(rq_context) -> None:
    _events, published, controller_box = rq_context

    def _fail(_filename: str):
        raise PlantFileProcessingError("broken.man", "cannot parse")

    controller_box["controller"] = SimpleNamespace(handle_plant_file_db_upload=_fail)

    with pytest.raises(PlantFileProcessingError):
        ag_fields_rq.process_ag_fields_plant_db_rq("demo", "plants.zip")

    failure_message = next(message for _, message in published if "EXCEPTION_JSON" in message)
    payload = json.loads(failure_message.split("EXCEPTION_JSON ", 1)[1])
    assert payload["filename"] == "broken.man"


def test_run_wepp_rq_failure_names_subfield_and_parent_field(rq_context) -> None:
    events, published, controller_box = rq_context

    def _fail(*, max_workers):
        assert max_workers == 3
        raise AgFieldsRunError(12, 34, "runner failed")

    controller_box["controller"] = SimpleNamespace(run_wepp_ag_fields=_fail)

    with pytest.raises(AgFieldsRunError):
        ag_fields_rq.run_ag_fields_wepp_rq("demo", max_workers=3)

    failure_message = next(message for _, message in published if "EXCEPTION_JSON" in message)
    payload = json.loads(failure_message.split("EXCEPTION_JSON ", 1)[1])
    assert payload["sub_field_id"] == 34
    assert payload["field_id"] == 12
    assert ("preflight-remove", ag_fields_rq.TaskEnum.run_ag_fields) in events
    assert ("preflight-stamp", ag_fields_rq.TaskEnum.run_ag_fields) not in events


def test_run_wepp_rq_applies_selected_binary_before_execution(rq_context) -> None:
    events, _published, controller_box = rq_context

    class DummyAgFields:
        wepp_bin = "wepp_260430"

        def run_wepp_ag_fields(self, *, max_workers):
            assert max_workers is None
            assert self.wepp_bin == "wepp_dcc52a6"
            return {"run_count": 2}

    controller = DummyAgFields()
    controller_box["controller"] = controller

    result = ag_fields_rq.run_ag_fields_wepp_rq(
        "demo",
        wepp_bin="wepp_dcc52a6",
    )

    assert result == {"run_count": 2}
    assert controller.wepp_bin == "wepp_dcc52a6"
    assert ("preflight-remove", ag_fields_rq.TaskEnum.run_ag_fields) in events
    assert ("preflight-stamp", ag_fields_rq.TaskEnum.run_ag_fields) in events
    assert events.index(("preflight-remove", ag_fields_rq.TaskEnum.run_ag_fields)) < events.index(
        ("preflight-stamp", ag_fields_rq.TaskEnum.run_ag_fields)
    )


def test_run_watershed_rq_publishes_phases_without_reusing_stage4_timestamp(rq_context) -> None:
    events, published, controller_box = rq_context

    class DummyAgFields:
        def run_watershed_integration(self, *, max_workers, phase_callback, scheme):
            assert max_workers == 2
            assert scheme == "hybrid"
            phase_callback("area_planning")
            phase_callback("watershed_rerun")
            return {"status": "completed", "parent_count": 3}

    controller_box["controller"] = DummyAgFields()

    result = ag_fields_rq.run_ag_fields_watershed_rq(
        "demo",
        max_workers=2,
        scheme="hybrid",
    )

    assert result == {"status": "completed", "parent_count": 3, "scheme": "hybrid"}
    assert not any(event[0].startswith("preflight-") for event in events)
    phase_messages = [message for _, message in published if "PHASE_JSON" in message]
    assert len(phase_messages) == 2
    assert all('"scheme":"hybrid"' in message for message in phase_messages)
    assert any("AGFIELDS_RUN_WATERSHED_TASK_COMPLETED" in message for _, message in published)


def test_suite_owned_watershed_child_does_not_publish_terminal_trigger(rq_context) -> None:
    _events, published, controller_box = rq_context
    controller_box["controller"] = SimpleNamespace(
        run_watershed_integration=lambda **_kwargs: {"status": "completed"}
    )

    ag_fields_rq.run_ag_fields_watershed_rq(
        "demo",
        scheme="concept_1",
        publish_completion_trigger=False,
    )

    assert any(" COMPLETED run_ag_fields_watershed_rq" in message for _, message in published)
    assert not any(" TRIGGER " in message for _, message in published)


def test_run_watershed_rq_rejects_worker_count_above_operational_bound(rq_context) -> None:
    with pytest.raises(ValueError, match="between 1 and 16"):
        ag_fields_rq.run_ag_fields_watershed_rq(
            "demo",
            max_workers=17,
            scheme="concept_1",
        )


def test_run_watershed_suite_registers_serial_children_and_allow_failure_finalizer(
    rq_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, published, controller_box = rq_context

    class DummyJob:
        def __init__(self, job_id: str, *, meta=None):
            self.id = job_id
            self.meta = dict(meta or {})
            self.save_count = 0

        def save(self) -> None:
            self.save_count += 1
            events.append(("save", self.id, dict(self.meta)))

        def refresh(self) -> None:
            events.append(("refresh", self.id))

    class DummyDependency:
        def __init__(self, *, jobs, allow_failure):
            self.dependencies = list(jobs)
            self.allow_failure = allow_failure

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def lock(self, key, *, timeout, blocking_timeout):
            events.append(("lock", key, timeout, blocking_timeout))
            return self

    enqueued = []

    class DummyQueue:
        def __init__(self, connection):
            assert isinstance(connection, DummyRedis)

        def enqueue_call(self, func, args, timeout, depends_on, job_id, meta):
            child = DummyJob(job_id, meta=meta)
            enqueued.append(
                {
                    "func": func,
                    "args": args,
                    "timeout": timeout,
                    "depends_on": depends_on,
                    "meta": dict(meta),
                    "job": child,
                }
            )
            events.append(("enqueue", job_id))
            return child

    class DummyPrep:
        def set_rq_job_id(self, key, job_id):
            events.append(("hint", (key, job_id)))

    class DummyAgFields:
        def set_watershed_integration_job_ids(self, job_ids):
            events.append(("state", dict(job_ids)))

    parent = DummyJob("suite-parent", meta={"auth_actor": {"sub": "operator"}})
    controller_box["controller"] = DummyAgFields()
    monkeypatch.setattr(ag_fields_rq, "get_current_job", lambda: parent)
    monkeypatch.setattr(ag_fields_rq.RedisPrep, "getInstance", lambda wd: DummyPrep())
    monkeypatch.setattr(ag_fields_rq.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(ag_fields_rq, "Queue", DummyQueue)
    monkeypatch.setattr(ag_fields_rq, "Dependency", DummyDependency)
    released = []
    monkeypatch.setattr(
        ag_fields_rq,
        "_release_deferred_job_if_ready",
        lambda queue, job: released.append(job.id),
    )

    planned = {
        "concept_1": "child-c1",
        "concept_2": "child-c2",
        "hybrid": "child-hybrid",
    }
    result = ag_fields_rq.run_ag_fields_watershed_suite_rq(
        "demo",
        4,
        planned,
        "suite-finalizer",
    )

    assert result == {
        "job_ids": planned,
        "finalizer_job_id": "suite-finalizer",
        "schemes": ["concept_1", "concept_2", "hybrid"],
    }
    assert [call["func"] for call in enqueued] == [
        ag_fields_rq.run_ag_fields_watershed_rq,
        ag_fields_rq.run_ag_fields_watershed_rq,
        ag_fields_rq.run_ag_fields_watershed_rq,
        ag_fields_rq.finalize_ag_fields_watershed_suite_rq,
    ]
    assert [call["args"][-1] for call in enqueued[:3]] == [False, False, False]
    assert enqueued[0]["depends_on"] is None
    assert enqueued[1]["depends_on"].dependencies == ["child-c1"]
    assert enqueued[2]["depends_on"].dependencies == ["child-c2"]
    assert enqueued[3]["depends_on"].dependencies == [
        "child-c1",
        "child-c2",
        "child-hybrid",
    ]
    assert all(
        call["depends_on"].allow_failure
        for call in enqueued[1:]
    )
    assert released == ["child-c2", "child-hybrid", "suite-finalizer"]
    assert parent.meta == {
        "auth_actor": {"sub": "operator"},
        "runid": "demo",
        "child_dispatch_lock_key": "agfields:suite_dispatch:suite-parent",
        "jobs:0,scheme:concept_1": "child-c1",
        "jobs:1,scheme:concept_2": "child-c2",
        "jobs:2,scheme:hybrid": "child-hybrid",
        "jobs:3,func:finalize_ag_fields_watershed_suite_rq": "suite-finalizer",
    }
    assert all(call["meta"]["parent_job_id"] == "suite-parent" for call in enqueued)
    assert all(call["meta"]["auth_actor"] == {"sub": "operator"} for call in enqueued)
    parent_save_index = next(
        index
        for index, event in enumerate(events)
        if event[0:2] == ("save", "suite-parent")
    )
    state_index = events.index(("state", planned))
    first_enqueue_index = events.index(("enqueue", "child-c1"))
    assert parent_save_index < first_enqueue_index
    assert state_index < first_enqueue_index
    assert (
        "lock",
        "agfields:suite_dispatch:suite-parent",
        30,
        30,
    ) in events
    assert not any(
        message.startswith("rq:suite-parent TRIGGER")
        for _channel, message in published
    )


def test_release_deferred_job_if_ready_enqueues_met_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    removed = []

    class DummyRegistry:
        def __init__(self, queue):
            self.queue = queue

        def remove(self, job):
            removed.append(job)

    class DummyJob:
        def get_status(self, refresh=True):
            return ag_fields_rq.JobStatus.DEFERRED

        def dependencies_are_met(self):
            return True

    class DummyQueue:
        def __init__(self):
            self.enqueued = []

        def _enqueue_job(self, job):
            self.enqueued.append(job)

    monkeypatch.setattr(ag_fields_rq, "DeferredJobRegistry", DummyRegistry)
    queue = DummyQueue()
    job = DummyJob()

    ag_fields_rq._release_deferred_job_if_ready(queue, job)

    assert removed == [job]
    assert queue.enqueued == [job]


def test_release_deferred_job_if_ready_keeps_unmet_dependency_deferred(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    removed = []

    class DummyRegistry:
        def __init__(self, queue):
            self.queue = queue

        def remove(self, job):
            removed.append(job)

    class DummyJob:
        def get_status(self, refresh=True):
            return ag_fields_rq.JobStatus.DEFERRED

        def dependencies_are_met(self):
            return False

    class DummyQueue:
        def __init__(self):
            self.enqueued = []

        def _enqueue_job(self, job):
            self.enqueued.append(job)

    monkeypatch.setattr(ag_fields_rq, "DeferredJobRegistry", DummyRegistry)
    queue = DummyQueue()
    job = DummyJob()

    ag_fields_rq._release_deferred_job_if_ready(queue, job)

    assert removed == []
    assert queue.enqueued == []


def test_suite_dispatch_refresh_preserves_concurrent_cancellation_marker(
    rq_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, _published, controller_box = rq_context

    class DummyJob:
        id = "suite-parent"

        def __init__(self):
            self.meta = {"runid": "demo"}
            self.save_count = 0

        def refresh(self):
            self.meta = {
                "runid": "demo",
                "child_dispatch_lock_key": "agfields:suite_dispatch:suite-parent",
                "cancel_requested": True,
            }
            events.append(("refresh", self.id))

        def save(self):
            self.save_count += 1

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def lock(self, key, *, timeout, blocking_timeout):
            return self

    parent = DummyJob()
    controller_box["controller"] = object()
    monkeypatch.setattr(ag_fields_rq, "get_current_job", lambda: parent)
    monkeypatch.setattr(ag_fields_rq.redis, "Redis", lambda **_kwargs: DummyRedis())
    monkeypatch.setattr(
        ag_fields_rq,
        "Queue",
        lambda **_kwargs: pytest.fail("children must not be enqueued after cancellation"),
    )

    with pytest.raises(RuntimeError, match="canceled before child dispatch"):
        ag_fields_rq.run_ag_fields_watershed_suite_rq(
            "demo",
            4,
            {
                "concept_1": "child-c1",
                "concept_2": "child-c2",
                "hybrid": "child-hybrid",
            },
            "suite-finalizer",
        )

    assert parent.meta["cancel_requested"] is True
    assert parent.save_count == 0
    assert not any(event[0] in {"hint", "state", "enqueue"} for event in events)


def test_watershed_suite_finalizer_reports_failed_children_without_failing(
    rq_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _events, published, _controller_box = rq_context

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    statuses = {
        "child-c1": "failed",
        "child-c2": "finished",
        "child-hybrid": "finished",
    }
    monkeypatch.setattr(ag_fields_rq.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(
        ag_fields_rq.Job,
        "fetch",
        lambda job_id, connection: SimpleNamespace(
            get_status=lambda refresh=False: statuses[job_id]
        ),
    )
    planned = {
        "concept_1": "child-c1",
        "concept_2": "child-c2",
        "hybrid": "child-hybrid",
    }

    result = ag_fields_rq.finalize_ag_fields_watershed_suite_rq("demo", planned)

    assert result == {"job_ids": planned, "statuses": {
        "concept_1": "failed",
        "concept_2": "finished",
        "hybrid": "finished",
    }}
    assert any("AGFIELDS_RUN_WATERSHED_TASK_COMPLETED" in message for _, message in published)
