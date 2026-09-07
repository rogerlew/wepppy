# Implement fork read retries and prerequisite failure reporting

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Fork users should recover from brief file-read visibility failures and receive
an explicit failure when a prerequisite cannot complete. The incident involved
small-file-heavy fork activity; no specific worker host is considered causal.

## Progress

- [x] (2026-09-07 UTC) Incident evidence, scope and package scaffold recorded.
- [x] Ratify contracts through two reviews and an ancestor commit.
- [x] Implement read retry/diagnostics and fork failure reporting.
- [x] Complete targeted, direct-boundary and full-suite validation; resolve discovered test failures.
- [x] Complete independent reviews and update operator/user guidance.

## Surprises & Discoveries

- `exists()` currently discards the errno that would distinguish ENOENT from
  ESTALE. The finalizer can remain deferred after an upstream failure.
- The read retry deadline cannot interrupt a hard-mounted NFS kernel call.
- Optional absence can occur during any signature check, not only before the
  first read. All scoped signature checks now carry the optional policy.
- RQ skips job failure callbacks on abrupt work-horse death; the surviving
  production worker supervisor now calls the same guarded reporter.
- Line-number-based broad exception allowlisting reported false growth when
  existing handlers moved; inline boundary explanations now keep those existing
  RQ handlers stable under edits.

## Decision Log

- 2026-09-07 UTC, operator/Codex: Scope is initial read recovery, original errno
  and fork failure reporting. Working hypothesis is burst-related visibility,
  not wepp3. No mounts, whole-job retries or model changes.
- 2026-09-07 UTC, Codex: Budget 5 seconds shared across initial controller reads;
  ENOENT/ESTALE only, backoff 0.1 seconds doubling to at most 1 second.

## Outcomes & Retrospective

Implemented locally after checkpoint `2ad307aeb`. Focused tests: 228 passed;
correctness, QA and security reviews accepted with all findings resolved.
The user-requested shape-converter test repair passes 15 tests. Final broad
validation reached 6,477 passed, 63 skipped and 1 deselected before an unrelated
roads authorization/backend assertion failed. The excluded shape test passed
separately. A subsequent user-requested test repair resolves those gaps: the final full
suite passes 7,489 tests with 63 skipped and 12 passing subtests. No production deployment or
user-run retry has occurred; production-equivalent workflow evidence remains
a rollout gate.

## Context and Orientation

`wepppy/nodb/base.py` loads NoDb JSON controllers and validates cache signatures.
`wepppy/rq/wepp_rq_stage_prep.py` loads controllers before exporting model inputs.
`wepppy/rq/wepp_rq_pipeline.py` registers child jobs before enqueue.
`wepppy/rq/project_rq.py` creates forks and records destination lifecycle state.
A prerequisite is an RQ job that must finish before a dependent job executes.

## Plan of Work

Milestone 1: Amend the NoDb and RQ response contracts, add ADR-0049 and a
contract decision artifact, obtain two independent read-only reviews, and
commit that checkpoint before implementation. This user's implement request
is authority for necessary local checkpoint work; do not deploy or push.

Milestone 2: Add a small opt-in filesystem read context under NoDb. Default
behavior has no retries. Required file open/read and cache-validation stat
within initial WEPP preparation controller loading may retry ENOENT/ESTALE
within one deadline. Preserve optional missing-file None behavior, malformed
JSON failure, locking, cache signature validation, and original exceptions.
Log retry recovery/exhaustion with original errno and worker/run/job context.
No retry may enclose controller mutation or model execution.

Milestone 3: Carry server-generated fork source/target/root association on
WEPP pipeline children and register an RQ failure callback. Verify lineage and
current destination receipt before recording failure and publishing source
fork status with the failed child ID. Do not change strict dependency edges or
cancel siblings. Use `wepppy/rq/rq_worker.py` supervisor failure handling
to cover work-horse death when RQ skips the callback. Prevent stale callbacks and late parent progress from
clobbering terminal states. Verify existing polling sees failed descendants.

Milestone 4: Add deterministic failure injection and actual filesystem reads,
actual isolated Redis/RQ callback execution, and focused regressions. Run the
full suite, graph and stub gates. Independent correctness, QA and security
reviews must close medium/high findings. Update all living docs and final
operator guidance. Production-equivalent full workflow validation remains an
explicit rollout gate if unavailable locally.

## Concrete Steps

From `/home/workdir/wepppy`, use `wctl run-pytest` on changed NoDb/RQ tests,
then `wctl run-pytest tests --maxfail=1`, `wctl check-rq-graph`,
`wctl check-test-stubs`, and scoped `wctl doc-lint --path <file>`.
Regenerate catalog drift only with `python tools/check_rq_dependency_graph.py --write`.
Capture exact results and review dispositions under this package's artifacts.

## Validation and Acceptance

Required existing files load with no sleeps; transient ENOENT/ESTALE recover;
permanent missing files exhaust the budget with original errno; optional
absence returns None immediately; empty/corrupt JSON and EACCES/EIO fail
without retries. A failing WEPP child marks only its associated current fork
failed while strict downstream jobs remain blocked. Successful forks retain
success; stale/foreign callbacks do nothing. Verify a real Redis/RQ job tree.

## Idempotence and Recovery

Tests use temporary directories and unique Redis key/queue namespaces. Never
flush shared Redis databases or mutate existing user runs. Rollback is the
code revision through canonical deployment; no mount or data migration exists.

## Artifacts and Notes

See `package.md`, `tracker.md`, and `artifacts/2026-09-07_contract_decision.md`.
Record validation limitations honestly; injected ESTALE is not a NAS reproduction.

## Interfaces and Dependencies

Use existing Python standard library, NoDb, RQ and Redis APIs only. Retry scope
is a context manager around initial controller loads; the original exception
is re-raised on exhaustion. Failure callback uses RQ's job/connection/type/
value/traceback interface and guarded Redis publication.

Revision note (2026-09-07 UTC): Initial scaffold reflects the operator's
burst-of-small-files hypothesis and explicitly excludes host-specific fixes.

Revision note (2026-09-07 UTC): Added optional-disappearance handling,
supervisor failure fallback and resolved independent review findings. The
working NAS hypothesis remains burst-related; no host-specific action taken.

Revision note (2026-09-07 UTC): User requested the unrelated shape-converter
test repair found by broad validation; test-only fix committed as `efd78afc6`,
15 focused tests passed, and independent QA accepted. No production config
change was needed.


## Retry Budget Amendment — 2026-09-07 UTC

Operator-directed correction after production recurrence: supersede the original
5-second/0.1-second-to-1-second policy with a 120-second shared budget and
2-second initial delay doubling to a 10-second cap. Existing production storage
measurements already justified a longer timescale. ADR-0049 and the canonical
NoDb contract carry the amended policy. No broader retry scope or mount changes.
Validation: 93 targeted NoDb/read/preparation tests passed in 17.59 seconds,
including simulated recovery after 60 seconds and permanent-error exhaustion.
Scoped documentation lint and diff checks passed. Production rollout pending.
