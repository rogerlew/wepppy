# Roads GeoJSON Attribute Discovery and Mapping UI

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, a Roads user can upload GeoJSON, see which attributes were discovered, and explicitly map attribute names to Roads semantics (`design`, `surface`, `traffic`) before pressing `Prepare Segment Candidates` or `Run WEPPcloud Roads`. Users can also choose fallback values for `surface` and `traffic`. This removes current schema guesswork, especially when uploads use non-standard property names. A successful implementation is visible on the Roads control: mapping selectors appear after upload, mappings can be saved, and prepare/run outcomes reflect those mappings.

## Progress

- [x] (2026-03-26 00:00Z) Audited current Roads detection behavior and identified contract gaps.
- [x] (2026-03-26 00:00Z) Authored package/tracker/ExecPlan scaffold.
- [x] (2026-03-26 00:20Z) Captured product decision to allow user-set fallback controls for `surface` and `traffic`.
- [x] (2026-03-26 01:05Z) Added explicit code-review + QA-review gates to package/tracker/ExecPlan per user request.
- [x] (2026-03-26 02:00Z) Implemented controller discovery contract + mapping-aware resolution helpers.
- [x] (2026-03-26 02:15Z) Integrated mapping into prepare-stage design eligibility and run-stage input resolution.
- [x] (2026-03-26 02:35Z) Implemented Roads UI mapping controls and wiring.
- [x] (2026-03-26 03:20Z) Added/updated tests and docs; ran validation gates.
- [x] (2026-03-26 03:30Z) Completed code review + QA review artifacts.
- [x] (2026-03-26 04:10Z) Updated fallback semantics to value selectors (`surface_default`, `traffic_default`) and re-ran targeted validation.
- [x] (2026-03-26 04:35Z) Re-ran full `tests --maxfail=1` and doc-lint checks; refreshed code/QA review artifacts.
- [x] (2026-03-26 05:05Z) User-confirmed manual Roads run-page E2E pass (UI behavior expected; Roads WEPP run completed).

## Surprises & Discoveries

- Observation: Prepare-stage lowpoint eligibility currently reads `DESIGN` directly.
  Evidence: `wepppy/nodb/mods/roads/monotonic_segments.py` uses `design_value = properties.get("DESIGN")`.

- Observation: Run-stage design gating already supports both `DESIGN` and `design`.
  Evidence: `wepppy/nodb/mods/roads/roads.py` uses `_first_non_empty_property(properties, ("DESIGN", "design"))` in run loop and segment input resolution.

- Observation: Surface and traffic lookup are hard-coded key lists with no user-configurable mapping.
  Evidence: `_resolve_segment_run_inputs()` reads only `("SURFACE", "surface", "ROAD_SURFACE")` and `("TRAFFIC", "traffic")`, with `CONDITION` fallback.

- Observation: Roads UI currently has upload + prepare + run controls only; there is no mapping control region.
  Evidence: `wepppy/weppcloud/templates/controls/roads_pure.htm` has no select inputs for attribute assignment.

## Decision Log

- Decision: Keep current hard-coded fallback keys as compatibility behavior when mappings are unset.
  Rationale: Existing uploads must keep working without requiring new UI interaction.
  Date/Author: 2026-03-26 / Codex.

- Decision: Apply mapping in both prepare and run paths.
  Rationale: Prepare determines lowpoint attribution eligibility; run determines segment parameterization. Both must be coherent.
  Date/Author: 2026-03-26 / Codex.

- Decision: Extend existing Roads upload/config payloads before introducing a new dedicated discovery endpoint.
  Rationale: Smaller route-surface delta and easier regression coverage.
  Date/Author: 2026-03-26 / Codex.

- Decision: When a mapped field is missing on individual features, log/return warnings and fallback to legacy/default resolution.
  Rationale: User requested compatibility-first behavior with explicit observability.
  Date/Author: 2026-03-26 / User + Codex.

- Decision: On every new upload, auto-reset prior mappings and attempt best-effort remap discovery against the new field catalog.
  Rationale: User requested protection from stale mappings crossing schema changes.
  Date/Author: 2026-03-26 / User + Codex.

- Decision: Attribute discovery is restricted to top-level feature properties; nested paths are out of scope.
  Rationale: User requested feature-properties-only scope for this package.
  Date/Author: 2026-03-26 / User + Codex.

- Decision: Users can set fallback values for `surface` and `traffic` in addition to primary mapping fields.
  Rationale: User explicitly requested fallback value control (`surface`: `gravel|paved`; `traffic`: `high|low|none`).
  Date/Author: 2026-03-26 / User + Codex.

## Outcomes & Retrospective

Implementation outcome: feature delivered end-to-end with controller/API/UI contract updates, fallback value controls, warning summaries, and regression coverage. Validation gates passed across targeted suites, full repo pytest sweep, and scoped doc-lint checks. User-confirmed manual browser E2E also passed, including successful Roads WEPP completion.

## Context and Orientation

`Roads` is a run-scoped NoDb controller (`wepppy/nodb/mods/roads/roads.py`) with persisted state in `roads.nodb`. Roads ingest starts with `upload_geojson`, then `prepare_segments`, then queue-backed `run_roads_wepp`.

Current `design/surface/traffic` detection behavior is:

- Prepare-stage design eligibility:
  - `monotonic_segments.py` checks `properties.get("DESIGN")` only.
  - Eligible values are `inslope_bd` and `inslope_rd` (case-insensitive once a value is found).

- Run-stage design selection:
  - `roads.py` checks `DESIGN` then `design`.
  - Unsupported design raises `ValueError`.

- Run-stage surface selection:
  - Reads `SURFACE`, `surface`, `ROAD_SURFACE`.
  - Normalizes through alias map (for example `dirt` -> `gravel`, `asphalt` -> `paved`).
  - Falls back to `surface_default` when missing/unrecognized.

- Run-stage traffic selection:
  - Reads `TRAFFIC`, `traffic`.
  - Alias normalization (`no`/`notraffic` -> `none`).
  - If traffic missing/unrecognized, reads `CONDITION`/`condition` via `CONDITION_TRAFFIC_MAP`.
  - Falls back to `traffic_default`.

The Roads UI controller is `wepppy/weppcloud/controllers_js/roads.js`; routes are in `wepppy/weppcloud/routes/nodb_api/roads_bp.py`; control template is `wepppy/weppcloud/templates/controls/roads_pure.htm`.

## Plan of Work

### Milestone 1 - Controller data contract and mapping-aware resolution

Implement upload-time attribute discovery and persisted mapping state in `Roads`.

1. Extend Roads params contract in `wepppy/nodb/mods/roads/roads.py`:
   - add `attribute_field_map` under `_default_params()`:
     - `{"design": None, "surface": None, "traffic": None}`.
   - update `set_params()` validation to accept and validate `attribute_field_map` when present.

2. Add upload-time discovery metadata:
   - create helper that scans top-level uploaded feature properties and emits:
     - all discovered field names,
     - non-empty count,
     - distinct non-empty count,
     - sample values (bounded by configurable limits).
   - add user-configurable discovery-limit params (for sample/value profiling bounds).
   - persist discovery summary on upload (for current uploaded file only).
   - reset mapping selections on upload, then attempt best-effort remap by exact field-name match in new catalog.
   - include summary in `set_uploaded_geojson()` response and `query_summary()` payload.

3. Add mapping-aware property resolution helpers:
   - helper to resolve mapped field name.
   - helper to read first non-empty property for mapped and legacy keys.
   - for `surface` and `traffic`, use configured fallback defaults (`surface_default`, `traffic_default`) when mapped fields are missing/invalid.
   - use these helpers in `_resolve_segment_run_inputs()` for `design`, `surface`, `traffic`.

4. Preserve compatibility behavior:
   - when mapped field is unset, keep current key-list behavior.
   - when mapped primary fields are set but missing on a specific feature, emit warning diagnostics and fallback to configured defaults.

### Milestone 2 - Prepare integration and monotonic-segment eligibility updates

Ensure mapping affects prepare-stage design eligibility and lowpoint attribution.

1. Extend `wepppy/nodb/mods/roads/monotonic_segments.py` APIs:
   - add optional `design_property_keys` parameter to conversion entrypoints.
   - default remains legacy behavior (`DESIGN`, `design`) if parameter omitted.

2. Replace hard-coded `properties.get("DESIGN")` with key-list resolver.

3. In `Roads.prepare_segments()`:
   - compute design-property key order from `attribute_field_map.design` + legacy fallbacks.
   - pass key order to `convert_geojson_file_to_monotonic_segments(...)`.

4. Add prepare summary diagnostics for mapping context:
   - include resolved design key order and active mapping values in `last_prepare_summary`.

### Milestone 3 - API/UI mapping controls

Add user-visible controls for assigning mappings after upload.

1. Backend route payload updates in `wepppy/weppcloud/routes/nodb_api/roads_bp.py`:
   - include discovered attribute catalog and `attribute_field_map` in relevant responses:
     - upload response,
     - `GET /api/roads/config`.

2. Template updates in `wepppy/weppcloud/templates/controls/roads_pure.htm`:
   - add a mapping section with five controls:
     - `Design field`, `Surface field`, `Traffic field`, `Surface fallback value`, `Traffic fallback value`.
   - include help text explaining warning + fallback behavior and top-level-property scope.
   - include `Apply Attribute Mapping` button.

3. Frontend controller updates in `wepppy/weppcloud/controllers_js/roads.js`:
   - render mapping options from discovered attribute catalog.
   - pre-select current mapping values from `roads_params.attribute_field_map`.
   - post updated mapping via existing `tasks/roads/set_params` route.
   - refresh summary/info region and status messages after successful apply.

### Milestone 4 - Tests and specification updates

1. Controller tests (`tests/nodb/mods/test_roads_controller.py`):
   - upload discovery summary is persisted and returned.
   - mapping-aware resolution for design/surface/traffic works with custom field names.
   - mapped-missing behavior for `surface`/`traffic` uses configured fallback values.
   - fallback behavior remains intact.

2. Monotonic-segment tests (`tests/nodb/mods/test_roads_monotonic_segments.py`):
   - custom design key list controls inslope eligibility.

3. Route tests (`tests/weppcloud/routes/test_roads_bp.py`):
   - config/upload payload includes mapping/discovery fields.
   - set-params accepts mapping payload and persists it.

4. JS tests (`wepppy/weppcloud/controllers_js/__tests__/roads.test.js`):
   - mapping selectors render.
   - apply button sends expected payload.

5. Spec update (`wepppy/nodb/mods/roads/specification.md`):
   - document discovery payload and mapping resolution order.

### Milestone 5 - Code Review and QA Review

1. Code review pass:
   - review changed backend + frontend files for regressions, fallback precedence correctness, and stale-state invalidation coverage.
   - capture findings (or explicit no-findings note) in package artifacts.

2. QA review pass:
   - execute upload -> mapping -> prepare -> run workflow checks, including mapped-field-missing warning/fallback behavior.
   - capture QA results and any residual risks in package artifacts.

## Concrete Steps

Run from `/workdir/wepppy`.

1. Implement Milestone 1 and run controller tests:

    wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1

2. Implement Milestone 2 and run monotonic-segment tests:

    wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1

3. Implement Milestone 3 and run routes + JS tests:

    wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1
    wctl run-npm test -- roads

4. Run full sanity and docs lint:

    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path wepppy/nodb/mods/roads/specification.md
    wctl doc-lint --path docs/work-packages/20260326_roads_geojson_attribute_mapping/package.md
    wctl doc-lint --path docs/work-packages/20260326_roads_geojson_attribute_mapping/tracker.md
    wctl doc-lint --path docs/work-packages/20260326_roads_geojson_attribute_mapping/prompts/active/roads_geojson_attribute_mapping_execplan.md

5. Record review artifacts:

    - code-review findings note under `docs/work-packages/20260326_roads_geojson_attribute_mapping/artifacts/`
    - QA review note under `docs/work-packages/20260326_roads_geojson_attribute_mapping/artifacts/`

## Validation and Acceptance

Acceptance is complete when all of the following are true:

- Uploading a Roads GeoJSON produces a discovered-attributes summary visible in API payloads and in the Roads UI.
- User can assign primary mappings (`design`, `surface`, `traffic`) from discovered fields and set fallback values for `surface`/`traffic`.
- `prepare_segments()` eligibility/lowpoint attribution changes when design mapping changes.
- `run_roads_wepp()` uses mapped fields for design/surface/traffic resolution, with configured fallback values used when mapped `surface`/`traffic` fields are missing/invalid.
- Missing mapped primary fields produce warnings and then fallback behavior (no silent failure mode).
- Uploading a new file resets stale mappings and attempts best-effort remap discovery against the new catalog.
- Targeted tests and full sanity gates pass.
- Code review and QA review artifacts are present with findings disposition.

## Idempotence and Recovery

- Re-uploading GeoJSON overwrites previous discovery summary for that run and resets stale prepare/run state through existing controller behavior.
- Re-uploading also resets explicit mapping selections and reruns mapping discovery/remap logic.
- Changing mapping via `set_params` remains idempotent and reuses existing stale-state invalidation.
- If UI mapping changes fail, user can keep running with unmapped defaults because legacy fallbacks remain active.

## Artifacts and Notes

Store implementation and validation notes under:

- `docs/work-packages/20260326_roads_geojson_attribute_mapping/artifacts/`

Recommended artifacts:

- payload samples before/after mapping changes,
- targeted test command outputs,
- manual UI verification notes.

## Interfaces and Dependencies

End-state interface expectations:

- `wepppy/nodb/mods/roads/roads.py`
  - `set_params()` accepts `attribute_field_map`.
  - `set_uploaded_geojson()` returns discovery summary for current upload.
  - `query_summary()` includes discovery summary and active mapping state.

- `wepppy/nodb/mods/roads/monotonic_segments.py`
  - conversion entrypoints accept optional `design_property_keys`.

- `wepppy/weppcloud/routes/nodb_api/roads_bp.py`
  - upload/config responses expose mapping + discovery payload fields.

- `wepppy/weppcloud/templates/controls/roads_pure.htm`
  - mapping controls (including fallback value selectors for `surface`/`traffic`) are present and wired to Roads controller JS.

- `wepppy/weppcloud/controllers_js/roads.js`
  - supports rendering + applying attribute mappings.

## Open Questions

None currently. Product decisions for fallback handling are captured in the Decision Log.

---

Revision note (2026-03-26 00:00Z): Initial ExecPlan authored from current Roads detection audit, with milestones for controller contract, prepare/run integration, API/UI wiring, tests, validation, and explicit open questions.
Revision note (2026-03-26 00:15Z): Updated plan with user decisions: warn+fallback behavior, upload-time mapping auto-reset/remap, discovery limits as user-configurable bounds, top-level properties only, and narrowed open question to traffic fallback UX.
Revision note (2026-03-26 00:20Z): Resolved open question by adopting user-set fallback controls for both `surface` and `traffic`.
Revision note (2026-03-26 01:05Z): Added Milestone 5 code-review and QA-review gates and marked ExecPlan execution start.
Revision note (2026-03-26 03:30Z): Completed milestones 1-5 with test/doc gates passing; added code-review and QA-review artifacts.
Revision note (2026-03-26 04:10Z): Updated implementation/docs to fallback value controls (`surface_default`, `traffic_default`) and re-ran targeted validation.
Revision note (2026-03-26 04:35Z): Re-ran full test sweep and doc-lint checks; synchronized tracker and review artifacts with fallback-value semantics.
Revision note (2026-03-26 05:05Z): Recorded user-confirmed manual run-page E2E success and cleared remaining manual-QA risk.
