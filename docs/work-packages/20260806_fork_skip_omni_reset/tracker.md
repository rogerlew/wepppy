# Tracker - Fork Skip Omni Scenarios/Contrasts and Reset

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-06 14:55 UTC
**Current phase**: Complete
**Last updated**: 2026-08-06 18:34 UTC
**Next milestone**: Worker-first deployment after draining fork/archive consumers
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `artifacts/2026-08-06_security_review.md`

## Task Board

### Ready / Backlog

- [x] Select rewrite-in-place `Omni.reset_for_fork()` contract, exact persisted
  fresh-state comparison, and unconditional cache/lock sequence.
- [x] Dispatch two independent contract reviews and disposition all findings.
- [x] Commit the accepted contract/reviews as standalone ancestor `82e47916f`.
- [x] Implement UI, schema/default, route, enqueue, worker, copy, and reset flow.
- [x] Add exhaustive boolean-matrix and destination-invariant tests.
- [x] Complete documentation, validation, and final reviews.

### In Progress

- [x] Obtain post-fix confirmation for COR-01 through COR-03 and SEC-01 through
  SEC-07, then ratify the contract decision.

### Blocked

- None. The contract checkpoint is accepted and all implementation gates pass.

### Done

- [x] Scaffold package, tracker, contract draft, security artifact, and active
  ExecPlan (2026-08-06 14:55 UTC).
- [x] Independent scaffold review completed with HOLD disposition; all ten
  findings accepted for amendment (2026-08-06 UTC).
- [x] Registered SURF-04B, cross-linked all four owners, and incorporated
  REV-01 through REV-10 into the contract/package/plan (2026-08-06 UTC).
- [x] Follow-up review resolved seven findings, retained REV-03/04/08, and found
  RedisPrep/query-engine integrity gaps; all were incorporated (2026-08-06 UTC).
- [x] Final follow-up confirmed REV-01 through REV-10, NEW-01/02, and REG-01
  resolved; scaffold PASS with no medium/high findings (2026-08-06 UTC).
- [x] Independent checkpoint reviews found COR-01 through COR-03 and SEC-01
  through SEC-07; every finding was accepted and incorporated (2026-08-06 UTC).
- [x] Post-fix correctness and security reviews passed with zero unresolved
  medium/high findings; operator acceptance recorded (2026-08-06 UTC).

## Decisions Log

### 2026-08-06 14:55 UTC: Bounded Omni-only reset

**Context**: Omitting child projects without resetting copied controller and
aggregate state would leave the fork internally inconsistent.

**Decision**: The option resets only Omni state and Omni-owned directories in
the destination. Source data and unrelated destination controllers are outside
scope.

**Impact**: The worker needs one explicit destination-only Omni reset operation
after root NoDb identity rewrite, not scattered field edits across the fork path.

### 2026-08-06 14:55 UTC: Existing-tool property coverage

**Context**: Three fork booleans form a finite state space.

**Decision**: Generate and assert all eight boolean combinations in pytest and
Jest without adding Hypothesis or fast-check.

**Impact**: Tests must assert invariants, not duplicate eight hand-written
examples.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Missing children but stale `omni.nodb` references | High | High | Single Omni reset transaction plus load-after-reset tests | Open |
| Broad rsync exclude drops unrelated `_pups` data | High | Low | Anchored exact collection exclusions and sibling-preservation properties | Open |
| Reset mutates source through symlink/path confusion | High | Low | Descriptor/no-follow containment review and source hash invariant | Open |
| Option interactions drift | Medium | Medium | Exhaustive eight-state matrix | Open |
| Partial reset reports success | High | Low | Fail before readiness/success and test injected failures | Open |
| Fifth-argument producer reaches an old worker | High | Medium | Worker-first drained rollout and legacy-job tests | Open |
| Partial registered destination is mistaken for rollback | Medium | Medium | Specify unready partial behavior; do not claim transaction rollback | Open |
| RedisPrep claims removed Omni work completed | High | High | Remove exactly two Omni timestamps; preserve unrelated timestamps | Open |
| Query catalog advertises deleted Omni artifacts | Medium | High | Invalidate copied catalog/cache and test regenerated unrelated discovery | Open |
| Copied cleanup node redirects outside destination | High | Low | Held destination-rooted descriptors, no-follow validation, external sentinels | Open |
| Copied RedisPrep node redirects metadata mutation | High | Low | Reject symlink/special `redisprep.dump` before hydration | Open |
| Live Omni lock is erased during reset | High | Low | Prove destination ownership and reject active locks | Open |
| Profile target helpers resolve different trees | High | Low | Resolve one canonical destination for copy/cache/lock/controller operations | Open |
| Profile claim outlives or races its RQ owner | High | Low | Per-target flock, atomic ownership transfer, failure-tolerant finalizer, terminal/missing recovery | Mitigated |

## Verification Checklist

### Contract and Security

- [x] Exact UI/request/default/response/RQ contract accepted.
- [x] Two independent pre-implementation reviews complete.
- [x] Dedicated security review has no unresolved medium/high findings.
- [x] Standalone checkpoint SHA `82e47916f` recorded here.

### Testing

- [x] Jest/render property matrix covers initial state and serialized payload.
- [x] Route/schema coverage proves parsing/default/response/enqueue args.
- [x] Worker property matrix covers exclusions and reset decision.
- [x] Checked tuples clear exactly two Omni timestamps and invalidate stale
  query-engine catalog/cache without losing unrelated state.
- [ ] Integration tests prove empty coherent destination and unchanged source.
- [x] `wctl run-pytest tests/rq/test_project_rq_fork.py` passes.
- [x] `wctl run-pytest tests/microservices/test_rq_engine_fork_archive_routes.py` passes.
- [x] `wctl run-pytest tests/nodb/mods/test_omni.py` passes.
- [x] `wctl run-npm lint` and `wctl run-npm test` pass.
- [x] `wctl run-pytest tests --maxfail=1` passes (`5891 passed, 61 skipped`).
- [x] `wctl check-rq-graph` passes after catalog regeneration.
- [x] Docs lint and changed broad-exception enforcement pass.
- [x] Final correctness, QA, and security reviews pass with zero unresolved
  medium/high findings.

## Progress Notes

### 2026-08-06 14:55 UTC: Scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Mapped the current template -> JavaScript -> rq-engine -> `fork_rq` boolean
  flow and the existing Omni child/aggregate layout.
- Captured the operator-directed behavior as a draft normative contract.
- Defined exhaustive property-style coverage without a new dependency.

**Next steps**:

- Confirm exact reset fields and cache/lock sequence from canonical NoDb rules.
- Review and ratify the contract before any production implementation edits.

**Test results**: Documentation-only scaffold; docs lint pending.

### 2026-08-06 UTC: Independent scaffold review

**Agent/Contributor**: independent risk-focused reviewer agent

**Work completed**:

- Reviewed the package against current fork route/worker, Omni controller,
  NoDb, readiness, UI, schema, and RQ contracts.
- Found and documented ten governance/correctness/test gaps in
  `artifacts/2026-08-06_scaffold_review.md`.
- Set the gate to HOLD and accepted every finding for contract amendment.

**Next steps**:

- Amend canonical registration, exact ordering/state/exclusion/failure
  semantics, readiness, rollout, cache/lock, and property requirements.
- Re-review the amended checkpoint before implementation.

**Test results**: Review only; no production implementation exists.

### 2026-08-06 UTC: Findings incorporated

**Agent/Contributor**: Codex

**Work completed**:

- Registered SURF-04B in the canonical child register and cross-linked SURF-04,
  SURF-04A, DOM-25A, and DOM-25B without changing their state.
- Amended ordering, fresh-state, exclusion, failure/readiness, deployment,
  cache/lock, boundary/accessibility, and source-evidence contracts.

**Next steps**:

- Complete independent follow-up review and disposition any remaining finding.
- Keep implementation blocked until dual review and checkpoint requirements are
  satisfied.

**Test results**: Documentation validation pending.

### 2026-08-06 UTC: Follow-up review complete

**Agent/Contributor**: independent risk-focused reviewer agent

**Work completed**:

- Confirmed every initial finding and both additional integrity findings are
  incorporated in the normative contract and plan.
- Confirmed the canonical register includes the exact RedisPrep/query-engine
  mutation and preservation boundaries.
- Issued final scaffold PASS with no unresolved medium/high findings.

**Next steps**:

- Complete the mandatory security review and second independent checkpoint
  review.
- Record explicit operator acceptance and commit the accepted checkpoint as a
  standalone ancestor before production implementation.

**Test results**: Review artifact only; production implementation remains absent.
