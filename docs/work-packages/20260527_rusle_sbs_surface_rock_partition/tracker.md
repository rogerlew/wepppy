# Tracker - RUSLE `scenario_sbs` Surface-Rock Partition Integration

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-05-27 23:09 UTC  
**Current phase**: Closed  
**Last updated**: 2026-05-27 23:49 UTC  
**Next milestone**: N/A  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`  
**Parameterization ADR**: `docs/adrs/ADR-0004-rusle-scenario-sbs-surface-rock-partition.md`

## Task Board

### Ready / Backlog

- [ ] None.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Created package scaffold (`package.md`, `tracker.md`, `prompts/active/`, `artifacts/`) (2026-05-27 23:09 UTC).
- [x] Updated RUSLE specification with RAP-independent SBS rock-partition contract and controls (2026-05-27 23:09 UTC).
- [x] Drafted active ExecPlan for implementation execution (2026-05-27 23:09 UTC).
- [x] Implemented `rock_fraction_of_sbs_bare` controller/runtime plumbing and RAP-independent `scenario_sbs` C partition math (2026-05-27 23:34 UTC).
- [x] Added UI/rq-engine contract wiring and targeted regressions across Python and JS suites (2026-05-27 23:34 UTC).
- [x] Ran targeted validation gates and rebuilt controller bundle (2026-05-27 23:38 UTC).
- [x] Completed independent review and disposition artifacts with no unresolved high/medium findings (2026-05-27 23:42 UTC).
- [x] Closed package docs and archived ExecPlan under `prompts/completed/` (2026-05-27 23:49 UTC).

## Timeline

- **2026-05-27 23:09 UTC** - Package initialized and scoped.
- **2026-05-27 23:09 UTC** - Specification updated with SBS rock-partition formula/default policy.
- **2026-05-27 23:34 UTC** - Runtime/UI/API/test implementation completed.
- **2026-05-27 23:38 UTC** - Targeted validation suites passed.
- **2026-05-27 23:42 UTC** - Independent review and findings disposition completed.
- **2026-05-27 23:49 UTC** - Package documentation closed; ExecPlan archived.

## Decisions Log

### 2026-05-27 23:09 UTC: Keep SBS rock handling RAP-independent
**Context**: Earlier discussion considered carrying rock behavior through RAP, but SBS mode should be usable without RAP dependencies.

**Options considered**:
1. Reuse RAP-only rock control in SBS mode.
2. Add an SBS-native rock control independent of RAP.
3. Keep SBS unchanged and rely on K/profile-rock only.

**Decision**: Option 2.

**Impact**: SBS runs can represent protective surface rock without requiring RAP retrieval/year selection.

### 2026-05-27 23:09 UTC: Use `cosurffrags`-first `auto` default with `cfvo` fallback
**Context**: SBS control needs a sensible default prior when field measurements are unavailable.

**Options considered**:
1. `cfvo` only.
2. `cosurffrags` first, then `cfvo`, then `0.0`.
3. No `auto`, require explicit entry.

**Decision**: Option 2.

**Impact**: Keeps defaults operational while preserving surface-proxy precedence and explicit uncertainty.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Users treat `auto` as canonical truth | High | Medium | Explicit UI guidance and manifest provenance | Mitigated |
| Cross-layer payload drift (`UI -> API -> runtime`) | Medium | Medium | Added focused route/controller JS tests | Mitigated |
| Lookup schema ambiguity (`ground_cover` vs `fg_lookup_pct`) | Medium | Medium | Runtime now uses explicit lookup `ground_cover` semantics with fallback inversion for `c_override` | Mitigated |

## Verification Checklist

### Code Quality
- [x] Targeted Python/JS tests pass for changed modules.
- [x] No regressions in existing `observed_rap` behavior.

### Security
- [x] Security impact triage recorded (`low`) with rationale.
- [x] No dedicated security artifact required by triage.

### Documentation
- [x] Spec updated for SBS contract.
- [x] Package and active ExecPlan created.
- [x] Parameterization ADR linked.

### Testing
- [x] Unit coverage for SBS rock-partition math and validation paths.
- [x] API payload tests for new SBS option.
- [x] JS controller tests for mode-specific payload behavior.

## Progress Notes

### 2026-05-27 23:09 UTC: Package and Spec Scoping
**Agent/Contributor**: Codex

**Work completed**:
- Updated `wepppy/nodb/mods/rusle/specification.md` with RAP-independent SBS rock-partition contract.
- Created this package scaffold and active ExecPlan.
- Registered package in `PROJECT_TRACKER.md`.

**Blockers encountered**:
- None.

**Next steps**:
- Execute active ExecPlan implementation milestones.
- Add targeted regressions and collect validation evidence.

**Test results**: Not run yet (specification/work-package scaffolding stage).

### 2026-05-27 23:42 UTC: Implementation + Validation + Review
**Agent/Contributor**: Codex

**Work completed**:
- Implemented SBS rock-partition runtime in `c_integration.py` with user/auto controls and provenance.
- Added `rock_fraction_of_sbs_bare` parsing/plumbing in `rusle.py`, UI/template wiring, and rq-engine payload/schema updates.
- Added targeted regression coverage in NoDb, rq-engine, and JS suites.
- Completed independent review artifact and findings disposition artifact.

**Blockers encountered**:
- None.

**Next steps**:
- None; package closed.

**Test results**:
- `wctl run-pytest tests/nodb/mods/test_rusle_c_formula.py tests/nodb/mods/test_rusle_c_integration.py tests/nodb/mods/test_rusle_controller.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_rusle_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
- `wctl run-npm test -- controllers_js/__tests__/rusle.test.js`
- `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`
