# Landuse Legacy Flask State Route Removal (Post Gate 3)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, deprecated Flask landuse state/mutator compatibility routes will be removed, and rq-engine will be the sole machine/state API surface for landuse operations. Users will still have WEPPcloud render pages (`/report/landuse`, `/landuse-user-defined`, `/landuse-map`), but those pages and all in-repo callers will rely only on rq-engine endpoints for state and mutation.

## Progress

- [x] (2026-04-24 06:14 UTC) Created package scaffold and active ExecPlan.
- [x] (2026-04-24 06:14 UTC) Created dedicated security artifact scaffold.
- [x] (2026-04-24 06:18 UTC) Registered package in `PROJECT_TRACKER.md` Backlog with execution prompt link.
- [x] (2026-04-24 06:18 UTC) Lint-validated package docs and tracker (`6 files validated, 0 errors, 0 warnings`).
- [x] (2026-04-24 06:23 UTC) Froze exact route removal set, including `tasks/modify_landuse_mapping/`.
- [x] (2026-04-24 06:24 UTC) Completed in-repo caller audit for removed endpoints; production callers use rq-engine paths.
- [x] (2026-04-24 06:27 UTC) Removed legacy Flask handlers and updated route tests/docs/contracts.
- [x] (2026-04-24 06:33 UTC) Ran required validation suites and closed security findings.
- [x] (2026-04-24 06:36 UTC) Moved prompts to `prompts/completed/` and marked package closure in tracker artifacts.
- [x] (2026-04-24 06:54 UTC) Applied post-closure smoke remediation for Finder ZIP uploads (`landuse-user-defined/upload`) and re-ran required validation matrix.
- [x] (2026-04-24 07:26 UTC) Applied post-closure UX/state-integrity remediation: converted landuse catalog/map pages to shared WEPPcloud title shell styling and auto-cleared stale system map-override references when `landuse/landuse_user_defined_mapping.json` is missing.
- [x] (2026-04-24 07:30 UTC) Applied post-closure root-cause remediation: `Landuse.clean()` now preserves run-scoped `user-defined/` catalog files and `landuse_user_defined_mapping.json` during build cleanup.
- [x] (2026-04-24 07:38 UTC) Applied run-page load-path recovery in `run_0` so stale missing system map overrides no longer make projects unloadable (`500`) during `/runs/<runid>/<config>/` rendering.
- [x] (2026-04-24 07:50 UTC) Applied stale-write follow-on remediation: stale system-map cleanup on unlocked read paths is now in-memory-only, and `run_0` recovery now retries recoverable `NoDbStaleWriteError` boundary failures.
- [x] (2026-04-24 08:00 UTC) Applied custom-map description integrity follow-on: changed map assignments now normalize labels (example key `43` -> `Moderate Severity Fire`) and legacy stale custom-map descriptions are relabeled during build summary generation.
- [x] (2026-04-24 08:08 UTC) Applied post-closure control-shell polish: added run-home `runid` link to the left of `wc-control__title` on `/landuse-user-defined` and `/landuse-map` using shared title-meta styling patterns, with render regression coverage.
- [x] (2026-04-24 08:53 UTC) Disposed cross-package review findings with rq-engine auth/input hardening (mapping-selection allowlist, unknown token-class denial), mapping error path redaction, schema/OpenAPI parity fixes (`428` + precondition header/body), and added regressions (including landuse map inline save-header coverage).

## Surprises & Discoveries

- Observation: Gate 3 package already moved Phase 3 state surfaces to rq-engine and closed security findings for parity/hardening; this package is purely deprecation/removal cleanup.
  Evidence: `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/package.md` and its closed tracker/security artifacts.

- Observation: Generated bundle `wepppy/weppcloud/static/js/controllers-gl.js` contained a stale legacy caller (`tasks/modify_landuse/`) even though source controllers were rq-engine-first.
  Evidence: pre-rebuild grep hit in generated bundle; resolved by running `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`.

- Observation: Finder-created `.zip` uploads for user-defined landuse catalogs can contain macOS metadata sidecars (for example `__MACOSX/._*.man`) that triggered false `invalid_archive` rejections under strict root-member policy.
  Evidence: operator smoke test reproduced `"Archive members must be at the archive root."` against valid `.man` payloads.

- Observation: Some runs carried stale `Landuse.custom_mapping_relpath=landuse/landuse_user_defined_mapping.json` after the override file was absent, causing `build_landuse_rq` hard-fail before catalog/map UX actions could recover.
  Evidence: operator smoke traceback showed `LanduseCustomMappingError: Configured landuse custom mapping file is missing: landuse/landuse_user_defined_mapping.json`.

- Observation: `Landuse.clean()` was clearing the full `landuse/` root on rebuild, which removed both `landuse/user-defined/` and `landuse/landuse_user_defined_mapping.json` and reintroduced stale-state failures.
  Evidence: operator reproduction + code-path inspection (`Landuse.build()` -> `Landuse.clean()` -> `_clear_directory_preserving_symlink_mount(lc_dir)`).

- Observation: Run-page rendering (`run_0`) accessed `landuse.landuseoptions` directly and could surface stale custom-map failures as unrecoverable page-load `500`s.
  Evidence: operator traceback from `run_0._build_runs0_context` on `landuseoptions` read path.

- Observation: Attempting lock-persist cleanup from stale-system-map recovery on unlocked render reads can surface `NoDbStaleWriteError` races and still produce run-page `500`s.
  Evidence: follow-on operator traceback showed stale write rejection while exiting `NoDbBase.locked()` in stale cleanup path.

- Observation: Custom-map overrides could persist stale base-map `Description` text (for example key `43` stayed `Mixed Forest`) even when `ManagementFile` changed, making build outputs appear to ignore custom assignments.
  Evidence: run artifact inspection showed `ManagementFile=UnDisturbed/Moderate_Severity_Fire.man` with stale `Description=Mixed Forest` for key `43`.

- Observation: After migrating landuse catalog/map pages to shared `ui.card_shell`, the run-home `runid` link still was not surfaced in the title row, creating a small style/navigation parity gap versus existing editor pages.
  Evidence: operator UX report and page inspection showed no run-link element to the left of `wc-control__title`.

- Observation: Cross-package review surfaced additional hardening gaps not covered by prior closure matrix: `build-landuse` mapping selection accepted path-like values, read routes accepted unknown token classes, and mapping error details could expose filesystem `map_path`.
  Evidence: code/QA/security review findings disposition run on 2026-04-24.

## Decision Log

- Decision: Remove legacy state/mutator Flask routes in a dedicated package rather than mixing cleanup into Gate 3 migration package.
  Rationale: Keeps migration risk and deprecation-removal risk isolated and auditable.
  Date/Author: 2026-04-24 / Codex.

- Decision: Keep render routes in WEPPcloud and out of scope for this removal package.
  Rationale: Route ownership boundary is already established and tested.
  Date/Author: 2026-04-24 / Codex.

- Decision: Keep package in Backlog until first implementation edit/test run begins.
  Rationale: Preparation work is complete, but lifecycle state should reflect implementation start, not scaffolding.
  Date/Author: 2026-04-24 / Codex.

- Decision: Remove all candidate legacy Flask machine/state compatibility routes, including `tasks/modify_landuse_mapping/`.
  Rationale: Caller audit found no production in-repo dependencies on these Flask paths; rq-engine equivalents are present and tested.
  Date/Author: 2026-04-24 / Codex.

- Decision: Retain shared landuse helper utilities in `landuse_bp.py` that rq-engine imports (`_coerce_*`, catalog/map helpers) while removing only Flask compatibility route handlers.
  Rationale: Preserves explicit rq-engine contracts without reintroducing dual route ownership.
  Date/Author: 2026-04-24 / Codex.

- Decision: Keep strict root-only `.man` archive contract but explicitly allow/ignore known macOS metadata sidecars for `landuse-user-defined/upload`.
  Rationale: Accepts normal Finder-generated archives without widening payload surface or introducing fallback mutator behavior.
  Date/Author: 2026-04-24 / Codex.

- Decision: Auto-clear only the stale system-managed override reference (`landuse/landuse_user_defined_mapping.json`) when the file is absent, while keeping explicit `LANDUSE_CUSTOM_MAP_MISSING` failures for all other custom map paths.
  Rationale: Recovers from orphaned system override state without introducing broad silent fallback semantics for arbitrary custom mapping contracts.
  Date/Author: 2026-04-24 / Codex.

- Decision: Render `/landuse-user-defined` and `/landuse-map` titles using shared WEPPcloud control-shell styling (`ui.card_shell`) instead of one-off page header markup.
  Rationale: Matches established WEPPcloud page-title visual language (for example editor pages) and removes custom one-off styling drift.
  Date/Author: 2026-04-24 / Codex.

- Decision: Preserve `landuse/user-defined/` and `landuse/landuse_user_defined_mapping.json` during `Landuse.clean()` while continuing to remove transient generated landuse build artifacts.
  Rationale: Fixes destructive cleanup behavior that caused user-defined catalog/map state loss and downstream build failures.
  Date/Author: 2026-04-24 / Codex.

- Decision: Add explicit stale-system-override recovery boundary in `run_0` load context (`_call_landuse_with_stale_mapping_recovery`) for `landuseoptions` and landuse report context generation.
  Rationale: Ensures project pages remain loadable/recoverable even when stale system override state is encountered during render-time reads.
  Date/Author: 2026-04-24 / Codex.

- Decision: Avoid lock acquisition/writeback in `Landuse._clear_stale_system_custom_mapping_reference()` for unlocked callers and add `NoDbStaleWriteError` retry handling in `run_0` stale-map recovery wrapper.
  Rationale: Keeps stale-system-map cleanup recoverable on render reads without reintroducing stale-write race hard failures.
  Date/Author: 2026-04-24 / Codex.

- Decision: Normalize changed-key descriptions on map-save and relabel legacy stale custom-map descriptions during build summary creation when custom `ManagementFile` diverges from base-map entry while carrying base description text.
  Rationale: Prevents stale description drift from masking custom-map assignment effects (including severity labels) without introducing silent fallback mutator behavior.
  Date/Author: 2026-04-24 / Codex.

- Decision: Add run-home `runid` link via the shared control `meta` slot (`order: -1`) on both landuse editor pages instead of introducing custom header markup.
  Rationale: Matches established editor-page title treatment while keeping both pages on the canonical shared control shell.
  Date/Author: 2026-04-24 / Codex.

- Decision: Disposition cross-package review findings in this package closure pass rather than opening a separate follow-up package.
  Rationale: Findings were localized to the already-touched landuse rq-engine/flask surfaces and could be resolved with targeted contract-safe patches and immediate regression coverage.
  Date/Author: 2026-04-24 / Codex.

## Outcomes & Retrospective

Final removed Flask compatibility routes:
- `/runs/{runid}/{config}/tasks/set_landuse_mode/`
- `/runs/{runid}/{config}/tasks/set_landuse_db/`
- `/runs/{runid}/{config}/tasks/modify_landuse_coverage[/]`
- `/runs/{runid}/{config}/tasks/modify_landuse_mapping/`
- `/runs/{runid}/{config}/api/landuse/user_defined/catalog`
- `/runs/{runid}/{config}/tasks/landuse/user_defined/upload`
- `/runs/{runid}/{config}/tasks/landuse/user_defined/delete`
- `/runs/{runid}/{config}/tasks/landuse/user_defined/update-description`
- `/runs/{runid}/{config}/api/landuse/map_snapshot`
- `/runs/{runid}/{config}/tasks/landuse/map/save`
- `/runs/{runid}/{config}/tasks/landuse/map/clear-override`
- `/runs/{runid}/{config}/tasks/modify_landuse/`

Caller-audit disposition:
- No production in-repo callers remain on removed Flask endpoints.
- `tests/weppcloud/routes/test_landuse_bp.py` intentionally keeps negative assertions that removed routes return `404`.

Validation evidence:
- `tests/weppcloud/routes/test_landuse_bp.py`: `21 passed`
- `tests/weppcloud/routes/test_pure_controls_render.py`: `46 passed`
- `tests/microservices/test_rq_engine_landuse_routes.py`: `50 passed` (includes mapping-selection hardening, row validation, redaction, read token-class, and header-precondition regressions)
- `tests/microservices/test_rq_engine_schema_defaults_routes.py`: `54 passed`
- `tests/microservices/test_rq_engine_openapi_contract.py`: `10 passed`
- `tests/microservices/test_rq_engine_auth.py`: `32 passed`
- `tests/nodb/test_landuse_custom_mapping.py`: `10 passed` (includes stale system override auto-clear + unlocked cleanup no-lock + stale custom-map description relabeling regression)
- `tests/nodb/test_root_dir_materialization.py`: `7 passed` (includes clean-path preservation regression)
- `tests/weppcloud/routes/test_run_0_openet_admin_gate.py`: `29 passed` (includes run_0 stale mapping + stale-write recovery regressions)
- `wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`: `20 passed`
- `wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js`: `3 passed`
- `wepppy/weppcloud/controllers_js/__tests__/landuse_map_inline.test.js`: `2 passed`
- `wctl doc-lint ...`: `10 files validated, 0 errors, 0 warnings`

Residual risk disposition:
- No unresolved medium/high findings; package security gate closed.

## Context and Orientation

Prior packages established:
- Phase 1/2 migration and deprecation policy: `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/`
- Phase 3 migration/parity pass: `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/`

Primary removal target file:
- `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`

Related docs/contracts/tests:
- `wepppy/weppcloud/routes/nodb_api/README.md`
- `tests/weppcloud/routes/test_landuse_bp.py`
- `tests/weppcloud/routes/test_pure_controls_render.py`
- `tests/microservices/test_rq_engine_landuse_routes.py`
- `tests/microservices/test_rq_engine_schema_defaults_routes.py`
- `tests/microservices/test_rq_engine_openapi_contract.py`
- `docs/schemas/rq-engine-agent-api-contract.md`
- `docs/schemas/rq-response-contract.md`
- `docs/schemas/weppcloud-csrf-contract.md`

## Plan of Work

### Milestone 1: Route removal set freeze and caller audit
- Enumerate all legacy Flask landuse state/mutator routes still present.
- Audit in-repo references in JS/templates/tests/docs.
- Decide final removal set and document it in tracker Decision Log.

Acceptance:
- Exact removal list is frozen and all in-repo dependencies are identified.

### Milestone 2: Remove handlers and update tests
- Remove selected Flask handler routes from `landuse_bp.py`.
- Update `test_landuse_bp.py` to stop exercising removed endpoints and assert render routes still behave.
- Add any not-found assertions needed for removed route paths.

Acceptance:
- Legacy handlers are removed and WEPPcloud route tests pass.

### Milestone 3: Contract/docs cleanup
- Update `nodb_api/README.md` route table.
- Update schema contracts and discovery/openapi expectations if required.

Acceptance:
- Route ownership docs match runtime behavior and doc-lint passes.

### Milestone 4: Security closure
- Update security artifact with closure evidence for each finding.
- Confirm no unresolved medium/high findings.

Acceptance:
- Security artifact verdict is pass and package can close.

## Concrete Steps

Run commands from `/home/workdir/wepppy`.

1. Caller audit:
   - `rg -n "tasks/set_landuse_mode|tasks/set_landuse_db|tasks/modify_landuse_coverage|tasks/modify_landuse/|tasks/modify_landuse_mapping|api/landuse/user_defined/catalog|tasks/landuse/user_defined/(upload|delete|update-description)|api/landuse/map_snapshot|tasks/landuse/map/(save|clear-override)" wepppy tests docs`

2. Validate route and render suites:
   - `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1`
   - `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`

3. Validate rq-engine suites:
   - `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1`
   - `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
   - `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`

4. Validate browser suites:
   - `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`
   - `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js`

5. Validate docs:
   - `wctl doc-lint --path docs/work-packages/20260424_landuse_legacy_flask_state_route_removal --path wepppy/weppcloud/routes/nodb_api/README.md --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md`

## Validation and Acceptance

Package is accepted only when:
1. Frozen legacy route set is removed from Flask handlers.
2. No in-repo callers remain on removed endpoints.
3. Render routes remain intact and passing tests.
4. rq-engine suites remain green for the same functional area.
5. Security artifact has no unresolved medium/high findings.
6. Docs/contracts are updated and lint-clean.

## Idempotence and Recovery

- Removal should be done in small route batches so regressions can be reverted cleanly.
- If a removed route is still required by an in-repo caller, restore route in patch, update caller first, then retry removal.
- Keep route docs synchronized with each batch to avoid drift.

## Artifacts and Notes

- Security artifact: `docs/work-packages/20260424_landuse_legacy_flask_state_route_removal/artifacts/2026-04-24_security_review.md`
- Tracker: `docs/work-packages/20260424_landuse_legacy_flask_state_route_removal/tracker.md`

### Revision Notes
- 2026-04-24 / Codex: Initial ExecPlan authored for post-Gate-3 legacy Flask state-route removal.
- 2026-04-24 / Codex: Updated Progress + Decision Log after tracker registration and doc-lint readiness pass.
- 2026-04-24 / Codex: Executed full removal package, updated validations/security evidence, and prepared closure artifacts.
- 2026-04-24 / Codex: Added post-closure Finder ZIP smoke remediation notes, decisions, and validation evidence.
- 2026-04-24 / Codex: Added post-closure stale system-override recovery and page-title styling remediation notes with validation evidence.
- 2026-04-24 / Codex: Added post-closure root-cause remediation for destructive `Landuse.clean()` behavior with regression + validation evidence.
- 2026-04-24 / Codex: Added run-page (`run_0`) render-path stale custom-map recovery boundary and regression evidence.
- 2026-04-24 / Codex: Added stale-write race closure notes (in-memory unlocked stale cleanup + `run_0` stale-write retry regressions).
- 2026-04-24 / Codex: Added custom-map description integrity closure notes (changed-key map-save normalization + build-time stale-description relabeling).
- 2026-04-24 / Codex: Added runid-link title-meta parity polish for landuse catalog/map pages with render regression coverage.
- 2026-04-24 / Codex: Added cross-package review findings disposition updates (auth/input hardening, redaction, schema/openapi parity, and regression evidence).
