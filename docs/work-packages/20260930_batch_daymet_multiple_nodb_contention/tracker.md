# Tracker - Batch Daymet Multiple NoDb Contention

## Quick Status

**Timezone**: UTC
**Started**: 2026-09-30 19:00 UTC
**Current phase**: Forest gates passed; external cluster acceptance pending
**Last updated**: 2026-09-30 (117 focused; 10015 broad passes/99 skips)
**Next milestone**: obtain approved cluster access and exact integration fixture
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `docs/work-packages/20260930_batch_daymet_multiple_nodb_contention/artifacts/2026-09-30_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Capture the affected climate mode, spatial mode, and batch configuration
      without copying secrets or mutable run data into the repository.
- [x] Build deterministic real-file reproductions for Daymet and PRISM stages.
- [ ] Attribute all `climate.nodb` writers and verify the batch directory-root
      lock identity across processes.
- [x] Implement bounded Daymet/PRISM finalization and pre-startup ownership.
- [x] Validate real CLIGEN/PRISM output and the actual WEPP climate copy on forest.
- [x] Complete independent correctness and security reviews.
- [ ] Prepare and execute the separately gated open-wepp.org file integration
      test, then retain exact evidence.

### In Progress

- [ ] External incident attribution and bounded cluster integration.

### Blocked

- Open-wepp.org access and exact fixture remain unspecified. Forest has no
  kubectl. Approved access/fixture information was requested; local work continues.
  The separate cluster gate remains unsatisfied.

### Done

- [x] Classified the live exception family and separated the unrelated WBT
      terrain exception (2026-09-30 18:xx UTC).
- [x] Confirmed the deployed revision and uncovered legacy Daymet/`Multiple`
      path (2026-09-30 19:00 UTC).
- [x] Scaffolded package, tracker, ExecPlan, and environment split
      (2026-09-30 19:00 UTC).

## Timeline

- **2026-09-30 18:xx UTC** - Full Dell/HP worker batch exposed recurrent
  `climate.nodb` stale-write failures.
- **2026-09-30 19:00 UTC** - Roger selected forest for package execution and
  open-wepp.org for the final file integration test.
- **2026-09-30 19:00 UTC** - Work package scaffolded.

## Decisions Log

### 2026-09-30 19:00 UTC: Reuse the existing ownership pattern

**Context**: Earlier finalization work is present, but the live stack shows the
legacy observed-Daymet build still holds a controller through expensive work.

**Decision**: Begin with faithful extension of the existing snapshot,
collect, rehydrate, validate, publish, and dump-once pattern. Do not introduce
new runtime machinery or weaken stale-write checks.

**Impact**: Implementation must prove the actual batch path is wired, not only
that a new helper passes unit tests.

### 2026-09-30 19:00 UTC: Separate forest validation from cluster acceptance

**Context**: Roger will execute the work package on forest; the decisive
file-backed integration belongs on the open-wepp.org cluster.

**Decision**: Complete implementation, focused tests, broad tests, and reviews
on forest. Only then execute a bounded, separately recorded cluster integration
test. Keep deployment, integration, affected-run repair, and incident closure
as distinct claims.

**Impact**: Forest success cannot close the package's environment-validation
criterion. Cluster execution must record exact revision/image and artifact
content.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Competing writer remains unattributed | High | Medium | Instrument real file and lock identities before choosing a fix | Open |
| Finalizer loses unrelated durable state | High | Medium | Fresh rehydrate plus explicit relevant-input and derived-output sets | Locally verified |
| Scientific output changes | High | Low | Semantic artifact parity for unchanged fixture | Locally verified |
| Helper is implemented but production path is not wired | High | Medium | Trace the real batch call path and require cluster evidence | Open |
| Cluster test mutates more than the selected fixture | High | Low | Predeclare fixture, paths, rollback, and stop conditions | Open |

## Hardening Signal Log

- **Baseline health signals**: live job contains 38 child stale-write failures
  across observed-Daymet and PRISM revision paths.
- **Post-change health signals**: local fixtures preserve unrelated edits, reject
  relevant changes and match generated/consumed climate; cluster recurrence pending.
- **Danger signals observed**: pre-fix startup/reset/resync ownership bypasses
  and failed-artifact loss, corrected and independently reviewed locally.
- **Temporary callus register**: none.
- **Softening experiments**: not applicable; no temporary mitigation is
  authorized.

## Verification Checklist

### Code and Contracts

- [x] Canonical NoDb contract conformance reviewed.
- [x] Real-file pre-fix reproduction retained.
- [x] Focused NoDb, climate, and batch suites pass.
- [x] Full `wctl run-pytest tests --maxfail=1` passes on forest.
- [x] Stub/API checks pass if public surfaces change.
- [ ] RQ dependency catalog/check passes if an enqueue edge changes.

### Reviews

- [x] Independent correctness review complete.
- [x] Dedicated security review complete.
- [x] No unresolved medium/high findings.

### Generated Artifacts and Integration

- [ ] Intent and climate mode read back.
- [x] Fresh durable `climate.nodb` read through normal controller.
- [x] Generated climate intermediates semantically parsed.
- [x] Exact downstream-consumed climate input read back.
- [x] Forest integration evidence retained.
- [ ] Open-wepp.org file integration evidence retained.
- [x] Completion claim does not exceed evidence.

## Progress Notes

### 2026-09-30 19:00 UTC: Initial scaffold

**Agent/Contributor**: Codex with Roger as decision owner

**Work completed**:
- Captured the live failure signature, affected path, exclusions, and prior
  package lineage.
- Recorded the forest/open-wepp.org validation split.
- Created the package and executable plan without changing production code or
  live state.

**Blockers encountered**: none.

**Next steps**:
- Execute the discovery milestone on forest.
- Retain writer and lock attribution before implementing a correction.

**Test results**: documentation scaffold only; validation pending.

## Watch List

- **Duplicate leaf execution**: determine whether two RQ jobs can reach the
  same run despite the directory-root lock.
- **Long-lived Daymet controller**: distinguish an uncovered mutation boundary
  from an internal nested writer.
- **PRISM revision**: verify its current finalizer is entered with fresh state
  after Daymet publication.

### 2026-09-30: Forest execution

Two pre-fix real-file router tests failed with same-size `NoDbStaleWriteError`.
Initial correction passes 84 focused tests. Source attribution retained in
`artifacts/2026-09-30_writer_attribution.md`; startup/resync ownership bypasses
corrected locally; exact cluster writer remains open. Forest lacks kubectl; approved cluster
access was requested while local work continues. No live mutation performed.

### 2026-09-30: Ownership and artifact validation

- The new `tests/nodb/test_batch_daymet_multiple_contention.py` passes 33 cases,
  followed by two legacy/current base-resync cases after the final compatibility
  addition. Coverage includes a 12-case absent/empty/populated × mode × spatial
  matrix, duplicate exclusion across projection reset, no callback replay,
  preserved live Climate tokens, serializer rollback, visible failed attempts,
  unknown-commit backup browser/archive/restore and real numerical parity.
- Climate stubtest, stub completeness and broad-exception enforcement pass.
  Final affected suites pass 117 tests; the full suite passes 10015 with 99 skips.
- Existing six-hour root leases remain unchanged/unrenewed. Shared resolved
  paths, Redis identity and duration must be read on the cluster before release.
- Durable decisions and rationale are documented in
  `docs/dev-notes/batch-climate-rap-finalization.md` (“Batch ownership” and
  “Publication and recovery”) and
  `docs/schemas/climate-parquet-lineage-contract.md` (“Daymet acquisition source
  preservation”). No scientific parameterization changed; ADR not required.
- The observed incident writer remains unproven. Local injected writes establish
  corrected boundaries; they do not establish cross-node incident causality.

### 2026-09-30: Final focused validation and retained evidence

Final combined climate/batch/RQ run: **117 passed** in 26.66 seconds; the new
regression module alone: **35 passed** in 21.85 seconds. Independent source
reviews cleared local findings. The full repository suite passed **10015 tests**, with **99 skips** and 3558
warnings, in 2433.36 seconds (40m33s), exit 0.
A redundant overlapping NoDb/RQ run was intentionally interrupted after 1569
passes/23 skips to avoid fixture contention; it is not claimed as a pass gate.

Retained evidence: `artifacts/2026-09-30_forest_validation.md`,
`artifacts/2026-09-30_forest_artifact_manifest.json`, and the unexecuted external
`artifacts/2026-09-30_cluster_integration_gate.md`. The canonical lineage contract,
“Daymet acquisition source preservation,” and developer note, “User and operator
behavior,” document one commit per finalized stage and incomplete Multiple
readiness after PRISM failure. No deployment, run repair or closure is claimed.

### Final forest handoff

All local gates pass. Cluster access/target identity, actual incident writer and
cross-node lock identity remain open external acceptance work. No branches,
commits, registry writes, cluster mutations, deployments or affected-run repairs
were performed. The exact source diff is reviewed and retained locally; the
cluster gate must record an immutable candidate revision/image before execution.

### Publication instruction

Roger authorized committing and pushing the forest-validated change on the
current branch. This publishes source and evidence only; cluster integration,
deployment and affected-run repair remain separate open gates. The candidate
revision is the Git commit containing this package update.
