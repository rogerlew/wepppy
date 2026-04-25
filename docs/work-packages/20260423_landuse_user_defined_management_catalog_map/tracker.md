# Tracker - Landuse User-Defined Management Catalog + Mapping Editor

> Living document tracking progress, decisions, risks, and verification evidence for this package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-24 02:32 UTC  
**Current phase**: Complete  
**Last updated**: 2026-04-25 06:24 UTC  
**Next milestone**: Archived (ExecPlan moved to `prompts/completed/`).  
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `docs/work-packages/20260423_landuse_user_defined_management_catalog_map/artifacts/2026-04-24_security_review.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `notes`, `artifacts`) (2026-04-24 02:32 UTC).
- [x] Authored active ExecPlan at `prompts/active/landuse_user_defined_management_catalog_map_execplan.md` (2026-04-24 02:32 UTC).
- [x] Completed codebase feasibility investigation and captured touchpoints/contracts in package artifacts (2026-04-24 02:32 UTC).
- [x] Added dedicated security review artifact skeleton with initial findings and gate state (2026-04-24 02:32 UTC).
- [x] Added package entry to `PROJECT_TRACKER.md` backlog (2026-04-24 02:32 UTC).
- [x] Implemented run-scoped user-defined management catalog storage + endpoints under `landuse/user-defined/` (2026-04-24 07:11 UTC).
- [x] Implemented `Landuse User-Defined` control page + PowerUser link integration (2026-04-24 07:14 UTC).
- [x] Implemented `Landuse Map` control page + PowerUser link integration (2026-04-24 07:18 UTC).
- [x] Implemented run-local map persistence (`landuse/landuse_user_defined_mapping.json`) with optimistic concurrency and clear-override flow (2026-04-24 07:22 UTC).
- [x] Implemented NoDb custom mapping preference with explicit typed failures for missing/invalid configured custom mapping (2026-04-24 07:26 UTC).
- [x] Extended management map loading to support explicit mapping JSON paths and deterministic `ManagementDir` resolution (2026-04-24 07:30 UTC).
- [x] Added regression suites for management map loading, NoDb custom mapping, rq-engine validation, and new Flask control/API contracts (2026-04-24 07:44 UTC).
- [x] Ran focused validation and package docs lint (`86 passed`; `5 files validated, 0 errors, 0 warnings`) (2026-04-24 07:47 UTC).
- [x] Ran `wctl check-rq-graph` sanity gate (`RQ dependency graph artifacts are up to date`) (2026-04-24 07:48 UTC).
- [x] Attempted pre-handoff full-suite sanity (`wctl run-pytest tests --maxfail=1` / local `.venv` full-suite); blocked by environment prerequisites (`wctl` exit `137`, local missing `SECRET_KEY`) (2026-04-24 08:09 UTC).
- [x] Closed dedicated security findings with no unresolved medium/high items (2026-04-24 07:47 UTC).
- [x] Archived ExecPlan to `prompts/completed/landuse_user_defined_management_catalog_map_execplan.md` (2026-04-24 07:47 UTC).
- [x] Post-closeout contract adjustment: `landuseopts` now excludes only `UnDisturbed/null.man` and deduplicates by `ManagementFile` (does not exclude solely on `IsTreatment`) with regression coverage in `tests/nodb/test_landuse_catalog.py` (2026-04-24 23:03 UTC).
- [x] Post-closeout contract refinement: `landuseopts` dedupe relaxed to unique `(Description, ManagementFile)` pairs so distinct descriptions sharing the same management file remain available (2026-04-25 06:24 UTC).

## Timeline

- **2026-04-24 02:32 UTC** - Package created from user request for run-scoped user-defined management catalog + mapping editor.
- **2026-04-24 02:32 UTC** - Discovery touchpoints validated across PowerUser UI, landuse NoDb, rq-engine upload boundary, and multi-year prep paths.
- **2026-04-24 02:32 UTC** - Contract decisions drafted (upload limits, archive semantics, mapping save semantics, NoDb preference behavior).
- **2026-04-24 07:11 UTC** - Catalog APIs and hardened upload/archive handling implemented under run-scoped landuse user-defined directory.
- **2026-04-24 07:22 UTC** - Mapping snapshot/save/clear endpoints implemented with optimistic concurrency and atomic writes.
- **2026-04-24 07:30 UTC** - NoDb and management loader contract updates completed for run-local custom map preference.
- **2026-04-24 07:44 UTC** - Regression tests expanded across touched modules.
- **2026-04-24 07:48 UTC** - Validation, RQ graph sanity check, security closeout, and package closure updates completed.
- **2026-04-24 08:09 UTC** - Full-suite sanity attempt documented as environment-blocked (`SECRET_KEY` requirement in local `.venv`; `wctl` run exited `137`).
- **2026-04-24 23:03 UTC** - Post-closeout `landuseopts` filtering semantics revised to canonical `ManagementFile` rules (`UnDisturbed/null.man` exclusion + dedup) with targeted regression tests.
- **2026-04-25 06:24 UTC** - Post-closeout `landuseopts` dedupe refined to unique `(Description, ManagementFile)` pairs to preserve distinct option labels that share a management file.

## Decisions Log

### 2026-04-24 02:32 UTC: Deliver two dedicated pages linked from PowerUser Actions
**Context**: User requested separate UX for catalog management and mapping assignment.

**Options considered**:
1. Fold both workflows into existing `landuse` control/report.
2. Provide one page and modal overlays for the second function.
3. Provide two dedicated pages and link from PowerUser Actions.

**Decision**: Option 3.

**Impact**: Cleaner mental model and lower coupling with existing landuse control/report UX.

---

### 2026-04-24 02:32 UTC: Treat package as high-security work with dedicated artifact
**Context**: Scope includes untrusted file upload + archive extraction + run-tree mutation.

**Options considered**:
1. Low/medium triage with no formal security artifact.
2. High triage with explicit by-surface security gate.

**Decision**: Option 2.

**Impact**: Requires resolved medium/high findings before closeout.

---

### 2026-04-24 02:32 UTC: Use all-or-nothing semantics for archive import and mapping save
**Context**: Partial apply across files/mappings risks inconsistent runtime state.

**Options considered**:
1. Partial apply with per-row/per-file errors.
2. Validate entire request and apply atomically.

**Decision**: Option 2.

**Impact**: Deterministic retry behavior, cleaner failure recovery, lower operational ambiguity.

---

### 2026-04-24 02:32 UTC: Persist run-scoped mapping override in `landuse/` and make NoDb prefer it
**Context**: User requires revised mapping file to be project-local and authoritative.

**Options considered**:
1. Keep using static map keys only and store overrides separately.
2. Materialize a run-local map JSON and use it as effective mapping source.

**Decision**: Option 2.

**Impact**: Landuse options/report derive from the same persisted run-local source used by prep.

---

### 2026-04-24 23:03 UTC: Align `landuseopts` exclusion semantics to `ManagementFile` contract
**Context**: Treatment-tagged mappings such as `UnDisturbed/Prescribed_Fire.man` must remain selectable when they are canonical disturbed map entries; only sentinel `UnDisturbed/null.man` should be hidden.

**Options considered**:
1. Continue excluding options via `IsTreatment`.
2. Exclude only `UnDisturbed/null.man` and deduplicate options by `ManagementFile`.

**Decision**: Option 2.

**Impact**: Keeps `disturbed.json` as canonical mapping source while preventing sentinel/null pseudo-management rows from leaking into user-facing options.

---

### 2026-04-25 06:24 UTC: Relax `landuseopts` dedupe to preserve distinct labels
**Context**: Dedupe by `ManagementFile` alone removed semantically distinct options that intentionally share the same management file.

**Options considered**:
1. Keep dedupe strictly on `ManagementFile`.
2. Deduplicate by unique `(Description, ManagementFile)` pairs.

**Decision**: Option 2.

**Impact**: Prevents duplicate spam while preserving user-visible label distinctions and keeping `disturbed.json` canonical.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| ZIP ingestion abuse (traversal, zip bomb, encrypted payloads) | High | Medium | Shared archive validator + strict `.man` member policy + bounded limits + regression tests | Closed |
| Path escape or unsafe run-tree writes | High | Low | Writes constrained to `landuse/user-defined/` and `landuse/`, secure filenames, normalized relpaths | Closed |
| Mapping override not honored consistently across prep paths | High | Medium | Explicit NoDb preference contract + typed errors + regression coverage | Closed |
| Soil association drift after mapping edits | Medium | Medium | Deterministic map-entry rewrite preserving `SoilFile` and validated mapping contracts | Mitigated |
| UI theming/accessibility regressions | Medium | Medium | Pure control templates and existing control-shell patterns reused | Mitigated |

## Verification Checklist

### Code/Contract
- [x] Upload and mapping APIs emit canonical response/error envelopes.
- [x] Run-local mapping override path is validated, deterministic, and tested.
- [x] No silent fallback when a configured custom map is invalid/missing.

### Security
- [x] Security impact triage documented (`high`).
- [x] Dedicated security artifact created.
- [x] No unresolved medium/high findings remain.

### Tests
- [x] Backend tests added/updated for upload and mapping contracts.
- [x] NoDb/RQ tests added/updated for mapping preference and prep-adjacent behavior.
- [x] Management map loader tests added for explicit path/contract failures.

### Docs
- [x] Package/tracker/ExecPlan/security artifact authored.
- [x] Closeout notes and outcomes recorded after implementation.

## Progress Notes

### 2026-04-24 02:32 UTC: Discovery + package authoring
**Agent/Contributor**: Codex

**Work completed**:
- Mapped existing touchpoints for landuse mapping, PowerUser Actions, editable-table UX, upload boundaries, archive validation, NoDb mapping resolution, and prep-time multi-year handling.
- Authored package brief, tracker, active ExecPlan, and security review artifact.
- Drafted concrete contract decisions (payloads/limits, atomic semantics, NoDb preference, backward compatibility).

**Blockers encountered**:
- None.

**Next steps**:
1. Implement secured catalog API and storage model under `landuse/user-defined/`.
2. Implement UI page shells/routes and PowerUser links.
3. Implement run-local map persistence + NoDb preference + regression tests.

**Test results**:
- N/A (discovery/docs only).

### 2026-04-24 07:47 UTC: Implementation + validation closure
**Agent/Contributor**: Codex

**Work completed**:
- Implemented catalog and mapping pages/routes/templates:
  - `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`
  - `wepppy/weppcloud/templates/controls/landuse_user_defined.htm`
  - `wepppy/weppcloud/templates/controls/landuse_map.htm`
  - `wepppy/weppcloud/templates/controls/poweruser_panel.htm`
- Implemented run-local map preference and explicit path loading support:
  - `wepppy/nodb/core/landuse.py`
  - `wepppy/wepp/management/managements.py`
- Added typed custom-map validation in rq-engine landuse route surface:
  - `wepppy/microservices/rq_engine/landuse_routes.py`
- Added/updated regression tests:
  - `tests/wepp/management/test_management_map_loading.py`
  - `tests/nodb/test_landuse_custom_mapping.py`
  - `tests/microservices/test_rq_engine_landuse_routes.py`
  - `tests/weppcloud/routes/test_landuse_bp.py`
  - `tests/weppcloud/routes/test_pure_controls_render.py`

**Blockers encountered**:
- `wctl run-pytest` container path visibility did not reflect newly created host files in this environment; local `.venv` pytest was used for the required touched suites.
- Full-suite local `.venv` collection requires `SECRET_KEY`/`SECRET_KEY_FILE` environment configuration and aborts before tests start.

**Next steps**:
1. None required for this package.

**Test results**:
- `.venv/bin/pytest tests/wepp/management/test_management_map_loading.py tests/nodb/test_landuse_custom_mapping.py tests/microservices/test_rq_engine_landuse_routes.py tests/weppcloud/routes/test_landuse_bp.py tests/weppcloud/routes/test_pure_controls_render.py -q` (`86 passed`)
- `wctl doc-lint --path docs/work-packages/20260423_landuse_user_defined_management_catalog_map` (`5 files validated, 0 errors, 0 warnings`)
- `wctl check-rq-graph` (`RQ dependency graph artifacts are up to date`)
- `wctl run-pytest tests --maxfail=1` (`exit 137` after startup in containerized environment)
- `.venv/bin/pytest tests --maxfail=1` (`collection error: SECRET_KEY or SECRET_KEY_FILE must be configured`)

### 2026-04-24 23:03 UTC: Post-closeout `landuseopts` contract correction
**Agent/Contributor**: Codex

**Work completed**:
- Updated `wepppy/nodb/locales/landuse_catalog.py` to:
  - exclude only `ManagementFile == UnDisturbed/null.man`,
  - deduplicate mapping datasets by `ManagementFile`,
  - stop filtering by `IsTreatment`.
- Added regression coverage in `tests/nodb/test_landuse_catalog.py` for null sentinel exclusion, dedup behavior, and retention of non-null treatment-tagged management files.
- Ran targeted validation:
  - `wctl run-pytest tests/nodb/test_landuse_catalog.py --maxfail=1`
  - `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1`
  - `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`

**Blockers encountered**:
- None.

**Next steps**:
1. Follow-up package can reconcile broader option-consistency semantics across templates/routes if desired.

**Test results**:
- `tests/nodb/test_landuse_catalog.py` -> `4 passed`
- `tests/weppcloud/routes/test_landuse_bp.py` -> `22 passed`
- `tests/weppcloud/routes/test_pure_controls_render.py` -> `46 passed`

### 2026-04-25 06:24 UTC: Post-closeout `landuseopts` dedupe refinement
**Agent/Contributor**: Codex

**Work completed**:
- Updated `wepppy/nodb/locales/landuse_catalog.py` dedupe key from `ManagementFile` to `(Description, ManagementFile)`.
- Updated `tests/nodb/test_landuse_catalog.py` to assert:
  - exact duplicate description/file rows are deduped,
  - distinct descriptions that share a file remain present,
  - `UnDisturbed/null.man` remains excluded.
- Updated package contract language to match the refined dedupe rule.

**Blockers encountered**:
- None.

**Next steps**:
1. None required unless broader cross-template option-normalization is requested.

**Test results**:
- `wctl run-pytest tests/nodb/test_landuse_catalog.py --maxfail=1` -> `4 passed`
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> `22 passed`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` -> `46 passed`

## Communication Log

### 2026-04-24 02:32 UTC: Work-package request
**Participants**: User, Codex  
**Question/Topic**: Investigate feasibility and author a work package for run-scoped user-defined landuse management catalog + mapping UI.  
**Outcome**: Feasibility confirmed; package and execution artifacts created with high-security triage.

### 2026-04-24 07:47 UTC: End-to-end implementation closeout
**Participants**: User, Codex  
**Question/Topic**: Carry package execution through full implementation and closeout.  
**Outcome**: Scope implemented and validated; security findings closed; ExecPlan archived.

### 2026-04-24 23:03 UTC: Post-closeout behavior clarification
**Participants**: User, Codex  
**Question/Topic**: Clarify why `Prescribed Fire` appears in options and align exclusion semantics.  
**Outcome**: Confirmed canonical source behavior and shipped contract correction (`UnDisturbed/null.man` exclusion + `ManagementFile` dedup, no `IsTreatment` exclusion).

### 2026-04-25 06:24 UTC: Post-closeout dedupe adjustment
**Participants**: User, Codex  
**Question/Topic**: Relax dedupe strictness so distinct descriptions sharing one management file are retained.  
**Outcome**: Shipped `(Description, ManagementFile)` pair-based dedupe with updated regression coverage and docs.
