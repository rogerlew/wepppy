# Tracker - Roads Outslope Unrutted MOFE Hillslope Replacement

> Living document tracking progress, decisions, risks, and verification for step-4 `outslope_unrutted` replacement work.

## Quick Status

**Started**: 2026-03-27  
**Current phase**: Planning Complete - Implementation Ready  
**Last updated**: 2026-03-27  
**Active ExecPlan**: `prompts/active/roads_outslope_unrutted_mofe_replacement_execplan.md`  
**Next milestone**: Milestone 1 - lock replacement decomposition and area-conservation contracts

## Task Board

### Ready / Backlog
- [ ] Milestone 1: Implement targeted hillslope decomposition contract (`affected strip` + `unaffected remainder`).
- [ ] Milestone 2: Build MOFE contributors with ordering `hill -> road -> fill -> hill`.
- [ ] Milestone 3: Aggregate contributors to one replacement pass per targeted hillslope.
- [ ] Milestone 4: Stage replacement pass files with strict no-double-counting behavior.
- [ ] Milestone 5: Add area-conservation and topology-preservation validations.
- [ ] Milestone 6: Add regression tests and fixture-backed validation.
- [ ] Milestone 7: Complete independent code review and resolve medium/high findings.
- [ ] Milestone 8: Complete independent QA review and resolve medium/high findings.
- [ ] Milestone 9: Run final gates and handoff updates.

### In Progress
- [ ] None.

### Blocked
- [ ] Await step-1/2/3 completion and stable contributor contracts.

### Done
- [x] Authored package scaffold, tracker, and active ExecPlan (2026-03-27).
- [x] Added package entry to `PROJECT_TRACKER.md` backlog (2026-03-27).

## Timeline

- **2026-03-27** - Package authored and scoped as Roads step-4 work.

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

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Area-conservation violations silently bias outputs | High | Medium | Add strict per-hillslope area checks and fail-fast on violation | Open |
| Replacement staging mistakes cause hidden double counting | High | Medium | Explicit targeted-hillslope replacement inventory and tests | Open |
| Contributor aggregation degrades hydrograph-shape terms | High | Medium | Add contract tests and comparison checks against known synthetic cases | Open |
| Large contributor counts increase runtime substantially | Medium | Medium | Track contributor counts and profile runtime on fixtures | Open |

## Verification Checklist

### Targeted Tests
- [ ] `cd /workdir/wepppy && wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1`
- [ ] `cd /workdir/wepppy && wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1`
- [ ] `cd /workdir/wepppy && wctl run-pytest tests/wepp/reports --maxfail=1`

### Broader Validation
- [ ] `cd /workdir/wepppy && wctl run-npm test -- roads`
- [ ] `cd /workdir/wepppy && wctl run-npm lint`
- [ ] `cd /workdir/wepppy && wctl run-pytest tests --maxfail=1`

### Docs and Review Gates
- [ ] `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/roads/specification.md`
- [ ] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_outslope_unrutted_mofe_replacement/package.md`
- [ ] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_outslope_unrutted_mofe_replacement/tracker.md`
- [ ] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_outslope_unrutted_mofe_replacement/prompts/active/roads_outslope_unrutted_mofe_replacement_execplan.md`
- [ ] Code review artifact complete with no unresolved medium/high findings.
- [ ] QA review artifact complete with no unresolved medium/high findings.

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
