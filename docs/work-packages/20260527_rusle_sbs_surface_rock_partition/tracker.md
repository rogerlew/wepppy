# Tracker - RUSLE `scenario_sbs` Surface-Rock Partition Integration

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-05-27 23:09 UTC  
**Current phase**: Scoped / implementation pending  
**Last updated**: 2026-05-27 23:09 UTC  
**Next milestone**: Implement SBS control through UI -> API -> runtime and add regressions  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`  
**Parameterization ADR**: `docs/adrs/ADR-0004-rusle-scenario-sbs-surface-rock-partition.md`

## Task Board

### Ready / Backlog

- [ ] Implement `rock_fraction_of_sbs_bare` option parsing/storage in `Rusle` controller.
- [ ] Implement SBS `C` partition math in `c_integration.py` using lookup-derived `bare_lookup`.
- [ ] Add UI control and guidance copy in `rusle_pure.htm` and `controllers_js/rusle.js`.
- [ ] Extend rq-engine payload allowlist/schema-default contracts for SBS rock control.
- [ ] Add and run focused Python/JS regression tests.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Created package scaffold (`package.md`, `tracker.md`, `prompts/active/`, `artifacts/`) (2026-05-27 23:09 UTC).
- [x] Updated RUSLE specification with RAP-independent SBS rock-partition contract and controls (2026-05-27 23:09 UTC).
- [x] Drafted active ExecPlan for implementation execution (2026-05-27 23:09 UTC).

## Timeline

- **2026-05-27 23:09 UTC** - Package initialized and scoped.
- **2026-05-27 23:09 UTC** - Specification updated with SBS rock-partition formula/default policy.

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
| Users treat `auto` as canonical truth | High | Medium | Explicit UI guidance and manifest provenance | Open |
| Cross-layer payload drift (`UI -> API -> runtime`) | Medium | Medium | Add focused route/controller JS tests | Open |
| Lookup schema ambiguity (`ground_cover` vs `fg_lookup_pct`) | Medium | Medium | Pin canonical field handling in runtime + tests | Open |

## Verification Checklist

### Code Quality
- [ ] Targeted Python/JS tests pass for changed modules.
- [ ] No regressions in existing `observed_rap` behavior.

### Security
- [x] Security impact triage recorded (`low`) with rationale.
- [x] No dedicated security artifact required by triage.

### Documentation
- [x] Spec updated for SBS contract.
- [x] Package and active ExecPlan created.
- [x] Parameterization ADR linked.

### Testing
- [ ] Unit coverage for SBS rock-partition math and validation paths.
- [ ] API payload tests for new SBS option.
- [ ] JS controller tests for mode-specific payload behavior.

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
