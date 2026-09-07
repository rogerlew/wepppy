# Validation — FORK-READ-01

## Revision and Scope

Contract ancestor `2ad307aeb` precedes implementation. All commands used the
existing dev Compose stack through wctl where applicable. No deployed production code,
mount, user run or job was modified. Independent review findings are closed.

## Completed Checks

| Check | Result |
| --- | --- |
| Pre-change NoDb/fork/pipeline baseline | 136 passed |
| Final focused NoDb/read/preparation/fork/pipeline/worker tests | 228 passed |
| Worker subset after Redis-refresh failure regression | 23 passed |
| Stubtest of `wepppy.nodb._read_retry` and `wepppy.rq.fork_failure` | 2 modules clean |
| `wctl check-test-stubs` | All stubs complete |
| `wctl check-rq-graph` | Generated artifacts current; 144 static edges |
| Broad exception changed-file enforcement against `2ad307aeb` | Pass, no added unsuppressed catches |
| Code-quality observability | Ran observe-only; radon unavailable and no changed-file analysis, so no complexity claim |
| `git diff --check` | Pass |

Focused command:

```bash
wctl run-pytest tests/nodb/test_initial_read_retry.py tests/nodb/test_base_boundary_characterization.py tests/rq/test_fork_failure.py tests/rq/test_wepp_prep_read_retry.py tests/rq/test_wepp_rq_pipeline.py tests/rq/test_project_rq_fork.py tests/rq/test_rq_worker_runid.py --maxfail=1 -q
```

## Real Boundary Evidence

- Actual missing-file open raises ENOENT before a coordinated atomic publication;
  the same opted-in loader then reads/decodes the completed NoDb payload.
- Cold/singleton/Redis cases exercise actual payloads and signature handling.
  Injected ENOENT/ESTALE cover deterministic timing; ESTALE injection is not a
  reproduction of NAS behavior.
- Isolated real Redis/RQ queues verify current/foreign/legacy lineage, atomic
  receipt replacement, duplicate suppression and source pub/sub. The live job
  tree is queried through `get_wepppy_rq_job_status`: active sibling gives
  queued status; after it finishes the aggregate is failed while the strict
  dependent remains deferred. Temporary jobs/receipts/queues are cleaned up.
- A real `WepppyRqWorker` child calls `os._exit(17)`. The surviving supervisor
  records failed job/outcome and source notification without a child callback.
- A Redis status-refresh exception is injected separately and proves original
  failure handling continues to subsequent publication.

## Broad Suite

`wctl run-pytest tests --maxfail=1 -q` stopped after 5,129 passed and 50 skipped
on `tests/shape_converter/unit/test_runtime_hardening.py::test_prod_wepp1_overlay_does_not_override_shape_converter_hardening`.
The old test asserted shape-converter was absent from the wepp1 overlay, while the
overlay defines it. Before the test correction, test and overlay were unchanged from checkpoint `2ad307aeb`;
loading that revision's YAML independently confirms the contradiction. The
isolated pre-fix test also failed. The user then explicitly requested this test be fixed. The test now permits
only image/build/environment overlay fields while rejecting runtime hardening
overrides and changed shape-converter hardening environment values. Production
Compose is unchanged. Independent QA accepted the correction; the full shape
runtime-hardening and rollout-contract modules pass 15 tests.

The broad run began before the final review fixes; final focused tests above
cover those fixes. A final full run with that test excluded was already running when the user
requested its repair. The repaired test is covered by the separate 15-test
passing run. The remaining full run stopped after 6,477 passed, 63 skipped,
1 deselected and 12 passing subtests at
`tests/weppcloud/routes/test_project_bp.py::test_set_mod_roads_requires_wbt_backend`.
The assertion expected a WBT-backend rejection but received the PowerUser
authorization rejection first. The test and route are unchanged from checkpoint
`2ad307aeb`. This is an outstanding broad-suite gap; full-suite green is not claimed.

Final broad command:

```bash
wctl run-pytest tests --maxfail=1 -q -k 'not test_prod_wepp1_overlay_does_not_override_shape_converter_hardening'
```

## Rollout Gate and Limitations

Local implementation/tests do not prove production NAS recovery or full model
workflow parity. Before rollout, exercise fork/undisturbify through the real
workflow under production-equivalent identities, groups, mounts, umask and
orchestration. Callback support must be available to workers before producing
callback-bearing jobs. Legacy queued jobs do not retroactively gain metadata
or callbacks; they retain existing aggregate polling behavior. Existing
production failures need explicit operator recovery, not automatic retries.
