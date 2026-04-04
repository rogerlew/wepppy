# Tracker - Roads Map Visualization and Drilldown Parity

> Living document tracking progress, decisions, risks, and verification for Roads map/drilldown parity.

## Quick Status

**Started**: 2026-04-03  
**Current phase**: Handoff Ready  
**Last updated**: 2026-04-04  
**Active ExecPlan**: `prompts/active/roads_map_drilldown_execplan.md`  
**Next milestone**: Final user handoff

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created package scaffold (`package.md`, `tracker.md`, active ExecPlan, `artifacts/.gitkeep`, `notes/.gitkeep`) (2026-04-03).
- [x] Reviewed map/controller seams and existing Channels/Subcatchments interaction patterns to reuse for Roads behavior (2026-04-03).
- [x] Added backend Roads map/drilldown payload helpers and routes (`resources/roads.json`, `query/roads/segment/<segment_id>`, `report/roads/segment_summary/<segment_id>`) (2026-04-04).
- [x] Added frontend Roads map overlay module (`roads_gl.js`) with Roads + Road Labels registration, hover highlight/info, and click-to-drilldown via `map.roadQuery()` (2026-04-04).
- [x] Added/updated backend + frontend tests for Roads map/drilldown interactions and route wiring (2026-04-04).
- [x] Ran required validation commands including full `wctl run-pytest tests --maxfail=1` (2026-04-04).
- [x] Performed manual endpoint validation on `/wc1/runs/cl/clogging-starch` (`resources/roads.json`, segment query, segment report) (2026-04-04).
- [x] Completed `reviewer` and `qa_reviewer` subagent reviews; resolved correctness findings and documented QA follow-ups (2026-04-04).
- [x] Applied post-review fixes: CAP gating parity, deterministic unique fallback segment IDs, and hover refresh cleanup/rebuild guard (2026-04-04).

## Timeline

- **2026-04-03** - Package created; ExecPlan activated.
- **2026-04-03** - Implementation started.
- **2026-04-04** - Backend + frontend implementation completed; validation commands passed; manual endpoint validation recorded.
- **2026-04-04** - Reviewer findings resolved, QA suggestions dispositioned, and full validation rerun completed.

## Decisions

### 2026-04-03: Reuse existing map overlay and drilldown contracts instead of introducing Roads-specific map framework
**Context**: Channels/Subcatchments already implement overlay registration, labels, hover behavior, and click-driven drilldown transitions.

**Options considered**:
1. Build bespoke Roads map controls and drilldown flow.
2. Reuse existing `map_gl` overlay + drilldown plumbing used by Channels/Subcatchments.

**Decision**: Use option 2.

**Impact**: Keeps UX parity, minimizes regression risk, and reduces surface area for future maintenance.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Roads prepared artifacts missing expected segment properties needed for drilldown | High | Medium | Extended payload formatter with defaults and added route/controller tests | Mitigated |
| Map overlay ordering regressions when adding Roads/Road Labels | Medium | Medium | Updated ordering logic and covered `roadQuery` + Roads overlay behavior in Jest | Mitigated |
| Drilldown route payload gaps for WEPP-relevant fields | High | Medium | Added per-segment detail payload contract + template route tests | Mitigated |
| Segment-id collisions for missing `segment_id` values could misroute click/drilldown | Medium | Medium | Added deterministic fallback IDs (`roads-seg-missing-<index>`) and regression coverage for multi-missing-ID features | Mitigated |
| Roads segment drilldown CAP auth parity drift vs WEPP drilldowns | High | Low | Added `@requires_cap` parity on segment summary report route and CAP-block regression test | Mitigated |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/nodb/mods/test_roads_controller.py`
- [x] `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py` (targeted touched suite)
- [x] `wctl run-npm lint`
- [x] `wctl run-npm test`
- [x] `wctl run-pytest tests --maxfail=1`

### Feature Acceptance
- [x] Roads layer appears only after prepare artifacts are available (404/missing-prep path hides overlay; covered in route + overlay behavior).
- [x] Road Labels overlay is toggleable and styled/readable.
- [x] Hover highlights selected road segment and shows compact info.
- [x] Clicking road segment enters DrillDown and renders road-segment details.
- [x] DrillDown details include required WEPP-relevant parameters/metrics when available.

### Review Gates
- [x] `reviewer` subagent correctness/regression review completed.
- [x] `qa_reviewer` subagent test-quality/maintainability review completed.
- [x] Findings addressed or explicitly dispositioned.

## Progress Notes

### 2026-04-03: Package bootstrap and implementation kickoff
**Agent/Contributor**: Codex

**Work completed**:
- Created new work package `docs/work-packages/20260403_roads_map_drilldown/` with required docs and active ExecPlan.
- Confirmed clean worktree and identified existing Roads + map controller integration points.

**Blockers encountered**:
- None.

**Next steps**:
- Implement backend roads map/drilldown routes + controller payload extraction and tests.
- Implement frontend Roads map layer registration and interactions.
- Run required validations and mandatory subagent reviews.

**Test results**: Not run yet (setup stage).

### 2026-04-04: Implementation + validation completed
**Agent/Contributor**: Codex

**Work completed**:
- Implemented Roads map payload + per-segment drilldown backend contracts and routes.
- Added Roads map overlay controller and map wiring parity with Channels/Subcatchments.
- Added tests for backend payload/routes and frontend map interactions.
- Executed required validations and broad sanity sweep.
- Verified live run endpoints for `clogging-starch` (`disturbed9002-wbt-mofe`) return expected Roads map/detail content.

**Blockers encountered**:
- None.

**Next steps**:
- Complete mandatory subagent review gates and disposition findings.

**Test results**:
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py` (pass)
- `wctl run-npm lint` (pass)
- `wctl run-npm test -- map_gl roads_gl` (pass)
- `wctl run-npm test` (pass)
- `wctl run-pytest tests --maxfail=1` (pass)

### 2026-04-04: Mandatory review loop closed + post-review validation rerun
**Agent/Contributor**: Codex

**Work completed**:
- Applied all `reviewer` correctness findings:
  - Added CAP guard parity for roads segment summary report route.
  - Replaced collision-prone `roads-seg-unknown` fallback behavior with deterministic unique fallback IDs by feature index.
  - Hardened map hover refresh by clearing stale hover artifacts on rebuild and short-circuiting redundant same-segment hover rebuilds.
- Expanded tests for the above and additional QA-recommended interaction coverage (completion events + layer-toggle hover cleanup).
- Re-ran all required validation gates after fixes.

**Blockers encountered**:
- None.

**Follow-up dispositions**:
- QA suggestions for deeper branch/error-path coverage and explicit layer-ordering regression assertions were not fully expanded in this pass; existing route + map suites plus full-repo validation remain green, so residual risk is low and follow-up can be tracked separately if desired.

**Test results**:
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py` (31 passed)
- `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py` (18 passed)
- `wctl run-npm test -- roads_gl map_gl` (pass)
- `wctl run-npm lint` (pass)
- `wctl run-npm test` (74 suites passed, 495 tests passed)
- `wctl run-pytest tests --maxfail=1` (3016 passed, 36 skipped)
