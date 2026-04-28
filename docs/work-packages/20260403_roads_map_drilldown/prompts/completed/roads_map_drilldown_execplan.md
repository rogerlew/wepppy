# Roads Map Visualization and Drilldown Parity

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, a user who has completed `Prepare Segment Candidates` in Roads can turn on `Roads` and `Road Labels` overlays on the map, hover each segment for quick context, and click a segment to open DrillDown details using the same interaction style as Channels/Subcatchments. This closes a current UX gap where Roads prepare data exists but is not explorable from the map.

The behavior is observable on the run page for `clogging-starch` (or equivalent available run): once Roads prepare succeeds, Roads layers become available in the map layer list; hovering highlights segment geometry; clicking opens DrillDown segment details with WEPP-relevant fields.

## Progress

- [x] (2026-04-04 04:26Z) Created work-package scaffold and activated this ExecPlan.
- [x] (2026-04-04 04:26Z) Completed context mapping across map controller stack, Roads controller/routes, and existing Subcatchment/Channel map interaction patterns.
- [x] (2026-04-04 13:52Z) Implemented backend Roads layer + per-segment drilldown payload contract and tests.
- [x] (2026-04-04 13:52Z) Implemented frontend Roads overlay registration (paths + labels), hover interaction, and click-to-drilldown behavior + tests.
- [x] (2026-04-04 13:52Z) Executed required validation commands and collected manual endpoint validation evidence on `/wc1/runs/cl/clogging-starch`.
- [x] (2026-04-04 16:38Z) Completed mandatory `reviewer` and `qa_reviewer` subagent reviews; resolved correctness findings and recorded QA follow-up dispositions.
- [x] (2026-04-04 16:38Z) Applied post-review fixes (CAP guard parity, deterministic fallback segment IDs, hover refresh cleanup) and re-ran required validation commands.

## Surprises & Discoveries

- Observation: Existing map overlays rely on shared `map.registerOverlay` plumbing plus overlay ordering in `map_gl_layer_control.js`; roads parity requires touching both overlay module and ordering helper.
  Evidence: `wepppy/weppcloud/controllers_js/channel_gl.js`, `subcatchments_gl.js`, and `map_gl_layer_control.js`.
- Observation: Roads endpoints can return HTTP 200 with an error payload (module disabled), while missing prepared artifacts return 404.
  Evidence: `wepppy/weppcloud/routes/nodb_api/roads_bp.py` and live endpoint probing against `clogging-starch`.
- Observation: Reviewer found a CAP/auth parity gap on the Roads segment drilldown report route relative to WEPP drilldown routes.
  Evidence: `wepppy/weppcloud/routes/nodb_api/roads_bp.py` vs `wepppy/weppcloud/routes/nodb_api/wepp_bp.py`.

## Decision Log

- Decision: Implement Roads map behavior by reusing the Channels/Subcatchments overlay/query architecture instead of introducing a new map interaction layer.
  Rationale: Reduces risk and guarantees UX parity with established map controls.
  Date/Author: 2026-04-03 / Codex.
- Decision: Add a dedicated `RoadsMapOverlay` controller (`roads_gl.js`) and keep Roads map interaction logic out of the form controller (`roads.js`), while adding `MapController.roadQuery()` for drilldown parity.
  Rationale: Mirrors existing `*_gl.js` map module boundaries and keeps map behavior cohesive with other overlay controllers.
  Date/Author: 2026-04-04 / Codex.
- Decision: For prepared features missing `segment_id`, generate deterministic fallback IDs (`roads-seg-missing-<index>`) at feature-collection traversal time.
  Rationale: Avoids `roads-seg-unknown` collisions so hover/click/drilldown mapping remains one-to-one for missing-ID segments.
  Date/Author: 2026-04-04 / Codex.

## Outcomes & Retrospective

- Backend: Added Roads map/resource and segment-detail report/query endpoints, plus Roads controller helpers to serve map-ready feature collections and per-segment detail payloads with WEPP-relevant fields.
- Frontend: Added `roads_gl.js` with `Roads` + `Road Labels` overlays, magenta styling via UI CSS variables, hover highlight + compact hover label, and click-to-drilldown via new `map.roadQuery()`.
- Tests: Added/updated backend and frontend tests covering payload contracts, routes, map query wiring, and Roads overlay interactions.
- Review-driven hardening: Added CAP guard to roads segment report route, replaced collision-prone missing segment keys with deterministic unique fallback IDs, and prevented hover artifact churn/stale state across overlay refreshes.
- Validation: Ran all required commands including full `wctl run-pytest tests --maxfail=1` (3016 passed, 36 skipped).
- Manual endpoint validation: Against `clogging-starch/disturbed9002-wbt-mofe`, verified `resources/roads.json`, `query/roads/segment/<segment_id>`, and `report/roads/segment_summary/<segment_id>` return 200 with populated payload/detail fields.
- Subagent review outcomes:
  - `reviewer`: 3 findings (CAP parity, segment ID collision risk, hover churn) all resolved in code and regression tests.
  - `qa_reviewer`: Coverage/maintainability suggestions mostly addressed (completion-event refresh, layer-toggle hover cleanup, refresh-clears-hover coverage); remaining deeper branch/ordering coverage deferred with low residual risk.
- Lifecycle cleanup: On 2026-04-28, completion was re-verified from this ExecPlan and the package tracker, this file was archived from `prompts/active/` to `prompts/completed/`, and root `AGENTS.md` was updated so no active work-package ExecPlan points at this completed package.

## Context and Orientation

The WEPPcloud deck.gl map is orchestrated in `wepppy/weppcloud/controllers_js/map_gl.js` with helper modules for constants/order/UI behavior. Existing overlays for Subcatchments and Channels are implemented in `subcatchments_gl.js` and `channel_gl.js`, each registering path/fill + label overlays, hover info, and click-driven DrillDown transitions.

Roads domain state is managed by `wepppy/nodb/mods/roads/roads.py`. `prepare_segments()` already emits segmented GeoJSON and a summary file under `wepp/roads/segments/`. The current Roads blueprint `wepppy/weppcloud/routes/nodb_api/roads_bp.py` exposes status/summary workflows but no map-ready roads GeoJSON endpoint and no road-segment drilldown report route.

For this package, a road segment means one prepared feature from Roads monotonic segment output. Required drilldown fields include identifying, design, surface, traffic, road geometry metrics, routing indicators, and fill/buffer metrics when present in current artifacts.

## Plan of Work

Milestone 1 (Backend payloads): extend Roads controller and routes to expose a map-ready roads segments payload and a per-segment drilldown payload. Add helper methods in `Roads` to load prepared segment features, normalize defaults, and return per-segment detail dicts containing required keys where available. Add routes in `roads_bp.py` for map resource JSON and drilldown HTML rendering. Add/extend template(s) under `templates/reports/roads/` for segment details. Add focused Python route/controller tests.

Milestone 2 (Frontend overlays/interactions): add a `roads_gl.js` controller module mirroring Subcatchments/Channels patterns. Register `Roads` and `Road Labels` overlays with magenta styling and label behavior consistent with existing label layers. Implement hover highlight + hover text and click handling that triggers the existing DrillDown transition (via map query/drilldown helper). Wire overlay ordering/toggle behavior in map layer control utilities and shared constants. Add Jest coverage for overlay visibility, labels, hover, and click-to-drilldown.

Milestone 3 (Validation/review): run requested validations in the required order, then perform manual verification against `/wc1/runs/cl/clogging-starch` (or equivalent available run). Run mandatory `reviewer` and `qa_reviewer` subagents, address findings, and update this ExecPlan + tracker with final outcomes.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Backend implementation and targeted tests:
   - `wctl run-pytest tests/nodb/mods/test_roads_controller.py`
   - `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py`

2. Frontend implementation and targeted tests:
   - `wctl run-npm test -- roads map_gl`

3. Required validation commands:
   - `wctl run-pytest tests/nodb/mods/test_roads_controller.py`
   - `wctl run-pytest tests/weppcloud/...` (targeted files touched)
   - `wctl run-npm lint`
   - `wctl run-npm test`
   - `wctl run-pytest tests --maxfail=1`

4. Manual validation on run page:
   - Open `/weppcloud/runs/clogging-starch/disturbed9002-wbt-mofe/`.
   - Complete Roads prepare if not already complete.
   - Confirm `Roads` + `Road Labels` appear in map layer control only when prepare artifacts exist.
   - Confirm hover highlight/info and click-to-drilldown behavior on a road segment.

5. Mandatory reviews:
   - Spawn `reviewer` subagent for correctness/regression.
   - Spawn `qa_reviewer` subagent for test quality/maintainability.
   - Apply or disposition findings with rationale.

## Validation and Acceptance

Acceptance is satisfied when:
- Roads map and label overlays are present and toggleable after prepare artifacts exist.
- Hover visibly highlights road geometry and returns compact segment metadata.
- Clicking road geometry loads DrillDown road-segment details via the existing map DrillDown flow.
- Required fields are present in drilldown output when available in artifacts, with explicit placeholders/defaults where fields are absent.
- All required validation commands pass or have explicit documented constraints.
- Mandatory subagent reviews are complete and findings addressed/dispositioned.

## Idempotence and Recovery

Changes are additive and can be rerun safely. If test commands fail, rerun targeted suites after fixes before broad sweeps. If manual validation run artifacts are stale, rerun Roads prepare and refresh the map page before retesting interactions.

## Artifacts and Notes

- Validation logs and review summaries will be captured in package tracker notes and final handoff.

## Interfaces and Dependencies

Backend interfaces to add/extend:
- `Roads` helper(s) for prepared segment feature retrieval and single-segment detail lookup.
- Roads blueprint endpoints for map resource JSON and road segment drilldown rendering.

Frontend interfaces to add/extend:
- `MapController` overlay registration for Roads and Road Labels (new `roads_gl.js` module).
- Overlay ordering helpers in `map_gl_layer_control.js` for Roads parity.
- DrillDown query helper for road segment selection (mirroring existing sub/channel query helpers).

Dependencies are existing in-repo map helpers (`WCDom`, `WCHttp`, `MapController`) and Roads NoDb artifacts; no new external dependencies are introduced.

---
Revision Note (2026-04-03 / Codex): Initial active ExecPlan authored at package kickoff, with milestones for backend payloads, frontend overlay/drilldown parity, and required validation + review gates.

Revision Note (2026-04-28 / Codex): Completion state verified and ExecPlan archived under `prompts/completed/`; package tracker, package summary, project tracker, and root `AGENTS.md` now reflect closure.
