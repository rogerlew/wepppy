# Tracker - WEPP Gregorian Leap-Year Contract and Centurial Tolerance

> Living document tracking progress, decisions, risks, and validation for leap-year contract correction with legacy centurial 366-day tolerance.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-30 07:19 UTC  
**Current phase**: Completed (implementation + validation + vendoring)  
**Last updated**: 2026-04-30 08:53 UTC  
**Next milestone**: Optional release communication / PR packaging  
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
- [x] Work package scaffold created (`package.md`, `tracker.md`, active ExecPlan) (2026-04-30 07:19 UTC).
- [x] Added package entry to `PROJECT_TRACKER.md` backlog (2026-04-30 07:19 UTC).
- [x] Implemented Gregorian leap classification pattern in `/workdir/wepp-forest/src/stmget.for`, `/workdir/wepp-forest/src/wshpas.for`, `/workdir/wepp-forest/src/contin.for`, and `/workdir/wepp-forest/src/wshdrv.for` with non-400 centurial day-366 tolerance retained in day-count/loop branches (2026-04-30 08:05 UTC).
- [x] Rebuilt binaries and passed required `wepp-forest` gates: host smoke (`wepp`, `wepp_hill`), hillslope watchlist (`12/12`), ablation artifact policy, and `pytest -q` (`79 passed, 2 warnings`) (2026-04-30 08:17 UTC).
- [x] Captured centurial control replay evidence from `/tmp/wepp_leap_cases`: `year100/365` warning removed after patch, `year100/366` tolerated success, `year2000/366` leap success (2026-04-30 08:21 UTC).
- [x] Released and vendored `wepp_260430` + `wepp_260430_hill`, synced vendored changelog copy, and passed `wepppy` provenance/smoke/focused tests (`8 passed`) (2026-04-30 08:41 UTC).
- [x] Re-ran `wepp-forest` required validation suite on patched tree before handoff; pass status remained stable (`smoke` x2, `watchlist 12/12`, ablation policy, `pytest -q` `79 passed, 2 warnings`) (2026-04-30 08:53 UTC).

## Timeline

- **2026-04-30 07:19 UTC** - Package created and seeded with contract goals, risks, and validation plan.
- **2026-04-30 08:05 UTC** - Leap logic patch landed in four active source call sites in `/workdir/wepp-forest/src`.
- **2026-04-30 08:17 UTC** - `wepp-forest` validation gates completed successfully (smoke, watchlist, ablation policy, full pytest).
- **2026-04-30 08:21 UTC** - Centurial replay controls captured from `/tmp/wepp_leap_cases` before/after artifacts.
- **2026-04-30 08:41 UTC** - Vendored binaries/changelog into `wepppy` and completed post-vendor provenance/smoke/focused regression gates.
- **2026-04-30 08:53 UTC** - Re-ran full `wepp-forest` gate suite on patched tree and reconfirmed pass outcomes.

## Decisions Log

### 2026-04-30 07:19 UTC: Canonical rule is Gregorian, compatibility remains tolerant
**Context**: Existing WEPP behavior classifies leap years using `mod(year,4)` and mislabels centurial years like `100`.

**Options considered**:
1. Keep `mod(year,4)` behavior everywhere.
2. Switch to Gregorian behavior strictly and reject 366-day non-400 centurial input.
3. Switch to Gregorian behavior for classification while tolerating legacy 366-day non-400 centurial input.

**Decision**: Option 3.

**Impact**: Fixes false leap classification while preserving backward compatibility for legacy climate inputs.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Day-index off-by-one regressions in annual loops | High | Medium | Touched only leap classifiers/day-count branches; replayed centurial controls and baseline fixture | Mitigated |
| Inconsistent leap logic across files (`stmget`, `contin`, `wshdrv`, `wshpas`) | Medium | Medium | Implemented one canonical Gregorian branch pattern at all known active call sites | Closed |
| Backward compatibility break for legacy 366-day centurial climates | High | Medium | Explicit tolerance path and replay proof (`year100/366` success) | Mitigated |
| Output drift on non-centurial fixtures | Medium | Low | Passed host smoke, watchlist (`12/12`), and full `pytest -q` before vendoring | Mitigated |

## Hardening Signal Log (Required for incident/remediation packages)

- **Baseline health signals**: Year `100` emits leap warning with 28-day February in current baseline logs.
- **Post-change health signals**: Year `100` with 28-day February no longer emits false leap warning; year `100` with day 366 remains runnable; year `2000` leap behavior preserved.
- **Danger signals observed**: None during build, replay, or post-vendor validation.
- **Temporary callus register**:
  - None planned.
- **Softening experiments**:
  - Hypothesis: N/A.
  - Gate results: N/A.
  - Decision: N/A.

## Verification Checklist

### Code Quality
- [x] `tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp`
- [x] `tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp_hill`
- [x] `python /workdir/wepp-forest/tools/run_hillslope_watchlist.py --binary /workdir/wepp-forest/src/wepp_hill`
- [x] `python /workdir/wepp-forest/tools/check_ablation_artifact_policy.py`
- [x] `pytest -q` in `/workdir/wepp-forest`

### Documentation
- [x] `wepp-forest/change-log.md` updated with leap contract patch entry.
- [x] Vendored changelog copy in `wepppy/weppcloud/routes/usersum/vendor/wepp-forest/change-log.md` synced.
- [x] `PROJECT_TRACKER.md` updated with package lifecycle changes.

### Testing
- [x] Centurial-year replay without false warning (`year 100`, Feb=28).
- [x] Centurial-year replay with day 366 tolerance (`year 100`, explicit day 366 present).
- [x] Gregorian leap control replay (`year 2000`, leap semantics preserved).

### Vendoring
- [x] `tools/check_wepp_binary_provenance.sh wepp_runner/bin/wepp_260430 wepp_runner/bin/wepp_260430_hill`
- [x] `tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_260430`
- [x] `tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_260430_hill`
- [x] `pytest -q tests/wepp_runner/test_run_hillslope_retries.py tests/wepp/test_wepp_runner_outputs.py`

## Progress Notes

### 2026-04-30 07:19 UTC: Package bootstrap
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold under `docs/work-packages/20260430_wepp_gregorian_leap_tolerance/`.
- Captured requested behavioral contract: Gregorian leap logic with tolerance for non-400 centurial day-366 climates.
- Authored active ExecPlan for implementation handoff.

**Blockers encountered**:
- None.

**Next steps**:
1. Confirm contract text with user (warning/no-warning expectations for tolerant day-366 case).
2. Implement source edits in `wepp-forest` and add regression coverage.
3. Run validation gates and vendor updated binaries into `wepppy`.

**Test results**: N/A (documentation/scoping only).

### 2026-04-30 08:05 UTC: Source patch complete in `wepp-forest`
**Agent/Contributor**: Codex

**Work completed**:
- Replaced ad hoc leap checks with Gregorian classification branches in:
  - `/workdir/wepp-forest/src/stmget.for`
  - `/workdir/wepp-forest/src/wshpas.for`
  - `/workdir/wepp-forest/src/contin.for`
  - `/workdir/wepp-forest/src/wshdrv.for`
- Added explicit non-400 centurial tolerance booleans in day-count/loop-selection paths.

**Blockers encountered**:
- None.

**Next steps**:
1. Rebuild binaries.
2. Run required `wepp-forest` gates.
3. Capture centurial controls and vendor release binaries.

**Test results**: Build successful (`make wepp`, `make wepp_hill`).

### 2026-04-30 08:21 UTC: Centurial controls and source-gate validation
**Agent/Contributor**: Codex

**Work completed**:
- Passed source gates in `/workdir/wepp-forest`:
  - smoke (`wepp`, `wepp_hill`)
  - hillslope watchlist (`12/12`)
  - ablation artifact policy
  - `pytest -q` (`79 passed, 2 warnings`)
- Captured centurial control evidence from `/tmp/wepp_leap_cases`:
  - `case100_365/stdout.txt` (before) contains leap warning.
  - `case100_365/stdout_after.txt` (after) warning removed.
  - `case100_366/stdout_after.txt` and `case2000_366/stdout_after.txt` complete successfully.

**Blockers encountered**:
- None.

**Next steps**:
1. Update changelog and release artifacts.
2. Vendor into `wepppy`.
3. Run post-vendor provenance/smoke/focused tests.

**Test results**: All source gates passed.

### 2026-04-30 08:41 UTC: Vendoring and post-vendor validation complete
**Agent/Contributor**: Codex

**Work completed**:
- Installed vendored binaries:
  - `/workdir/wepppy/wepp_runner/bin/wepp_260430`
  - `/workdir/wepppy/wepp_runner/bin/wepp_260430_hill`
- Synced changelog copy:
  - `/workdir/wepppy/wepppy/weppcloud/routes/usersum/vendor/wepp-forest/change-log.md`
- Passed post-vendor checks:
  - `tools/check_wepp_binary_provenance.sh ...` (hash/interpreter/loader metadata)
  - smoke for both vendored binaries
  - `pytest -q tests/wepp_runner/test_run_hillslope_retries.py tests/wepp/test_wepp_runner_outputs.py` (`8 passed`)

**Blockers encountered**:
- None.

**Next steps**:
1. Prepare commit/PR if requested.
2. Coordinate any deployment/promotion workflow for `wepp_260430`.

**Test results**:
- Provenance: pass.
- Smoke: pass.
- Focused tests: `8 passed in 0.45s`.
