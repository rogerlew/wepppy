from __future__ import annotations

import json
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.check_rq_dependency_graph import check_rq_dependency_graph
from tools.export_rq_observed_graph import (
    _check_observed_graph,
    build_observed_graph_payload,
    serialize_observed_graph,
)
from tools.extract_rq_dependency_graph import SOURCE_GLOBS, extract_dependency_edges, serialize_edges
from tools.render_rq_dependency_graph_docs import (
    END_MARKER,
    START_MARKER,
    render_managed_section,
    replace_managed_section,
)

pytestmark = pytest.mark.unit


def _load_auth_actor_module():
    module_path = Path(__file__).resolve().parents[2] / "wepppy" / "rq" / "auth_actor.py"
    spec = importlib.util.spec_from_file_location("auth_actor_module_for_test", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dependency_graph_extractor_source_scope_includes_route_handlers() -> None:
    assert "wepppy/rq/*.py" in SOURCE_GLOBS
    assert "wepppy/microservices/rq_engine/*.py" in SOURCE_GLOBS
    assert "wepppy/weppcloud/routes/**/*.py" in SOURCE_GLOBS
    assert "wepppy/weppcloud/bootstrap/*.py" in SOURCE_GLOBS


def test_dependency_graph_extractor_handles_stage_and_depends_on_lists(tmp_path: Path) -> None:
    source_file = tmp_path / "wepppy" / "rq" / "sample_rq.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text(
        """
from rq import Queue


def orchestrate(runid):
    q = Queue(connection=redis_conn)
    dependencies = []
    job_prep = q.enqueue_call(_prep_rq, (runid,))
    job.meta["jobs:0,func:_prep_rq"] = job_prep.id
    dependencies.append(job_prep)
    job_run = q.enqueue_call(_run_rq, (runid,), depends_on=dependencies)
    job.meta["jobs:1,func:_run_rq"] = job_run.id
    q.enqueue(_done_rq, args=[runid], depends_on=job_run)
""".strip()
        + "\n",
        encoding="utf-8",
    )

    edges = extract_dependency_edges(repo_root=tmp_path, source_files=[source_file])

    assert [edge["enqueue_target"] for edge in edges] == ["_prep_rq", "_run_rq", "_done_rq"]
    assert edges[0]["job_meta_stage"] == "jobs:0"
    assert edges[1]["job_meta_stage"] == "jobs:1"
    assert edges[1]["depends_on"] == ["_prep_rq"]
    assert edges[2]["depends_on"] == ["_run_rq"]
    assert all(edge["queue_name"] == "default" for edge in edges)


def test_dependency_graph_extractor_handles_enqueue_wrapper_calls(tmp_path: Path) -> None:
    source_file = tmp_path / "wepppy" / "rq" / "sample_wrapper.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text(
        """
from rq import Queue


def _enqueue(q, parent_job, *, key, func, args=(), depends_on=None):
    child_job = q.enqueue_call(func=func, args=args, depends_on=depends_on)
    parent_job.meta[key] = child_job.id
    parent_job.save()
    return child_job


def orchestrate(runid):
    q = Queue(connection=redis_conn)
    parent_job = object()
    prep_job = _enqueue(q, parent_job, key="jobs:0,func:_prep_rq", func=_prep_rq, args=(runid,))
    _enqueue(
        q,
        parent_job,
        key="jobs:1,func:_run_rq",
        func=_run_rq,
        args=(runid,),
        depends_on=[prep_job],
    )
""".strip()
        + "\n",
        encoding="utf-8",
    )

    edges = extract_dependency_edges(repo_root=tmp_path, source_files=[source_file])
    assert [edge["enqueue_target"] for edge in edges] == ["_prep_rq", "_run_rq"]
    assert [edge["job_meta_stage"] for edge in edges] == ["jobs:0", "jobs:1"]
    assert edges[1]["depends_on"] == ["_prep_rq"]
    assert all(edge["source_function"] == "orchestrate" for edge in edges)


def test_dependency_graph_extractor_handles_nested_append_and_return_wrapper_calls(tmp_path: Path) -> None:
    source_file = tmp_path / "wepppy" / "rq" / "sample_nested_wrapper.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text(
        """
from rq import Queue


def _enqueue(q, parent_job, *, key, func, args=(), depends_on=None):
    child_job = q.enqueue_call(func=func, args=args, depends_on=depends_on)
    parent_job.meta[key] = child_job.id
    parent_job.save()
    return child_job


def orchestrate(runid):
    q = Queue(connection=redis_conn)
    parent_job = object()
    deps = []
    deps.append(_enqueue(q, parent_job, key="jobs:0,func:_prep_rq", func=_prep_rq, args=(runid,)))
    return _enqueue(
        q,
        parent_job,
        key="jobs:6,func:_log_complete_rq",
        func=_log_complete_rq,
        args=(runid,),
        depends_on=deps,
    )
""".strip()
        + "\n",
        encoding="utf-8",
    )

    edges = extract_dependency_edges(repo_root=tmp_path, source_files=[source_file])
    assert [edge["enqueue_target"] for edge in edges] == ["_prep_rq", "_log_complete_rq"]
    assert [edge["job_meta_stage"] for edge in edges] == ["jobs:0", "jobs:6"]
    assert edges[1]["depends_on"] == ["_prep_rq"]


def test_dependency_graph_extractor_handles_qualified_wrapper_calls(tmp_path: Path) -> None:
    source_file = tmp_path / "wepppy" / "rq" / "sample_qualified_wrapper.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text(
        """
from rq import Queue


def orchestrate(runid):
    q = Queue(connection=redis_conn)
    parent_job = object()
    prep_job = _pipeline._enqueue(
        q,
        parent_job,
        key="jobs:0,func:_prep_rq",
        func=_prep_rq,
        args=(runid,),
    )
    return _pipeline.enqueue_log_complete(
        q,
        parent_job,
        runid,
        tasks=tasks,
        depends_on=[prep_job],
    )
""".strip()
        + "\n",
        encoding="utf-8",
    )

    edges = extract_dependency_edges(repo_root=tmp_path, source_files=[source_file])
    assert [edge["enqueue_target"] for edge in edges] == ["_prep_rq", "tasks._log_complete_rq"]
    assert [edge["job_meta_stage"] for edge in edges] == ["jobs:0", "jobs:6"]
    assert edges[1]["depends_on"] == ["_prep_rq"]


def test_dependency_graph_extractor_includes_jobs6_edges_for_wepp_pipeline_module() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_file = repo_root / "wepppy" / "rq" / "wepp_rq_pipeline.py"

    edges = extract_dependency_edges(repo_root=repo_root, source_files=[source_file])

    assert any(
        edge["source_function"] == "enqueue_wepp_pipeline"
        and edge["job_meta_stage"] == "jobs:6"
        and edge["enqueue_target"] == "tasks._log_complete_rq"
        for edge in edges
    )
    assert any(
        edge["source_function"] == "enqueue_watershed_noprep_pipeline"
        and edge["job_meta_stage"] == "jobs:6"
        and edge["enqueue_target"] == "tasks._log_complete_rq"
        for edge in edges
    )


def test_dependency_graph_extractor_includes_culvert_batch_edges_for_pipeline_module() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_file = repo_root / "wepppy" / "rq" / "culvert_rq_pipeline.py"

    edges = extract_dependency_edges(repo_root=repo_root, source_files=[source_file])

    run_edge = next(
        edge
        for edge in edges
        if edge["source_function"] == "enqueue_culvert_batch_jobs"
        and edge["job_meta_stage"] == "jobs:0"
        and edge["enqueue_target"] == "tasks.run_culvert_run_rq"
    )
    final_edge = next(
        edge
        for edge in edges
        if edge["source_function"] == "enqueue_culvert_batch_jobs"
        and edge["job_meta_stage"] == "jobs:1"
        and edge["enqueue_target"] == "tasks._final_culvert_batch_complete_rq"
    )

    assert run_edge["queue_name"] == "batch"
    assert final_edge["queue_name"] == "batch"
    assert any(
        edge["source_function"] == "enqueue_culvert_batch_jobs"
        and edge["job_meta_stage"] == "jobs:0"
        and edge["enqueue_target"] == "tasks.run_culvert_run_rq"
        for edge in edges
    )
    assert any(
        edge["source_function"] == "enqueue_culvert_batch_jobs"
        and edge["job_meta_stage"] == "jobs:1"
        and edge["enqueue_target"] == "tasks._final_culvert_batch_complete_rq"
        for edge in edges
    )


def test_dependency_graph_extractor_normalizes_dynamic_stage_keys(tmp_path: Path) -> None:
    source_file = tmp_path / "wepppy" / "rq" / "sample_dynamic.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text(
        """
from rq import Queue


def orchestrate(runid, contrast_id):
    q = Queue("batch", connection=redis_conn)
    child_job = q.enqueue_call(run_omni_contrast_rq, (runid, contrast_id))
    job.meta[f"jobs:contrast:{contrast_id}"] = child_job.id
""".strip()
        + "\n",
        encoding="utf-8",
    )

    edges = extract_dependency_edges(repo_root=tmp_path, source_files=[source_file])
    assert len(edges) == 1
    assert edges[0]["enqueue_target"] == "run_omni_contrast_rq"
    assert edges[0]["job_meta_stage"] == "jobs:contrast"
    assert edges[0]["queue_name"] == "batch"


def test_dependency_graph_renderer_replaces_only_managed_markers() -> None:
    edges = [
        {
            "source_module": "wepppy/rq/sample_rq.py",
            "source_function": "orchestrate",
            "source_lineno": 10,
            "enqueue_target": "_run_rq",
            "depends_on": ["_prep_rq"],
            "job_meta_stage": "jobs:1",
            "queue_name": "default",
            "notes": [],
        }
    ]
    managed = render_managed_section(edges)
    original_document = (
        "before\n"
        f"{START_MARKER}\n"
        "old managed text\n"
        f"{END_MARKER}\n"
        "after\n"
    )

    updated = replace_managed_section(document_text=original_document, managed_content=managed)

    assert "before\n" in updated
    assert "\nafter\n" in updated
    assert "old managed text" not in updated
    assert START_MARKER in updated
    assert END_MARKER in updated


def test_dependency_graph_check_detects_static_graph_drift(tmp_path: Path) -> None:
    (tmp_path / "wepppy" / "rq").mkdir(parents=True)
    (tmp_path / "wepppy" / "microservices" / "rq_engine").mkdir(parents=True)

    source_file = tmp_path / "wepppy" / "rq" / "sample.py"
    source_file.write_text(
        """
from rq import Queue


def orchestrate(runid):
    q = Queue(connection=redis_conn)
    child = q.enqueue_call(run_child_rq, (runid,))
    job.meta["jobs:0,func:run_child_rq"] = child.id
""".strip()
        + "\n",
        encoding="utf-8",
    )

    static_file = tmp_path / "wepppy" / "rq" / "job-dependency-graph.static.json"
    static_file.write_text("[]\n", encoding="utf-8")

    catalog_file = tmp_path / "wepppy" / "rq" / "job-dependencies-catalog.md"
    catalog_file.write_text(
        "\n".join(
            [
                "# Catalog",
                START_MARKER,
                "outdated",
                END_MARKER,
                "",
            ]
        ),
        encoding="utf-8",
    )

    status, stale = check_rq_dependency_graph(repo_root=tmp_path)
    assert status == 1
    assert stale == [
        "wepppy/rq/job-dependency-graph.static.json",
        "wepppy/rq/job-dependencies-catalog.md",
    ]

    generated_edges = extract_dependency_edges(repo_root=tmp_path)
    static_file.write_text(serialize_edges(generated_edges), encoding="utf-8")
    catalog_file.write_text(
        replace_managed_section(
            document_text=catalog_file.read_text(encoding="utf-8"),
            managed_content=render_managed_section(generated_edges),
        ),
        encoding="utf-8",
    )

    status, stale = check_rq_dependency_graph(repo_root=tmp_path)
    assert status == 0
    assert stale == []


def test_dependency_graph_export_aggregates_observed_edges(tmp_path: Path) -> None:
    trace_file = tmp_path / "trace.jsonl"
    trace_file.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "child_job_id": "child-1",
                        "depends_on_job_ids": ["parent-0"],
                        "enqueue_target": "_run_rq",
                        "method": "enqueue_call",
                        "parent_enqueue_target": "wepppy.rq.wepp_rq.run_wepp_rq",
                        "parent_job_id": "parent-1",
                        "queue_name": "default",
                        "timestamp_utc": "2026-02-19T00:00:00Z",
                    },
                    sort_keys=True,
                ),
                json.dumps(
                    {
                        "child_job_id": "child-2",
                        "depends_on_job_ids": ["parent-0"],
                        "enqueue_target": "_run_rq",
                        "method": "enqueue_call",
                        "parent_enqueue_target": "wepppy.rq.wepp_rq.run_wepp_rq",
                        "parent_job_id": "parent-2",
                        "queue_name": "default",
                        "timestamp_utc": "2026-02-19T00:00:01Z",
                    },
                    sort_keys=True,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    payload = build_observed_graph_payload(trace_path=trace_file)
    assert payload["observation_count"] == 2
    assert payload["aggregated_edge_count"] == 1
    assert payload["aggregated_edges"][0]["count"] == 2
    assert payload["aggregated_edges"][0]["parent_job_ids"] == ["parent-1", "parent-2"]
    assert payload["aggregated_edges"][0]["child_job_ids"] == ["child-1", "child-2"]


def test_dependency_graph_export_check_ignores_generated_at_timestamp(tmp_path: Path) -> None:
    trace_file = tmp_path / "trace.jsonl"
    trace_file.write_text(
        json.dumps(
            {
                "child_job_id": "child-1",
                "depends_on_job_ids": [],
                "enqueue_target": "_run_rq",
                "method": "enqueue_call",
                "parent_enqueue_target": "wepppy.rq.wepp_rq.run_wepp_rq",
                "parent_job_id": "parent-1",
                "queue_name": "default",
                "timestamp_utc": "2026-02-19T00:00:00Z",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    observed_path = tmp_path / "wepppy" / "rq" / "job-dependency-graph.observed.json"
    observed_path.parent.mkdir(parents=True)

    payload = build_observed_graph_payload(trace_path=trace_file)
    payload["generated_at_utc"] = "2000-01-01T00:00:00Z"
    observed_path.write_text(serialize_observed_graph(payload), encoding="utf-8")

    status = _check_observed_graph(repo_root=tmp_path, trace_path=trace_file)
    assert status == 0


def test_dependency_graph_auth_actor_trace_records_enqueue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_actor = _load_auth_actor_module()
    trace_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("WEPPPY_RQ_TRACE_ENQUEUE", "1")
    monkeypatch.setenv("WEPPPY_RQ_TRACE_PATH", str(trace_path))
    monkeypatch.setattr(
        auth_actor,
        "get_current_job",
        lambda: SimpleNamespace(id="parent-job", func_name="wepppy.rq.wepp_rq.run_wepp_rq"),
    )

    queue = SimpleNamespace(name="default")
    child_job = SimpleNamespace(id="child-job")
    depends_job = SimpleNamespace(id="depends-job")

    auth_actor._append_enqueue_trace(  # type: ignore[attr-defined]
        queue,
        method_name="enqueue_call",
        args=(lambda: None,),
        kwargs={"depends_on": [depends_job]},
        child_job=child_job,
    )

    trace_lines = trace_path.read_text(encoding="utf-8").splitlines()
    assert len(trace_lines) == 1
    payload = json.loads(trace_lines[0])
    assert payload["child_job_id"] == "child-job"
    assert payload["depends_on_job_ids"] == ["depends-job"]
    assert payload["parent_job_id"] == "parent-job"
    assert payload["queue_name"] == "default"


def test_dependency_graph_auth_actor_trace_dedupes_enqueue_delegate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_actor = _load_auth_actor_module()
    recorded: list[str] = []

    class _FakeJob:
        def __init__(self, job_id: str) -> None:
            self.id = job_id
            self.meta = {}

        def save_meta(self) -> None:
            return None

    class _FakeQueue:
        name = "default"

        def enqueue_call(self, *args, **kwargs):
            return _FakeJob("child-job")

        def enqueue(self, *args, **kwargs):
            return self.enqueue_call(*args, **kwargs)

    monkeypatch.setattr(auth_actor, "Queue", _FakeQueue)

    def _record_trace(_queue, *, method_name, args, kwargs, child_job) -> None:
        recorded.append(method_name)

    monkeypatch.setattr(auth_actor, "_append_enqueue_trace", _record_trace)
    auth_actor.install_rq_auth_actor_hook()

    queue = _FakeQueue()
    queue.enqueue(lambda: None)

    assert recorded == ["enqueue"]


def test_dependency_graph_auth_actor_hook_persists_correlation_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_actor = _load_auth_actor_module()
    from wepppy.observability.correlation import reset_correlation_id, set_correlation_id

    class _FakeJob:
        def __init__(self, job_id: str) -> None:
            self.id = job_id
            self.meta: dict[str, str] = {}
            self.save_meta_calls = 0

        def save_meta(self) -> None:
            self.save_meta_calls += 1

    class _FakeQueue:
        name = "default"

        def enqueue_call(self, *args, **kwargs):
            return _FakeJob("child-job")

        def enqueue(self, *args, **kwargs):
            return self.enqueue_call(*args, **kwargs)

    monkeypatch.setattr(auth_actor, "Queue", _FakeQueue)
    auth_actor.install_rq_auth_actor_hook()

    token = set_correlation_id("cid-rq-propagation-01")
    try:
        queue = _FakeQueue()
        child_job = queue.enqueue_call(lambda: None)
    finally:
        reset_correlation_id(token)

    assert child_job.meta["correlation_id"] == "cid-rq-propagation-01"
    assert child_job.save_meta_calls == 1


def test_dependency_graph_auth_actor_hook_replaces_invalid_correlation_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_actor = _load_auth_actor_module()
    from wepppy.observability.correlation import reset_correlation_id, set_correlation_id

    class _FakeJob:
        def __init__(self, job_id: str) -> None:
            self.id = job_id
            self.meta: dict[str, str] = {"correlation_id": "invalid correlation id !!!"}
            self.save_meta_calls = 0

        def save_meta(self) -> None:
            self.save_meta_calls += 1

    class _FakeQueue:
        name = "default"

        def enqueue_call(self, *args, **kwargs):
            return _FakeJob("child-job")

        def enqueue(self, *args, **kwargs):
            return self.enqueue_call(*args, **kwargs)

    monkeypatch.setattr(auth_actor, "Queue", _FakeQueue)
    auth_actor.install_rq_auth_actor_hook()

    token = set_correlation_id("cid-rq-propagation-02")
    try:
        queue = _FakeQueue()
        child_job = queue.enqueue_call(lambda: None)
    finally:
        reset_correlation_id(token)

    assert child_job.meta["correlation_id"] == "cid-rq-propagation-02"
    assert child_job.save_meta_calls == 1
