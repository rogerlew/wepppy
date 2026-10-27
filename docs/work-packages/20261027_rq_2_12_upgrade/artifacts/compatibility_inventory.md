# RQ 2.12 compatibility inventory and dependency evaluation

Date: 2026-10-27. Read-only source inventory by the independent inventory agent.
This is compatibility evidence, not runtime or acceptance signoff. No container,
Redis, dependency input, or installed environment was modified for this inventory.

## Provenance

The exact [PyPI release metadata](https://pypi.org/pypi/rq/2.12.0/json), wheel,
and versioned source distribution were fetched and their published SHA256 hashes
verified. The source distribution's `rq/worker/base.py` is byte-identical to the
wheel's file. Release metadata and bundled `CHANGES.md` date 2.12.0 to 2026-08-30.

| Artifact | SHA256 |
| --- | --- |
| [rq-2.12.0 wheel](https://files.pythonhosted.org/packages/a4/c2/995863e88669133a058c2a6a912b62d18a64fa7baaf78eb66aaa4350b48d/rq-2.12.0-py3-none-any.whl) | `97e349a00e9f2a18962102b3dca156cb5ce315d3ef38145e24ba9cabd16a9361` |
| [rq-2.12.0 source](https://files.pythonhosted.org/packages/a2/81/dacb94c8f67606b233cb7836dd67042daf9a61f7b585dcec65113f1e71f7/rq-2.12.0.tar.gz) | `78116d0c860f6285817b52d7d6d0b16a726372073ce8ea1d229732ce74ef9378` |

Extracted files are temporarily available at `/tmp/rq212-inventory/source` and
`/tmp/rq212-inventory/rq-2.12.0`. GitHub raw-source and Git-ref API requests for
both `v2.12.0` and `2.12.0` returned HTTP 404 in this environment. The verified
versioned source distribution, not upstream master, is the source authority here.

## Search coverage and runtime inventory

- Read root, `wepppy/rq`, and inherited Docker/rq-engine guidance. Searched
  repository requirements, pyproject files and Dockerfiles for RQ/Redis pins;
  searched `tools`, `scripts`, `wctl`, `.github`, Docker README and developer
  notes for requirement generation/install commands.
- Searched `wepppy`, `services`, and `tools` Python sources for RQ imports,
  started registries, `rq:wip`, `rq:job:`, raw sorted-set operations, worker
  current-job APIs, enqueue wrappers, IDs and status conversions. An AST scan
  over all `wepppy/**/*.py` identified direct `str(...get_status(...))` calls.
- Inspected worker lifecycle and containment overrides, auth actor/profile
  wrappers, dependency reconciliation, cancellation, project recovery, job info,
  summary/listings, query-catalog admission/disclosure/pilot, batch recovery,
  fork/archive discovery, run-sync discovery, and postfire migration discovery.
- Enumerated relevant tests under `tests/rq`, `tests/microservices`,
  `tests/docker`, and shared fixtures under `tests/factories`/`tests/conftest.py`.
  This inventory does not claim an exhaustive audit of every test-local stub.
- The only authoritative exact RQ pin found is `docker/requirements-uv.txt`.
  `docker/Dockerfile` and `Dockerfile.dev` install that file; the dev base uses
  Python 3.12 and the shared image is `wepppy-dev`.
- Dev Compose declares `WepppyRqWorker` pools for `default` (6), `batch` (4),
  and `fork-archive` (1). Actual overrides, running counts and identities must
  be captured separately. Producers include WEPPcloud, rq-engine and jobs that
  enqueue children; shared-image services importing them require runtime checks.
- `Dockerfile.rq-dashboard` installs requirements from the external
  `rq-dashboard` checkout. Its independent image/runtime must be inspected.

## Compatibility matrix

Line numbers identify the initial source inventory, before migration repairs.

| Consumer / assumption | Finding | Required proof or repair |
| --- | --- | --- |
| `job_info.py:16`, `job_listings.py:17`, `test_run_catalog_rq.py:13` import `rq.utils.utcnow` | **Confirmed incompatible:** removed in 2.12; `rq.utils.now()` returns aware UTC | Replace removed API; test naive historical fixtures, aware values, elapsed time and ISO responses |
| `tools/wctl2/commands/rq.py:23,60` imports/calls `utcnow` | **Confirmed incompatible:** same removed API in worker administration | Preserve `utcformat` output using explicit UTC datetime; verify `rq-info` |
| `roads_rq.py:99`, `ag_fields_rq.py:382`, `batch_rq.py:287`, `ag_fields_routes.py:393,417` stringify status | **Confirmed incompatible:** `str(JobStatus.STARTED)` is `JobStatus.STARTED` | Normalize enum `.value`; verify conflict/recovery behavior and finalizer summaries |
| `tools/query_catalog_pilot.py:282` raw started membership | **Confirmed incompatible:** composite entries classified against plain ledger IDs, then used for raw job hashes | Public `StartedJobRegistry.get_job_ids(cleanup=False)`; real execution-ID regression |
| Worker success/failure overrides | Exact signatures still match 2.12 | Keep signatures; exercise retries, terminal failure, crash and callbacks |
| Project, batch, fork/archive, run-sync, summary/listings public registry discovery | Public `get_job_ids()` parses composite execution members | Actual active workers and graphs; test read-only `cleanup=False` where intended |
| `StartedJobRegistry.add/remove` | Now raise `NotImplementedError`; no direct production calls found | Test stubs must not fabricate old started-registry mutation semantics |
| `Worker.get_current_job_id()` | Still returns plain hash `current_job` value | Live status and worker mapping |
| `_query_catalog_admission.initialize_admission()` | Raw started entries only prefix-tested; composite suffix preserves check | Bootstrap refusal with preexisting active catalog execution |
| Postfire migration `_jobs_idle()` | Raw members passed to `Job.fetch`; 2.12 fetch parses composites | Real active-job refusal; public cleanup-free discovery is clearer |
| Canonical IDs / catalog IDs | UUID and `query_catalog_refresh_` prefix satisfy `[A-Za-z0-9_-]+` | Real producer IDs; inventory historical IDs separately |
| Auth actor/correlation wrappers | Same enqueue APIs remain; post-enqueue metadata and acknowledgment recovery need race tests | Real root/child metadata, pipeline rollback, lost acknowledgment and context isolation |
| Profile wrapper | Same methods remain; uses independent post-enqueue `save_meta()` | Child propagation and aborted transaction behavior; distinguish existing issues from regressions |
| Strict dependencies / approved tolerant finalizers | Public dependency APIs remain; status equality works because enum inherits `str` | Real success/failure/deferred reconciliation, no duplicate resubmission |
| Cancellation / ownership | `Job.cancel` retains pipeline and optional dependent release; stop command remains | API ownership boundaries, queued cancel, running stop and descendants |
| Directory lock containment | Existing fork/kill/monitor methods remain on Worker | Real workhorse death, detached writers, refusal to release uncertain locks |
| Worker pools / scheduler | 2.12 pool invokes `worker.work(with_scheduler=True)` and respawns failed workers | Actual pool replacement and scheduled retry; standalone worker alone is insufficient |
| Results / historical job states | Legacy hash result reading retained; started executions differ | Persisted six-state 1.16.2 fixture matrix; no mixed-worker or rollback safety inference |
| Native webhooks | New jobs default to empty list; `send_webhooks()` iterates that list | No exposed parameters or populated webhook state; assert no outbound delivery |

Verified override signatures from the distribution:

```python
handle_job_failure(self, job, queue, started_job_registry=None, exc_string='')
handle_job_success(self, job, queue, started_job_registry)
```

Ordinary string comparisons and JSON encoding of `JobStatus` remain compatible;
explicit `str()` formatting is the confirmed failure. Public registry APIs
already normalize execution IDs, so globally splitting all IDs is unjustified.

## Full dependency resolution and generation tooling

Using `uv 0.9.5`, copied the authoritative input to a temporary file, changed
only `rq==1.16.2` to `rq==2.12.0`, and appended `croniter==6.0.0`. Both full
Python 3.12 resolutions succeeded without installing anything:

```bash
uv pip compile --python-version 3.12 docker/requirements-uv.txt --output-file /tmp/rq212-inventory/requirements-baseline-resolved.txt
uv pip compile --python-version 3.12 /tmp/rq212-inventory/requirements-upgrade.in --output-file /tmp/rq212-inventory/requirements-resolved.txt
```

Baseline: 307 packages; candidate: 308. Comparing normalized requirement lines,
the **only differences** are RQ 1.16.2 to 2.12.0 and new croniter 6.0.0.
Both resolve `python-dateutil==3.0.0`, `pytz==2022.1`, `six==1.16.0`,
`redis==6.2.0`, and `click==8.1.7`. This proves resolver compatibility, not wheel
build, installation, runtime or generated-model-output compatibility.

| Temporary evidence | SHA256 |
| --- | --- |
| Candidate input | `8a59e32c14d41c4748251bcfd3fca752b63d139f39c11ddd1d60a1b35626bc03` |
| Baseline resolved output | `375a731b3ad428f16f4cbb0e004c33ec1dfc8bdd90c7b23c0cdf37977404f34c` |
| Candidate resolved output | `7a33d1dce2b9622b44d899503d239d43fbb602c3f16d59dde31f73233f0fd6e6` |

The existing unpinned Brotli Git input resolved to commit
`089e71983611a42643d75194fedfde086c5e58af`; this is unrelated input drift risk,
not authorization to rewrite that dependency. No canonical main-requirements
generator or main lockfile was found. Dockerfiles and `scripts/setup_host_venv.sh`
install `requirements-uv.txt` directly. `tools/update_stub_requirements.py`
generates only `requirements-stubs-uv.txt`; host setup also consumes host
overrides. Preserve those distinct inputs; do not replace the authoritative
file with the complete resolver output merely to introduce this upgrade.

### Separate dashboard image

The sibling `/workdir/rq-dashboard/requirements.txt` is generated by its own
`pip-compile requirements.in` workflow and pins `rq==2.0.0`, Redis 5.2.0,
python-dateutil 2.8.2, and Click 8.1.7. The owned
`docker/Dockerfile.rq-dashboard` currently uses Python 3.8, below RQ 2.12's floor.
Its Compose build context includes the sibling checkout and bind-mounts that
source; sibling edits are unnecessary for the image dependency selection.

Minimal owned repair: change the Dockerfile base to Python 3.12 and rewrite only
the copied temporary requirements' exact RQ pin to 2.12.0 before installing,
with an explicit assertion that exactly the expected pin was replaced. Add the
same explicit croniter 6.0.0 pin. An owned override input plus resolver would
also work but adds tooling; a pip constraints file alone cannot override the
conflicting exact sibling pin. Avoid first installing RQ 2.0 and then upgrading
because that obscures the single intended resolution.

A temporary dashboard input with only that RQ change, croniter 6.0.0 and existing
unpinned Gunicorn was resolved using `uv pip compile --python-version 3.12`:
16 packages, success. It retained Redis 5.2.0, Click 8.1.7, dateutil 2.8.2 and
six 1.16.0; added croniter 6.0.0 and pytz 2026.5; unpinned Gunicorn resolved to
26.2.0. This is compatible dependency metadata, not dashboard UI acceptance.
Temporary inputs/log/output: `/tmp/rq212-inventory/dashboard-upgrade.in`,
`dashboard-resolve.log`, `dashboard-resolved.txt`. Dashboard source uses public
started registries; no removed `utcnow` import was found in `rq_dashboard`.

Shared bind-mounted code must continue working with the 1.16.2 runtime until
baseline acceptance completes. Prefer the standard-library UTC clock over
switching shared imports to the 2.12-only `rq.utils.now`; enum `.value`
normalization already has compatible local precedents. Runtime cutover and
source-edit sequencing must be coordinated by the package owner.

## Dependency evaluation gates

1. **Precedent:** the dependency-evaluation registry has only the raster_tools
   evaluation; no RQ/croniter precedent was found in standards/developer notes.
2. **Overlap:** RQ already supplies application orchestration. This is an
   operator-authorized exact-version migration, not a competing queue or model
   engine. Croniter is a mandatory upstream dependency; no cron service or
   application cron configuration is introduced.
3. **Tax:** RQ has three direct dependencies (Click, Redis, croniter). Croniter
   has two direct dependencies (python-dateutil, pytz); resolved dateutil 3.0.0
   depends on six and tzdata, both already present in baseline resolution.
   Only croniter is new to the resolved environment. RQ requires Python >=3.10,
   Click >=5 and Redis >=3.5 excluding exactly 6; all current pins qualify.
   Croniter 6.0.0 requires pytz >2021.1 and supports the Python 3.12 baseline.
   PyPI reported no vulnerabilities for queried RQ 2.12.0 and croniter 6.0.0;
   this is a point-in-time metadata check, not a comprehensive security audit.
   RQ release metadata identifies two authors and the source names Selwin Ong
   as maintainer. Actual bus factor/funding continuity is unverified. Bundled
   release history demonstrates repeated 2.x API/state evolution; these are
   concrete migration costs, not a claim of stable cross-major storage.
   Croniter 6.0.0 was uploaded 2024-12-17. Both dependencies use ordinary Python
   packaging; no additional runtime environment/service is required. Redis job
   serialization and execution tracking remain an existing framework lock-in.
4. **Performance/parity:** no owned geospatial/native engine is replaced.
   Queue lifecycle and representative model-output acceptance remain required;
   source inspection and dependency resolution do not discharge that gate.
5. **Claims:** no marketing performance claim is used as evidence. Benefits
   beyond the operator's exact version target are not asserted.

## Historical-state and acceptance boundaries

Do not infer mixed-version worker safety or downgrade compatibility from hash
readability. Running 1.x work must drain under its original runtime; queued,
deferred, scheduled, completed and failed states need retained fixture evidence
before support is promised. Invalid historical IDs need an explicit preservation
and drain procedure. Rollback must account for 2.x execution/result writes,
with isolated restore/recovery proof and no Redis flush or discarded jobs.

Relevant existing suites: `test_job_dependencies`, `test_batch_deferred_recovery`,
`test_cancel_job`, `test_directory_lock_cleanup`, `test_submission_recovery`,
`test_query_catalog_rq`, `test_query_catalog_pilot`, `test_query_catalog_inventory`,
`test_query_catalog_disclosure`, `test_run_sync_rq`, `test_job_info`,
`test_job_listings`, `test_job_queue_rank`, and rq-engine fork/archive, run-sync,
auth and jobinfo tests. All runtime, API, generated artifact, and independent
review gates remain pending at the time of this inventory.
