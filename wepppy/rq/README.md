# wepppy.rq
> Redis Queue (RQ) workers plus task modules that orchestrate every WEPPcloud background workflow—from DEM prep and WEPP runs to Omni scenarios and CAO/Ash agents.  
> **See also:** `docs/prompt_templates/module_documentation_workflow.prompt.md` for the documentation standards applied here and `AGENTS.md` for repository-wide task conventions.

## Overview
- Encapsulates the Redis-backed job system that powers WEPPcloud. Each module exports RQ-safe helpers that lock NoDb controllers, publish granular StatusMessenger updates, and emit structured `job.meta` so the UI can render progress trees.
- Ships the custom `WepppyRqWorker` class, lifecycle utilities (job inspection/cancellation), and a library of domain-specific tasks: WEPP execution (`wepp_rq.py`), end-to-end project prep (`project_rq.py`), Omni scenarios (`omni_rq.py`), PATH cost-effective runs (`path_ce_rq.py`), land/soil extracts, interchange migrations, DEVAL rendering via weppcloudR, and CAO/Ash agent sessions.
- Provides orchestration primitives shared by Flask routes and CLI scripts: queue setup (`redis_connection_kwargs`), task gating via `RedisPrep`/`TaskEnum`, and consistent timeout/logging behavior.

## Architecture & Workflow
- **Queues & worker class.** All jobs run on Redis DB 9 (`RedisDB.RQ`) and are consumed by `WepppyRqWorker`, a thin wrapper around `rq.Worker` that (a) sets `default_result_ttl=604800`, (b) attaches per-run log files, (c) handles SIGUSR1 cancellations, and (d) publishes job lifecycle events to `<runid>:rq`.
- **Status fan-out.** Tasks publish human-readable updates using `StatusMessenger`. Channels follow the `<runid>:<panel>` convention (`:wepp`, `:batch`, `:omni`, `:path_ce`, etc.) so the UI knows which dashboard panes to refresh. Long-running flows additionally trigger synthetic events (for example `TRIGGER omni END_BROADCAST`).
- **Job metadata + cancellation.** Parent tasks stash child job ids under `job.meta["jobs:{order},..."]`. The `cancel_job` module relies on this ordering to propagate stop commands; `job_info.py` walks the same tree when the UI needs a recursive status snapshot.
- **RedisPrep integration.** Project-scoped tasks update `RedisPrep` timestamps (`TaskEnum.*`) to keep the progress bars in sync with what actually ran. New tasks must cooperate with these timestamps to avoid double-running expensive steps.
- **Timeouts & observability.** Most jobs share a 12-hour timeout (43 200 s) to accommodate large WEPP runs. Modules fall back to deterministic logging (`cligen.log`, `render_deval_*.stderr`, etc.) so operators can debug failures outside of Redis.

## Module Guide
| Module | Primary entry points | Responsibility |
| --- | --- | --- |
| `rq_worker.py / rq_worker.pyi` | `WepppyRqWorker`, `start_worker()` | Custom worker class, logging hooks, SIGUSR1 cancellation, queue bootstrap helper. |
| `project_rq.py / project_rq.pyi` | `test_run_rq`, `_prep_* helpers` | Full project provisioning (DEM, landuse, soils, climate, RAP TS, WEPP run triggering). Mirrors the UI's “Run” button end-to-end. |
| `wepp_rq.py / wepp_rq.pyi` | `run_*_rq`, `compress_fn` | Hillslope/flowpath/watershed execution, interchange doc generation, WEPP runner integration (single storm + batch). |
| `batch_rq.py / batch_rq.pyi` | `run_batch_rq`, `run_batch_watershed_rq` | Launches batched watershed runs via `BatchRunner`, tracks child jobs, emits Discord notifications when done. |
| `omni_rq.py / omni_rq.pyi` | `run_omni_scenario_rq`, `run_omni_scenarios_rq` | Executes Omni scenarios (optionally with job-pool concurrency), maintains dependency hashes, updates `Omni.scenario_run_state`. |
| `path_ce_rq.py / path_ce_rq.pyi` | `run_path_cost_effective_rq` | Runs the PATH cost-effective optimization flow and timestamps the result in `RedisPrep`. |
| `land_and_soil_rq.py / land_and_soil_rq.pyi` | `land_and_soil_rq` | Builds landuse/soils extracts for arbitrary extents, bundles them via `tar -I pigz`, returns the archive path. |
| `interchange_rq.py / interchange_rq.pyi` | `run_interchange_migration` | Generates WEPP interchange products (hillslope + watershed) and TotalWatSed summaries once the required outputs exist. |
| `weppcloudr_rq.py / weppcloudr_rq.pyi` | `render_deval_details_rq` | Bridges WEPPcloud runs to the R-based reporting container, handling caching, docker exec orchestration, and log capture. |
| `agent_rq.py / agent_rq.pyi` | `spawn_wojak_session` | Starts CAO/Ash (Codex Agent Orchestrator) sessions for Wojak, stores JWT/environment metadata in Redis, and kicks off bootstrap scripts. |
| `job_info.py / job_info.pyi` | `get_wepppy_rq_job_info`, `get_wepppy_rq_job_status` | Recursively inspects job trees for UI diagnostics (elapsed time, child states, aggregated status). |
| `cancel_job.py / cancel_job.pyi` | `cancel_jobs` | Stops a job plus all descendants by replaying the stored `job.meta["jobs:*"]` hierarchy. |

> **Note:** Every runtime module ships with a `.pyi` sibling. When adding new public helpers, update both files and run `wctl run-stubtest wepppy.rq.<module>` to keep the stubs honest.

## Quick Start / Examples
### Run a worker locally
```bash
wctl exec weppcloud bash -lc \
  "rq worker -u redis://$REDIS_HOST:6379/9 \
   --worker-class 'wepppy.rq.WepppyRqWorker' high default low"
```
- The worker class automatically listens for `SIGUSR1` so UI-driven cancellations take effect immediately.
- Use `rq worker-pool -n 8 -u redis://... --worker-class wepppy.rq.WepppyRqWorker high default low` when you need multiple OS processes on bare metal (see `wepppy/weppcloud/_baremetal/...` for full instructions).

### Enqueue a WEPP run from a shell
```python
import redis
from rq import Queue
from wepppy.rq.wepp_rq import run_watershed_rq
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

conn = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
q = Queue('default', connection=conn)
job = q.enqueue(run_watershed_rq, 'my-runid', wepp_bin='wepp_250915')
print("queued job", job.id)
```
- Jobs automatically log to `<run>/rq.log` and publish to `<runid>:wepp`.
- Store dependent job ids in `job.meta['jobs:<order>,...]` if you need cascading cancellation.

### Inspect or cancel a job tree
```python
from wepppy.rq.job_info import get_wepppy_rq_job_status
print(get_wepppy_rq_job_status(job.id))

from wepppy.rq.cancel_job import cancel_jobs
cancel_jobs(job.id)
```
- `cancel_jobs` walks the stored metadata and issues `send_stop_job_command` for running descendants before calling `Job.cancel()` on queued ones.

## Developer Notes
- **Task structure.** Follow the established pattern: resolve `job = get_current_job()`, compute a status channel (`f"{runid}:panel"`), call `StatusMessenger.publish` for STARTED/COMPLETED/EXCEPTION, and `raise` so the worker records the failure. Timeouts default to 12 hours—set `timeout=TIMEOUT` when enqueuing child jobs.
- **RedisPrep timestamps.** When a task materially advances a `TaskEnum`, call `prep.remove_timestamp(...)` just before the work starts and `prep.timestamp(...)` once it finishes. This keeps the dashboard in sync and prevents accidental short-circuiting the next time the run resumes.
- **Job dependencies.** Parent tasks (batch, omni, project) should save child job ids in `job.meta['jobs:{order},runid:{child_runid}] = child_job.id`. The ordering string is arbitrary but should remain stable so `cancel_job` and `job_info` can display the tree predictably.
- **Status channels & UI triggers.** Use `StatusMessenger.publish(channel, f"rq:{job.id} TRIGGER <panel> <event>")` whenever the front-end needs to broadcast custom lifecycle events (for example, `BATCH_RUN_COMPLETED`, `OMNI_SCENARIO_RUN_TASK_COMPLETED`).
- **Testing.** Route-level tests under `tests/weppcloud/routes/test_rq_api_*.py` exercise the Flask APIs that enqueue these tasks. Run them via `wctl run-pytest tests/weppcloud/routes -k rq_api` before shipping changes to queue wiring. Worker-specific helpers (job_info/cancel_job) are covered by unit tests in the same suite; extend them when adding new metadata conventions.
- **Type stubs & linting.** Whenever you adjust task signatures, edit the companion `.pyi` and run `python tools/sync_stubs.py`. The existing modules already import `from __future__ import annotations` for forward references—maintain that style.

## Further Reading
- `AGENTS.md` – operational expectations for RQ workers within the broader WEPPcloud stack.
- `docs/prompt_templates/module_documentation_workflow.prompt.md` – the workflow used for writing/maintaining documentation like this README.
- `wepppy/weppcloud/routes/rq/api/` – Flask endpoints that call into these modules; useful when tracing how user actions map to background jobs.
