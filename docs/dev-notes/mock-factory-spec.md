# Mock Factory Consolidation Specification
> Draft plan for centralising recurring Redis/RQ/NoDb stubs across the test suite.

## 1. Background & Motivation
Controller and route tests repeatedly hand-roll the same support mocks:

- **RedisPrep clones** – every RQ blueprint test defines an identical class with `_instances`, `remove_timestamp`, `set_rq_job_id`, and ad-hoc tracking lists/dicts.
- **`_redis_conn` wrappers** – tests capture `enter/exit` to assert Redis usage, but each file recreates the same context manager boilerplate.
- **RQ `Queue` / `Job` stubs** – identical `enqueue_call` recorders and fixed job IDs appear in nearly every `tests/weppcloud/routes/test_rq_api_*.py`.
- **`redis.Redis` context shims** – project/interchange routes duplicate a lightweight client wrapper purely to assert connection kwargs.
- **Singleton NoDb stubs** – almost every route suite defines classes with `_instances`, `getInstance`, and manual cleanup logic, despite sharing the same lifecycle pattern.

The duplication makes tests noisy, error-prone (e.g., inconsistent `job_ids` shapes), and raises the barrier for new suites. A central factory layer keeps behaviour consistent, exposes richer diagnostics, and shortens future refactors.

## 2. Survey Summary

| Stub Pattern | Current Usage (non-exhaustive) | Shared Behaviour |
|--------------|--------------------------------|------------------|
| `RedisPrep` singleton clones | `test_rq_api_{channel,subcatchments,landuse,ash,outlet,omni,wepp}.py` | `getInstance`, `remove_timestamp`, `set_rq_job_id`, per-run tracking, manual `_instances.clear()` |
| `_redis_conn` context | same files as above | records entry/exit, returns sentinel connection token |
| `Queue` & `Job` recorders | same RQ suites + `test_project_bp.py`, `test_interchange_bp.py` | capture connection kwargs, enqueue calls, surface job IDs |
| `redis.Redis` context | `test_project_bp.py`, `test_interchange_bp.py` | store kwargs, behave as context manager |
| NoDb singleton stubs | e.g. `DummyWatershed`, `DummyLanduse`, `DummyAsh`, `DummyRon`, `DummyUnitizer` across routes | `_instances` cache, `getInstance`, optional `locked()` context, simple attribute bags, manual cleanup |

Common pain points:
- Divergent `job_ids` storage (dict vs list of tuples).
- Manual `state` dict plumbing to assert queue/redis interactions.
- Boilerplate `_instances.clear()` repeated in every fixture.
- Difficulty adding new assertions because each stub exposes different shapes.

## 3. Goals
1. Ship shared factories under `tests/factories/` that expose consistent, well-documented mocks.
2. Provide pytest fixtures/helpers for quick adoption (opt-in per test module).
3. Preserve current assertion capabilities (removed timestamps, enqueued args, redis connection kwargs) while adding structured accessors.
4. Offer extension points so domain-specific tests can augment base stubs without copy/paste.

## 4. Proposed Factory Modules

### 4.1 `tests/factories/rq.py`

Responsible for RedisPrep/Queue/Job scaffolding and interaction recording.

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

@dataclass
class QueueCall:
    func: Callable[..., Any]
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]
    timeout: Optional[int]
    job_id: str

@dataclass
class RQRecorder:
    redis_entries: List[str] = field(default_factory=list)
    queue_calls: List[QueueCall] = field(default_factory=list)
    job_id_sequence: Iterable[str] = field(default_factory=lambda: iter(()))

    def next_job_id(self, default: str = "job-123") -> str:
        try:
            return next(self.job_id_sequence)
        except StopIteration:
            return default

    def reset(self) -> None:
        self.redis_entries.clear()
        self.queue_calls.clear()
```

Factories:
- `make_redis_conn(recorder: RQRecorder, label: str = "redis-conn")` → context manager recording `"enter"/"exit"`.
- `make_queue(recorder: RQRecorder, *, default_job_id: str = "job-123")` → class with `enqueue_call` that appends a `QueueCall` (capturing timeout and kwargs) and returns a `JobStub`.
- `JobStub` dataclass with `.id` and optional payload.

### 4.2 `tests/factories/redis.py`

Two primary stubs:
- `RedisPrepStub`: configurable singleton mirroring `RedisPrep`.
  - Constructor signature: `RedisPrepStub(record, *, initial_job_ids=None)`.
  - Attributes: `.removed`, `.job_ids` (list of `(key, job_id)` tuples for order), `.wd`.
  - Methods: `remove_timestamp(task)`, `set_rq_job_id(key, job_id)`, `reset_all()`, `getInstance(wd)`.
  - Provide adapter `as_dict()` returning `{key: last_job_id}` for backwards compatibility assertions.
- `RedisClientStub`: context manager capturing kwargs (for tests patching `redis.Redis` directly).

### 4.3 `tests/factories/singleton.py`

Utility builders for NoDb-style singletons:

```python
def singleton_factory(name: str, /, *, attrs=None, methods=None, mixins=()):
    """
    Create a singleton class with `_instances`, `getInstance`, `reset_instances`.
    `attrs` sets default attributes; `methods` is a dict of callables bound onto the class.
    `mixins` may include helpers such as LockedMixin (adds `locked()` context manager).
    """
```

Bundled mixins:
- `LockedMixin` – tracks `lock_calls`, returns context manager.
- `ParseInputsRecorder` – records payloads into `.parse_inputs_calls`.
- `DumpAndUnlockMixin` (no-op stub for compatibility).

Usage example:

```python
WatershedStub = singleton_factory(
    "WatershedStub",
    attrs={"run_group": "default", "delineation_backend_is_wbt": True},
    mixins=(LockedMixin,),
)
```

Provide helper `register_singleton(monkeypatch, target, stub_class)` that patches module symbols and registers cleanup in pytest fixtures.

## 5. Pytest Integration

Add opt-in fixtures in `tests/factories/fixtures.py` (importable from `tests/conftest.py`):

- `@pytest.fixture` `rq_recorder()` → yields `RQRecorder`.
- `@pytest.fixture` `redis_prep(monkeypatch, rq_recorder)` → patches target module attribute with `RedisPrepStub` bound to recorder.
- `@pytest.fixture` `rq_environment(monkeypatch)` → convenience fixture returning object with `recorder`, `redis_conn`, `queue_class`, and helper `.patch(module)`.

Examples in docs showing migration of an existing test:

```python
def test_api_set_outlet_accepts_json_payload(rq_env, monkeypatch):
    monkeypatch.setattr(rq_api_module, "_redis_conn", rq_env.redis_conn_factory())
    monkeypatch.setattr(rq_api_module, "RedisPrep", rq_env.redis_prep_factory())
    monkeypatch.setattr(rq_api_module, "Queue", rq_env.queue_class(default_job_id="job-456"))
```

## 6. Migration Plan
1. Implement factories + fixtures with documentation and docstrings.
2. Update `tests/AGENTS.md` to describe the new utilities and expectations.
3. Incrementally refactor route suites (starting with outlet/channel/subcatchments) to consume factories; ensure assertions use `recorder.queue_calls` / `redis_prep.job_ids`.
4. Replace direct `redis.Redis` stubs in project/interchange tests with `RedisClientStub`.
5. Roll out singleton factory usage for NoDb stubs, starting with simpler controllers (`DummyRon`, `DummyWatershed`) to validate ergonomics.
6. Enforce usage via lint/docs once coverage is broad (optional: pytest plugin to detect duplicate stub definitions).

## 7. Open Questions
- Should `RedisPrepStub.job_ids` default to dict or list? Proposal: store list internally for ordering but expose helper `last_job_ids()` returning dict for compatibility.
- Do we need per-enqueue custom job IDs? Recorder exposes `.job_id_sequence` so tests can seed values; confirm meets all scenarios.
- Where should state assertions live? Consider adding helper methods (`recorder.assert_queue_call(...)`) to cut down on manual indexing.
- How to best support highly specialised NoDb behaviour (e.g., `DummyAsh` needing `_ash_load_fn` logic)? Proposal: compose base stub from factory, then subclass/augment per test where necessary.

## 8. Deliverables
- `tests/factories/rq.py`, `tests/factories/redis.py`, `tests/factories/singleton.py`, and `tests/factories/fixtures.py`.
- Updated documentation: this spec, `tests/AGENTS.md`, and migration notes in `docs/dev-notes/controller_foundations.md`.
- Example refactored test showcasing adoption (initial rollout: `tests/weppcloud/routes/test_rq_api_outlet.py`).

## 9. Migration Checklist

- [x] Document factory usage in additional domain notes as new suites migrate.
- [x] Refactor `tests/weppcloud/routes/test_rq_api_channel.py` onto `rq_environment`.
- [x] Refactor `tests/weppcloud/routes/test_rq_api_subcatchments.py` onto shared factories.
- [x] Refactor `tests/weppcloud/routes/test_rq_api_landuse.py`.
- [x] Refactor `tests/weppcloud/routes/test_rq_api_ash.py`.
- [x] Refactor `tests/weppcloud/routes/test_rq_api_omni.py`.
- [x] Refactor `tests/weppcloud/routes/test_wepp_bp.py` (multiple queue interactions).
- [x] Refactor `tests/weppcloud/routes/test_project_bp.py` and `test_interchange_bp.py` to use `make_redis_client`.
- [x] Introduce singleton factory usage for recurring NoDb stubs (Ron, Watershed, Landuse, Ash).
- [x] After each refactor, prune redundant local stub classes and ensure `redis_prep_class.reset_instances()` is called in fixture teardowns.

By consolidating mocks, we reduce boilerplate, ease future refactors, and create a clearer testing toolkit for anyone navigating the full WEPPpy stack.
