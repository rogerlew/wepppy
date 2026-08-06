# Harden culvert batch NoDb writer ownership

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`. The required sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must
remain current.

## Purpose / Big Picture

Culvert batches must keep parallel child execution without allowing route,
parent, and child processes to overwrite one shared NoDb object. After this
change, the submit response still supplies the parent job receipt immediately,
the parent/finalizer are the only shared-state writers, each child reports to
its own `run_metadata.json`, and a stale cached parent state is refreshed and
retried without weakening the NoDb generation guard.

## Progress

- [x] (2026-08-06 00:24 UTC) Capture the production incident, writer timeline,
  and committed contract discrepancy.
- [x] (2026-08-06 00:24 UTC) Scaffold and register the work package.
- [x] (2026-08-06 00:36 UTC) Add focused failing regressions for route isolation, initial stale
  refresh, child isolation, and finalizer aggregation.
- [x] (2026-08-06 00:36 UTC) Implement route, parent, child, and runner conformance changes.
- [x] (2026-08-06 00:38 UTC) Update culvert integration documentation and package evidence.
- [x] (2026-08-06 01:10 UTC) Run focused/full validation and complete
  correctness, QA, and security review dispositions.
- [x] (2026-08-06 01:15 UTC) Close the package and archive this plan under
  `prompts/completed/`.

## Surprises & Discoveries

- Observation: the failed parent and the submit route wrote the same parent RQ
  receipt; the second write advanced the file generation while the parent was
  doing 207 seconds of topology work.
  Evidence: production file generations changed from 644 to 759 bytes between
  parent load and dump, and the route lock owner was visible during the
  worker's duplicate receipt write.
- Observation: no archive or fork job overlapped the failed batch.
  Evidence: the parent RQ tree contained only its root and no children; the
  concurrently visible work was an unrelated ag-fields job.
- Observation: child result durability already exists independently of the
  shared map.
  Evidence: `_process_culvert_run` writes per-run `run_metadata.json`, and the
  finalizer scans run directories and merges those files into `_runs`.
- Observation: the full repository suite provides direct coverage of the
  touched culvert, rq-engine, NoDb generation, lock-race, and RQ helper layers.
  Evidence: `wctl run-pytest tests --maxfail=1` completed with 5,842 passed and
  61 skipped.

## Decision Log

- Decision: classify this package as conformance to the unchanged NoDb
  contract committed in `bf88592dddd728df124edeff2ed78283148c2cdc`.
  Rationale: the normative contract already prefers single-writer/finalizer
  ownership and requires bounded fresh-state transactions when multiple
  writers are unavoidable.
  Date/Author: 2026-08-06 / Codex.
- Decision: retain parent-owned planned child receipts in `_runs`, but remove
  all child-owned shared metadata updates.
  Rationale: the parent performs one bounded transaction after enqueue; child
  outcomes are already durable in isolated directories and can be merged once.
  Date/Author: 2026-08-06 / Codex.
- Decision: do not alter the stale-write guard.
  Rationale: accepting a stale dump would turn a diagnosable failure into lost
  state.
  Date/Author: 2026-08-06 / Codex.

## Outcomes & Retrospective

Implementation, validation, and review are complete. The route now stops after
enqueue and response construction, the parent owns durable batch/job state,
and child tasks cannot create or lock the shared runner. Children retain
isolated result durability and the finalizer reconstructs the same aggregate
artifacts. The finalizer also clears prior finalizer-owned outcome fields
before merging current metadata, preventing a successful retry from retaining
an older error. The stale generation guard was not edited. Focused validation
passed with 43 tests and the full suite passed with 5,842 tests and 61 skips.
Independent correctness, QA, and security re-review closed with no unresolved
findings.

## Context and Orientation

Before this package, `wepppy/microservices/rq_engine/culvert_routes.py`
validated the upload, created the batch directory, enqueued
`run_culvert_batch_rq`, returned the job ID, and then wrote that same ID to
`CulvertsRunner`. The route now stops after enqueue/response construction.
`wepppy/rq/culvert_rq.py::run_culvert_batch_rq` persists the receipt, prepares
shared topology, initializes the batch state with bounded lock/stale retry,
enqueues child jobs, and records their IDs.

Before this package, `run_culvert_run_rq` invoked
`wepppy/nodb/culverts_runner.py::create_run_if_missing` for a unique child run
directory while the helper and child completion path also mutated shared
`_runs`. Those shared child mutations are removed. `_process_culvert_run`
writes `runs/<run_id>/run_metadata.json`; the finalizer discovers run
directories, replaces finalizer-owned outcome fields from these files,
computes counts, and persists the merged summary under one runner lock.

In this package, “refresh” means discard the stale in-memory runner reference,
call `CulvertsRunner.getInstance(..., allow_nonexistent=True)` again, reapply
only the intended idempotent initial fields, and retry a fixed number of times.

## Plan of Work

First change focused tests so they express the committed ownership contract:
the route must not create a runner file; an initial stale parent write must
cause a fresh runner lookup and successful retry; child preparation and result
completion must not lock or mutate the shared runner; and the finalizer must
still rebuild statuses and errors from run-local metadata.

Then remove the route's post-enqueue NoDb block and its now-unused import and
constant. Extend the parent's existing bounded initial transaction to handle
`NoDbStaleWriteError` by rehydrating before retry. Keep the parent-owned child
receipt transaction and its existing bounded stale refresh.

Remove shared `_runs` updates from `CulvertsRunner.create_run_if_missing`, the
child's completion block, and validation-failure reporting. Require the batch
UUID to have been initialized by the parent instead of letting a child repair
shared state. Preserve run-local metadata writes and the finalizer's single
merge transaction. Update the culvert integration specification to name each
writer and live/durable source of job identity.

Finally run targeted pytest, full pytest, docs lint, changed-file broad
exception enforcement, quality observability, and diff checks. Complete and
disposition correctness, QA, and security reviews. Update `package.md`,
`tracker.md`, and `PROJECT_TRACKER.md`, then move this plan to
`prompts/completed/` only when every required gate is satisfied.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/microservices/test_rq_engine_culverts.py tests/culverts/test_culvert_batch_rq.py tests/culverts/test_culvert_orchestration.py tests/culverts/test_culverts_runner.py --maxfail=1
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl doc-lint --path docs/culvert-at-risk-integration/weppcloud-integration.spec.md --path docs/work-packages/20260805_culvert_nodb_writer_hardening --path PROJECT_TRACKER.md
    git diff --check

`wctl check-rq-graph` is unnecessary unless implementation changes an enqueue
site or dependency edge. If that scope changes, run the gate and update
`wepppy/rq/job-dependencies-catalog.md` as required.

## Validation and Acceptance

The route regression must prove that successful submission returns a parent
job ID and RQ metadata while no `culverts_runner.nodb` exists. The initial
state regression must raise `NoDbStaleWriteError` once, show a second
`getInstance` result is used, and complete within the fixed retry count. Child
regressions must fail if the shared runner is locked or its `_runs` map changes,
while confirming `run_metadata.json` is written. Finalizer coverage must show
that independently written success/failure metadata produces matching shared
records and summary counts.

No test or implementation may monkeypatch, bypass, or relax the generation
guard. Existing response shapes, route authorization, RQ queue and dependency
edges, file roots, and final summary artifacts must remain unchanged. Package
closure requires no unresolved medium/high correctness, QA, or security
finding.

## Idempotence and Recovery

The code edits and tests are repeatable. The parent refresh transaction mutates
only deterministic batch fields and has a fixed attempt limit, so repeated
stale generations fail explicitly rather than looping indefinitely. The
finalizer remains safe to rerun because it reconstructs state from durable
run-local files. If validation exposes incompatible legacy behavior, stop and
record the exact contract conflict instead of weakening stale protection.

## Artifacts and Notes

Package evidence lives under
`docs/work-packages/20260805_culvert_nodb_writer_hardening/artifacts/`. Required
closeout artifacts are correctness review, QA review, and the high-impact
security review. Production observation should search for the incident's
`stale NoDb write rejected` signature on `culverts_runner.nodb`, child shared
metadata warnings, and mismatches between run directories and final counts.

## Interfaces and Dependencies

`POST /api/culverts-wepp-batch/` retains its response and authentication
contracts. `run_culvert_batch_rq(culvert_batch_uuid) -> Job` and
`run_culvert_run_rq(runid, culvert_batch_uuid, run_id) -> str` retain their
task interfaces. `CulvertsRunner.create_run_if_missing(...) -> None` retains
its signature but stops treating shared `_runs` registration as a side effect.
The finalizer remains the only result aggregation boundary. No dependency,
queue, payload, or public response schema is added.

Revision note (2026-08-06 00:24 UTC): Initial plan created from production job
`7e409490-68be-4471-bd4a-59414e7e1eaa`, the committed NoDb writer-ownership
contract, and the operator's four requested hardening actions.

Revision note (2026-08-06 00:52 UTC): Recorded completed implementation,
focused/full validation, the explicit missing-parent child contract, and the
pending independent review gate.

Revision note (2026-08-06 01:15 UTC): Recorded review remediation, final clean
re-review, package closure, and ExecPlan archival.
