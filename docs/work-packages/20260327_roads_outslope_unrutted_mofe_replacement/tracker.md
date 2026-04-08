# Tracker - Roads Outslope Unrutted MOFE Hillslope Replacement

> Living document tracking progress, decisions, risks, and verification for step-4 `outslope_unrutted` replacement work.

## Quick Status

**Started**: 2026-03-27  
**Current phase**: Milestones 1-9 complete (code + docs + review gates)  
**Last updated**: 2026-04-08  
**Active ExecPlan**: `prompts/active/roads_outslope_unrutted_mofe_replacement_execplan.md`  
**Next milestone**: None (package closure and monitoring only)

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked

- [ ] None.

### Done
- [x] Authored package scaffold, tracker, and active ExecPlan (2026-03-27).
- [x] Added package entry to `PROJECT_TRACKER.md` backlog (2026-03-27).
- [x] Locked step-4 contract decisions for physical-length thresholds, fixed 4% geometry parity, raster-burn hillslope segmentation, and multi-road (`N`) support (2026-04-08).
- [x] Adopted minimum diagnostics schema and closed remaining phase-4 decision gates (2026-04-08).
- [x] Implemented outslope-unrutted eligibility normalization, hillslope intersection gating (`60%` + `10 m`), and cap-at-3 selection diagnostics in `roads.py` (2026-04-08).
- [x] Implemented replacement-first pass staging with additive suppression on targeted hillslopes and run-summary diagnostics propagation (2026-04-08).
- [x] Added targeted regression tests for outslope-unrutted alias eligibility, selection/cap logic, and replacement staging path (2026-04-08).
- [x] Fixed routed three-OFE slope serialization bug (buffer point-count mismatch) and validated fixture-backed e2e replacement run with 5 successful outslope-unrutted segments on `clogging-starch-outslope-unrutted-e2e-20260407-232343` (2026-04-08).
- [x] Enforced step-4 defaults/bounds contract in Roads implementation (`rfg_pct_default=20`, strict required fill/buffer parsing and bounds, no silent fallback for invalid required fields) (2026-04-08).
- [x] Implemented deterministic strip ordering by `D_med` ranking (`discha_median_m` descending) for contributor execution and top-OFE compensation targeting (2026-04-08).
- [x] Added explicit `phase4` peak-flow strategy hook in `wepppyo3` pass combiner (2026-04-08).
- [x] Added regression coverage for phase-4 bounds/default behavior and deterministic contributor ordering (2026-04-08).
- [x] Published code review and QA review artifacts (`artifacts/20260327_code_review.md`, `artifacts/20260327_qa_review.md`) with no unresolved medium/high findings (2026-04-08).
- [x] Updated Roads specification and usersum Roads end-user doc to reflect implemented step-4 behavior (2026-04-08).

## Timeline

- **2026-03-27** - Package authored and scoped as Roads step-4 work.
- **2026-04-08** - Locked decomposition/inclusion contracts for physical-length gating, 4% geometry parity, and multi-road hillslope handling.
- **2026-04-08** - Adopted minimum diagnostics schema and closed remaining phase-4 decision gates in Roads step-4 docs.
- **2026-04-08** - Implemented `outslope_unrutted` hillslope intersection gating/cap logic plus replacement-pass staging in `wepppy/nodb/mods/roads/roads.py`.
- **2026-04-08** - Added targeted regression tests for selection/cap behavior and replacement staging summaries.
- **2026-04-08** - Corrected routed three-OFE slope serialization (`3` point-count for buffer OFE) and revalidated on cloned fixture run `clogging-starch-outslope-unrutted-e2e-20260407-232343` with 5 successful replacement segment executions.

## Decisions

### 2026-03-27: Replacement semantics are mandatory
**Context**: User required `outslope_unrutted` as enhanced modeling path, not additive comparison.

**Options considered**:
1. Add road contributors to baseline hillslope pass.
2. Replace targeted hillslope pass responses with roads-aware synthetic passes.

**Decision**: Option 2.

**Impact**: No double counting; direct roads-aware hillslope response.

---

### 2026-03-27: MOFE ordering fixed to `hill -> road -> fill -> hill`
**Context**: User clarified conceptual model and need for final buffer behavior.

**Options considered**:
1. Simplified delta model.
2. Explicit multi-OFE replacement profile with upslope/remainder representation.

**Decision**: Option 2.

**Impact**: Higher fidelity with more implementation complexity and stronger validation needs.

---

### 2026-04-08: Inclusion gating uses physical thresholds
**Context**: User rejected cell-size-based thresholds due to variable raster resolution.

**Options considered**:
1. Mixed ratio + cell-size guardrails.
2. Physical-length overlap rules with fixed minimums.

**Decision**: Option 2 (`L_overlap_h / W_h >= 0.60` and `L_overlap_h >= 10 m`).

**Impact**: Stable eligibility behavior across raster resolutions.

---

### 2026-04-08: Minimum landuse OFE length is physical
**Context**: Cell-size-dependent minimums drift with grid resolution.

**Options considered**:
1. Cell-count-derived minimum.
2. Fixed physical minimum.

**Decision**: Option 2 (`L_landuse_min = 10 m`).

**Impact**: Consistent contributor geometry and clearer acceptance checks.

---

### 2026-04-08: Outslope-unrutted segmentation is raster-burn and hillslope-local
**Context**: User directed this case should not rely on monotonic strip assumptions.

**Options considered**:
1. Reuse monotonic segmentation pathway.
2. Burn roads to raster, evaluate overlap hillslope-by-hillslope, then decompose.

**Decision**: Option 2.

**Impact**: Supports non-monotonic crossings and aligns decomposition with raster context.

---

### 2026-04-08: Multi-road (`N`) crossings per hillslope are required
**Context**: A hillslope can be crossed by multiple roads and fill segments.

**Options considered**:
1. Limit to one road crossing per hillslope.
2. Support `N` crossings via multiple contributors and replacement aggregation.

**Decision**: Option 2.

**Impact**: Enables patterns like repeated `landuse/road/fill` blocks while preserving replacement semantics.

---

### 2026-04-08: Inclusion length metric uses vector overlap (Gate 1)
**Context**: User rejected hybrid overlap measurement as unnecessary complexity.

**Options considered**:
1. Raster-cell approximation.
2. Vector intersection length (chosen).
3. Hybrid raster membership + vector measurement.

**Decision**: Option 2.

**Impact**: Simpler implementation while preserving physical-length semantics.

---

### 2026-04-08: Cross-hillslope segmentation and inclusion are independent per hillslope (Gate 2)
**Context**: User requires preserving hillslope replacement area contracts but allows non-conservative aggregate road area across crossed hillslopes.

**Options considered**:
1. Global multi-hillslope balancing.
2. Independent hillslope-specific segments with independent inclusion gates (chosen).

**Decision**: Option 2, with distinct outslope-unrutted segment IDs per hillslope.

**Impact**: Deterministic segmentation and cleaner per-hillslope replacement bookkeeping.

---

### 2026-04-08: No additional trace requirement for outslope-unrutted replacement (Gate 4)
**Context**: User requires simple replacement-pass semantics without extra phase-4 channel tracing logic.

**Options considered**:
1. Add new trace-to-channel requirement for replacement contributors.
2. Use hillslope-pass replacement and let watershed routing handle delivery (chosen).

**Decision**: Option 2.

**Impact**: Lower implementation complexity and alignment with replacement workflow intent.

---

### 2026-04-08: Parameter defaults/constraints sourced from fswepp2 and geojson (Gate 5)
**Context**: User requested phase-4 parameter contracts align to legacy WEPP:Road implementation and prefer segment `.geojson` values.

**Options considered**:
1. Reuse existing Roads point-source defaults.
2. New phase-4 contract based on fswepp2 defaults/validators plus `.geojson` precedence (chosen).

**Decision**: Option 2.

**Impact**: Better legacy parity and explicit segment-level parameterization.

---

### 2026-04-08: Gate 3 and Gate 6 recommendations accepted
**Context**: User accepted recommended path for aggregation math and design activation.

**Options considered**:
1. Keep phase-1 additive combiner and direct activation.
2. Use phase-4 replacement combiner plus unconditional alias normalization (chosen).

**Decision**: Option 2.

**Impact**: Safer rollout and higher-fidelity replacement behavior.

---

### 2026-04-08: Absolute area closure with top-OFE compensation (Gate 1 finalization)
**Context**: User required absolute area handling and explicit compensation target.

**Options considered**:
1. Relative/combined tolerance.
2. Absolute closure with top-OFE compensation (chosen).

**Decision**: Option 2.

**Impact**: Deterministic per-hillslope closure behavior aligned with user expectation.

---

### 2026-04-08: No feature-flag retirement workflow (Gate 3 simplification)
**Context**: User rejected feature-flag retirement complexity because the path has not shipped.

**Options considered**:
1. Feature-flag lifecycle with retirement criteria.
2. Immediate unconditional alias normalization (chosen).

**Decision**: Option 2.

**Impact**: Simpler rollout and fewer activation states.

---

### 2026-04-08: Performance cap set to 3 crossings per hillslope (Gate 4 finalization)
**Context**: User set explicit cap for outslope-unrutted crossing complexity.

**Options considered**:
1. Dynamic cap/performance heuristics.
2. Fixed cap = 3 (chosen).

**Decision**: Option 2.

**Impact**: Predictable runtime envelope and bounded contributor growth.

---

### 2026-04-08: Minimum diagnostics schema adopted (remaining gate closure)
**Context**: User directed adoption of the minimum schema for phase-4 diagnostics payloads.

**Options considered**:
1. Rich diagnostics schema with expanded contributor payload contracts.
2. Minimum diagnostics schema with required run-summary counts, per-hillslope records, and bounded status codes (chosen).

**Decision**: Option 2.

**Impact**: Closes the final phase-4 decision gate with a stable and implementation-light contract.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Area-conservation violations silently bias outputs | High | Medium | Add strict per-hillslope area checks and fail-fast on violation | Mitigated |
| Replacement staging mistakes cause hidden double counting | High | Medium | Explicit targeted-hillslope replacement inventory and tests | Mitigated |
| Contributor aggregation degrades hydrograph-shape terms | High | Medium | Add contract tests and comparison checks against known synthetic cases | Mitigated |
| Large contributor counts increase runtime substantially | Medium | Medium | Track contributor counts and profile runtime on fixtures | Open (monitoring) |

## Verification Checklist

### Targeted Tests
- [x] `cd /workdir/wepppy && wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1`
- [x] `cd /workdir/wepppy && wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1`
- [x] `cd /workdir/wepppy && wctl run-pytest tests/wepp/reports --maxfail=1`
- [x] `cd /workdir/wepppy && wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1`

### Broader Validation
- [x] `cd /workdir/wepppy && wctl run-npm test`
- [x] `cd /workdir/wepppy && wctl run-npm lint`
- [x] `cd /workdir/wepppy && wctl check-test-stubs`
- [x] `cd /workdir/wepppy && wctl check-test-isolation`
- [x] `cd /workdir/wepppy && wctl run-pytest tests --maxfail=1`
- [ ] `cd /workdir/wepppy && wctl run-stubtest wepppy.nodb.mods.roads.roads` (fails from pre-existing module/global typing debt; unchanged by this package)
- [x] `cd /workdir/wepppy && cargo test --manifest-path /workdir/wepppyo3/wepp_interchange/Cargo.toml hill_pass_combine -- --nocapture`

### Docs and Review Gates
- [x] `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/roads/specification.md`
- [x] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_outslope_unrutted_mofe_replacement/package.md`
- [x] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_outslope_unrutted_mofe_replacement/tracker.md`
- [x] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_outslope_unrutted_mofe_replacement/prompts/active/roads_outslope_unrutted_mofe_replacement_execplan.md`
- [x] `cd /workdir/wepppy && wctl doc-lint --path wepppy/weppcloud/routes/usersum/weppcloud/models/roads/ENDUSER.md`
- [x] Code review artifact complete with no unresolved medium/high findings.
- [x] QA review artifact complete with no unresolved medium/high findings.

## Progress Notes

### 2026-03-27: Package authoring
**Agent/Contributor**: Codex

**Work completed**:
- Created step-4 package docs with explicit replacement semantics and fidelity invariants.
- Captured area-conservation and no-double-counting acceptance requirements.

**Blockers encountered**:
- Awaiting upstream steps 1-3 completion.

**Next steps**:
- Begin Milestone 1 when upstream contributor contracts are stable.

**Test results**:
- Documentation authoring session; implementation tests not run yet.

### 2026-04-08: Contract lock update
**Agent/Contributor**: Codex

**Work completed**:
- Updated Roads specification with settled step-4 contracts for inclusion gating, physical minimum lengths, 4% geometry parity, and `N`-road support.
- Updated active ExecPlan and tracker decision logs with the same contracts.

**Blockers encountered**:
- No runtime blockers; implementation remains pending for Milestone 1 code changes.

**Next steps**:
- Implement hillslope decomposition from burned roads raster and enforce inclusion/length contracts in `roads.py`.

**Test results**:
- Documentation-only update session; executed markdown lint only.

### 2026-04-08: User gate selection confirmation
**Agent/Contributor**: Codex

**Work completed**:
- Captured user-selected Gate-1/2/4/5 decisions and accepted Gate-3/6 recommendations in spec, tracker, and active ExecPlan.
- Updated deferred-details list to only unresolved contracts.

**Blockers encountered**:
- None.

**Next steps**:
- Implement Milestone 1 decomposition using vector overlap metrics and hillslope-specific segmentation IDs.

**Test results**:
- Documentation-only update session; executed markdown lint only.

### 2026-04-08: Minimum diagnostics schema adoption
**Agent/Contributor**: Codex

**Work completed**:
- Added minimum diagnostics schema contract to Roads specification for `outslope_unrutted` replacement summaries.
- Updated deferred-details section to `none` and synchronized active ExecPlan/tracker decision logs.

**Blockers encountered**:
- None.

**Next steps**:
- Begin Milestone 1 implementation in code against the now-locked phase-4 contract set.

**Test results**:
- Documentation-only update session; executed markdown lint only.


### 2026-04-08: Initial code implementation pass
**Agent/Contributor**: Codex

**Work completed**:
- Enabled canonical design alias normalization so `Outslope`/`outunrut` map to `outslope_unrutted` in Roads run eligibility.
- Implemented hillslope-local outslope-unrutted selection via vector overlap length with settled thresholds (`L_overlap/W >= 0.60`, `L_overlap >= 10 m`) and deterministic cap at 3 crossings per hillslope.
- Added replacement-pass staging precedence: targeted hillslopes now stage replacement outputs (single-pass copy/symlink or replacement-only combine) and suppress additive combines for those same hillslopes.
- Propagated minimum diagnostics payload into both success and failure run summaries.
- Added regression tests for alias eligibility, selection/cap behavior, and replacement staging summary fields.

**Blockers encountered**:
- `wepppyo3.wepp_interchange.combine_hillslope_pass_files` currently only exposes `strategy='phase1'`; no phase-4 replacement strategy exists yet.

**Next steps**:
- Implement Milestones 2/3/5: MOFE contributor assembly (`hill -> road -> fill -> hill`), per-hillslope area-closure compensation at top OFE, and replacement aggregation contracts.

**Test results**:
- `wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py tests/nodb/mods/test_roads_controller.py --maxfail=1` (pass).

### 2026-04-08: Work-package completion pass
**Agent/Contributor**: Codex

**Work completed**:
- Closed step-4 discrepancies by enforcing strict phase-4 defaults/bounds contracts and required-field validation for outslope-unrutted replacement.
- Added deterministic `D_med` contributor ordering and corresponding regression coverage.
- Added explicit `phase4` combine hook in `wepppyo3` combiner path.
- Updated Roads specification and usersum Roads end-user documentation to implemented step-4 semantics.
- Authored required review artifacts:
  - `artifacts/20260327_code_review.md`
  - `artifacts/20260327_qa_review.md`

**Blockers encountered**:
- No blockers for required package gates.
- `wctl run-stubtest wepppy.nodb.mods.roads.roads` still fails due pre-existing module/global typing debt unrelated to this package.

**Next steps**:
- Monitor runtime/performance on additional fixture-backed e2e runs; no mandatory package milestones remain open.

**Test results**:
- Targeted and integration suites passed for Roads scope (`test_roads_controller`, `test_roads_monotonic_segments`, `tests/wepp/reports`, `test_roads_bp`).
- Frontend and hygiene gates passed (`run-npm lint`, `run-npm test`, `check-test-stubs`, `check-test-isolation`).
- Full Python suite passed (`wctl run-pytest tests --maxfail=1`: `3104 passed`, `36 skipped`).
- `run-stubtest wepppy.nodb.mods.roads.roads` remains blocked by pre-existing mypy/stub debt in module/global typing contracts.
