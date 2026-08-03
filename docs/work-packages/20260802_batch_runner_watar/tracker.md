# Tracker - Batch Runner WATAR Integration

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-03 01:33 UTC
**Current phase**: Contract checkpoint ready for standalone ancestor
**Last updated**: 2026-08-03 02:20 UTC
**Next milestone**: Commit checkpoint ancestor, then begin focused failing tests
**Security impact**: high
**Dedicated security review**: yes
**Security artifact**: `docs/work-packages/20260802_batch_runner_watar/artifacts/2026-08-03_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Create the contract-decision artifact with the starting revision and exact
  WATAR eligibility, ordering, retry, invalidation, UI, and compatibility rules.
- [ ] Obtain operator approval and two independent read-only contract reviews;
  disposition findings and commit the checkpoint as a standalone ancestor.
- [ ] Add focused failing tests for optional-task detection, WEPP dependency,
  WATAR/AshPost timestamp gating, retry selection, and old non-WATAR batches.
- [ ] Implement the smallest BatchRunner/worker integration allowed by the
  accepted checkpoint.
- [ ] Add actual snapshot/directive/render/controller coverage for `run_watar`.
- [ ] Update RQ dependency catalog if enqueue or dependency edges change and run
  `wctl check-rq-graph`.
- [ ] Produce generated-output evidence from a WATAR-enabled batch leaf.
- [ ] Complete security and independent correctness reviews.
- [ ] Update user/operator/developer docs and perform staging smoke validation.

### In Progress

- [ ] Commit the accepted SURF-02C/GOV-00A-M1F checkpoint as a standalone ancestor.

### Blocked

- [ ] Production edits are blocked until the operator-approved contract
  checkpoint and two review dispositions are committed as a standalone ancestor.
- [ ] None after ancestor commit; production edits remain blocked until then.

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
| WATAR runs before WEPP products are complete or recoverable. | High | Medium | Explicit dependency preflight and interrupted-output regression. | Open |
| Non-WATAR batches become permanently retry eligible. | High | Medium | Require `run_watar` only when `ash.nodb` exists; test old batches. | Open |
| Ash hillslopes succeed but AshPost aggregation/catalog publication fails. | High | Medium | Keep the timestamp after `AshPost.run_post`; test partial post failure and retry recovery. | Open |
| Changed base WATAR settings do not reach already-created leaves. | Medium | Medium | Ratify clone-only versus selective resync policy and test it explicitly. | Open |
| A failed WATAR retry repeats expensive completed WEPP work. | High | Medium | Timestamp gating and focused invalidation tests. | Open |
| Separate child jobs weaken finalizer failure propagation. | High | Low | Prefer inline leaf execution; if changed, use explicit dependency semantics and live job-tree proof. | Open |
| UI shows WATAR enabled for a batch that has no ash controller. | Medium | Medium | Snapshot eligibility metadata or clear directive semantics, ratified before implementation. | Open |

## Verification Checklist

### Code Quality

- [ ] Focused tests pass.
- [ ] `wctl run-pytest tests --maxfail=1` passes.
- [ ] `wctl run-npm lint` and `wctl run-npm test` pass.
- [ ] `wctl run-stubtest wepppy.nodb.batch_runner` and `wctl check-test-stubs` pass if API surfaces change.
- [ ] Changed broad-exception enforcement is clean or preexisting findings are dispositioned.

### Security

- [ ] Contract checkpoint and two independent reviews precede production edits.
- [ ] Dedicated security review is complete with no unresolved medium/high findings.
- [ ] Auth/JWT/CSRF behavior remains unchanged.
- [ ] Queue, worker, run-tree, locking, and cancellation surfaces are reviewed.

### Documentation and Testing

- [ ] Batch Runner and ash transport documentation are updated.
- [ ] Unit, integration, frontend, retry, and generated-output evidence is recorded.
- [ ] `wctl check-rq-graph` passes and live job-tree ordering is verified if wiring changes.
- [ ] Staging proves WEPP completes before WATAR and reruns select only eligible leaves.

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
