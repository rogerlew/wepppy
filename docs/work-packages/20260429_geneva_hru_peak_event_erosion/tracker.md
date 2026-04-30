# Tracker - Geneva HRU Peak Runoff and Event Erosion Enablement

> Living document tracking progress, decisions, risks, validation, and handoffs for HRU-local Geneva peak runoff and HRU choropleth measure support.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-30 06:04 UTC (package scoped; Pacific package date 2026-04-29)  
**Current phase**: Done  
**Last updated**: 2026-04-30 06:35 UTC  
**Next milestone**: None (package complete)  
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `docs/work-packages/20260429_geneva_hru_peak_event_erosion/artifacts/20260430_security_review.md`
**Validation artifact**: `docs/work-packages/20260429_geneva_hru_peak_event_erosion/artifacts/20260430_validation_summary.md`

## Task Board

### Ready / Backlog

None.

### In Progress

None.

### Blocked

None.

### Done

- [x] Scoped package, tracker, and active ExecPlan prompt (2026-04-30 06:04 UTC).
- [x] Added active execution prompt (2026-04-30 06:12 UTC).
- [x] Registered package in `PROJECT_TRACKER.md` Backlog (2026-04-30 06:04 UTC).
- [x] Started active ExecPlan implementation and recorded kickoff in tracker (2026-04-30 06:21 UTC).
- [x] Added Rust HRU-local peak runoff scalar fields and required one-HRU/multi-HRU tests (2026-04-30 06:26 UTC).
- [x] Updated PyO3 Geneva run-batch JSON test, rebuilt/synced shared objects, and captured SHA-256 values (2026-04-30 06:28 UTC).
- [x] Materialized `hru_peak_runoff` rows (`unit=m3_s`) from kernel `hru_excess[].peak_runoff_m3_s` (2026-04-30 06:31 UTC).
- [x] Added HRU-map validation/query support for `measure_id=hru_peak_runoff` while preserving `peak_discharge` scope rejection (2026-04-30 06:31 UTC).
- [x] Added Geneva Interactive Summary map measure option `HRU peak runoff` and updated JS route wiring/tests (2026-04-30 06:31 UTC).
- [x] Updated specification Sections 12.4/12.5 for implemented HRU peak substrate behavior (2026-04-30 06:33 UTC).
- [x] Completed code review, QA review, and dedicated security review artifacts (2026-04-30 06:34 UTC).
- [x] Ran required validation gates and recorded results in package artifact (2026-04-30 06:34 UTC).

## Timeline

- **2026-04-30 06:04 UTC** - Package created and implementation-ready ExecPlan authored.
- **2026-04-30 06:12 UTC** - Active execution prompt added for direct package execution.
- **2026-04-30 06:21 UTC** - Implementation kickoff: loaded package/tracker/ExecPlan + local AGENTS guidance and began Rust-first execution.
- **2026-04-30 06:26 UTC** - Rust kernel milestone complete: HRU-local peak runoff fields + one-HRU parity and multi-HRU non-area-split tests added and passing.
- **2026-04-30 06:28 UTC** - PyO3 milestone complete: bridge tests updated, release `.so` rebuilt/synced to both runtime paths, and matching SHA-256 hashes recorded.
- **2026-04-30 06:31 UTC** - WEPPpy materialization/query/UI milestone complete with `hru_peak_runoff` measure support and route/UI regression coverage.
- **2026-04-30 06:34 UTC** - Documentation/review/validation artifacts complete; package ready for closure.

## Decisions Log

### 2026-04-30 06:04 UTC: Use `hru_peak_runoff` as the HRU map measure ID

**Context**: Geneva already has watershed summary measure `peak_discharge`, and the current HRU map service intentionally rejects `peak_discharge` because it is watershed-scoped.

**Options considered**:
1. Reuse `peak_discharge` for HRU maps.
2. Add `hru_peak_runoff` as a separate HRU-scoped measure.
3. Add a generic `peak_runoff` measure with scope inferred by caller.

**Decision**: Use `hru_peak_runoff`.

**Impact**: The watershed summary contract remains unchanged, HRU map scope is explicit, and UI labels can distinguish `Peak discharge` from `HRU peak runoff`.

---

### 2026-04-30 06:04 UTC: Derive HRU peak locally with unit-hydrograph convolution

**Context**: The event-erosion design forbids area-splitting watershed peak discharge into HRU values.

**Options considered**:
1. Multiply watershed peak discharge by HRU area fraction.
2. Run the existing Geneva unit-hydrograph convolution for each HRU excess series and HRU area.
3. Create a separate empirical peak-flow formula for HRUs.

**Decision**: Use option 2.

**Impact**: HRU peak estimates remain consistent with Geneva's selected `uh_method`, `tc_hours`, timestep, and HRU excess calculation while preserving local HRU semantics.

---

### 2026-04-30 06:04 UTC: Defer full MUSLE erosion rows

**Context**: The user asked to set up Rust kernel HRU-local peak estimates and add a map measure. Full event erosion also needs RUSLE factor aggregation and source-hash invalidation.

**Options considered**:
1. Implement HRU peak and full MUSLE erosion in one package.
2. Implement HRU peak substrate and map measure now, then make MUSLE a follow-on package.

**Decision**: Use option 2.

**Impact**: This package remains focused and independently verifiable. It unblocks full event erosion without mixing the peak-flow substrate with RUSLE factor aggregation.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| HRU peak is accidentally computed by watershed peak area apportionment | High | Medium | Add multi-HRU fixture where HRU-local convolution differs from area-split peak and assert mismatch | Mitigated |
| Runtime cost grows with HRU count and storm count | Medium | Medium | Reuse existing UH per storm, limit persisted output to peak summaries rather than full HRU hydrograph series, benchmark representative HRU/panel counts | Open |
| Response payload size grows too much | Medium | Low | Add only scalar HRU peak fields to `hru_excess`; do not serialize full HRU hydrographs in v1 | Mitigated |
| Measure-scope confusion between `peak_discharge` and `hru_peak_runoff` | Medium | Medium | Keep `peak_discharge` rejected for HRU map rows; label new measure explicitly in schema/UI/tests | Mitigated |
| Public query route behavior changes unsafely | Medium | Low | Keep route auth/access unchanged, validate measure IDs through existing schema helper, complete security review artifact | Mitigated |
| Cross-repo Rust/Python binary drift | High | Medium | Rebuild/sync `cli_revision_rust` shared objects and record SHA-256 in validation artifact | Mitigated |

## Verification Checklist

### Code Quality

- [x] Rust Geneva core tests pass: `cd /workdir/wepppyo3 && cargo test -p geneva_core`.
- [x] PyO3 Geneva bridge tests pass for touched module/package.
- [x] WEPPpy Geneva tests pass: `wctl run-pytest tests/nodb/mods/geneva --maxfail=1`.
- [x] WEPPcloud route tests pass for Geneva query/report surfaces.
- [x] Frontend tests pass for Geneva summary report measure selection.
- [x] Changed-file broad-exception gate passes.
- [x] `git diff --check` passes in `/workdir/wepppy` and `/workdir/wepppyo3` if both repos are modified.

### Security

- [x] Security impact triage recorded as `high` with rationale.
- [x] Dedicated security review artifact is present and complete.
- [x] No unresolved medium/high security findings remain.
- [x] Public route/auth/access behavior is unchanged except for the new validated measure ID.
- [x] Query-engine payload cannot reference arbitrary datasets or columns outside the canonical HRU event-measure artifact.

### Documentation

- [x] `wepppy/nodb/mods/geneva/specification.md` documents implemented `hru_peak_runoff` behavior.
- [x] Package validation summary artifact records commands and results.
- [x] `PROJECT_TRACKER.md` status is current.
- [x] Active ExecPlan is updated throughout execution and moved to `prompts/completed/` at closure.

### Testing

- [x] One-HRU Rust test proves HRU peak equals watershed peak within tolerance.
- [x] Multi-HRU Rust/Python test proves HRU peak is local and not area-split watershed peak.
- [x] Python materialization test proves `hru_peak_runoff` rows are written with unit `m3_s`.
- [x] Query test proves `hru_peak_runoff` rows are returned and `peak_discharge` remains unsupported for HRU map rows.
- [x] UI test proves the HRU Choropleth Map measure selector includes `HRU peak runoff`.
- [x] Legacy runs missing the new measure return a contract-compliant unavailable/empty response or clear no-data state without unhandled exceptions.

## Progress Notes

### 2026-04-30 06:35 UTC: Package closure

**Agent/Contributor**: Codex

**Work completed**:
- Completed WEPPpy materialization/query/UI changes for `hru_peak_runoff`.
- Updated Geneva specification Sections 12.4 and 12.5 with implemented HRU peak behavior.
- Produced package artifacts:
  - `20260430_validation_summary.md`
  - `20260430_code_review.md`
  - `20260430_qa_review.md`
  - `20260430_security_review.md`
- Executed required validation commands and documented one unrelated pre-existing lint baseline.

**Blockers encountered**:
- None blocking package completion.

**Test results**:
- Required gates passed except known unrelated lint baseline in
  `wepppy/weppcloud/controllers_js/__tests__/landuse_map_inline.test.js`.

### 2026-04-30 06:28 UTC: Rust + PyO3 milestones complete

**Agent/Contributor**: Codex

**Work completed**:
- Extended `/workdir/wepppyo3/geneva_core/src/cn.rs` `hru_excess` rows with:
  - `peak_runoff_m3_s`
  - `time_to_peak_minutes`
- Reused `convolve_excess_to_hydrograph` with per-HRU incremental excess + HRU area to derive local HRU peaks from each storm's selected UH.
- Added required Rust tests:
  - one-HRU parity: HRU peak equals watershed `peak_discharge`
  - multi-HRU anti-area-split: local peaks differ from naive area-apportioned watershed peak.
- Updated `/workdir/wepppyo3/cli_revision/src/geneva/mod.rs` test assertions so `geneva_run_batch` JSON contract includes the new HRU peak fields.
- Rebuilt and synced shared objects:
  - `/workdir/wepppyo3/release/linux/py312/wepppyo3/climate/cli_revision_rust.so`
  - `/workdir/wepppy/cli_revision_rust/cli_revision_rust.abi3.so`
- Captured SHA-256 parity:
  - `644669cc1f04584012c9b772b2e2a0e87dfbafbb9e83745f025c07e01c6ac362` (both paths)

**Blockers encountered**:
- None.

**Next steps**:
- Complete WEPPpy materialization, HRU-map measure validation, route tests, and UI selector updates.
- Update specification sections 12.4/12.5 and package review artifacts.

**Test results**:
- `cd /workdir/wepppyo3 && cargo test -p geneva_core` passed.
- `cd /workdir/wepppyo3 && cargo test -p cli_revision_rust geneva` passed.

### 2026-04-30 06:21 UTC: Active execution kickoff

**Agent/Contributor**: Codex

**Work completed**:
- Read `package.md`, `tracker.md`, and active ExecPlan in full.
- Loaded nearest `AGENTS.md` guidance for touched areas (`wepppy/nodb`, `wepppy/weppcloud`, `wepppy/weppcloud/controllers_js`, `tests`, and `/workdir/wepppyo3` root).
- Inspected current Rust/PyO3/WEPPpy/UI surfaces to confirm concrete edit points for required implementation order.

**Blockers encountered**:
- None.

**Next steps**:
- Implement Rust HRU-local peak runoff fields and add parity/non-area-split tests in `geneva_core`.
- Update PyO3 bridge tests, then rebuild and sync shared objects.

**Test results**:
- Validation gates pending; execution in progress.

### 2026-04-30 06:04 UTC: Package scoping

**Agent/Contributor**: Codex

**Work completed**:
- Reviewed existing Geneva work-package patterns and current repo-wide work-package process.
- Inspected Rust Geneva core and confirmed existing `build_unit_hydrograph` and `convolve_excess_to_hydrograph` can be reused for HRU-local peak derivation.
- Scoped package, tracker, and active ExecPlan prompt.
- Registered package in `PROJECT_TRACKER.md` Backlog.

**Blockers encountered**:
- None.

**Next steps**:
- Start the active ExecPlan when implementation is approved/selected.
- Begin with Rust response contract and tests before touching WEPPpy/UI layers.

**Test results**:
- Documentation validation pending after initial scaffold.

## Watch List

- **Runtime cost**: Per-HRU convolution could be expensive for large HRU counts. The intended v1 output is scalar peak summaries only; full HRU hydrograph serialization is out of scope.
- **Measure semantics**: `hru_peak_runoff` must stay HRU-local. If future routing is added, use a new measure ID rather than changing this one silently.
- **Binary sync**: Any `wepppyo3` Rust bridge change must be rebuilt and copied into WEPPpy's runtime import surface before integration tests.

## Communication Log

### 2026-04-30 06:04 UTC: User request scope

**Participants**: User, Codex  
**Question/Topic**: Prepare work package to set up Rust kernel HRU-local hydrograph peak estimates and add a measure to the HRU Choropleth Map on Geneva Interactive Summary.  
**Outcome**: Package scoped as HRU peak substrate plus `hru_peak_runoff` map measure; full MUSLE event erosion deferred to follow-on.

## Handoff Summary

**From**: Codex  
**To**: Package maintainers  
**Date**: 2026-04-30 06:35 UTC

**Completion status**:
- Package implementation complete.
- Required code/QA/security review artifacts complete.
- Required validation artifacts complete.

**Residual items**:
1. Keep monitoring the known unrelated frontend lint baseline in `landuse_map_inline.test.js`.
2. Implement follow-on `musle_hru_event_v1` erosion rows using the now-available `hru_peak_runoff` substrate.
