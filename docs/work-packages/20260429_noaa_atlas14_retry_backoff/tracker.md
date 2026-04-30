# Tracker - NOAA Atlas 14 Retry Backoff Hardening for Climate Artifact Export

> Living document tracking progress, decisions, risks, and handoff context for NOAA download retry hardening.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-29 21:50 UTC  
**Current phase**: Complete (implementation + targeted validation)  
**Last updated**: 2026-04-30 05:42 UTC  
**Next milestone**: Optional post-deploy latency/health observation window review  
**Security impact**: `none`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Work-package scaffold created (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`) (2026-04-29 21:50 UTC).
- [x] Baseline incident evidence captured from `/wc1/runs/bo/bovine-clipboard/climate.log` (2026-04-29 21:50 UTC).
- [x] Retry precedent review completed across local implementations (status2, preflight2, Overpass, wepp_runner) (2026-04-29 21:50 UTC).
- [x] Active ExecPlan authored for implementation sequencing and validation (2026-04-29 21:50 UTC).
- [x] Root `PROJECT_TRACKER.md` backlog registration completed (2026-04-29 21:50 UTC).
- [x] Added bounded exponential retry for NOAA Atlas 14 download with parameterized defaults and attempt-level logging (2026-04-30 05:35 UTC).
- [x] Added deterministic NOAA retry regressions for transient recovery, retry exhaustion, and non-retryable no-coverage (2026-04-30 05:38 UTC).
- [x] Ran targeted pytest gate for `tests/nodb/test_climate_artifact_export_service.py` (`10 passed`) (2026-04-30 05:42 UTC).
- [x] Updated `PROJECT_TRACKER.md` lifecycle status to Done for this package (2026-04-30 05:42 UTC).

## Timeline

- **2026-04-29 21:50 UTC** - Package created and scoped from observed NOAA 503 artifact miss.
- **2026-04-29 21:50 UTC** - Local retry parameterization precedents reviewed and documented.
- **2026-04-30 05:35 UTC** - Implemented retry/backoff policy in `download_noaa_atlas14_intensity`.
- **2026-04-30 05:38 UTC** - Added deterministic retry regressions covering required NOAA scenarios.
- **2026-04-30 05:42 UTC** - Targeted validation passed (`10 passed`) and package moved to Done.

## Decisions Log

### 2026-04-29 21:50 UTC: Use bounded retries and preserve optional NOAA contract
**Context**: Climate build currently succeeds even when NOAA artifact download fails; users still need best-effort NOAA artifact generation.

**Options considered**:
1. Keep single-attempt behavior and rely on manual reruns.
2. Add bounded retries for transient errors while keeping final failure non-fatal.
3. Make NOAA artifact mandatory and fail climate build when download fails.

**Decision**: Option 2.

**Impact**: Better resilience to short outages without breaking existing optional-artifact behavior.

---

### 2026-04-29 21:50 UTC: Anchor retry timings to local precedent
**Context**: User requested parameterization guidance from existing implementations.

**Options considered**:
1. Invent new timing constants without precedent.
2. Reuse local defaults and patterns from existing retry code paths.

**Decision**: Option 2.

**Impact**: Proposed defaults for this package derive from:
- `status2/preflight2`: `1s` base, `30s` cap, bounded attempts.
- `overpass.py`: small bounded exponential schedule for HTTP retries.
- `wepp_runner.run_hillslope`: bounded exponential + jitter for transient recovery.

---

### 2026-04-30 05:35 UTC: Final retry policy values and parameterization contract
**Context**: NOAA retry behavior needed bounded resilience while keeping climate export latency bounded and tuneable.

**Options considered**:
1. Keep hard-coded values in function call sites.
2. Parameterize via environment-backed defaults with bounded exponential schedule.

**Decision**: Option 2.

**Impact**: Implemented environment-backed parameters:
- `WEPPPY_NOAA_ATLAS14_TIMEOUT_SECONDS` (default `30`)
- `WEPPPY_NOAA_ATLAS14_TOTAL_ATTEMPTS` (default `3`)
- `WEPPPY_NOAA_ATLAS14_RETRY_BASE_SECONDS` (default `1.0`)
- `WEPPPY_NOAA_ATLAS14_RETRY_CAP_SECONDS` (default `8.0`)

`ValueError` remains immediate non-retryable no-coverage handling; transient classes retry until bounded exhaustion.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Retry loop adds too much wall-clock delay to climate build | Medium | Medium | Keep attempts bounded and cap delay; validate runtime impact on representative run | Mitigated (bounded defaults landed); follow-up observation recommended |
| Retry classifier retries non-transient errors | Medium | Low | Keep `ValueError` no-coverage explicitly non-retryable; test classifier behavior | Closed (deterministic test added) |
| Logging insufficient for operator triage | Low | Medium | Include attempt counts, delay, and exhaustion summary in logs | Closed (attempt + backoff + exhaustion logging landed) |

## Hardening Signal Log (Required for incident/remediation packages)

- **Baseline health signals**: NOAA artifact missing when transient NOAA 503 occurs.
- **Post-change health signals**: More runs emit successful NOAA artifact creation after transient upstream failures.
- **Danger signals observed**: None during targeted test validation.
- **Temporary callus register**:
  - Bounded retry loop for NOAA downloads, owner: package implementer, introduced date: 2026-04-30, review date: +14 days post deploy, status: Active.
- **Softening experiments**:
  - Hypothesis: If NOAA outage incidence is low and latency impact is measurable, retry cap can be reduced.
  - Gate results: Deterministic retry tests pass; live latency telemetry not captured in this package.
  - Decision: Keep defaults for now; tune only with production evidence.

## Verification Checklist

### Code Quality
- [x] Changed tests pass for climate artifact exporter.
- [x] No broad exception regression in production path.
- [x] Retry helper remains readable and bounded.

### Documentation
- [x] Work-package docs initialized and linked.
- [x] Decision rationale and precedent captured in package docs.
- [x] Post-implementation validation evidence captured in tracker and ExecPlan.

### Testing
- [x] Retry-success path covered with deterministic test.
- [x] Retry-exhaustion path covered with deterministic test.
- [x] No-coverage (`ValueError`) stays non-retryable.
- [x] Existing climate artifact exporter tests remain green.

### Deployment/Operational
- [ ] Validate behavior on a representative run flow.
- [ ] Capture observed latency impact and log clarity.

## Progress Notes

### 2026-04-29 21:50 UTC: Package authoring session
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold and recorded incident context.
- Reviewed retry/backoff precedent implementations across local Go and Python surfaces.
- Authored package scope and active ExecPlan aligned with requested retry-parameterization guidance.
- Prepared backlog registration for root tracker.

**Blockers encountered**:
- None.

**Next steps**:
1. Implement bounded retry/backoff in `ClimateArtifactExportService.download_noaa_atlas14_intensity`.
2. Add deterministic regressions for retry behavior.
3. Run targeted tests and record evidence.

**Test results**:
- Discovery-only session; no test suite run in this session.

### 2026-04-30 05:42 UTC: Implementation and validation session
**Agent/Contributor**: Codex

**Work completed**:
- Implemented bounded NOAA retry/backoff with environment-backed default timings in `ClimateArtifactExportService.download_noaa_atlas14_intensity`.
- Preserved non-fatal optional NOAA contract and kept `ValueError` path immediate/non-retryable.
- Added deterministic NOAA regressions:
  - transient failure then success (`sleeps == [1.0]`, `attempts == [1, 2]`),
  - bounded retry exhaustion (`sleeps == [1.0, 2.0]`, `attempts == [1, 2, 3]`),
  - no-coverage immediate return (`sleeps == []`, `attempts == [1]`).
- Updated root tracker lifecycle state for this package.

**Blockers encountered**:
- None.

**Next steps**:
1. Observe production-like run logs for latency and success-rate impact over the 14-day observation window.

**Test results**:
- `wctl run-pytest tests/nodb/test_climate_artifact_export_service.py --maxfail=1`
  - `12 passed, 3 warnings in 8.19s`.
- `wctl doc-lint --path docs/work-packages/20260429_noaa_atlas14_retry_backoff --path PROJECT_TRACKER.md`
  - `✅ 4 files validated, 0 errors, 0 warnings`.

### 2026-04-30 06:05 UTC: Subagent review disposition session
**Agent/Contributor**: Codex + `reviewer` + `qa_reviewer`

**Findings disposition**:
- **Accepted (Medium)**: Restored NOAA timeout default from `10s` to `30s` to preserve prior successful slow-call behavior while keeping retry/backoff and env override support.
- **Accepted (Medium)**: Expanded deterministic regression coverage for parameterization contract:
  - asserted timeout kwargs passed to `atlas14.download`,
  - added cap-hit schedule assertion (`attempts=4`, `base=4.0`, `cap=5.0` => sleeps `[4.0, 5.0, 5.0]`),
  - added invalid-env fallback assertion (`timeout=30`, `attempts=3`, sleeps `[1.0, 2.0]`).
- **Accepted (Medium/Low process)**: Moved completed ExecPlan from `prompts/active/` to `prompts/completed/` and added outcome note at top.
- **Accepted (Low polish)**: Reduced repeated retry-env test setup by introducing shared helper `_configure_noaa_retry_env`.

**Validation**:
- `wctl run-pytest tests/nodb/test_climate_artifact_export_service.py --maxfail=1`
  - `12 passed, 3 warnings in 8.19s`.

## Communication Log

### 2026-04-29 21:50 UTC: User requested retry/backoff work-package preparation
**Participants**: User, Codex  
**Question/Topic**: Prepare implementation work package for NOAA Atlas 14 retry with exponential backoff using local precedent timings.  
**Outcome**: Package created with scoped implementation plan, parameterization rationale, and tracker ready for execution handoff.
