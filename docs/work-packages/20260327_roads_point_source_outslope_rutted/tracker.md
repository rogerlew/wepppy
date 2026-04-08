# Tracker - Roads Point-Source Outslope Rutted with Fill OFE

> Living document tracking progress, decisions, risks, and verification for step-3 `outslope_rutted` implementation.

## Quick Status

**Started**: 2026-03-27  
**Current phase**: Completed  
**Last updated**: 2026-04-07  
**Active ExecPlan**: `prompts/active/roads_point_source_outslope_rutted_execplan.md`  
**Next milestone**: Handoff complete; follow-on package is step-4 `outslope_unrutted`

## Task Board

### Ready / Backlog
- [ ] Step-4 follow-on package: `outslope_unrutted` MOFE hillslope replacement.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Authored package scaffold, tracker, and active ExecPlan (2026-03-27).
- [x] Added package entry to `PROJECT_TRACKER.md` backlog (2026-03-27).
- [x] Milestone 1: Added `outslope_rutted` design eligibility plus fill default contracts (`fill_length_default_m`, `fill_slope_default_pct`).
- [x] Milestone 2: Implemented run-stage `road -> fill -> buffer` contributor assembly for `outslope_rutted`.
- [x] Milestone 3: Implemented explicit channel-associated and non-channel routing branches with branch counters and trace diagnostics.
- [x] Milestone 4: Added regression coverage for fill parsing/defaults, three-OFE soil/slope generation, and branch behavior.
- [x] Milestone 5: Completed code-review artifact with no unresolved medium/high findings.
- [x] Milestone 6: Completed QA-review artifact with no unresolved medium/high findings.
- [x] Milestone 7: Completed final validation gates and synchronized package docs/spec.

## Timeline

- **2026-03-27** - Package authored and scoped as Roads step-3 work.
- **2026-03-27** - Package activated after step-1 and step-2 completion handoff.
- **2026-04-07** - Step-3 implementation completed end-to-end with green targeted/full gates and documentation sync.

## Decisions

### 2026-03-27: `outslope_rutted` uses explicit fill OFE
**Context**: User clarified that outslope-rutted point sources must include fill dynamics, unlike inslope culvert bypass assumptions.

**Options considered**:
1. Model `outslope_rutted` as `road -> buffer`.
2. Model `outslope_rutted` as `road -> fill -> buffer`.

**Decision**: Option 2.

**Impact**: Better representation of potential fill-slope erosion.

---

### 2026-03-27: Fill geometry comes from vector attributes with defaults
**Context**: DEM (`10m`/`30m`) cannot resolve fill geometry adequately.

**Options considered**:
1. Infer fill length/slope from DEM only.
2. Use roads-vector attributes plus explicit defaults.

**Decision**: Option 2.

**Impact**: Stable parameterization and explicit assumptions in run summaries.

---

### 2026-04-07: Channel-associated `outslope_rutted` buffer uses feature/default derivation
**Context**: Channel-associated segments do not always have trace-derived path geometry.

**Options considered**:
1. Require trace for all `outslope_rutted` branches.
2. Derive buffer from segment properties/profile defaults for channel-associated branch; keep trace-derived buffers for non-channel routed branch.

**Decision**: Option 2.

**Impact**: Deterministic channel-associated execution without weakening non-channel trace contract.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Fill defaults may be overused on sparse attribute uploads | Medium | Medium | Persist `fill_default_usage_counts` in run summary and logs for operator visibility | Mitigated (telemetry in place) |
| Channel-associated buffer derivation may need calibration tuning | Medium | Medium | Defaults are explicit, clamped, and test-covered; future calibration can adjust values/aliases without contract breaks | Open (follow-up calibration) |
| Added OFEs could break WEPP input files | High | Low | Added direct file-structure tests for routed three-OFE soil/slope generation | Mitigated |

## Verification Checklist

### Targeted Tests
- [x] `cd /workdir/wepppy && wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1`
- [x] `cd /workdir/wepppy && wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1`
- [x] `cd /workdir/wepppy && wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1`

### Broader Validation
- [x] `cd /workdir/wepppy && wctl run-npm test -- roads`
- [x] `cd /workdir/wepppy && wctl run-npm lint`
- [x] `cd /workdir/wepppy && wctl run-pytest tests --maxfail=1`

### Docs and Review Gates
- [x] `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/roads/specification.md`
- [x] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_point_source_outslope_rutted/package.md`
- [x] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_point_source_outslope_rutted/tracker.md`
- [x] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_point_source_outslope_rutted/prompts/active/roads_point_source_outslope_rutted_execplan.md`
- [x] Code review artifact complete with no unresolved medium/high findings.
- [x] QA review artifact complete with no unresolved medium/high findings.

## Progress Notes

### 2026-04-07: End-to-end implementation and validation complete
**Agent/Contributor**: Codex

**Work completed**:
- Enabled `outslope_rutted` design eligibility in prepare/run contracts (`roads.py`, `monotonic_segments.py`).
- Added fill parameter defaults, parsing, validation/clamping, and run-summary telemetry.
- Implemented routed three-OFE (`road -> fill -> buffer`) soil/slope assembly and management template materialization.
- Added branch-aware behavior for channel-associated and non-channel routed `outslope_rutted` segments.
- Added/updated regression tests across NoDb controller and monotonic-segment suites.
- Updated Roads report segment summary template and Roads specification contract text.
- Authored required code review and QA review artifacts.

**Blockers encountered**:
- None.

**Test results**:
- `tests/nodb/mods/test_roads_controller.py`: 37 passed.
- `tests/nodb/mods/test_roads_monotonic_segments.py`: 14 passed.
- `tests/weppcloud/routes/test_roads_bp.py`: 18 passed.
- `wctl run-npm test -- roads`: 19 passed.
- `wctl run-pytest tests --maxfail=1`: 3097 passed, 36 skipped.
