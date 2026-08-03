# Tracker - Batch Runner WATAR Integration

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-03 01:33 UTC
**Current phase**: Closed
**Last updated**: 2026-08-03 02:56 UTC
**Next milestone**: Observe the first live worker-pool WATAR batch run
**Security impact**: high
**Dedicated security review**: yes
**Security artifact**: `docs/work-packages/20260802_batch_runner_watar/artifacts/2026-08-03_security_review.md`

## Task Board

### Ready / Backlog

- [ ] None.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Traced Batch Runner directives, leaf execution, retry classification,
  snapshots, UI rendering, RQ orchestration, and existing tests. (2026-08-03 01:33 UTC)
- [x] Traced standalone WATAR base-project configuration, worker locking,
  `Ash.run_ash`, `AshPost`, and `TaskEnum.run_watar` completion behavior.
  (2026-08-03 01:33 UTC)
- [x] Scaffolded package, tracker, active ExecPlan, security placeholder, and
  project tracker entry. (2026-08-03 01:33 UTC)
- [x] Drafted the contract decision and canonical field matrix under the
  superseded REM-06 identity, then reclassified them as SURF-02C, with the
  GOV-00A-M1F register amendment. (2026-08-03 01:52 UTC)
- [x] Completed two independent read-only checkpoint reviews and recorded the
  blocked disposition. (2026-08-03 02:00 UTC)
- [x] Recorded Roger Lew's explicit authorization and amended governance,
  timestamp-authoritative retry, no-data, old-state, exact prerequisite, lock,
  and evidence contracts. (2026-08-03 02:10 UTC)
- [x] Obtained dual post-fix confirmation with no remaining high/medium
  findings. (2026-08-03 02:20 UTC)
- [x] Committed the accepted checkpoint as standalone ancestor `7f69e6654`.
  (2026-08-03 02:25 UTC)
- [x] Implemented optional WATAR/AshPost leaf execution, retry classification,
  generic UI support, climate invalidation, and durable base inputs.
- [x] Added positive, negative, compatibility, AshPost, route, snapshot, and
  frontend regressions.
- [x] Captured generated data-producing, no-data, failure/retry, catalog, and
  non-default input evidence.
- [x] Passed full pytest (`5800 passed, 61 skipped`), full Jest (`105 suites,
  756 tests`), lint, docs, graph, stubs, and exception-policy gates.
- [x] Closed independent security and correctness reviews with no open
  high/medium findings.

## Timeline

- **2026-08-03 01:33 UTC** - Package scoped from current Batch Runner and WATAR
  implementation evidence; no production code changed.
- **2026-08-03 01:52 UTC** - Operator execution direction recorded; the
  superseded REM-06/GOV-00A-M1F draft checkpoint entered dual review.
- **2026-08-03 02:00 UTC** - Dual review found four blocking high issues:
  enhancement authority, exact operator approval, retry authority, and AshPost
  no-data semantics. Production implementation remains blocked.
- **2026-08-03 02:10 UTC** - Roger Lew explicitly authorized the recommended
  contract; all findings were amended for dual post-fix confirmation.
- **2026-08-03 02:20 UTC** - Both independent reviewers confirmed no remaining
  high/medium findings; checkpoint ready for standalone ancestor commit.
- **2026-08-03 02:25 UTC** - Standalone checkpoint committed at `7f69e6654`;
  production tests/implementation are now authorized against that ancestor.
- **2026-08-03 02:56 UTC** - Implementation, generated acceptance, full gates,
  and post-fix independent reviews completed; package closed.

## Decisions Log

### 2026-08-03 01:33 UTC: Treat WATAR as an optional leaf completion task

**Context**: `TaskEnum.run_watar` and its UI label/glyph already exist globally,
but `BatchRunner.DEFAULT_TASKS` omits it. WATAR is initialized only for configs
with `ash.nodb` and depends on WEPP hillslope/watershed products.

**Options considered**:

1. Require WATAR for every batch leaf, which would make non-WATAR batches retry forever.
2. Add WATAR only when `ash.nodb` exists in the leaf, matching RAP/OpenET optional-task precedent.
3. Add a separate WATAR-only batch mode, which duplicates selection and progress machinery.

**Decision**: Plan for `run_watar` as an optional, directive-controlled leaf
task whose completion is required only when the leaf contains `ash.nodb`.

**Impact**: Existing batches remain compatible, while WATAR-enabled batches gain
normal progress and retry semantics. The checkpoint must ratify the exact rule.

### 2026-08-03 01:33 UTC: Preserve the WEPP-before-WATAR dependency in the leaf boundary

**Context**: `Ash.run_ash` reads WEPP hillslope interchange data and runs
`AshPost`; the standalone worker locks climate, watershed, and landuse roots.

**Decision**: WATAR must not run until required WEPP work and interchange
artifacts are complete. Prefer the existing per-leaf execution boundary unless
tests prove a separate RQ job is necessary.

**Impact**: The simplest implementation adds no new cross-job edge. If an RQ
edge is introduced, the dependency catalog and live job-tree evidence become
mandatory and the security review must assess cancellation/failure propagation.

### 2026-08-03 01:40 UTC: Make AshPost part of WATAR completion

**Context**: `Ash.run_ash` performs hillslope simulations, invokes
`AshPost.run_post`, and only then timestamps `TaskEnum.run_watar`. The batch UI
needs one meaningful terminal stage rather than a misleading simulation-only
success state.

**Decision**: Keep one `Run WATAR` directive and timestamp, but define it as the
combined Ash plus AshPost pipeline. A post-processing, documentation, version,
or catalog failure leaves WATAR incomplete and retry eligible.

**Impact**: Tests and generated-output evidence must cover post artifacts and a
failure after hillslope outputs exist. No separate `run_ash_post` directive is
introduced unless the contract checkpoint later records an operator-approved
reason to split user-visible stages.

### 2026-08-03 01:33 UTC: Do not change WATAR parameterization

**Context**: Base-project WATAR inputs are already persisted by the existing
route without enqueueing when the run is a batch base project.

**Decision**: Consume existing persisted `Ash` state. Do not select new defaults
or alter formulas, thresholds, units, model, transport mode, or fallback rules.

**Impact**: No parameterization ADR is required. Any need to alter those values
must stop this package and enter a separately approved ADR-backed scope.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| WATAR runs before WEPP products are complete or recoverable. | High | Medium | Explicit dependency preflight and interrupted-output regression. | Closed |
| Non-WATAR batches become permanently retry eligible. | High | Medium | Require `run_watar` only when `ash.nodb` exists; test old batches. | Closed |
| Ash hillslopes succeed but AshPost aggregation/catalog publication fails. | High | Medium | Keep the timestamp after `AshPost.run_post`; test partial post failure and retry recovery. | Closed |
| Changed base WATAR settings do not reach already-created leaves. | Medium | Medium | Clone-only policy plus explicit replacement guidance. | Closed |
| A failed WATAR retry repeats expensive completed WEPP work. | High | Medium | Timestamp gating and focused invalidation tests. | Closed |
| Separate child jobs weaken finalizer failure propagation. | High | Low | Kept inline leaf execution; no new job edge. | Closed |
| UI shows WATAR enabled for a batch that has no ash controller. | Medium | Medium | Documented generic directive versus per-leaf eligibility. | Closed |

## Verification Checklist

### Code Quality

- [x] Focused tests pass.
- [x] `wctl run-pytest tests --maxfail=1` passes.
- [x] `wctl run-npm lint` and `wctl run-npm test` pass.
- [x] `wctl check-test-stubs` passes; direct BatchRunner stubtest is blocked by documented preexisting module mypy errors.
- [x] Changed broad-exception enforcement is clean.

### Security

- [x] Contract checkpoint and two independent reviews precede production edits.
- [x] Dedicated security review is complete with no unresolved medium/high findings.
- [x] Auth/JWT/CSRF behavior remains unchanged.
- [x] Queue, worker, run-tree, locking, and cancellation surfaces are reviewed.

### Documentation and Testing

- [x] Batch Runner and ash transport documentation are updated.
- [x] Unit, integration, frontend, retry, and generated-output evidence is recorded.
- [x] `wctl check-rq-graph` passes; no RQ topology change was introduced.
- [x] Staging proves WEPP inputs precede WATAR and timestamp gating selects incomplete leaves.

## Progress Notes

### 2026-08-03 01:33 UTC: Discovery and scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Confirmed Batch Runner uses `DEFAULT_TASKS`, per-task RedisPrep timestamps,
  optional controller files, and missing-task classification for retry selection.
- Confirmed WATAR already owns `TaskEnum.run_watar`, timestamps it after
  `AshPost.run_post`, and persists inputs on batch base-project submission.
- Confirmed WATAR consumes WEPP hillslope/interchange outputs and standalone RQ
  execution uses climate/watershed/landuse NoDir locks.
- Created documentation scaffold only; no production implementation was edited.

**Blockers encountered**:

- The contract-first standard requires a ratified standalone ancestor before
  this intended UI/NoDb/RQ behavior change can be implemented.

**Next steps**:

1. Record the starting revision and exact normative delta in the contract artifact.
2. Resolve base-to-existing-leaf WATAR input resync behavior with the operator.
3. Obtain two independent reviews, commit the checkpoint, then start tests-first implementation.

**Test results**: Documentation validation pending at scaffold creation.

## Watch List

- **Ash controller timestamp ownership**: `Ash.run_ash` and `run_ash_rq` both
  timestamp `run_watar`; integration must remain idempotent and unambiguous.
- **Existing debris-flow typo**: `run_debris_flow_rq` appears to timestamp
  `TaskEnum.run_watar`; this is out of scope unless it contaminates Batch Runner
  acceptance evidence, in which case record a separate confirmed defect.

### 2026-08-03 02:56 UTC: Implementation closeout

**Agent/Contributor**: Codex

**Work completed**:

- Implemented and documented the approved SURF-02C Batch Runner WATAR/AshPost
  contract, including the reviewer-discovered batch-base input persistence gap.
- Generated both data-producing and no-data Ash/AshPost results on disposable
  development leaf copies and confirmed non-default persisted input use.
- Regenerated the RQ graph/catalog provenance after the enqueue-site file edit;
  topology remains 144 edges.
- Closed independent correctness and security reviews with no open high/medium
  findings.

**Validation**:

- `wctl run-pytest tests --maxfail=1`: 5,800 passed, 61 skipped.
- `wctl run-npm lint`: passed.
- `wctl run-npm test`: 105 suites and 756 tests passed.
- `wctl check-test-stubs`, `wctl check-rq-graph`, documentation lint, diff
  checks, and changed broad-exception enforcement: passed.
- `wctl run-stubtest wepppy.nodb.batch_runner`: blocked before stub comparison
  by the module's preexisting mypy errors; the new lock-scope typing deltas were
  corrected and the limitation is retained explicitly.

**Residual**: The generated staging run called the production Batch Runner leaf
stage directly and disabled Ash multiprocessing to accommodate an stdin harness.
The first live RQ worker-pool run remains a low-severity observation item.
