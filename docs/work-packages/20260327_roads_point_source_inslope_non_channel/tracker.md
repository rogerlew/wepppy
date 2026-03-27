# Tracker - Roads Point-Source Inslope Non-Channel Routing

> Living document tracking progress, decisions, risks, and verification for inslope non-channel routing.

## Quick Status

**Started**: 2026-03-27  
**Current phase**: Implementation Complete - Handoff Ready  
**Last updated**: 2026-03-27  
**Active ExecPlan**: `prompts/active/roads_point_source_inslope_non_channel_execplan.md`  
**Next milestone**: Package handoff and downstream follow-up triage.

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
- [x] Milestone 1: Prepare-stage non-channel routable classification implemented (`_roads_routing_eligibility`, `_roads_non_channel_routable`) (2026-03-27).
- [x] Milestone 2: Run-stage trace integration implemented via `wepppyo3.roads_flowpath.trace_downslope_flowpath` (2026-03-27).
- [x] Milestone 3: Routed contributor assembly implemented as `road OFE + buffer OFE` with trace-derived buffer metrics (2026-03-27).
- [x] Milestone 4: Routed contributor pass merge + run summary diagnostics integrated (2026-03-27).
- [x] Milestone 5: Regression tests expanded in Roads monotonic/controller suites (2026-03-27).
- [x] Milestone 6: Code review artifact completed; unresolved medium/high findings = 0 (2026-03-27).
- [x] Milestone 7: QA review artifact completed; unresolved medium/high findings = 0 (2026-03-27).
- [x] Milestone 8: Validation/doc gates executed; out-of-scope full-suite baseline failure documented (2026-03-27).

## Timeline

- **2026-03-27** - Package authored and scoped as step-2 Roads work.
- **2026-03-27** - Implemented step-2 prepare/run routing behavior, routed contributor assembly, and expanded tests/review artifacts.

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
| Step-1 trace API drift invalidates integration assumptions | High | Medium | Run path now imports and calls `wepppyo3` step-1 API directly; regression tests assert trace-result handling | Mitigated |
| Routed-buffer parameterization diverges from WEPP expectations | High | Medium | Added routed contributor builders + controller tests for routed run/skip behavior | Mitigated |
| New routing paths regress channel-associated inslope behavior | High | Medium | Channel-associated path retained and validated through existing and updated tests | Mitigated |
| Large segment counts cause slow per-point tracing | Medium | Medium | Trace context now caches topaz raster load once per run; per-segment tracer calls remain | Open |

## Verification Checklist

### Targeted Tests
- [x] `cd /workdir/wepppy && wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1`
- [x] `cd /workdir/wepppy && wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1`
- [x] `cd /workdir/wepppy && wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1`

### Broader Validation
- [x] `cd /workdir/wepppy && wctl run-npm test -- roads`
- [x] `cd /workdir/wepppy && wctl run-npm lint`
- [ ] `cd /workdir/wepppy && wctl run-pytest tests --maxfail=1` (fails on unrelated baseline issue in `tests/nodb/test_soils_gridded_root_creation.py`)

### Docs and Review Gates
- [x] `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/roads/specification.md`
- [x] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_point_source_inslope_non_channel/package.md`
- [x] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_point_source_inslope_non_channel/tracker.md`
- [x] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_point_source_inslope_non_channel/prompts/active/roads_point_source_inslope_non_channel_execplan.md`
- [x] Code review artifact complete with no unresolved medium/high findings.
- [x] QA review artifact complete with no unresolved medium/high findings.

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

### 2026-03-27: Step-2 implementation + validation
**Agent/Contributor**: Codex

**Work completed**:
- Added prepare-stage routing eligibility metadata for inslope non-channel routable low points.
- Added run-stage trace integration for `_roads_non_channel_routable` segments using step-1 `wepppyo3` API.
- Implemented routed contributor assembly (`road OFE + buffer OFE`) and integrated pass merge/summary diagnostics.
- Expanded Roads regression coverage (`test_roads_monotonic_segments.py`, `test_roads_controller.py`).
- Authored required code-review and QA-review artifacts for this package.

**Blockers encountered**:
- Full-suite baseline has unrelated failing test (`tests/nodb/test_soils_gridded_root_creation.py`), outside Roads step-2 scope.

**Next steps**:
- Optional follow-up package to triage/resolve the unrelated full-suite baseline failure.

**Test results**:
- Targeted Roads pytest suites: pass.
- Roads route pytest suite: pass.
- Roads frontend Jest + lint: pass.
- Full `tests --maxfail=1`: fails on unrelated baseline test noted above.
