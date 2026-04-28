# Roads Map Visualization and Drilldown Parity

**Status**: Closed (2026-04-28; implementation completed 2026-04-04)

## Overview
This work package delivers Roads map visibility and road-segment drilldown in WEPPcloud after Roads prepare completes. The implementation must match the existing Channels/Subcatchments interaction model so users get familiar toggle, hover, and click behavior with no new UX paradigm.

## Objectives
- Add a `Roads` overlay layer (magenta road paths) that appears when prepared Roads artifacts exist.
- Add a `Road Labels` overlay layer with label behavior consistent with existing map label overlays.
- Add per-segment hover highlighting and compact hover info.
- Add click-to-drilldown transition for road segments, including WEPP-relevant segment details.
- Add backend and frontend tests covering layer visibility/data wiring, labels, hover, and click drilldown.

## Scope
This package includes map/controller wiring, route/controller payload extensions, Roads report drilldown rendering, and regression tests. It does not introduce new Roads physics or queue workflow changes.

### Included
- Roads layer and Road Labels registration in the deck.gl map controller stack.
- Backend Roads payload contract needed to drive layer rendering and per-segment detail drilldown.
- Drilldown route/template for road-segment detail rendering.
- Targeted Python and Jest coverage for routing, payloads, and interactions.
- Manual validation notes using `clogging-starch` (or equivalent available run).

### Explicitly Out of Scope
- Changes to Roads prepare/run scientific computation beyond exposing existing outputs.
- New map UX patterns that diverge from Channels/Subcatchments conventions.
- Any branch/CI/release workflow changes.

## Stakeholders
- **Primary**: WEPPcloud users analyzing Roads segment outcomes.
- **Reviewers**: WEPPcloud map/controller maintainers and Roads NoDb maintainers.
- **Informed**: QA maintainers for routes + frontend controller test suites.

## Success Criteria
- [x] Roads overlay is available after prepare artifacts exist and renders magenta paths.
- [x] Road Labels overlay is available/toggleable and readable.
- [x] Hover interaction highlights a road segment and exposes compact hover details.
- [x] Clicking a road segment opens DrillDown with required segment fields/metrics.
- [x] Targeted backend/frontend tests for layer visibility, labels, hover, and click drilldown pass.
- [x] Requested validation commands run and outcomes are recorded.
- [x] Mandatory `reviewer` and `qa_reviewer` subagent reviews are executed and dispositioned.

## Closure Summary

Implementation completed on 2026-04-04 and lifecycle documentation was reconciled on 2026-04-28. Roads map resources and per-segment drilldown endpoints are implemented, the frontend Roads/Road Labels overlays are wired into the map controller, hover and click-to-drilldown behavior is covered by tests, and reviewer/QA findings were resolved or explicitly dispositioned in the tracker and completed ExecPlan.

## Dependencies

### Prerequisites
- Existing Roads prepare artifacts from `wepppy/nodb/mods/roads/roads.py`.
- Existing map/deck.gl controller stack in `wepppy/weppcloud/controllers_js/`.

### Blocks
- Follow-on Roads UX refinements depend on this parity baseline.

## Related Packages
- **Related**: `docs/work-packages/20260323_roads_nodb_inslope_e2e/`.
- **Related**: `docs/work-packages/20260326_roads_geojson_attribute_mapping/`.

## Timeline Estimate
- **Expected duration**: 1-2 focused sessions.
- **Complexity**: High.
- **Risk level**: Medium.

## References
- `docs/prompt_templates/codex_exec_plans.md` - ExecPlan requirements.
- `wepppy/weppcloud/controllers_js/subcatchments_gl.js` - map layer/hover/click pattern.
- `wepppy/weppcloud/controllers_js/channel_gl.js` - map layer labels/drilldown pattern.
- `wepppy/weppcloud/routes/nodb_api/roads_bp.py` - Roads API/query route surface.
- `wepppy/nodb/mods/roads/roads.py` - Roads prepare artifacts and summary fields.

## Deliverables
- `docs/work-packages/20260403_roads_map_drilldown/prompts/completed/roads_map_drilldown_execplan.md`
- `docs/work-packages/20260403_roads_map_drilldown/tracker.md`
- Backend + frontend implementation for Roads map layers and drilldown details.
- Test additions and validation evidence.
