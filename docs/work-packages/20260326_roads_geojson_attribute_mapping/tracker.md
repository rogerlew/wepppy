# Tracker - Roads GeoJSON Attribute Discovery and Mapping UI

> Living document tracking progress, decisions, risks, and verification for Roads GeoJSON attribute mapping.

## Quick Status

**Started**: 2026-03-26
**Current phase**: Complete (implementation + validation + review artifacts)
**Last updated**: 2026-03-26
**Active ExecPlan**: `prompts/active/roads_geojson_attribute_mapping_execplan.md`
**Next milestone**: Package closeout/handoff

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Reviewed current Roads detection behavior for `design`, `surface`, and `traffic` across prepare/run paths and tests (2026-03-26).
- [x] Authored work-package scaffold (`package.md`, `tracker.md`, active ExecPlan, notes/artifacts placeholders) (2026-03-26).
- [x] Added package listing to `PROJECT_TRACKER.md` backlog (2026-03-26).
- [x] Captured user decisions: warn+fallback when mapped fields are missing, auto-reset mappings on upload, top-level properties only, and user-configurable discovery limits (2026-03-26).
- [x] Captured user decision: fallback controls must be explicit values (`surface`: `gravel|paved`; `traffic`: `high|low|none`) (2026-03-26).
- [x] Implemented Roads controller contract updates for discovery metadata, mapping fields, fallback values, prepare/run integration, and warning summaries (2026-03-26).
- [x] Extended monotonic segment conversion with configurable design-property key resolution (2026-03-26).
- [x] Updated Roads API/config responses and UI controls/controller wiring for mapping workflow (2026-03-26).
- [x] Added/updated regression tests across controller, monotonic utility, routes, and JS controller (2026-03-26).
- [x] Updated Roads specification with discovery/mapping contract and fallback precedence (2026-03-26).
- [x] Completed code review artifact (`artifacts/20260326_code_review.md`) (2026-03-26).
- [x] Completed QA review artifact (`artifacts/20260326_qa_review.md`) (2026-03-26).

## Timeline

- **2026-03-26** - Package created and scoped from current Roads implementation audit.
- **2026-03-26** - Active ExecPlan authored with milestone-level implementation and validation flow.

## Decisions

### 2026-03-26: Keep compatibility by preserving legacy key fallbacks
**Context**: Existing runs and uploads may rely on hard-coded keys (`DESIGN`, `SURFACE`, `TRAFFIC`, etc.).

**Options considered**:
1. Replace legacy resolution with mapping-only behavior.
2. Add mapping support but keep current fallback order when mappings are unset.

**Decision**: Option 2.

**Impact**: Existing uploads continue to work unchanged, while users gain explicit mapping controls for non-standard schemas.

---

### 2026-03-26: Apply mapping in both prepare and run paths
**Context**: Design eligibility affects lowpoint attribution during `prepare_segments`, while parameterization occurs during `run_roads_wepp`.

**Options considered**:
1. Apply mapping only in run-stage segment input resolution.
2. Apply mapping in both prepare and run stages.

**Decision**: Option 2.

**Impact**: Users do not get inconsistent outcomes where mapped design fields are ignored during prepare.

---

### 2026-03-26: Reuse existing Roads config/results endpoints before adding new endpoints
**Context**: Feature can likely piggyback on current `api/roads/config` and upload response payloads.

**Options considered**:
1. Introduce a dedicated discovery endpoint immediately.
2. Extend existing Roads upload/config summary payloads first.

**Decision**: Option 2 (with option 1 reserved if payload size or lifecycle constraints emerge).

**Impact**: Smaller API surface delta and lower route/test overhead.

---

### 2026-03-26: Missing mapped fields should warn and fallback
**Context**: User clarified desired behavior when a selected mapping field is missing on some features.

**Options considered**:
1. Fail fast and block prepare/run.
2. Warn and fallback to legacy/default resolution.

**Decision**: Option 2.

**Impact**: Keeps compatibility and run continuity while surfacing mapping quality issues explicitly.

---

### 2026-03-26: Auto-reset mapping state on each upload and attempt remap discovery
**Context**: User clarified mapping lifecycle when new GeoJSON files are uploaded.

**Options considered**:
1. Retain previous mapping selections by default.
2. Reset mappings on upload and attempt best-effort rediscovery from new field catalog.

**Decision**: Option 2.

**Impact**: Prevents stale mapping carry-over across schema changes.

---

### 2026-03-26: Discovery scope is top-level feature properties with user-configurable limits
**Context**: User clarified discovery breadth and nested-property support.

**Options considered**:
1. Support nested property paths and fixed discovery caps.
2. Limit to top-level feature properties and let users configure discovery limits.

**Decision**: Option 2.

**Impact**: Keeps parsing deterministic and UI simpler while supporting large schemas through configurable bounds.

---

### 2026-03-26: Let users set fallback values for surface and traffic
**Context**: User clarified that fallback behavior for `surface` and `traffic` should be explicit value controls.

**Options considered**:
1. Keep fallback values fixed to module defaults (`surface_default=gravel`, `traffic_default=low`).
2. Add user-selectable fallback values: `surface` in `{gravel, paved}` and `traffic` in `{high, low, none}`.

**Decision**: Option 2.

**Impact**: Makes fallback behavior explicit and user-controlled without adding extra fallback-field mapping complexity.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Mapping applied in run path but not prepare path causes inconsistent eligibility/mapping results | High | Medium | Add prepare-stage mapping integration + targeted tests proving mapped design behavior | Open |
| Ambiguous/invalid user field selection causes hidden misconfiguration | Medium | Medium | Validate mapping field names against discovered catalog; emit explicit warning payloads/logs on fallback | Open |
| UI controls drift from backend mapping contract | Medium | Medium | Add JS + route tests for round-trip mapping state and apply action | Open |
| Discovery payloads become too large for very wide schemas | Medium | Medium | Keep all field names but bound value previews; expose user-configurable discovery limits + truncation metadata | Open |
| Fallback precedence (`mapped field -> user default`, legacy keys only when mapping is unset) may be misunderstood | Medium | Medium | Document precedence in UI help/spec and add explicit route/controller regression tests | Open |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1`
- [x] `wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1`
- [x] `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1`
- [x] `wctl run-npm test -- roads`
- [x] `wctl run-npm lint`
- [x] `wctl run-pytest tests --maxfail=1`

### Documentation
- [x] `wctl doc-lint --path wepppy/nodb/mods/roads/specification.md`
- [x] `wctl doc-lint --path docs/work-packages/20260326_roads_geojson_attribute_mapping/package.md`
- [x] `wctl doc-lint --path docs/work-packages/20260326_roads_geojson_attribute_mapping/tracker.md`
- [x] `wctl doc-lint --path docs/work-packages/20260326_roads_geojson_attribute_mapping/prompts/active/roads_geojson_attribute_mapping_execplan.md`

### Integration
- [x] Manual run-page check: upload roads GeoJSON, inspect discovered attributes, apply mappings, then run prepare/run.
- [x] Confirm changed mapping invalidates stale prepare/run state and requires re-prepare (controller contract + tests).
- [x] Code review checklist completed and findings dispositioned.
- [x] QA review checklist completed and findings dispositioned.

## Progress Notes

### 2026-03-26: Initial scoping and package authoring
**Agent/Contributor**: Codex

**Work completed**:
- Audited current `design`/`surface`/`traffic` detection and fallback logic in Roads controller + monotonic segment utility.
- Identified key contract gap: prepare-stage design eligibility in `monotonic_segments.py` currently checks `DESIGN` directly.
- Authored package docs and active ExecPlan with file-level milestone plan.
- Captured user product decisions for fallback/reset/discovery scope and updated plan artifacts.

**Blockers encountered**:
- None.

**Next steps**:
- Implement Milestone 1 contract changes and controller tests.

**Test results**:
- Documentation-scoping session; no code tests executed.

### 2026-03-26: ExecPlan end-to-end implementation and validation
**Agent/Contributor**: Codex

**Work completed**:
- Implemented controller mapping/discovery contract and warning summaries in `roads.py`.
- Added design-property-key support in monotonic conversion for prepare-stage eligibility consistency.
- Added Roads UI mapping controls and controller apply workflow, plus route payload updates.
- Updated Roads specification and package docs.
- Added code-review and QA-review artifacts under package `artifacts/`.

**Blockers encountered**:
- None.

**Test results**:
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1` (pass)
- `wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1` (pass)
- `wctl run-npm test -- roads` (pass)
- `wctl run-npm lint` (pass)
- `wctl run-pytest tests --maxfail=1` (pass)

### 2026-03-26: Fallback semantics clarification and re-validation
**Agent/Contributor**: Codex

**Work completed**:
- Updated Roads fallback semantics from fallback field mapping to fallback value controls.
- Updated template/controller/tests/docs for:
  - `attribute_field_map` keys: `design`, `surface`, `traffic`
  - fallback value controls: `surface_default` (`gravel|paved`) and `traffic_default` (`high|low|none`)
- Re-ran targeted validation suites and rebuilt controller bundle.

**Blockers encountered**:
- None.

**Test results**:
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1` (pass)
- `wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` (pass)
- `wctl run-npm test -- roads` (pass)
- `wctl run-npm lint` (pass)
- `wctl run-pytest tests --maxfail=1` (pass)
- `wctl doc-lint --path wepppy/nodb/mods/roads/specification.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260326_roads_geojson_attribute_mapping/package.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260326_roads_geojson_attribute_mapping/tracker.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260326_roads_geojson_attribute_mapping/prompts/active/roads_geojson_attribute_mapping_execplan.md` (pass)

### 2026-03-26: Manual E2E validation confirmation
**Agent/Contributor**: User + Codex

**Work completed**:
- User executed manual run-page E2E for Roads: upload/mapping/apply/prepare/run.
- Confirmed UI behavior matched expectations and Roads WEPP run completed successfully.
- Recorded manual QA completion and removed the remaining manual-validation gap from package docs.

**Blockers encountered**:
- None.
