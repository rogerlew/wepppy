# Tracker - Roads Point-Source Outslope Rutted with Fill OFE

> Living document tracking progress, decisions, risks, and verification for step-3 `outslope_rutted` implementation.

## Quick Status

**Started**: 2026-03-27  
**Current phase**: Active - Milestone 1 in progress  
**Last updated**: 2026-03-27  
**Active ExecPlan**: `prompts/active/roads_point_source_outslope_rutted_execplan.md`  
**Next milestone**: Milestone 1 - finalize fill-parameter contract and design eligibility integration

## Task Board

### Ready / Backlog
- [ ] Milestone 2: Implement run-stage `road -> fill -> buffer` contributor assembly.
- [ ] Milestone 3: Handle channel-associated vs non-channel routing branches with diagnostics.
- [ ] Milestone 4: Update summaries/reports and add regression tests.
- [ ] Milestone 5: Execute fixture-backed validation.
- [ ] Milestone 6: Complete independent code review and resolve medium/high findings.
- [ ] Milestone 7: Complete independent QA review and resolve medium/high findings.
- [ ] Milestone 8: Run final gates and handoff updates.

### In Progress
- [ ] Milestone 1: Add `outslope_rutted` design eligibility and fill-parameter contract.

### Blocked
- [ ] None.

### Done
- [x] Authored package scaffold, tracker, and active ExecPlan (2026-03-27).
- [x] Added package entry to `PROJECT_TRACKER.md` backlog (2026-03-27).

## Timeline

- **2026-03-27** - Package authored and scoped as Roads step-3 work.
- **2026-03-27** - Package activated after step-1 and step-2 completion handoff.

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
**Context**: User noted DEM (`10m`/`30m`) cannot resolve fill geometry adequately.

**Options considered**:
1. Infer fill length/slope from DEM only.
2. Use roads-vector attributes plus explicit defaults.

**Decision**: Option 2.

**Impact**: Stable parameterization and explicit assumptions in run summaries.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Fill defaults produce unrealistic sensitivity in some landscapes | High | Medium | Log default usage counts and add fixture sanity checks | Open |
| Channel-associated branch over/underestimates buffer effects | High | Medium | Use explicit branch diagnostics and regression tests for each branch | Open |
| New design eligibility regresses inslope-only phase-1 flows | Medium | Medium | Keep per-design gating tests and parity checks | Open |
| Added OFEs introduce malformed slope/soil/man files | High | Medium | Add file-structure tests and run WEPP fixture execution in CI path | Open |

## Verification Checklist

### Targeted Tests
- [ ] `cd /workdir/wepppy && wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1`
- [ ] `cd /workdir/wepppy && wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1`
- [ ] `cd /workdir/wepppy && wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1`

### Broader Validation
- [ ] `cd /workdir/wepppy && wctl run-npm test -- roads`
- [ ] `cd /workdir/wepppy && wctl run-npm lint`
- [ ] `cd /workdir/wepppy && wctl run-pytest tests --maxfail=1`

### Docs and Review Gates
- [ ] `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/roads/specification.md`
- [ ] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_point_source_outslope_rutted/package.md`
- [ ] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_point_source_outslope_rutted/tracker.md`
- [ ] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_point_source_outslope_rutted/prompts/active/roads_point_source_outslope_rutted_execplan.md`
- [ ] Code review artifact complete with no unresolved medium/high findings.
- [ ] QA review artifact complete with no unresolved medium/high findings.

## Progress Notes

### 2026-03-27: Package authoring
**Agent/Contributor**: Codex

**Work completed**:
- Created step-3 package docs with fill-contract expectations and branch diagnostics.
- Captured required defaults and review-gate requirements.

**Blockers encountered**:
- Awaiting step-1/step-2 completion.

**Next steps**:
- Begin Milestone 1 after upstream interfaces stabilize.
- Begin Milestone 1 implementation using step-2 trace integration as fixed contract.

**Test results**:
- Documentation authoring session; implementation tests not run yet.

### 2026-03-27: Package activation for implementation
**Agent/Contributor**: Codex

**Work completed**:
- Confirmed step-1 (peridot/wepppyo3 trace core) and step-2 (inslope non-channel routing) handoffs are complete.
- Promoted this package to active work-package in root `AGENTS.md`.
- Moved Milestone 1 to In Progress.

**Blockers encountered**:
- None at activation time.

**Next steps**:
- Execute Milestone 1 end-to-end, then continue through Milestone 8 without widening scope beyond `outslope_rutted`.

**Test results**:
- Activation/documentation update only; no implementation tests run in this activation pass.
