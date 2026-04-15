# WP-07 Evidence: CN Table Workflow + Edit CSV Integration
Status: done  
Last Updated: 2026-04-15  
Work-Package: `WP-07`  
Owner: `codex`

References:
- Plan: `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md`
- Spec: `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`
- Prior package evidence: `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-06_geneva_nodb_facade_collaborators.md`
- NoDb facade standard: `/workdir/wepppy/docs/standards/nodb-facade-collaborator-pattern.md`

## 1. Scope Implemented
Implemented WP-07 end-to-end for run-scoped Geneva CN-table lifecycle + edit workflow integration:
- Added run-scoped CN-table lifecycle service (`init`, missing-file `recreate`, `reset`) for `<run>/geneva/data/cn_table.csv`.
- Added schema/version integrity enforcement with explicit legacy migration support for missing `antecedent_condition_source`.
- Added deterministic metadata/snapshot payloads (path, sha256, rows, columns, schema_version) and append-only JSONL audit events.
- Added optimistic concurrency mutation flow requiring `if_match_sha256` and returning canonical conflict/precondition envelopes.
- Added WP-07-scoped Geneva routes for:
  - `GET /runs/<runid>/<config>/modify_geneva_cn_table`
  - `POST /runs/<runid>/<config>/tasks/modify_geneva_cn_table`
  - `GET /runs/<runid>/<config>/api/geneva/cn_table_meta`
  - `GET /runs/<runid>/<config>/api/geneva/cn_table_snapshot`
  - `POST /runs/<runid>/<config>/tasks/reset_geneva_cn_table`
- Integrated Geneva with shared `controls/edit_csv.htm` semantics while preserving disturbed parity.
- Wired Geneva into Mods navigation/rendering and run-header project-mod toggles with Roads-parity backend gating (WBT-only enable checks).
- Added dedicated `controls/geneva_pure.htm` launch control with full-width action-row semantics (`button_row(full_width=True)`).
- Updated shared editor UI to follow Pure control-shell pattern and theme-system contracts:
  - theme bootstrap + `data-theme` behavior,
  - `ui-foundation.css` + `css/themes/all-themes.css` + `js/theme.js`,
  - no hardcoded color literals in new styling (uses `--wc-*` tokens).
- Expanded `edit_csv` UX scope to include:
  - fluid container/max-width behavior for Geneva and disturbed editor paths,
  - runid breadcrumb link (left of control title) back to run page,
  - column-width stretch logic so the table fills `#spreadsheet1` width while preserving normal button width.
- Added explicit JSpreadsheet theme-bridge states for selected header cells, selected body cells, row-index cells, and regular body cells with dark/light polarity checks.

Preread note:
- User-requested path `/workdir/wepppy/docs/ui-docs/ui-styling-guide.md` does not exist in this repo.
- Used canonical current docs/templates instead:
  - `/workdir/wepppy/docs/ui-docs/ui-style-guide.md`
  - `/workdir/wepppy/docs/ui-docs/theme-system.md`
  - `/workdir/wepppy/wepppy/weppcloud/templates/base_pure.htm`
  - `/workdir/wepppy/wepppy/weppcloud/templates/controls/_pure_macros.html`
  - `/workdir/wepppy/wepppy/weppcloud/templates/controls/disturbed_sbs_pure.htm`

## 2. Code Changes
### Repo: `/workdir/wepppy`
- `wepppy/nodb/mods/geneva/collaborators/cn_table_service.py` (new)
- `wepppy/nodb/mods/geneva/collaborators/__init__.py`
- `wepppy/nodb/mods/geneva/geneva.py`
- `wepppy/weppcloud/routes/nodb_api/geneva_bp.py` (new)
- `wepppy/weppcloud/routes/nodb_api/geneva_bp.pyi` (new)
- `wepppy/weppcloud/routes/__init__.py`
- `wepppy/weppcloud/routes/nodb_api/__init__.py`
- `wepppy/weppcloud/_blueprints_context.py`
- `wepppy/weppcloud/routes/nodb_api/project_bp.py`
- `wepppy/weppcloud/routes/run_0/run_0_bp.py`
- `wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2`
- `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`
- `wepppy/weppcloud/templates/header/_run_header_fixed.htm`
- `wepppy/weppcloud/templates/controls/geneva_pure.htm` (new)
- `wepppy/weppcloud/templates/controls/edit_csv.htm`
- `wepppy/weppcloud/templates/controls/disturbed_modal.htm`
- `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py`
- `wepppy/weppcloud/templates/ui_showcase/component_gallery.htm`
- `wepppy/weppcloud/static-src/tests/smoke/theme-metrics.spec.js`
- `tests/nodb/mods/geneva/test_geneva_cn_table_service.py` (new)
- `tests/weppcloud/routes/test_geneva_bp.py` (new)
- `tests/weppcloud/routes/test_pure_controls_render.py`
- `tests/weppcloud/routes/test_ui_showcase_bp.py`
- `wepppy/nodb/mods/geneva/work-packages/wp-07_cn_table_workflow_edit_csv_integration.md`
- `wepppy/nodb/mods/geneva/implementation-plan.md`

## 3. Tests Added/Extended
Added/extended coverage for:
- CN-table lifecycle init/recreate/reset and deterministic reset hash behavior.
- Schema migration behavior for legacy tables missing `antecedent_condition_source`.
- Optimistic concurrency success/missing-token/stale-token paths.
- Deterministic meta/snapshot behavior.
- Geneva route contracts for modify/meta/snapshot/reset endpoints.
- Shared editor template theme/Pure contract checks.
- Disturbed parity regression coverage after shared template update.
- Mods menu + run-header Geneva placement/visibility checks.
- Theme-lab wiring + target registration checks for JSpreadsheet selected/row/regular cells.
- Playwright theme-metrics polarity assertions for dark-vs-light selected/header/row/regular cell backgrounds.

Primary test files:
- `tests/nodb/mods/geneva/test_geneva_cn_table_service.py`
- `tests/weppcloud/routes/test_geneva_bp.py`
- `tests/weppcloud/routes/test_pure_controls_render.py`
- `tests/weppcloud/routes/test_disturbed_bp.py` (regression run)
- `tests/weppcloud/routes/test_ui_showcase_bp.py`
- `wepppy/weppcloud/static-src/tests/smoke/theme-metrics.spec.js`

## 4. Required Gates
Executed from `/workdir/wepppy` on final WP-07 changes:

1. `wctl run-pytest tests/nodb/mods/geneva --maxfail=1`
- Result: **pass** (`19 passed`)

2. `wctl run-pytest tests/nodb --maxfail=1`
- Result: **pass** (`954 passed, 4 skipped`)

3. `wctl doc-lint --path wepppy/nodb/mods/geneva`
- Result: **pass** (`13 files validated, 0 errors, 0 warnings`)

4. `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- Result: **pass** (`Result: PASS`)

5. `wctl run-npm lint`
- Result: **pass**

6. `wctl run-npm test`
- Result: **pass** (`76 suites passed, 510 tests passed`)

Conditional queue wiring gate:
- `wctl check-rq-graph`: **not required** (no queue wiring changes).

Additional regression validation (shared editor safety):
- `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- Result: **pass** (`88 passed`)

Additional UI theme metrics validation:
- `cd wepppy/weppcloud/static-src && SMOKE_BASE_URL=http://localhost:8000 SMOKE_SITE_PREFIX= npm run smoke:theme-metrics -- --project runs0`
- Result: **pass** (`1 passed`)

## 5. Manual Integration Evidence
Manual WP-07 harness executed inside `weppcloud` container via Flask test-client against the new Geneva routes.

Scenario summary:
- `manual.page.status = 200`
- `manual.page.theme_assets = True` (editor renders with theme CSS + `theme.js` contract)
- `manual.meta.rows = 144`
- `manual.meta.sha = True`
- `manual.save.status = 200`
- `manual.save.updated_sha = True`
- `manual.stale.status = 409`
- `manual.stale.code = STALE_LOOKUP`
- `manual.recreate.exists = True` (file-delete then metadata read recreates table)
- `manual.reset.status = 200`
- `manual.reset.sha = True`

Theme-system evidence:
- Shared editor now loads `ui-foundation.css`, `css/themes/all-themes.css`, and `js/theme.js`.
- Early bootstrap script applies persisted `wc-theme` to `data-theme` before render.
- Automated template-contract tests assert the required theme hooks are present.
- Theme lab includes dedicated JSpreadsheet specimen IDs:
  - `theme_lab_jexcel_header_selected`
  - `theme_lab_jexcel_selected_cell`
  - `theme_lab_jexcel_row_index`
  - `theme_lab_jexcel_regular_cell`
- Theme-metrics smoke checks enforce dark-theme dark backgrounds and light-theme light backgrounds for selected, row-index, and regular table cells.

## 6. Review Workflow
### 6.1 Code Review (manual, risk-focused)
- Reviewed collaborator lifecycle + concurrency contracts, route envelope behavior, and shared template impacts.

### 6.2 QA Review (manual + automated)
- Verified lifecycle, concurrency, and snapshot determinism with new Geneva tests.
- Verified disturbed parity with route regression tests after shared template changes.
- Verified Pure/theme contract expectations through template assertions.

### 6.3 Security Review (manual)
- Verified no broad exception handlers introduced in new production files.
- Verified path handling remains run-scoped through `GenevaArtifactIO.resolve_path`.
- Verified mutation endpoints require explicit concurrency token and return explicit conflict/precondition codes.

## 7. QA Review Checklist
- [x] CN-table lifecycle behavior (init/recreate/reset) is deterministic and contract-consistent.
- [x] Concurrency token semantics match disturbed parity and canonical envelopes.
- [x] Control UX follows existing Pure CSS controller patterns/macros.
- [x] Theme switching contract works for updated controls without hardcoded color regressions.

## 8. Security Review Checklist
- [x] No broad exception swallowing on production paths.
- [x] Save/reset endpoints validate payload and token semantics explicitly.
- [x] File-path and schema handling avoid traversal/injection behavior.
- [x] Conflict/error envelopes remain explicit and non-ambiguous.

## 9. Findings and Disposition
- Finding ID: `WP07-CODE-STATIC-URL-TEMPLATE-CONTEXT`
  - Severity: medium
  - Disposition: resolved_fix_now
  - Action/Notes: `edit_csv.htm` initially assumed `static_url` always existed; added template-local `asset()` fallback so Flask test and non-standard render contexts do not 500.

- Finding ID: `WP07-QA-SHARED-EDITOR-PARITY-RISK`
  - Severity: medium
  - Disposition: resolved_fix_now
  - Action/Notes: shared editor theme modernization risked disturbed regression; added and executed disturbed route regression suite (`88 passed`).

- Finding ID: `WP07-SEC-UNTRACKED-BROAD-CATCH-VISIBILITY`
  - Severity: low
  - Disposition: resolved_fix_now
  - Action/Notes: broad-exception changed-file gate only reported tracked modified files; performed explicit regex scan on new Geneva files and confirmed no broad catches.

- Finding ID: `WP07-QA-TEMPLATE-STALE-RUNNER`
  - Severity: low
  - Disposition: resolved_fix_now
  - Action/Notes: theme-metrics initially reflected stale pre-change template output in the running container; restarted `weppcloud`, revalidated CSS payload, then reran theme-metrics successfully.

## 10. Exit-Criteria Check
- [x] Run-scoped `cn_table.csv` init/recreate/reset behavior implemented.
- [x] Modify/meta/snapshot flow with optimistic concurrency implemented.
- [x] Disturbed `edit_csv.htm` parity behavior achieved for Geneva CN-table workflow.
- [x] Pure CSS controller UX patterns followed for new/changed controls.
- [x] Theme system support validated for updated controls.
- [x] Required tests added/updated and passing.
- [x] Required gates all passing.
- [x] Manual integration evidence captured.
- [x] Code/QA/security reviews completed and findings dispositioned.
- [x] Board row updated to `done` with evidence link.
