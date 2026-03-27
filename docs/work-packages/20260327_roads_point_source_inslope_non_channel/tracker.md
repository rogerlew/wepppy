# Tracker - Roads Point-Source Inslope Non-Channel Routing

> Living document tracking progress, decisions, risks, and verification for inslope non-channel routing.

## Quick Status

**Started**: 2026-03-27  
**Current phase**: Planning Complete - Implementation Ready  
**Last updated**: 2026-03-27  
**Active ExecPlan**: `prompts/active/roads_point_source_inslope_non_channel_execplan.md`  
**Next milestone**: Milestone 1 - lock step-1 trace API assumptions and prepare-stage routing eligibility

## Task Board

### Ready / Backlog
- [ ] Milestone 1: Implement prepare-stage routable non-channel inslope classification.
- [ ] Milestone 2: Integrate step-1 tracer calls in run path for routed segments.
- [ ] Milestone 3: Implement inslope MOFE contributor build (`road -> buffer`) and pass generation.
- [ ] Milestone 4: Merge routed contributors into receiving hillslope pass files and update summaries.
- [ ] Milestone 5: Expand tests and execute fixture-backed validation.
- [ ] Milestone 6: Complete independent code review and resolve medium/high findings.
- [ ] Milestone 7: Complete independent QA review and resolve medium/high findings.
- [ ] Milestone 8: Run final gates and package handoff updates.

### In Progress
- [ ] None.

### Blocked
- [ ] Await step-1 package completion (`20260327_roads_peridot_trace_core`) and stable trace API contract.

### Done
- [x] Authored package scaffold, tracker, and active ExecPlan (2026-03-27).
- [x] Added package entry to `PROJECT_TRACKER.md` backlog (2026-03-27).

## Timeline

- **2026-03-27** - Package authored and scoped as step-2 Roads work.

## Decisions

### 2026-03-27: Inslope non-channel contributors use `road -> buffer`
**Context**: User clarified point-source semantics for inslope with culvert bypass assumptions.

**Options considered**:
1. `road -> fill -> buffer`.
2. `road -> buffer`.

**Decision**: Option 2.

**Impact**: Keeps inslope consistent with culvert bypass of fill slope dynamics.

---

### 2026-03-27: Non-channel low-point routing is conditional on hillslope-cell eligibility
**Context**: User required explicit non-channel gating on `subwta` hillslope suffix (`1|2|3`).

**Options considered**:
1. Attempt routing from any non-channel low point.
2. Route only when low point is on eligible hillslope pixel class.

**Decision**: Option 2.

**Impact**: Reduces false routing and preserves predictable routing scope.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Step-1 trace API drift invalidates integration assumptions | High | Medium | Lock exact API keys/types in Milestone 1 and add adapter contract tests | Open |
| Routed-buffer parameterization diverges from WEPP expectations | High | Medium | Add deterministic buffer OFE construction tests and fixture sanity checks | Open |
| New routing paths regress channel-associated inslope behavior | High | Medium | Preserve existing code path and add parity regression tests | Open |
| Large segment counts cause slow per-point tracing | Medium | Medium | Cache raster handles and trace once per eligible segment with bounded diagnostics | Open |

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
- [ ] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_point_source_inslope_non_channel/package.md`
- [ ] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_point_source_inslope_non_channel/tracker.md`
- [ ] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_point_source_inslope_non_channel/prompts/active/roads_point_source_inslope_non_channel_execplan.md`
- [ ] Code review artifact complete with no unresolved medium/high findings.
- [ ] QA review artifact complete with no unresolved medium/high findings.

## Progress Notes

### 2026-03-27: Package authoring
**Agent/Contributor**: Codex

**Work completed**:
- Created package scope, tracker milestones, and ExecPlan for step-2 inslope non-channel routing.
- Captured explicit user modeling assumptions and review requirements.

**Blockers encountered**:
- Awaiting step-1 implementation completion and interface freeze.

**Next steps**:
- Start Milestone 1 after step-1 API is available.

**Test results**:
- Documentation authoring session; implementation tests not run yet.
