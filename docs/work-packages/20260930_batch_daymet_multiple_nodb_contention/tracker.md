# Tracker - Batch Daymet Multiple NoDb Contention

## Quick Status

**Timezone**: UTC
**Started**: 2026-09-30 19:00 UTC
**Current phase**: Discovery
**Last updated**: 2026-09-30 19:00 UTC
**Next milestone**: reproduce and attribute the competing `climate.nodb` writer on forest
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `docs/work-packages/20260930_batch_daymet_multiple_nodb_contention/artifacts/2026-09-30_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Capture the affected climate mode, spatial mode, and batch configuration
      without copying secrets or mutable run data into the repository.
- [ ] Build a deterministic real-file reproduction for the Daymet/`Multiple`
      stale-write signature.
- [ ] Attribute all `climate.nodb` writers and verify the batch directory-root
      lock identity across processes.
- [ ] Implement the smallest contract-conforming collect/finalize correction.
- [ ] Validate generated and consumed climate artifacts on forest.
- [ ] Complete independent correctness and security reviews.
- [ ] Prepare and execute the separately gated open-wepp.org file integration
      test, then retain exact evidence.

### In Progress

- [ ] Discovery and source attribution.

### Blocked

- Open-wepp.org integration is intentionally gated until forest tests and
  review gates pass; this is sequencing, not an implementation blocker.

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
| Finalizer loses unrelated durable state | High | Medium | Fresh rehydrate plus explicit relevant-input and derived-output sets | Open |
| Scientific output changes | High | Low | Semantic artifact parity for unchanged fixture | Open |
| Helper is implemented but production path is not wired | High | Medium | Trace the real batch call path and require cluster evidence | Open |
| Cluster test mutates more than the selected fixture | High | Low | Predeclare fixture, paths, rollback, and stop conditions | Open |

## Hardening Signal Log

- **Baseline health signals**: live job contains 38 child stale-write failures
  across observed-Daymet and PRISM revision paths.
- **Post-change health signals**: pending.
- **Danger signals observed**: none beyond the confirmed uncovered path.
- **Temporary callus register**: none.
- **Softening experiments**: not applicable; no temporary mitigation is
  authorized.

## Verification Checklist

### Code and Contracts

- [ ] Canonical NoDb contract conformance reviewed.
- [ ] Real-file pre-fix reproduction retained.
- [ ] Focused NoDb, climate, and batch suites pass.
- [ ] Full `wctl run-pytest tests --maxfail=1` passes on forest.
- [ ] Stub/API checks pass if public surfaces change.
- [ ] RQ dependency catalog/check passes if an enqueue edge changes.

### Reviews

- [ ] Independent correctness review complete.
- [ ] Dedicated security review complete.
- [ ] No unresolved medium/high findings.

### Generated Artifacts and Integration

- [ ] Intent and climate mode read back.
- [ ] Fresh durable `climate.nodb` read through normal controller.
- [ ] Generated climate intermediates semantically parsed.
- [ ] Exact downstream-consumed climate input read back.
- [ ] Forest integration evidence retained.
- [ ] Open-wepp.org file integration evidence retained.
- [ ] Completion claim does not exceed evidence.

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
