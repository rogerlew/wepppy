# Batch and Culvert Climate Rehydration Hardening Tracker

> Living operator/agent handoff for
> `docs/work-packages/20260904_batch_culvert_climate_rehydration_b/`.

**Status**: Conditional closeout - implementation and batch acceptance complete

**Owner**: Codex on Forest

**Started**: 2026-09-05 00:29 UTC

**Security artifact**: `artifacts/2026-09-05_security_review.md` (pass with
Forest closeout condition)

## Backlog

- [x] Capture a compact equivalent direct filesystem interleaving test without
  modifying Forest run data; a pre-change live reproduction was not repeated.
- [x] Add failing batch-runner and culvert-runner regressions for late Climate
  hydration, exact cache scope, and lock ordering.
- [x] Implement the minimal batch and culvert changes.
- [x] Verify downstream climate consumers use current post-build state.
- [x] Update affected canonical and subsystem documentation.
- [x] Run focused validation gates; full suite has the unrelated baseline
  failure recorded below.
- [x] Complete independent correctness, QA, and security reviews and resolve
  every medium/high finding.
- [x] Deploy the reviewed source to Forest under the existing worker restart
  procedure and record representative acceptance evidence.
- [ ] Close the package, archive the ExecPlan, and synchronize this tracker and
  `PROJECT_TRACKER.md`.

## In Progress

- Verified clean Forest `master` at `87559fe26`; the changed batch and culvert
  implementations now rehydrate Climate at the locked mutation boundary.
- Applicable contracts and nested playbooks read: NoDb persistence/concurrency,
  scoped RQ cache guard, hardening lifecycle, NoDb, RQ, and test guidance.
- Added and passed the real same-size `.nodb` interleaving regressions plus
  exact-scope/order tests (36 batch/rehydration tests; 5 culvert guard tests).
- Implemented fresh Climate boundary helpers in
  `wepppy/nodb/batch_runner.py` and `wepppy/rq/culvert_rq.py`; downstream
  interchange identity is asserted in both orchestration paths.
- Focused gates passed; the full suite reached 5,078 passed and 50 skipped
  before stopping on the unrelated pre-existing shape-converter compose
  contract failure in
  `tests/shape_converter/unit/test_runtime_hardening.py`.
- Restarted only `rq-worker` and `rq-worker-batch` on Forest. Source bind and
  helper imports were verified against image digest
  `sha256:6ac7e71030467a10e5d73dc18893cbd85c9202976d4b1b561a19dbb0d7ef2b75`.
- Batch acceptance job `codex-climate-batch-victoria-sooke18-20260905` finished
  `(True, 59.49883031845093)` with durable `status: success` metadata after
  Climate, RAP/OpenET, hillslope, watershed, and WATAR work. Stress job
  `codex-climate-batch-nasa-roses-202603-or28-20260905` completed its 11,748
  Climate tasks and downstream hillslope/management preparation without the
  target signature, then was stopped at 10,278/11,748 soil-prep tasks after
  functional verification.
- Culvert acceptance jobs `...-2907-20260905` and `...-573-20260905`
  reached later soil preparation but failed on missing existing `.sol`
  artifacts; neither emitted the target stale-write signature.

## Known limitation

- Forest culvert fixtures are incomplete: tested runs lack required soil
  artifacts or have a pre-existing raster-shape mismatch and cannot provide a
  full downstream-success receipt without manually changing run data. The
  target stale-write signature did not recur. Production deployment remains
  out of scope and requires separate operator authorization.

## Done

- [x] Captured the openWEPP batch failure signature, job IDs, timing, and
  populated-state classification (2026-09-05 00:29 UTC).
- [x] Confirmed the batch RQ registry had no duplicate `OR-10` job in the
  affected batch (2026-09-05 00:29 UTC).
- [x] Identified the existing `project_rq::build_climate_rq` exact-scope,
  hydrate-inside-lock implementation precedent (2026-09-05 00:29 UTC).
- [x] Scaffolded the package, active ExecPlan, lifecycle signals, review gates,
  Forest boundary, and rollback shape (2026-09-05 00:29 UTC).

## Decisions

- **2026-09-05 00:29 UTC - Treat the NoDb rejection as a safety signal, not the
  defect.** The stale-write guard prevented a lost update. The defect is the
  orchestration retaining a mutable Climate controller across unrelated,
  long-running stages.
- **2026-09-05 00:29 UTC - Use the established project RQ pattern in both
  runners.** Exact cache invalidation and hydration belong inside the accepted
  climate root-lock callback immediately before mutable work.
- **2026-09-05 00:29 UTC - Keep downstream controller freshness explicit.** An
  executor must not fix the build call while leaving RAP/OpenET or WEPP
  interchange on an early stale object.
- **2026-09-05 00:29 UTC - Require high-impact review.** RQ worker persistence
  and lock/cache ordering trigger correctness, QA, and security gates even
  though no public or credential surface changes.
- **2026-09-05 00:29 UTC - Limit live rollout to Forest.** Production repair,
  historical run mutation, and deployment are separate authorization
  boundaries.
- **2026-09-05 00:45 UTC - Return the current Climate from the locked build
  callback.** This keeps downstream consumers on the post-build controller
  without a second mutable hydration or a stale pre-stage reference.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Fresh build is followed by downstream use of an early Climate object | High | Medium | Assert controller identity/state ordering in both runner tests | Resolved |
| Cache clear occurs before root/archive rejection | High | Low | Place guard inside existing root-lock callback and test rejection ordering | Resolved |
| Retry masks a true concurrent writer | High | Low | Do not add stale-write catch/retry around `build()`; retain lock and guard | Resolved |
| Scientific artifacts change | High | Low | Preserve inputs/build API and compare representative outputs | No change observed |
| Culvert fixtures omit realistic long-stage mutation | Medium | Medium | Add direct same-size file-generation advance at persistence boundary | Accepted fixture limitation |
| Stale serialized runid labels obscure evidence | Medium | Medium | Record as separate follow-up unless persistence identity impact is proven | Out of scope; no causal defect found |

## Hardening Signal Log

- **Baseline**: openWEPP leaf `OR-10` retained Climate generation
  `(1788567519.6239834, 1864)` and later observed
  `(1788567558.374864, 1864)`, then returned `(False, approximately 150.5s)`.
- **Current health evidence**: `project_rq::build_climate_rq` already clears
  `climate.nodb` and hydrates inside its climate root-lock callback.
- **Post-change evidence**: focused tests pass; Victoria batch acceptance
  completed successfully, and culvert runs reached the changed workflow
  without the target signature before fixture failures.
- **Recurrence trigger**: any batch or culvert leaf reporting
  `NoDbStaleWriteError` for `climate.nodb` after deployment opens a new
  incident package and compares controller-hydration ordering and writer
  attribution with this baseline.

## Verification Checklist

- [x] `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1`
- [x] Focused culvert RQ test module(s) pass.
- [x] Direct, unmocked same-size generation-advance regression passes for each
  changed orchestration boundary.
- [x] `wctl run-pytest tests --maxfail=1` attempted; unrelated baseline failure
  is recorded above.
- [x] `wctl check-rq-graph` recorded as not applicable because no queue or
  dependency wiring changed;
  otherwise record `not applicable` with diff evidence.
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- [x] `python3 tools/code_quality_observability.py --base-ref origin/master`
- [x] `wctl doc-lint --path docs/work-packages/20260904_batch_culvert_climate_rehydration_b --path PROJECT_TRACKER.md`
- [x] `git diff --check`
- [x] Correctness, QA, and security review artifacts pass with documented
  baseline/fixture conditions.
- [x] Forest batch evidence and rollback details are recorded. Successful
  batch evidence is complete; the supplemental stress job was stopped after
  verification, while culvert full success is limited by existing missing
  soil/raster fixture artifacts.

## Notes - 2026-09-05 02:42 UTC

- User-directed cancellation stopped the supplemental OR-28 stress job through
  `wepppy.rq.cancel_job.cancel_jobs`; RQ reports `stopped` and all Forest
  queues are idle.
- The package is left at conditional closeout rather than claiming a culvert
  full-workflow success that the available fixtures cannot support.

## Notes - 2026-09-05 00:29 UTC

- The package was scaffolded from live canary evidence and repository
  precedent; no production implementation or live mutation was performed.
- The executing agent should begin by verifying current `master`, because the
  implementation may have moved after this scaffold commit.
- Test design must distinguish controller-cache staleness from legitimate
  malformed or missing Climate state. Do not make invalid state silently
  buildable.
- Next step: dispatch the active ExecPlan on Forest and move the relevant
  tracker items to In Progress before code edits.
