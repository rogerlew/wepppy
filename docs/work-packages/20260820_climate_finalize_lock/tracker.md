# Tracker - Climate Multiple-Build Finalize Lock

> Living record for the multiple-interpolated climate stale-write hardening.

## Quick Status

**Timezone**: UTC

**Started**: 2026-08-21 04:23 UTC

**Current phase**: Implementation and validation complete; canary pending separate authorization

**Last updated**: 2026-08-21 06:00 UTC

**Next milestone**: Separately authorized canary deployment and observation

**Security impact**: `high`

**Dedicated security review**: `yes`

**Security artifact**: `artifacts/2026-08-21_security_review.md`

## Task Board

### Ready / Backlog

- [x] Ratify refresh-on-finalize behavior in the canonical NoDb contract.
- [x] Add a failing same-size concurrent-rewrite regression for GridMET.
- [x] Add parity coverage for Daymet multiple-interpolated finalization.
- [x] Implement collection results and fresh-state finalization.
- [x] Run focused and environment-qualified repository validation.
- [x] Complete correctness, QA, and security reviews.
- [x] Resolve the Topanga validation follow-up and verify the failing test
  ordering.
- [ ] Deploy through the separately authorized canary workflow and observe.

### In Progress

- None; implementation and validation are complete.

### Blocked

- Deployment is outside this scaffold request and requires separate authority.

### Done

- [x] Captured the incident signature and constrained scope (2026-08-21 04:23 UTC).
- [x] Identified the existing culvert finalizer precedent (2026-08-21 04:23 UTC).
- [x] Scaffolded package, tracker, ExecPlan, and review gates (2026-08-21 04:23 UTC).
- [x] Added the canonical collect-then-finalize contract checkpoint
  (2026-08-21 04:43 UTC).
- [x] Implemented shared input snapshots/results/finalization and added
  GridMET/Daymet regressions (2026-08-21 05:04 UTC).
- [x] Completed focused, base-persistence, stub, docs, quality, and
  environment-qualified repository gates: `6087 passed, 61 skipped` (2026-08-21
  05:32 UTC).
- [x] Completed correctness, QA, and security reviews with no unresolved
  medium/high findings (2026-08-21 05:32 UTC).
- [x] Made the Docker canary contract test explicitly skip when Compose v2 is
  unavailable and documented the expected environment condition (2026-08-21
  06:00 UTC).

## Timeline

- **2026-08-21 04:12:03 UTC** - Climate job began collection.
- **2026-08-21 04:13:17 UTC** - `climate.nodb` received a same-size rewrite.
- **2026-08-21 04:15:03 UTC** - Final stale Climate dump was correctly rejected.
- **2026-08-21 04:23 UTC** - Package scaffolded.

## Decisions Log

### 2026-08-21 04:23 UTC: Use a collect-then-finalize lock pattern

**Context**: The current multiple GridMET build holds one hydrated Climate
object across minutes of parallel work and then dumps that stale mutation base.

**Options considered**:

1. Weaken stale-write detection or retry the stale dump.
2. Build a generation/manifests orchestration subsystem.
3. Collect derived results outside the lock, then refresh and finalize under a
   short lock after verifying relevant inputs.

**Decision**: Option 3. It is the smallest pattern conforming to the canonical
NoDb multiple-writer contract.

**Impact**: The implementation must explicitly enumerate input and output
fields; it must not provide generic automatic object merging.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Relevant input comparison omits a field | High | Medium | Explicit build-input snapshot plus GridMET/Daymet parity tests | Resolved by implementation review and focused tests |
| Finalizer overwrites unrelated state | High | Low | Fresh durable rehydrate and derived-field allowlist | Resolved by real same-size rewrite regression |
| Lock remains held during expensive work | High | Low | Collection moved outside lock; finalizer is bounded | Resolved by code review and path tests |
| Partial generated files survive failure | Medium | Existing | Preserve current behavior; do not expand scope without evidence | Accepted baseline |
| GridMET and Daymet diverge | Medium | Medium | Shared semantic contract and separate path tests | Open |
| Process CWD leaks into later tests/callers | Medium | Medium | Restore CWD at Omni scenario boundary and root repository artifact paths | Resolved by combined regression |

## Hardening Signal Log

- **Baseline health signals**: one observed GridMET build lost its successful
  computation at final persistence due to a same-size concurrent rewrite.
- **Post-change health signals**: focused climate suite, environment-qualified repository suite, and Omni-then-Topanga ordering regression pass; canary observation pending.
- **Danger signals observed**: long-lived mutation base and final dump after
  expensive parallel work.
- **Temporary callus register**: none planned.
- **Softening experiments**: N/A.

## Verification Checklist

### Code Quality

- [x] Focused NoDb and climate tests pass.
- [x] Environment-qualified repository suite passes: `6087 passed, 61 skipped`.
- [x] Changed-file broad-exception and quality checks recorded.
- [x] `git diff --check` passes.

### Security

- [x] NoDb strict stale-write and ownership checks remain unchanged.
- [x] Worker subprocess inputs and run-tree boundaries remain unchanged.
- [x] Dedicated review has no unresolved medium/high findings.

### Documentation

- [x] Contract checkpoint precedes production implementation edits.
- [x] NoDb docs describe the finalize-lock pattern.
- [x] Package, tracker, and ExecPlan remain synchronized.

### Testing

- [x] Unrelated same-size rewrite is preserved.
- [x] Relevant climate-input rewrite supersedes the finalizer.
- [x] GridMET and Daymet success paths persist derived outputs.
- [x] Collection failure performs no final controller mutation.
- [x] Existing single-climate paths remain unchanged.

### Deployment

- [x] Local/container validation completed.
- [ ] Canary deployment separately authorized and completed.
- [ ] Fourteen-day observation window started.

## Progress Notes

### 2026-08-21 04:23 UTC: Package scaffolded

**Agent/Contributor**: Codex

**Work completed**:

- Reduced the proposed design to a refresh-on-finalize lock pattern.
- Recorded the exact incident and relevant culvert precedent.
- Defined contract-first, correctness, and security gates.

**Blockers encountered**: None during scaffolding.

**Next steps**:

- Review and ratify the contract checkpoint.
- Write the exact interleaving regressions before production code.

**Test results**: `git diff --check` passed. `wctl doc-lint` was unavailable on
the macOS authoring host (`wctl: command not found`) and remains a Linux
development-environment validation step.

### 2026-08-21 04:43 UTC: Contract checkpoint ratified

**Agent/Contributor**: Codex

**Work completed**:

- Added a climate-neutral collect-then-finalize clause to the canonical NoDb
  persistence/concurrency contract.
- Required fresh durable hydration under the finalization lock, explicit
  relevant-input conflict handling, derived-field allowlisting, and no generic
  object merge.

**Blockers encountered**: None.

**Next steps**: Add the failing interleaving regressions before production
implementation edits.

**Test results**: Contract diff inspected; focused tests not yet rerun.

### 2026-08-21 05:04 UTC: Implementation and regression milestone

**Agent/Contributor**: Codex

**Work completed**:

- Added `ClimateMultipleBuildInputs` and `ClimateMultipleBuildResult` with an
  explicit derived-field allowlist.
- Refactored GridMET and Daymet multiple-interpolated paths so collection runs
  without the Climate lock and finalization refreshes the durable singleton
  before one bounded mutation.
- Added an explicit `ClimateMultipleBuildSupersededError` and RQ
  `SUPERSEDED` status boundary.
- Added real temporary Climate NoDb tests for same-size unrelated, relevant,
  and malformed rewrites, plus collection-failure and path-parity coverage.

**Blockers encountered**: None.

**Next steps**: Run base persistence gates, the full suite, changed-file
quality checks, and complete independent review artifacts.

**Test results**: Focused climate suite passed: `57 passed`; Climate stubtest
passed with no issues.

### 2026-08-21 05:45 UTC: Topanga validation follow-up resolved

**Agent/Contributor**: Codex

**Work completed**:

- Wrapped Omni scenario execution with a `finally` CWD restoration boundary;
  both success and exception paths are covered.
- Rooted all peakflow census references to the repository using
  `Path(__file__).resolve()` so tests do not depend on leaked process CWD.
- Added an Omni regression assertion and ran Omni orchestration before the full
  peakflow census module to reproduce the former failing order.

**Environment note**: The Docker Compose smoke test is unavailable in this
  runner because its Docker CLI lacks the Compose v2 plugin. The test now skips
  explicitly for that expected environment condition; this follow-up did not
  change deployment authority.

**Test results**: `wctl run-pytest tests/nodb/mods/test_omni_run_orchestration_service.py tests/wepp/peakflow_census/test_peakflow_census.py --maxfail=1` — `25 passed, 1 skipped`.

### 2026-08-21 06:00 UTC: Compose capability skip documented

**Agent/Contributor**: Codex

**Work completed**:

- Added an explicit Docker Compose v2 capability probe to the canary contract
  test; unavailable Compose tooling produces a pytest skip, while real Compose
  rendering failures remain test failures.
- Documented the expected container capability difference in `docker/README.md`
  and synchronized the package, QA artifact, and ExecPlan notes.

**Environment note**: This runner's Docker CLI lacks the Compose v2 plugin,
which is the expected skip condition for this local test environment.

**Test results**: `wctl run-pytest tests/docker/test_canary_smoke_contract.py
--maxfail=1` — `1 passed, 1 skipped`.

### 2026-08-21 05:32 UTC: Validation and review closeout

**Agent/Contributor**: Codex

**Work completed**:

- Completed the repository suite with only the Docker Compose smoke test and
  mounted-data Topanga integration test excluded; both exclusions are recorded
  as environment limitations in the QA artifact.
- Completed correctness, QA, and security artifacts with no unresolved
  medium/high findings.
- Updated the existing RQ broad-exception allowlist line after the new climate
  superseded-status boundary shifted the governed fork catch.

**Blockers encountered**: Canary deployment and observation remain separately
authorized operational work.

**Test results**: `6087 passed, 61 skipped`; changed-file broad-exception gate
passed; code-quality observability passed; docs lint passed for all changed
Markdown package/docs paths; `git diff --check` passed.

## Watch List

- **Input snapshot completeness**: covered by the explicit ten-field snapshot,
  parity tests, and correctness review.
- **Lock duration**: finalization remains a short read-modify-write transaction;
  canary observation should watch for regressions.
