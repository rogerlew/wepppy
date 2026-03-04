# Tracker - Browse Parquet Quick-Look Filter Builder

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-03-04  
**Current phase**: Closed; deliverables implemented and documented  
**Last updated**: 2026-03-04  
**Next milestone**: None (closed).  
**Implementation plan**: `docs/work-packages/20260304_browse_parquet_quicklook_filters/prompts/completed/browse_parquet_quicklook_filters_execplan.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created work-package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `notes`, `artifacts`) (2026-03-04).
- [x] Evaluated current browse/parquet flow across HTML preview, download/CSV, D-Tale bridge, and templates (2026-03-04).
- [x] Authored active ExecPlan with phased implementation, validation, and risk controls (2026-03-04).
- [x] Added package entry to `PROJECT_TRACKER.md` backlog (2026-03-04).
- [x] Ran docs lint checks for package docs and `PROJECT_TRACKER.md` (2026-03-04).
- [x] Resolved requester decisions for download/filter semantics and operator behavior (2026-03-04).
- [x] Updated root `AGENTS.md` to set this package ExecPlan as current active work-package plan (2026-03-04).
- [x] Added and archived end-to-end agent execution prompt with outcome summary at `prompts/completed/run_browse_parquet_quicklook_filters_e2e.prompt.md` (2026-03-04).
- [x] Implemented shared parquet filter core in `wepppy/microservices/parquet_filters.py` with bounded AST validation and schema-aware compile/execution helpers (2026-03-04).
- [x] Integrated filtered parquet preview with row-cap + feedback in `wepppy/microservices/browse/flow.py` and browse feature-flag wiring in `wepppy/microservices/browse/browse.py` (2026-03-04).
- [x] Integrated filtered parquet download/CSV in `wepppy/microservices/browse/_download.py` (2026-03-04).
- [x] Integrated browse->D-Tale `pqf` forwarding in `wepppy/microservices/browse/dtale.py` and D-Tale loader parquet filtering in `wepppy/webservices/dtale/dtale.py` (2026-03-04).
- [x] Implemented browse `Parquet Filter Builder` UI and parquet-link propagation in templates/static JS/listing (`directory.htm`, `data_table.htm`, `parquet_filter_builder.js`, `listing.py`) (2026-03-04).
- [x] Added browse parquet schema quick-preview UX: `schema` row action link, inline collapsible schema panel, and authenticated `/schema/{subpath}` metadata endpoints for run/culvert/batch browse routes (2026-03-04).
- [x] Updated Caddy route proxy regexes (`docker/caddy/Caddyfile`, `docker/caddy/Caddyfile.wepp1`) so `/weppcloud/.../schema/...` routes proxy to `browse:9009` for run/culvert/batch surfaces (2026-03-04).
- [x] Removed pre-rendered hidden schema rows from browse listing HTML and switched to dynamic panel insertion on `schema` click to eliminate row-height drift for parquet rows; verified with Playwright against Caddy-routed browse URL (2026-03-04).
- [x] Added regression tests: `tests/microservices/test_parquet_filters.py`, plus filter coverage updates in `test_browse_routes.py`, `test_download.py`, and `test_browse_dtale.py` (2026-03-04).
- [x] Updated docs: `wepppy/microservices/browse/README.md` and `docs/schemas/weppcloud-browse-parquet-filter-contract.md` (2026-03-04).
- [x] Captured final validation evidence in `artifacts/20260304_e2e_validation_results.md` (2026-03-04).
- [x] Recorded broad-exception enforcement drift as explicit deferred follow-up scope (outside this package’s functional deliverables) (2026-03-04).
- [x] Closed package docs and archived active ExecPlan to `prompts/completed/browse_parquet_quicklook_filters_execplan.md` (2026-03-04).

## Timeline

- **2026-03-04** - Package created and scoped.
- **2026-03-04** - Browse-service evaluation completed and integration risks documented.
- **2026-03-04** - Active ExecPlan authored for end-to-end agent execution.
- **2026-03-04** - Docs lint validated package docs and project tracker updates.
- **2026-03-04** - Requester clarified semantic defaults (filtered download parquet, case-insensitive contains, numeric-only GT/LT with graceful NaN/missing exclusion).
- **2026-03-04** - Root AGENTS active ExecPlan pointer switched to this package; end-to-end execution prompt added.
- **2026-03-04** - Milestones 1-5 implemented end-to-end across browse, download, D-Tale, and UI surfaces.
- **2026-03-04** - Added parquet schema preview interactions in browse listing with row-level toggle panels and new schema metadata routes.
- **2026-03-04** - Routed schema endpoints through Caddy browse proxy matchers to prevent fallback Flask "Run Not Found" responses.
- **2026-03-04** - Fixed parquet row-height regression and validated parity between parquet/non-parquet row heights via Playwright (`14px` each).
- **2026-03-04** - Required route suites, broad microservice suite, and doc-lint checks executed; broad-exception enforcement failure recorded with explicit scope note.
- **2026-03-04** - Archived `run_browse_parquet_quicklook_filters_e2e.prompt.md` into `prompts/completed/` with completion outcome summary.
- **2026-03-04** - Closed package and moved active ExecPlan into `prompts/completed/`; tracker/package closeout metadata synchronized.

## Decisions

### 2026-03-04: Keep implementation scoped to browse + dtale integration surfaces
**Context**: User request targets quick-look behaviors in browse service paths.

**Options considered**:
1. Redesign query-engine payload contracts first.
2. Implement feature in browse service with shared filter contract and minimal external blast radius.

**Decision**: Scope the package to browse microservice + D-Tale loader bridge, with no query-engine public API changes.

**Impact**: Lower regression risk and clearer ownership boundaries.

---

### 2026-03-04: Preserve no-filter behavior as default path
**Context**: Existing browse routes are heavily used and already tested.

**Options considered**:
1. Replace current parquet preview/download behavior globally.
2. Add opt-in filtered path that activates only when filter payload is present.

**Decision**: Keep existing behavior unchanged unless filter state is provided.

**Impact**: Reduces regression risk and allows gradual adoption.

---

### 2026-03-04: Centralize filter parsing/validation in one backend module
**Context**: Four surfaces must apply identical filter semantics.

**Options considered**:
1. Parse filters independently in each route handler.
2. Build a shared parser/compiler module and reuse across browse/flow/download/dtale handlers.

**Decision**: Use one shared module to avoid semantic drift.

**Impact**: Consistency, testability, and maintainability improve.

---

### 2026-03-04: Filtered parquet download is the default when filter state is active
**Context**: Requester clarified download semantics.

**Options considered**:
1. Keep `download` unfiltered while filtering only HTML/CSV/D-Tale.
2. Return filtered parquet from `download` when filter is active.

**Decision**: Return filtered parquet from `download` whenever filter state is active.

**Impact**: Users get consistent filtered output across all quick-look surfaces.

---

### 2026-03-04: `Contains` is case-insensitive; GT/LT are numeric-only
**Context**: Requester asked for best judgement on `Contains` and explicit behavior for GT/LT.

**Options considered**:
1. Case-sensitive `Contains`; permissive GT/LT on text columns.
2. Case-insensitive `Contains`; numeric-only GT/LT with graceful missing/NaN handling.

**Decision**: Implement case-insensitive `Contains` and numeric-only GT/LT; missing/NaN rows are excluded gracefully.

**Impact**: Behavior aligns with analyst expectations while avoiding ambiguous lexical comparisons.

---

### 2026-03-04: Keep parquet schema preview endpoint in browse service
**Context**: Requester asked whether schema endpoint should live in query-engine.

**Options considered**:
1. Add schema metadata API in query-engine.
2. Add schema metadata API in browse service alongside browse listing UX.

**Decision**: Implement schema endpoint in browse service (`/runs|culverts|batch/.../schema/{subpath}`).

**Impact**: Reuses existing browse auth/path controls and keeps schema preview tightly coupled to browse UI behavior.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Full-file reads persist in one surface and negate performance gains | High | Medium | Added shared filter execution helpers + cross-surface tests for preview/download/dtale/filter propagation | Mitigated |
| Filter payload injection or malformed AST triggers unsafe execution | High | Medium | Bounded AST limits + schema field validation + parameterized values + quoted identifiers | Mitigated |
| UI builder and backend contract drift | Medium | Medium | Added shared contract doc + route tests + link propagation assertions | Mitigated |
| Large filtered exports still overwhelm resources | Medium | Medium | Added `BROWSE_PARQUET_EXPORT_MAX_ROWS` guard with explicit `413`/`422` contracts | Mitigated |
| Auth/path security regressions on grouped routes | High | Low | Re-ran browse auth/files suites successfully | Mitigated |
| Broad exception changed-file enforcement drift in touched browse/dtale files | Medium | High | Recorded explicit gate failure and follow-up scope note in artifacts/tracker | Open |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/microservices/test_browse_routes.py`
- [x] `wctl run-pytest tests/microservices/test_download.py`
- [x] `wctl run-pytest tests/microservices/test_browse_dtale.py`
- [x] `wctl run-pytest tests/microservices/test_files_routes.py`
- [x] `wctl run-pytest tests/microservices/test_browse_auth_routes.py`
- [x] `wctl run-pytest tests/microservices --maxfail=1`
- [x] `wctl run-npm lint`
- [x] `wctl run-npm test`
- [ ] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (fails: pre-existing broad-catch deltas in touched files vs `origin/master`; recorded in artifacts)

### Documentation
- [x] Work package docs created (`package.md`, `tracker.md`, active ExecPlan).
- [x] Browse README and schema docs updated for filter contract.
- [x] `wctl doc-lint --path docs/work-packages/20260304_browse_parquet_quicklook_filters`
- [x] `wctl doc-lint --path PROJECT_TRACKER.md`
- [x] `wctl doc-lint --path docs/schemas/weppcloud-browse-parquet-filter-contract.md`

### Functional Validation
- [x] Automated parity test: filtered parquet HTML preview shows only matching rows (`test_parquet_preview_contains_case_insensitive_filter`).
- [x] Automated parity test: filter-aware parquet download returns filtered output (`test_download_returns_filtered_parquet_when_pqf_active`).
- [x] Automated parity test: filtered `?as_csv=1` zero-row contract is explicit (`test_download_filtered_csv_no_rows_returns_structured_error`).
- [x] Automated parity test: D-Tale bridge forwards `pqf` and loader cache key differentiates filters (`test_dtale_open_forwards_parquet_filter_payload`, `test_dtale_loader_uses_distinct_dataset_ids_for_distinct_filters`).
- [x] Automated parity test: invalid numeric operator against text field returns explicit validation error (`test_parquet_preview_numeric_filter_rejects_text_field`).

## Progress Notes

### 2026-03-04: Initial scoping and plan authoring
**Agent/Contributor**: Codex

**Work completed**:
- Read root and subsystem guidance relevant to browse and dtale flows.
- Evaluated current behavior in:
  - `wepppy/microservices/browse/browse.py`
  - `wepppy/microservices/browse/flow.py`
  - `wepppy/microservices/browse/_download.py`
  - `wepppy/microservices/browse/dtale.py`
  - `wepppy/webservices/dtale/dtale.py`
  - browse templates and microservice tests
- Identified current bottlenecks:
  - full-file pandas reads for parquet preview
  - full-file parquet-to-CSV conversion
  - D-Tale loading full dataframe
  - no cross-surface filter state propagation
- Authored work-package docs and active ExecPlan.

**Blockers encountered**:
- Functional semantics questions remain for certain operators/export behavior (captured in `Blocked`).

**Next steps**:
1. Execute Milestone 1 from active ExecPlan.
2. Keep tracker and ExecPlan living sections synchronized during implementation.
3. Begin parser + validation tests with requester-approved semantics.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260304_browse_parquet_quicklook_filters` -> pass (`3 files validated, 0 errors, 0 warnings`).
- `wctl doc-lint --path PROJECT_TRACKER.md` -> pass (`1 files validated, 0 errors, 0 warnings`).

### 2026-03-04: Requester semantic defaults captured
**Agent/Contributor**: Codex

**Work completed**:
- Captured requester decisions in package + tracker + active ExecPlan:
  - `download` returns filtered parquet when filter is active.
  - `Contains` is case-insensitive.
  - `GreaterThan`/`LessThan` are numeric-only and gracefully exclude missing/`NaN`.
- Removed open semantic blockers from tracker and ExecPlan.
- Updated backlog next steps in `PROJECT_TRACKER.md` to reflect resolved semantics.

**Blockers encountered**:
- None.

**Next steps**:
1. Start Milestone 1 implementation with resolved semantics.
2. Add targeted tests asserting filtered-download and numeric-operator contracts.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260304_browse_parquet_quicklook_filters` -> pass (`3 files validated, 0 errors, 0 warnings`).
- `wctl doc-lint --path PROJECT_TRACKER.md` -> pass (`1 files validated, 0 errors, 0 warnings`).

### 2026-03-04: Milestones 1-5 implementation and validation closeout
**Agent/Contributor**: Codex

**Work completed**:
- Implemented shared filter parser/validator/compiler and execution helpers in `wepppy/microservices/parquet_filters.py`.
- Integrated filtered parquet behavior into browse preview, download/CSV, and D-Tale bridge/loader paths.
- Added filter UI builder + parquet-link propagation for browse listing workflows.
- Added/updated regression coverage in:
  - `tests/microservices/test_parquet_filters.py`
  - `tests/microservices/test_browse_routes.py`
  - `tests/microservices/test_download.py`
  - `tests/microservices/test_browse_dtale.py`
- Updated docs:
  - `wepppy/microservices/browse/README.md`
  - `docs/schemas/weppcloud-browse-parquet-filter-contract.md`
- Added validation artifact: `artifacts/20260304_e2e_validation_results.md`.

**Blockers encountered**:
- `check_broad_exceptions --enforce-changed` fails against `origin/master` due pre-existing broad catches in touched browse/dtale files; recorded as follow-up scope.

**Next steps**:
1. Handoff package as implemented with validation artifact and explicit broad-exception follow-up note.
2. If required by merge policy, execute a dedicated broad-exception cleanup package for affected browse/dtale files.

**Test results**:
- `wctl run-pytest tests/microservices/test_parquet_filters.py` -> pass (`7 passed`).
- `wctl run-pytest tests/microservices/test_browse_routes.py` -> pass (`10 passed`).
- `wctl run-pytest tests/microservices/test_browse_routes.py` -> pass (`13 passed`).
- `wctl run-pytest tests/microservices/test_download.py` -> pass (`6 passed`).
- `wctl run-pytest tests/microservices/test_browse_dtale.py` -> pass (`3 passed, 4 skipped`).
- `wctl run-pytest tests/microservices/test_files_routes.py` -> pass (`93 passed`).
- `wctl run-pytest tests/microservices/test_browse_auth_routes.py` -> pass (`86 passed`).
- `wctl run-pytest tests/microservices --maxfail=1` -> pass (`539 passed, 4 skipped`).
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> fail (recorded in artifacts).
- `wctl doc-lint --path docs/work-packages/20260304_browse_parquet_quicklook_filters` -> pass (`4 files validated`).
- `wctl doc-lint --path PROJECT_TRACKER.md` -> pass (`1 file validated`).
- `wctl run-npm lint` -> pass.
- `wctl run-npm test` -> pass (`66 suites passed, 413 tests passed`).

## Communication Log

### 2026-03-04: Feature scoping request
**Participants**: User, Codex  
**Question/Topic**: Need secure, performant, low-regression mechanism to real-time filter large parquet quick-look paths (HTML/download/CSV/D-Tale).  
**Outcome**: Work package and detailed active ExecPlan authored; clarification questions documented for operator/export semantics.

### 2026-03-04: Semantic clarification responses
**Participants**: User, Codex  
**Question/Topic**: Clarify filtered download behavior, `Contains` matching semantics, and GT/LT type handling.  
**Outcome**: Confirmed defaults: filtered parquet download, case-insensitive `Contains`, numeric-only GT/LT with graceful exclusion of missing/`NaN`.

### 2026-03-04: Agent-install request
**Participants**: User, Codex  
**Question/Topic**: Install package in `AGENTS.md` and provide an end-to-end execution prompt.  
**Outcome**: Updated root active ExecPlan pointer, authored the E2E run prompt, and archived it at `prompts/completed/run_browse_parquet_quicklook_filters_e2e.prompt.md` with an outcome summary.
