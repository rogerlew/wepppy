# Browse Parquet Quick-Look Filters Across HTML, Download, CSV, and D-Tale

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Users need to inspect very large interchange parquet outputs without loading full files into memory. After this change, users can build a nested parquet filter once, then apply it consistently across browse HTML quick-look, filtered parquet download, filtered CSV export, and filtered D-Tale launch.

Success is observable when a user opens browse, builds a filter tree, and every parquet action reflects that same filter with explicit feedback for invalid filters and zero-row matches.

## Progress

- [x] (2026-03-04 19:00Z) Created package scaffold at `docs/work-packages/20260304_browse_parquet_quicklook_filters/`.
- [x] (2026-03-04 19:10Z) Evaluated current browse/parquet flow and identified full-file read bottlenecks in preview, download conversion, and D-Tale load paths.
- [x] (2026-03-04 19:20Z) Authored package brief and tracker with initial risks, blockers, and milestones.
- [x] (2026-03-04 19:25Z) Authored this active ExecPlan with concrete implementation sequence and validation gates.
- [x] (2026-03-04 19:30Z) Added package entry to `PROJECT_TRACKER.md` backlog.
- [x] (2026-03-04 19:35Z) Ran docs lint for package docs and `PROJECT_TRACKER.md` with zero errors/warnings.
- [x] (2026-03-04 19:45Z) Recorded requester semantic defaults: filtered parquet download, case-insensitive `Contains`, numeric-only GT/LT with graceful missing/NaN exclusion.
- [x] (2026-03-04 21:35Z) Milestone 1 complete: added shared parser/validator/compiler module at `wepppy/microservices/parquet_filters.py` with bounded AST validation, schema checks, and execution helpers; added unit coverage in `tests/microservices/test_parquet_filters.py`.
- [x] (2026-03-04 21:50Z) Milestone 2 complete: integrated parquet preview filtering in `wepppy/microservices/browse/flow.py` with `BROWSE_PARQUET_PREVIEW_LIMIT`, filter-state propagation in browse query handling, and explicit no-row feedback.
- [x] (2026-03-04 22:05Z) Milestone 3 complete: integrated filtered parquet download/CSV in `wepppy/microservices/browse/_download.py` and browse->D-Tale `pqf` forwarding in `wepppy/microservices/browse/dtale.py`; integrated D-Tale parquet filter application in `wepppy/webservices/dtale/dtale.py`.
- [x] (2026-03-04 22:20Z) Milestone 4 complete: implemented `Parquet Filter Builder` UI in `wepppy/weppcloud/static/js/parquet_filter_builder.js` and template wiring/links propagation in browse templates + listing generation.
- [x] (2026-03-04 22:45Z) Milestone 5 complete: added/updated regression tests (`test_browse_routes.py`, `test_download.py`, `test_browse_dtale.py`), updated docs (`wepppy/microservices/browse/README.md`, `docs/schemas/weppcloud-browse-parquet-filter-contract.md`), and executed validation gates with one recorded non-blocking failure (`check_broad_exceptions`, see artifacts).
- [x] (2026-03-04 23:30Z) Added parquet schema quick-preview UX in browse listings: new `schema` action link, row-level collapsible `Column/Type` panel, and authenticated parquet schema endpoint for run/culvert/batch browse surfaces.
- [x] (2026-03-04 23:45Z) Updated Caddy browse proxy route matchers to forward `/schema/*` run/culvert/batch paths to `browse:9009` instead of falling through to Flask 404.
- [x] (2026-03-04 23:55Z) Fixed schema-preview listing row-height regression by removing pre-rendered hidden schema rows and creating schema panels dynamically on click; validated with Playwright row-height checks through Caddy proxy.

## Surprises & Discoveries

- Observation: Current parquet HTML preview reads the entire file into pandas with no row cap.
  Evidence: `wepppy/microservices/browse/flow.py::_tabular_preview` calls `pd.read_parquet(path)` and then `df.to_html(...)`.

- Observation: Current parquet CSV export converts full parquet to dataframe before writing CSV.
  Evidence: `wepppy/microservices/browse/_download.py::download_response_file` and `_parquet_to_dataframe_with_units`.

- Observation: D-Tale loader currently reads full datasets and only enforces max-file/max-row guardrails after load.
  Evidence: `wepppy/webservices/dtale/dtale.py::load_into_dtale` -> `_load_dataframe(target)`.

- Observation: Browse UI has filename wildcard filtering and diff compare input, but no row-level parquet filter state.
  Evidence: `wepppy/weppcloud/routes/browse/templates/browse/directory.htm` + `_path_input_script.htm` + `listing.py`.

- Observation: Route auth/path controls are mature and must be preserved unchanged.
  Evidence: `docs/schemas/weppcloud-browse-auth-contract.md`, `wepppy/microservices/browse/auth.py`, browse route tests under `tests/microservices/`.

- Observation: D-Tale dataset caching originally keyed only by run/config/path and would incorrectly reuse state across different `pqf` filters.
  Evidence: `wepppy/webservices/dtale/dtale.py::load_into_dtale` reused `data_id` derived from `runid|config|rel_path` before filtered cache-scope fix.

- Observation: Broad exception enforcement failed against `origin/master` due pre-existing broad catches in touched files that are outside this package’s functional scope.
  Evidence: `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` reported deltas in `browse.py`, `flow.py`, and `dtale.py`.

- Observation: Schema preview requirements are browse-context metadata lookups tied to existing browse auth/path contracts rather than analytics/query workloads.
  Evidence: Requester asked for inline row panel toggles in browse listing and endpoint shape `GET .../schema/<path>.parquet`.

## Decision Log

- Decision: Keep implementation inside browse + dtale integration surfaces; do not redesign query-engine public contracts.
  Rationale: Request scope is browse quick-look behavior, and minimizing cross-service contract changes lowers regression risk.
  Date/Author: 2026-03-04 / Codex.

- Decision: Preserve existing no-filter behavior exactly when no filter payload is present.
  Rationale: Existing browse workflows are widely used and heavily tested.
  Date/Author: 2026-03-04 / Codex.

- Decision: Introduce one shared filter contract/parser/compiler module used by browse and dtale.
  Rationale: Four surfaces need identical semantics; duplicated parsing would drift.
  Date/Author: 2026-03-04 / Codex.

- Decision: Use bounded filter AST with explicit limits (depth, nodes, value length) and schema-based field validation.
  Rationale: Prevents denial-of-service and injection-style abuse while keeping error handling explicit.
  Date/Author: 2026-03-04 / Codex.

- Decision: Use filter-aware execution only for parquet-family files (`.parquet`, `.pq`) in this package.
  Rationale: User requirement is parquet quick-look; this keeps scope bounded and testable.
  Date/Author: 2026-03-04 / Codex.

- Decision: When filter state is active, `download` returns filtered parquet output.
  Rationale: Requester confirmed filtered output must be consistent across all quick-look surfaces.
  Date/Author: 2026-03-04 / Codex.

- Decision: `Contains` uses case-insensitive matching; `GreaterThan`/`LessThan` are numeric-only and exclude missing/NaN rows gracefully.
  Rationale: Requester asked for best judgement on contains semantics and explicit numeric-only GT/LT behavior.
  Date/Author: 2026-03-04 / Codex.

- Decision: Use a shared DuckDB-backed execution layer for filtered preview/export to keep value binding parameterized and avoid unsafe SQL interpolation.
  Rationale: Supports case-insensitive contains and numeric coercion semantics while keeping query construction centralized and testable.
  Date/Author: 2026-03-04 / Codex.

- Decision: Include active `pqf` payload in D-Tale dataset cache identity.
  Rationale: Prevents stale dataset reuse across different filter payloads for the same parquet path.
  Date/Author: 2026-03-04 / Codex.

- Decision: Record `check_broad_exceptions` failure as explicit validation evidence instead of broadening this package scope to unrelated boundary cleanup.
  Rationale: Package objective is parquet quick-look filtering; broad-catch deltas are pre-existing in touched files relative to `origin/master` and require separate remediation scope.
  Date/Author: 2026-03-04 / Codex.

- Decision: Implement parquet schema metadata endpoint in browse microservice (`/schema/{subpath}`) rather than query-engine.
  Rationale: Feature is run-scoped file-browser UX, reuses browse auth/path controls, and avoids introducing a cross-service contract for simple schema introspection.
  Date/Author: 2026-03-04 / Codex.

## Outcomes & Retrospective

Implementation is complete for all planned milestones. The package now ships a shared parquet filter contract and applies identical requester-specified semantics across:
- browse parquet preview,
- filtered parquet download,
- filtered CSV export,
- and D-Tale parquet load.

Key outcomes:
- `download` now returns filtered parquet when filter state is active.
- `Contains` is case-insensitive.
- `GreaterThan`/`LessThan` are numeric-only and exclude missing/`NaN` rows.
- UI operator control is implemented as a `<select>` in the filter builder.
- Browse parquet rows now include a `schema` action that toggles an inline read-only `Column`/`Type` schema panel.
- No-filter behavior remains unchanged when `pqf` is absent or feature flag is disabled.

Validation summary:
- Required route and microservice suites passed (`test_browse_routes`, `test_download`, `test_browse_dtale`, `test_files_routes`, `test_browse_auth_routes`, `tests/microservices --maxfail=1`).
- Docs lint checks passed for package docs and `PROJECT_TRACKER.md`.
- `check_broad_exceptions` failed due pre-existing broad-catch deltas relative to `origin/master`; failure recorded in `artifacts/20260304_e2e_validation_results.md`.

## Context and Orientation

This feature touches two services and shared templates:

- Browse microservice:
  - `wepppy/microservices/browse/browse.py` (routes, request handling, template env)
  - `wepppy/microservices/browse/flow.py` (directory/file rendering pipeline)
  - `wepppy/microservices/browse/_download.py` (download + parquet->CSV)
  - `wepppy/microservices/browse/dtale.py` (browse->dtale bridge)
  - `wepppy/microservices/browse/listing.py` (directory link generation)
- D-Tale service:
  - `wepppy/webservices/dtale/dtale.py` (`/internal/load` dataset loading)
- Browse templates/UI:
  - `wepppy/weppcloud/routes/browse/templates/browse/directory.htm`
  - `wepppy/weppcloud/routes/browse/templates/browse/data_table.htm`
  - `wepppy/weppcloud/routes/browse/templates/browse/not_found.htm`
  - `wepppy/weppcloud/routes/browse/templates/browse/_path_input_script.htm`

### Filter Contract (Target)

A filter payload is a JSON tree serialized into query parameter `pqf` as URL-safe base64 JSON.

Tree nodes:
- Group node:
  - `{"kind":"group","logic":"AND"|"OR","children":[...]} `
- Condition node:
  - `{"kind":"condition","field":"<string>","operator":"Equals|NotEquals|Contains|GreaterThan|LessThan","value":"<string>"}`

Validation rules:
- Max depth: 6.
- Max total nodes: 50.
- Field max length: 128.
- Value max length: 512.
- Field must exist in parquet schema before execution.
- Operators map to backend semantics:
  - `Equals` -> `=`
  - `NotEquals` -> `!=`
  - `Contains` -> case-insensitive substring match
  - `GreaterThan` -> numeric-only `>` (missing/NaN rows excluded)
  - `LessThan` -> numeric-only `<` (missing/NaN rows excluded)

Error behavior:
- Invalid payload -> HTTP 422 with structured message (`validation_error`) and node-path details.
- Unknown field/operator mismatch -> HTTP 422.
- Filter matches zero rows -> explicit feedback (`no_rows_matched_filter`) rather than silent empty render.

## Plan of Work

### Milestone 1: Shared Filter Contract and Execution Core

Create a shared module (recommended path: `wepppy/microservices/parquet_filters.py`) that owns:
- payload decode (`pqf` base64url -> JSON),
- AST normalization/validation,
- schema validation for field existence,
- operator/value coercion,
- and safe compile/execution helpers for parquet-backed queries.

Execution helpers must avoid unsafe SQL interpolation. Values are always bound parameters; field names are allowed only after schema validation and safe identifier quoting.

Acceptance:
- Unit tests cover valid/invalid ASTs, depth/node limits, operator mapping, and error payload details.

### Milestone 2: Browse HTML Table Integration

Integrate filter execution into parquet preview path in `flow.py`.

Behavior when `pqf` is present on parquet browse request:
- execute filtered query with preview row cap (`BROWSE_PARQUET_PREVIEW_LIMIT`, default 500),
- render `data_table.htm` with filtered rows,
- display active-filter summary and row feedback.

Behavior when no filter:
- current path remains unchanged.

Acceptance:
- Browse parquet page renders filtered results.
- Invalid filter and zero-row outcomes are user-visible and non-ambiguous.

### Milestone 3: Download/CSV/D-Tale Integration

Download and CSV:
- Extend `_download.py` to accept `pqf` for parquet targets.
- For filtered parquet download: return filtered parquet artifact.
- For filtered `as_csv=1`: return CSV from filtered result only.
- Apply export row guard (`BROWSE_PARQUET_EXPORT_MAX_ROWS`, default 2_000_000) with explicit 413/422 response when exceeded/empty.

D-Tale:
- Extend browse bridge payload in `wepppy/microservices/browse/dtale.py` to forward `pqf` (or normalized filter tree) to `/internal/load`.
- Extend D-Tale loader in `wepppy/webservices/dtale/dtale.py` to apply same filter contract before dataframe creation.

Acceptance:
- Download/CSV/D-Tale outputs align with the same filter used in HTML preview.
- Auth, path validation, and allowed suffix checks are unchanged.

### Milestone 4: UI Filter Builder and Link Propagation

Implement `Parquet Filter Builder` in browse templates with lightweight JS (recommended new static file under `wepppy/weppcloud/static/js/`).

Required behavior:
- user can add nested `AND`/`OR` groups and conditions,
- field/operator/value are text/operator controls,
- filter state is persisted per run/config in `localStorage`,
- parquet action links append active `pqf` automatically:
  - open parquet HTML,
  - `download`,
  - `.csv`,
  - `d-tale`.

Provide inline validation hints before submission (required fields, empty groups).

Acceptance:
- Filter can be created before selecting a parquet file.
- Selected parquet action receives identical filter state.

### Milestone 5: Hardening, Tests, Docs, Rollout

Add/extend tests:
- `tests/microservices/test_browse_routes.py`
- `tests/microservices/test_download.py`
- `tests/microservices/test_browse_dtale.py`
- `tests/microservices/test_files_routes.py` (ensure no route/auth regressions)

Docs:
- update `wepppy/microservices/browse/README.md` with filter query contract and route behavior.
- if contract is stable and cross-team-consumed, add `docs/schemas/weppcloud-browse-parquet-filter-contract.md`.

Rollout:
- gate feature behind `BROWSE_PARQUET_FILTERS_ENABLED` (default `0` for first merge).
- collect latency/usage feedback before default enablement.

Acceptance:
- test suites pass,
- docs lint passes,
- feature flag allows safe opt-in rollout.

## Concrete Steps

Run from `/workdir/wepppy`.

1. Implement shared filter module + unit tests.

    wctl run-pytest tests/microservices/test_browse_routes.py -k filter

2. Integrate browse preview and template updates.

    wctl run-pytest tests/microservices/test_browse_routes.py

3. Integrate download + csv + dtale filtered paths.

    wctl run-pytest tests/microservices/test_download.py
    wctl run-pytest tests/microservices/test_browse_dtale.py

4. Add/adjust auth and edge-route regression coverage.

    wctl run-pytest tests/microservices/test_files_routes.py
    wctl run-pytest tests/microservices/test_browse_auth_routes.py

5. Run broader validation.

    wctl run-pytest tests/microservices --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

6. Lint docs.

    wctl doc-lint --path docs/work-packages/20260304_browse_parquet_quicklook_filters
    wctl doc-lint --path PROJECT_TRACKER.md

## Validation and Acceptance

Manual acceptance checks (with `BROWSE_PARQUET_FILTERS_ENABLED=1`):

1. Build a nested filter in browse UI and open a large parquet table.
   Expected: HTML table shows only filtered rows, with filter summary visible.

2. Click `.csv` link from the same parquet listing.
   Expected: CSV contains filtered rows only.

3. Click `download` for the same parquet target.
   Expected: `download` returns filtered parquet output, not unfiltered full-file parquet.

4. Click `d-tale` for the same parquet target.
   Expected: D-Tale dataset reflects same filtered subset.

5. Use an invalid field name.
   Expected: clear validation error (`validation_error`) with field reference.

6. Use a filter that matches no rows.
   Expected: explicit "no rows matched" feedback (not silent blank table/file).

## Idempotence and Recovery

- All edits are additive and safe to re-run.
- If filter integration causes regressions, disable with `BROWSE_PARQUET_FILTERS_ENABLED=0` while keeping code for debugging.
- If a route-specific integration fails, keep parser module and tests; revert only the failing integration layer in the same PR.
- Never bypass auth/path checks to unblock filter features.

## Artifacts and Notes

Store supporting evidence in this package:
- `notes/` for manual curl transcripts and latency notes.
- `artifacts/` for finalized contract and rollout notes.

Recommended evidence snippets:
- one valid filtered request/response for each surface,
- one invalid filter response,
- one zero-row response.

## Interfaces and Dependencies

New internal interfaces (target signatures; adapt names if needed but keep semantics):

- In `wepppy/microservices/parquet_filters.py`:
  - `decode_filter_payload(raw: str | None) -> FilterNode | None`
  - `validate_filter_tree(node: FilterNode, *, max_depth: int, max_nodes: int, max_len: int) -> None`
  - `compile_filter(node: FilterNode, schema: ParquetSchema) -> CompiledFilter`
  - `query_preview(path: str, compiled: CompiledFilter | None, *, limit: int) -> pd.DataFrame`
  - `query_export(path: str, compiled: CompiledFilter | None, *, max_rows: int) -> pyarrow.Table`

Dependency expectations:
- Reuse existing Parquet stack (`pandas`, `pyarrow`) and existing runtime libraries already present for query-engine usage.
- Do not add new third-party dependencies unless required and justified under `docs/standards/dependency-evaluation-standard.md`.

---
Revision Note (2026-03-04, Codex): Initial ExecPlan authored after browse-service evaluation and package scaffolding.
Revision Note (2026-03-04, Codex): Incorporated requester semantic defaults for filtered download and operator handling; removed open-question blocker section.
Revision Note (2026-03-04, Codex): Milestones 1-5 executed end-to-end, validation/artifacts captured, and living sections updated with implementation outcomes and gate status.
