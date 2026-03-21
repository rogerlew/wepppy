# Tracker - RUSLE LS Tooling: `RusleLsFactor` in `weppcloud-wbt`

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-03-20  
**Completed**: 2026-03-20  
**Current phase**: Closed  
**Last updated**: 2026-03-21  
**Final ExecPlan**: `prompts/completed/rusle_ls_factor_execplan.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Reviewed current locked `LS` specification and cited literature/precedent targets (2026-03-20).
- [x] Mapped `weppcloud-wbt` implementation locations, registration flow, wrapper patterns, and validation gates (2026-03-20).
- [x] Authored canonical work package with goals, non-goals, implementation milestones, validation plan, risks, and touch points (2026-03-20).
- [x] Updated locked `LS` spec to enforce handbook-based cap default, fixed stop-mask routing semantics, hydrologically sound DEM assumption, and required `LS` metadata contract (2026-03-20).
- [x] Implemented and registered `RusleLsFactor` in `weppcloud-wbt` (2026-03-20).
- [x] Added Python wrapper bindings in both `whitebox_tools.py` files (2026-03-20).
- [x] Added WEPPpy LS integration module + exports under `wepppy/nodb/mods/rusle` (2026-03-20).
- [x] Added WEPPpy LS integration tests under `tests/nodb/mods/` (2026-03-20).
- [x] Ran WBT + WEPPpy validation gates and recorded outcomes (2026-03-20).
- [x] Closed ExecPlan and moved it to `prompts/completed/` (2026-03-20).

## Decisions

### 2026-03-20: Implement as a new terrain-analysis tool, not STI reuse
**Context**: `SedimentTransportIndex` is documented as a unit-stream-power index and only "sometimes" used as LS.

**Decision**: Create a dedicated `RusleLsFactor` tool under `terrain_analysis`.

**Impact**: Scientific contract stays explicit and auditable; routing/mask semantics can be purpose-built for RUSLE LS.

---

### 2026-03-20: Keep `DInf` as default; retain `FD8` and `D8` only as non-default paths
**Context**: Spec locks `DInf` default and limits `FD8`/`D8` to sensitivity/comparison.

**Decision**: Preserve this as a hard runtime default with manifest provenance for any override.

**Impact**: Prevents accidental drift from locked spec while preserving analyst comparability runs.

---

### 2026-03-20: Adopt handbook-based default slope-length cap
**Context**: Prior draft left cap behavior open and risked inconsistent run-to-run interpretation.

**Decision**: Set canonical default `max_slope_length_m = 304.8` (1000 ft basis), with override allowed only for explicit sensitivity analysis and required manifest rationale.

**Impact**: Aligns implementation with handbook guidance and provides auditable, reproducible cap behavior.

---

### 2026-03-20: Assume hydrologically sound DEM and fail fast on artifacts
**Context**: Ambiguity remained on whether LS tool should condition DEM internally.

**Decision**: Require conditioned DEM upstream and fail fast on likely interior no-flow artifacts; do not silently fill/breach inside `RusleLsFactor`.

**Impact**: Prevents hidden preprocessing assumptions and keeps LS provenance explicit.

---

### 2026-03-20: Freeze stop-mask routing semantics
**Context**: Multi-flow behavior at mask boundaries was under-specified.

**Decision**: Treat stop cells as terminal sinks; routed fractions entering stop cells terminate with no renormalization to nonstop neighbors.

**Impact**: Removes a major implementation ambiguity and makes sensitivity results comparable across runs.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Ambiguous stop-mask routing semantics alter LS materially | High | Medium | Semantics frozen in spec; tool + metadata contract implemented | Mitigated |
| Fixed 304.8 m cap underestimates long uninterrupted hillslope paths in some terrain | Medium | Medium | Keep override path for sensitivity runs and require manifested rationale | Residual |
| Performance overhead from diagnostic output set | Medium | Medium | Benchmark fixture and representative AOI workloads in follow-on hardening | Open |

## Progress Notes

### 2026-03-20: Scoping and package authoring
**Agent/Contributor**: Codex

**Work completed**:
- Reviewed `wepppy` RUSLE LS spec and local process docs.
- Reviewed `weppcloud-wbt` tool architecture, registration points, wrappers, and reusable hydrology components.
- Produced package scope and implementation/validation milestones.
- Added this package to `PROJECT_TRACKER.md` backlog.

**Blockers encountered**:
- None.

**Test results**:
- Documentation-only session.

### 2026-03-20: E2E implementation and closure
**Agent/Contributor**: Codex

**Work completed**:
- Implemented `whitebox-tools-app/src/tools/terrain_analysis/rusle_ls_factor.rs`.
- Registered `RusleLsFactor` in WBT terrain-analysis exports and tool manager dispatch.
- Added Python wrappers in `whitebox_tools.py` and `WBT/whitebox_tools.py`.
- Added WEPPpy integration:
  - `wepppy/nodb/mods/rusle/ls_integration.py`
  - `wepppy/nodb/mods/rusle/__init__.py`
- Added WEPPpy tests:
  - `tests/nodb/mods/test_rusle_ls_integration.py`
- Closed and archived ExecPlan to `prompts/completed/rusle_ls_factor_execplan.md`.

**Validation evidence**:
- `cargo check -p whitebox_tools` passed.
- `cargo build -p whitebox_tools` passed.
- `cargo test -p whitebox_tools rusle_ls_factor -- --nocapture` passed (`6 passed`).
- `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py` passed.
- `./target/debug/whitebox_tools --listtools` includes `RusleLsFactor`.
- `wctl run-pytest tests/nodb/mods/test_rusle_ls_integration.py --maxfail=1` passed (`3 passed`).
- `wctl run-pytest tests --maxfail=1` passed (`2385 passed, 34 skipped`).
- `wctl doc-lint` passed on updated docs; `uk2us` diffs were clean.

**Blockers encountered**:
- `cargo fmt --check` remains blocked by preexisting unrelated trailing whitespace in `whitebox-tools-app/src/tools/math_stat_analysis/principal_component_analysis.rs`; no repo-wide formatting churn applied in this package.

**Follow-up**:
1. Add fixture-driven scientific-parity tests for LS surfaces/mask-routing edge cases in `weppcloud-wbt`.
2. Add representative-AOI performance benchmarking for diagnostic output overhead.

### 2026-03-21: Real-run acceptance validation (Claude)
**Agent/Contributor**: Claude

**Work completed**:
- Executed acceptance checks across 5 real `/wc1/runs/*` DEMs (159x166 up to 998x1062).
- Validated all five LS artifacts (`ls`, `l`, `s`, `sca`, `effective_slope_length`) as valid GeoTIFF outputs.
- Confirmed `LS = L * S` identity with max absolute error `< 2e-5` across tested runs.
- Confirmed `effective_slope_length <= 304.8 m` cap behavior across tested runs.
- Confirmed manifest fields for tool/routing/cap/regime/timestamp and raster CRS/grid preservation.

**Integration note**:
- Raw run DEMs can include interior pits (22 to 1567 cells) and are correctly rejected by `RusleLsFactor` with the hydrologic-conditioning error.
- Acceptance workflow used `wbt.breach_depressions()` preprocessing before LS computation, matching the locked `dem_hydrologically_sound_assumed = true` contract.

## Communication Log

### 2026-03-20: Package request
**Participants**: User, Codex  
**Question/Topic**: Review LS spec and author canonical work package for end-to-end implementation in `weppcloud-wbt`.  
**Outcome**: Package created with implementation-ready scope, milestones, validation, and risk framing.

### 2026-03-20: Execute E2E implementation
**Participants**: User, Codex  
**Question/Topic**: Install active ExecPlan in `AGENTS.md` and execute end-to-end implementation.  
**Outcome**: Active ExecPlan created, implementation executed across both repos, validation gates passed, and plan archived to `prompts/completed/rusle_ls_factor_execplan.md`.
