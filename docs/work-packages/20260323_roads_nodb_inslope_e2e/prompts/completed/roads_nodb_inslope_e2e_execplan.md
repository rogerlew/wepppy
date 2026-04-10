# Roads NoDb Inslope End-to-End Implementation

## Outcome Summary (2026-04-10)

- Completed all planned milestones plus post-closeout runtime/review remediation.
- Captured rollback validation evidence (`mod disable` roundtrip, roads artifact isolation checks, queue lock/job rollback hygiene).
- Archived this ExecPlan from `prompts/active/` to `prompts/completed/` as part of package closure.

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture


After this change, a WEPPcloud user can enable the `Roads` mod on a disturbed WBT run, upload Roads GeoJSON, run a queue-backed Roads workflow, and see Roads completion in run-page preflight and reports. The observable outcome is a successful Roads run that writes `wepp/roads/*` artifacts, injects combined hillslope pass files into a watershed rerun, and surfaces Roads status/results on the run page immediately after Debris Flow.

All commands and examples in this plan use the canonical fixture run unless explicitly stated otherwise:

- run id: `clogging-starch`
- wd: `/wc1/runs/cl/clogging-starch`
- config: `disturbed9002-wbt-mofe.cfg`
- roads input: `/wc1/runs/cl/clogging-starch/roads/UM1_roads_info.geojson`
- DEM: `/wc1/runs/cl/clogging-starch/dem/wbt/relief.tif`

## Progress


- [x] (2026-03-23 22:45Z) Authored package scaffold and activated this ExecPlan.
- [x] (2026-03-23 22:45Z) Mapped current integration seams and test/governance surfaces across NoDb, WEPPcloud, preflight2, rq-engine, RQ, and `wepppyo3`.
- [x] (2026-03-23 23:35Z) Replaced provisional `_pups/roads/*` artifact layout with `wepp/roads/{segments,runs,output}` and updated validation/rollback commands accordingly.
- [x] (2026-03-23 23:55Z) Milestone 1 complete: implemented `Roads(NoDbBase)` scaffold, inslope parity (`Inslope_bd` + `Inslope_rd`), deterministic `topaz_id_hill_lowpoint` assignment, and controller tests.
- [x] (2026-03-23 23:58Z) Milestone 2 complete: wired Roads mod registration/header/run-page ordering/task enum/preflight mappings and preflight2 checklist semantics (`roads` gated by `run_wepp` freshness).
- [x] (2026-03-23 00:40Z) Milestone 3 complete: added `roads_bp`, rq-engine Roads routes, RQ workers, and targeted route/worker tests.
- [x] (2026-03-23 02:10Z) Milestone 4 complete: implemented `combine_hillslope_pass_files` in `wepppyo3/wepp_interchange`, exported Python bindings, wired Roads pass combination with staged segment pass artifacts, and validated with Rust + Python tests.
- [x] (2026-03-23 04:25Z) Milestone 5 complete: synchronized queue graph/catalog + route-freeze artifacts, resolved OpenAPI freeze count/metadata updates, executed fixture-backed `clogging-starch` e2e command path, and passed full validation gates.
- [x] (2026-03-24 00:30Z) Post-closeout regression fix complete: corrected Roads prepare raster-path resolution to explicit WBT rasters (`relief/netful/subwta`), added per-segment lowpoint decision diagnostics + summary counts, aligned upload-first UI copy with style guide, and re-ran required validation gates.
- [x] (2026-03-24 01:22Z) Milestone 4 fidelity closeout: replaced provisional baseline-pass staging with real single-OFE segment WEPP runs (legacy-derived one-OFE soil/management/slope assets), ensured road-only soil OFE outputs, and added end-to-end per-step `roads.log` observability across segment decisions, segment runs, pass combination, and watershed rerun boundaries.
- [x] (2026-03-24 01:23Z) Failure observability hardening: persist `last_run_summary` on watershed-rerun failure with `status=failed` and `failed_stage=watershed_rerun`, keeping segment execution counts/report context visible in UI/query payloads.
- [x] (2026-03-24 01:25Z) Revalidated post-fidelity changes: targeted Roads suites + queue graph checks pass, and full gate passes (`wctl run-pytest tests --maxfail=1` => `2491 passed, 34 skipped`).
- [x] (2026-03-24 01:29Z) Re-ran remaining ExecPlan validation gates: `wctl run-npm lint`, `wctl run-npm test`, `wctl run-preflight-tests ./internal/checklist`, `python tools/check_endpoint_inventory.py`, `python tools/check_route_contract_checklist.py`, `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`, and doc lint for package/tracker/active ExecPlan.
- [x] (2026-03-24 01:52Z) Runtime closeout complete: fixed Roads pass staging/combine runtime defects (append-only lifecycle `roads.log`, targeted-pass symlink unlink before combine, WEPP fixed-format pass writer in `wepppyo3`), rebuilt `wepp_interchange_rust.so`, and verified `clogging-starch` Roads rerun completes (`status=completed`, `executed_segment_count=23`, `targeted_hillslope_count=14`).
- [x] (2026-03-24 03:36Z) Componentized comprehensive review closeout complete (UI controller, NoDb controller, API/queue, `wepppyo3` combiner): resolved all high/medium findings (multipart-only upload contract, queue single-flight governance + 409 conflicts, stale-prepare guards, strict param validation, UI active-job correlation, NO EVENT groundwater merge correctness + header/calendar checks), regenerated queue graph/catalog, and re-ran full validation gates (`wctl run-pytest tests --maxfail=1` => `2499 passed, 34 skipped`).
- [x] (2026-04-10 16:40Z) Package closeout finalized: rollback validation captured (`mod disable` backup/restore parity, queue lock/job rollback checks, roads artifact isolation verification), targeted rollback-related tests re-run, and ExecPlan archived under `prompts/completed/`.

## Surprises & Discoveries


- Observation: `monotonic_segments.py` currently writes `topaz_id_chn_lowpoint` only for `Inslope_bd` and does not yet emit `topaz_id_hill_lowpoint`.
  Evidence: `wepppy/nodb/mods/roads/monotonic_segments.py` and current unit tests in `tests/nodb/mods/test_roads_monotonic_segments.py`.

- Observation: Run-page dynamic mod rendering requires touching both template and runtime bootstrap maps, not only `MOD_UI_DEFINITIONS`.
  Evidence: `run_page_bootstrap.js.j2` (`runContext.mods.flags`, controller entry list) and `controllers_js/project.js` (`MOD_BOOTSTRAP_MAP`).

- Observation: New rq-engine agent-facing routes require frozen inventory/checklist synchronization in addition to route/test code.
  Evidence: `tests/microservices/test_rq_engine_openapi_contract.py`, `tests/tools/test_endpoint_inventory_guard.py`, and `tests/tools/test_route_contract_checklist_guard.py`.

- Observation: Existing in-run NoDb mods (for example AgFields) store WEPP artifacts under `wepp/<mod>/*`, while `_pups/*` is primarily used for child-run workspaces (not needed for Roads phase 1).
  Evidence: `wepppy/nodb/mods/ag_fields/ag_fields.py` (`wepp/ag_fields/runs`, `wepp/ag_fields/output`) and `wepppy/nodb/base.py` (`is_child_run`, `_pups`-prefixed checks).

- Observation: Dynamic mod enable/disable via `/view/mod/<mod>` requires the mod template to exist as soon as the mod is registered, even before full workflow endpoints are wired.
  Evidence: `run_0_bp.py` `view_mod_section` renders `MOD_UI_DEFINITIONS[mod].template` for every enabled mod.

- Observation: Watershed run assembly using absolute pass paths caused WEPP to truncate pass filenames in `pw0.err`, producing `forrtl: file not found` errors.
  Evidence: `/wc1/runs/cl/clogging-starch/wepp/roads/runs/pw0.err` showed truncated `/.../output/H1.` references until `make_watershed_omni_contrasts_run` inputs were switched to `../output/H<id>` paths.

- Observation: Fixture run `clogging-starch` currently yields zero eligible Roads segments with both channel and receiving-hillslope IDs (`eligible_with_lowpoint_ids = 0`), so pass combination is a no-op in this fixture despite successful end-to-end execution.
  Evidence: `Roads.prepare_segments()` + `Roads.run_roads_wepp()` output during fixture validation (`targeted_hillslope_count = 0`).

- Observation: Roads prepare was reading DEM from `ron.dem_fn` (`dem/dem.vrt`) and relying on adjacent auto-detected channel/topaz rasters, which misses WBT rasters in `dem/wbt/*` and yields zero lowpoint mappings.
  Evidence: `Roads.prepare_segments()` path wiring plus fixture diagnostics before fix (`eligible_with_lowpoint_ids = 0`); after explicit `watershed.relief/netful/subwta` wiring, `eligible_with_lowpoint_ids = 23` on `clogging-starch`.

- Observation: Re-running watershed from existing fixture pass files currently fails with `forrtl: severe (64): input conversion error` on `H1.pass.dat` in both baseline and Roads rerun directories.
  Evidence: `/wc1/runs/cl/clogging-starch/wepp/runs/pw0.err` and `/wc1/runs/cl/clogging-starch/wepp/roads/runs/pw0.err`.

- Observation: When watershed rerun failed, `Roads` status moved to `failed` but `last_run_summary` remained null, hiding executed-segment context from UI/report summary consumers.
  Evidence: `roads.nodb` (`py/state`) on `clogging-starch` before fix showed `_status=failed` with `_last_run_summary=None` despite populated `roads.segment.pass.manifest.json` and `roads.log`.

- Observation: Single-OFE soil outputs must contain only the Road OFE (`ntemp=1`, no Fill/Forest OFEs) to stay aligned with phase-1 specification semantics.
  Evidence: `p900001.sol` at `/wc1/runs/cl/clogging-starch/wepp/roads/runs/p900001.sol` now contains only one OFE header (`'Road' ...`) and `1 0` on the `ntemp` line.

- Observation: Roads targeted hillslope output files were initially staged as symlinks to baseline `wepp/output/H*.pass.dat`; combining into those symlink paths mutated baseline pass files and obscured failure diagnosis.
  Evidence: `ls -l /wc1/runs/cl/clogging-starch/wepp/roads/output/H1.pass.dat` showed symlink-to-baseline before fix; runtime logs now capture `output_was_symlink=true` and unlink before combine.

- Observation: `wepppyo3` pass combiner writer must follow WEPP Fortran `format 1000` grouping (`...10(e11.5,1x),2(5x,5(e11.5,1x))...`) and EVENT continuation behavior; generic space-delimited scientific output still triggers `forrtl severe(64)`.
  Evidence: `/workdir/wepp-forest/src/wshpas.for` read contract and fixture failures until `wepp_interchange/src/hill_pass_combine.rs` writer was updated to fixed-width grouped fields plus continuation line.

- Observation: Roads upload accepted server-file JSON payloads (`{"geojson_path": ...}`), allowing ingestion from arbitrary host paths rather than browser-uploaded files.
  Evidence: `wepppy/weppcloud/routes/nodb_api/roads_bp.py` route contract prior to review and `tests/weppcloud/routes/test_roads_bp.py` pre-fix behavior.

- Observation: Roads enqueue surfaces allowed duplicate concurrent prepare/run submissions (no submit/runtime lock + active-job conflict check), producing race-prone overlapping jobs.
  Evidence: enqueue flow in `wepppy/weppcloud/routes/nodb_api/roads_bp.py`, `wepppy/microservices/rq_engine/roads_routes.py`, and missing lock enforcement in `wepppy/rq/roads_rq.py` prior to review.

- Observation: `NO EVENT` rows in pass combiner were zeroing groundwater fields (`gwbfv`, `gwdsv`) instead of summing contributors, and source/base calendar/header mismatches were not validated.
  Evidence: `wepp_interchange/src/hill_pass_combine.rs` merge logic/tests before fix; review hardening added correctness checks and rejection tests.

## Decision Log


- Decision: Keep Roads enable/disable on canonical `/tasks/set_mod` instead of creating a custom enable endpoint.
  Rationale: Preserves existing module lifecycle contract and dependency guard behavior.
  Date/Author: 2026-03-23 / Codex.

- Decision: Enforce Roads as WBT-only at enable time with explicit error response on non-WBT runs.
  Rationale: Required by Roads specification and aligned with existing backend-gated module patterns.
  Date/Author: 2026-03-23 / Codex.

- Decision: Implement pass combiner in `/workdir/wepppyo3/wepp_interchange` (not a Python fallback path) and call it from WEPPpy.
  Rationale: Matches performance/ownership standards and Roads spec guidance.
  Date/Author: 2026-03-23 / Codex.

- Decision: Use `wepp/roads/{segments,runs,output}` for Roads artifacts instead of `_pups/roads/*`.
  Rationale: Roads is an in-run module workflow, and `wepp/roads/output` enables a single `wepp/roads/runs/pw0.run` contract for both untouched and combined hillslope pass files.
  Date/Author: 2026-03-23 / Codex.

- Decision: Add a minimal `controls/roads_pure.htm` now (Milestone 2) so run-page dynamic mod toggling remains valid while API/queue routes are implemented in Milestone 3.
  Rationale: Prevents `/view/mod/roads` and mod section rendering from failing when Roads is enabled via header Mods before full control wiring lands.
  Date/Author: 2026-03-23 / Codex.

- Decision: Use relative pass roots (`../output/H<wepp_id>`) when building Roads watershed reruns.
  Rationale: Prevents WEPP pass-path truncation failures encountered with long absolute paths in `pw0.run`.
  Date/Author: 2026-03-23 / Codex.

- Decision: Supersede provisional baseline-pass cloning and execute mapped segments as real single-OFE WEPP hillslope runs.
  Rationale: Roads specification requires one-OFE segment execution (road-only soil/man/slope assets), and real runs provide observable per-segment execution records rather than placeholder artifacts.
  Date/Author: 2026-03-24 / Codex.

- Decision: Resolve prepare-stage rasters explicitly from `Watershed` (`relief`, `netful`, `subwta`) and fail fast when any required raster is missing.
  Rationale: Prevents silent fallback to non-WBT adjacency detection and makes lowpoint mapping deterministic/observable.
  Date/Author: 2026-03-24 / Codex.

- Decision: Persist lowpoint decision diagnostics per segment (`_roads_lowpoint_decision`, channel/hillslope search metadata) and roll up decision counts in `roads.inslope.summary.json`.
  Rationale: Satisfies Roads observability requirements and provides operator-visible reasons for mapped vs skipped segment candidates.
  Date/Author: 2026-03-24 / Codex.

- Decision: Persist failed run summaries (`last_run_summary.status=failed`, `failed_stage=watershed_rerun`) before re-raising watershed rerun exceptions.
  Rationale: Keeps query/report consumers observable under failure while preserving explicit exception behavior and canonical failed-status transitions.
  Date/Author: 2026-03-24 / Codex.

- Decision: Keep `roads.log` append-only and log lifecycle/config/upload/query/run boundaries (instead of truncating per stage) so all controller actions remain observable in one timeline.
  Rationale: Operators need full request-to-run auditability; stage resets hid upstream actions and made diagnosis brittle.
  Date/Author: 2026-03-24 / Codex.

- Decision: Unlink targeted staged hillslope outputs before pass combine and emit WEPP-fixed-format EVENT/SUBEVENT/NO EVENT output from `wepp_interchange`.
  Rationale: Prevents baseline pass mutation through symlink-following writes and satisfies Fortran fixed-format parsing required by watershed reruns.
  Date/Author: 2026-03-24 / Codex.

- Decision: Restrict Roads upload to multipart file ingest only and reject path-based JSON upload modes.
  Rationale: Eliminates host-path ingestion risk and aligns Roads UI/API with existing NoDb upload controller patterns.
  Date/Author: 2026-03-24 / Codex.

- Decision: Enforce Roads queue single-flight semantics across submit and runtime boundaries, returning `409` conflicts for active/busy Roads jobs.
  Rationale: Prevents overlapping prepare/run jobs from mutating shared `roads.nodb` and staged artifacts concurrently; aligns with queue-governance expectations.
  Date/Author: 2026-03-24 / Codex.

- Decision: Treat stale prepare state as a hard run precondition failure (`roads_params_signature`/upload checksum/input CRS mismatch) and fail-fast on segment execution failures.
  Rationale: Prevents running with stale prepared artifacts and preserves explicit failure semantics/observability instead of silently skipping failed segments.
  Date/Author: 2026-03-24 / Codex.

## Outcomes & Retrospective


Milestones 1-5 remain complete, execution-fidelity closeout remains in place, and the componentized comprehensive review pass has now closed all identified high/medium findings. Roads now enforces upload/file contracts and strict param/state freshness, blocks concurrent prepare/run submissions via queue single-flight checks, correlates UI completion to active Roads jobs, and validates combiner source headers/calendars while preserving groundwater aggregation correctness for `NO EVENT` rows. Runtime execution continues to use real single-OFE mapped segments (road-only soil OFE files), append-only `roads.log`, and `wepp/roads/*` artifact outputs.

Post-review validation passes: targeted Roads Python/JS/Rust suites, `cargo test -p wepp_interchange_rust -- --nocapture`, `wctl check-rq-graph` (after regeneration), route inventory/checklist guards, npm lint/test, preflight checklist tests, broad-exception changed-file enforcement, and full `wctl run-pytest tests --maxfail=1` (`2499 passed, 34 skipped`). The prior watershed runtime blocker (`forrtl: severe (64)` on `H1.pass.dat`) remains resolved by the pass-writer and staging fixes; fixture reruns on `clogging-starch` complete successfully.

## Context and Orientation


`NoDb` means run state is persisted as JSON-like controller files under the run working directory (for Roads, `roads.nodb`). A “mod” is an optional run capability toggled through `/tasks/set_mod` and rendered dynamically on the run page. “WBT backend” refers to WhiteboxTools delineation and is checked through `watershed.delineation_backend_is_wbt`. A “Topaz ID” is a watershed cell identifier from `subwta` rasters; channel IDs end with `4` and hillslope IDs end with `1`, `2`, or `3`. A “PASS file” is WEPP hillslope routing output (`H*.pass.dat`) used to drive watershed routing.

The current codebase already has Roads monotonic segmentation utilities in `wepppy/nodb/mods/roads/monotonic_segments.py`, but no `Roads(NoDbBase)` controller, no Roads blueprint, no Roads task enum/preflight key, and no run-page/header integration for Roads. The run page currently includes Debris Flow and then DSS/PATH sections, so Roads placement must be inserted immediately after Debris Flow in both TOC and content stack. rq-engine currently has module-specific async route patterns (for example `run-debris-flow`, `build-rusle`) that Roads should follow with two jobs: prepare and run.

## Plan of Work


Milestone 1 implements the Roads controller and segment-preparation substrate. Create `wepppy/nodb/mods/roads/roads.py` with `class Roads(NoDbBase)` and the state contract from the Roads specification (`enabled`, upload metadata, params, summaries, lifecycle status, errors, timestamps). Export the controller in `wepppy/nodb/mods/roads/__init__.py`. Extend `monotonic_segments.py` so inslope eligibility includes both `Inslope_bd` and `Inslope_rd`, add deterministic `topaz_id_hill_lowpoint` selection, and guarantee invariants required by spec. Update/add tests under `tests/nodb/mods/` for inslope parity, deterministic tie-breaks, and suffix invariants.

Milestone 2 wires run registration, UI placement, and preflight/task semantics. Update `wepppy/weppcloud/routes/nodb_api/project_bp.py` to include `roads` in `MOD_DISPLAY_NAMES` and enforce Roads WBT guard in `set_project_mod_state` with explicit message when blocked. Add Roads to header dropdown in `wepppy/weppcloud/templates/header/_run_header_fixed.htm`. Add Roads to run-page registries in `wepppy/weppcloud/routes/run_0/run_0_bp.py` and render it immediately after Debris Flow in `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`. Keep dynamic rendering consistent by adding Roads flags and bootstrap entries in `wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2` and `wepppy/weppcloud/controllers_js/project.js` (`MOD_BOOTSTRAP_MAP`). Add `TaskEnum.run_roads` with label `Run Roads` and emoji `🚗` in `wepppy/nodb/redis_prep.py`, wire `#roads` in `TOC_TASK_ANCHOR_TO_TASK`, and add selector mapping in `wepppy/weppcloud/static/js/preflight.js`. In `services/preflight2/internal/checklist/checklist.go`, add `check["roads"] = safeGT(prep["timestamps:run_roads"], runWepp)` so Roads can only complete after WEPP completion; add corresponding Go tests in `checklist_test.go`.

Milestone 3 adds Roads web and queue surfaces. Create `wepppy/weppcloud/routes/nodb_api/roads_bp.py` with route family from spec (`upload_geojson`, `set_params`, `prepare_segments`, `run`, config/status/results/query/summary/report). Register the blueprint in `wepppy/weppcloud/routes/nodb_api/__init__.py`, `wepppy/weppcloud/routes/__init__.py`, and `wepppy/weppcloud/_blueprints_context.py`. Add rq-engine Roads routes in `wepppy/microservices/rq_engine/roads_routes.py` and include router registration in `wepppy/microservices/rq_engine/__init__.py`. Implement queue workers in `wepppy/rq/roads_rq.py` with two entrypoints (`run_roads_prepare_rq`, `run_roads_rq`) and status/timestamp updates in `roads.nodb` and RedisPrep.

Milestone 4 implements run assembly and pass injection. Add Roads single-OFE build logic in `Roads.run_roads_wepp()` to generate per-segment slope/soil/management/run files under `wepp/roads/`, execute segment runs, and map segments to hillslope WEPP IDs via `WeppTopTranslator.top2wepp`. Implement phase-1 pass combiner in `/workdir/wepppyo3/wepp_interchange` (new combiner module + lib exports + Python binding) following spec math for EVENT/SUBEVENT/NO EVENT merge behavior and hydrograph-shape rules. Stage pass files in `wepp/roads/output` (baseline for untouched hillslopes, combined for mapped hillslopes) and build watershed reruns from `wepp/roads/runs/pw0.run`.

Milestone 5 closes governance and validation. Update `wepppy/rq/job-dependencies-catalog.md` with Roads enqueue edges, run `wctl check-rq-graph`, and regenerate graph with `python tools/check_rq_dependency_graph.py --write` if needed. Because rq-engine routes are added, sync `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md` and `route_contract_checklist_20260208.md` to keep route-freeze tests green. Add targeted test modules for Roads blueprint/rq-engine/RQ and run fixture-backed e2e validation on `clogging-starch`.

### File-Level Edit Map


Repository-local edits (all under `/workdir/wepppy` unless noted):

- `wepppy/nodb/mods/roads/roads.py` (new)
- `wepppy/nodb/mods/roads/__init__.py`
- `wepppy/nodb/mods/roads/monotonic_segments.py`
- `wepppy/weppcloud/routes/nodb_api/project_bp.py`
- `wepppy/weppcloud/templates/header/_run_header_fixed.htm`
- `wepppy/weppcloud/routes/run_0/run_0_bp.py`
- `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`
- `wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2`
- `wepppy/weppcloud/controllers_js/project.js`
- `wepppy/weppcloud/static/js/preflight.js`
- `wepppy/weppcloud/routes/nodb_api/roads_bp.py` (new)
- `wepppy/weppcloud/routes/nodb_api/__init__.py`
- `wepppy/weppcloud/routes/__init__.py`
- `wepppy/weppcloud/_blueprints_context.py`
- `wepppy/weppcloud/templates/controls/roads_pure.htm` (new)
- `wepppy/weppcloud/templates/reports/roads/summary.htm` (new)
- `wepppy/microservices/rq_engine/roads_routes.py` (new)
- `wepppy/microservices/rq_engine/__init__.py`
- `wepppy/rq/roads_rq.py` (new)
- `wepppy/rq/job-dependencies-catalog.md`
- `wepppy/nodb/redis_prep.py`
- `services/preflight2/internal/checklist/checklist.go`
- `services/preflight2/internal/checklist/checklist_test.go`
- `tests/nodb/mods/test_roads_monotonic_segments.py`
- `tests/nodb/mods/test_roads_controller.py` (new)
- `tests/weppcloud/routes/test_project_bp.py`
- `tests/weppcloud/routes/test_pure_controls_render.py`
- `tests/weppcloud/routes/test_run_0_openet_admin_gate.py` (or new run_0 Roads-specific test module)
- `tests/weppcloud/routes/test_roads_bp.py` (new)
- `tests/microservices/test_rq_engine_roads_routes.py` (new)
- `tests/rq/test_roads_rq.py` (new)
- `wepppy/weppcloud/static-src/tests/smoke/mods-menu.spec.js`
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

Cross-repo edits for pass combiner (`/workdir/wepppyo3`):

- `wepp_interchange/src/lib.rs`
- `wepp_interchange/src/hill_pass_combine.rs` (new)
- `release/linux/py312/wepppyo3/wepp_interchange/__init__.py`
- corresponding `wepppyo3` tests for combiner behavior.

## Concrete Steps


Run all commands from `/workdir/wepppy` unless the command explicitly changes directory.

1. Confirm fixture prerequisites before code edits:

    cd /workdir/wepppy
    test -d /wc1/runs/cl/clogging-starch
    test -f /wc1/runs/cl/clogging-starch/roads/UM1_roads_info.geojson
    test -f /wc1/runs/cl/clogging-starch/dem/wbt/relief.tif
    ls /wc1/runs/cl/clogging-starch/wepp/output/H*.pass.dat | head

   Expected signal: `H*.pass.dat` paths are listed and no command fails.

2. Implement Milestone 1 and run focused utility/controller tests:

    wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1
    wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1

3. Implement Milestone 2 and validate registration/order behavior:

    wctl run-pytest tests/weppcloud/routes/test_project_bp.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py --maxfail=1

4. Implement Milestone 3 and validate Roads API/queue wiring:

    wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_roads_routes.py --maxfail=1
    wctl run-pytest tests/rq/test_roads_rq.py --maxfail=1

5. Implement Milestone 4 combiner and run interchange-facing tests (repo and `wepppyo3`):

    wctl run-pytest tests/rq/test_roads_rq.py --maxfail=1

    cd /workdir/wepppyo3
    cargo test -p wepp_interchange_rust -- --nocapture

   Return to `/workdir/wepppy` after `wepppyo3` tests.

6. Run queue and route governance checks:

    cd /workdir/wepppy
    wctl check-rq-graph
    python tools/check_endpoint_inventory.py
    python tools/check_route_contract_checklist.py

   If queue graph drift is reported:

    python tools/check_rq_dependency_graph.py --write
    wctl check-rq-graph

7. Fixture e2e verification on `clogging-starch` (manual + observable):

    - Open `http://localhost:8080/weppcloud/runs/clogging-starch/disturbed9002-wbt-mofe/`.
    - Confirm `Roads` appears in header Mods and run-page TOC directly after Debris Flow once enabled.
    - Enable Roads via Mods (internally `POST /tasks/set_mod`).
    - Upload `/wc1/runs/cl/clogging-starch/roads/UM1_roads_info.geojson`.
    - Run prepare, then `Run WEPPcloud Roads`.
    - Confirm new artifacts exist:

        /wc1/runs/cl/clogging-starch/wepp/roads/segments/roads.inslope.monotonic.geojson
        /wc1/runs/cl/clogging-starch/wepp/roads/segments/roads.inslope.low_points.geojson
        /wc1/runs/cl/clogging-starch/wepp/roads/output/
        /wc1/runs/cl/clogging-starch/wepp/roads/runs/pw0.run

    - Confirm preflight Roads item (🚗) only marks complete after WEPP completion timestamp.

8. Run required lint/doc and final sanity gates:

    wctl run-npm lint
    wctl run-npm test
    wctl run-preflight-tests ./internal/checklist
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260323_roads_nodb_inslope_e2e/package.md
    wctl doc-lint --path docs/work-packages/20260323_roads_nodb_inslope_e2e/tracker.md
    wctl doc-lint --path docs/work-packages/20260323_roads_nodb_inslope_e2e/prompts/active/roads_nodb_inslope_e2e_execplan.md

## Validation and Acceptance


Acceptance is complete when all of the following are true and observable:

- Roads can be enabled through `/tasks/set_mod` and returns a clear WBT-backend error on non-WBT runs.
- Header Mods menu contains Roads, and run-page TOC/content show Roads immediately after Debris Flow.
- `TaskEnum.run_roads` exists with label `Run Roads` and emoji `🚗`.
- Preflight checklist includes `roads` and only marks it complete when `timestamps:run_roads > runWepp`.
- Roads prepare/run jobs execute asynchronously and persist lifecycle status in `roads.nodb`.
- Segment outputs include both `topaz_id_chn_lowpoint` and `topaz_id_hill_lowpoint` with deterministic behavior and suffix invariants.
- Roads run writes pass artifacts under `wepp/roads/output` and executes watershed rerun from `wepp/roads/runs/pw0.run`.
- Queue governance and route-freeze checks pass without unresolved drift.
- Targeted tests plus `wctl run-pytest tests --maxfail=1` pass.

## Idempotence and Recovery


Most plan steps are repeatable. Re-running tests, queue checks, and doc lint is safe. Re-running Roads prepare/run for the same uploaded input should update summaries/timestamps and overwrite `wepp/roads/*` artifacts deterministically.

If implementation fails mid-way, rollback in this order:

1. Disable Roads mod through UI (or `POST /tasks/set_mod` with `{"mod":"roads","enabled":false}`).
2. Preserve failure evidence in package artifacts before cleanup.
3. Remove incomplete Roads artifacts under `/wc1/runs/cl/clogging-starch/wepp/roads/`.
4. Clear stale Roads timestamp/job metadata if necessary.
5. Re-run targeted Roads tests before retrying e2e.

If queue graph or route-freeze artifacts drift, regenerate and commit in the same change set so guards stay aligned.

## Artifacts and Notes


Store implementation evidence under `docs/work-packages/20260323_roads_nodb_inslope_e2e/artifacts/`:

- milestone validation logs
- `clogging-starch` e2e checklist and observed outcomes
- queue-graph and route-freeze drift/fix notes
- final validation summary for closeout.

## Interfaces and Dependencies


Required end-state interfaces:

- `wepppy/nodb/mods/roads/roads.py`:
  - `class Roads(NoDbBase)`
  - `filename = "roads.nodb"`
  - `set_enabled(enabled: bool) -> None`
  - `set_params(payload: dict) -> dict`
  - `set_uploaded_geojson(src_path: str) -> dict`
  - `prepare_segments() -> dict`
  - `run_roads_wepp() -> dict`
  - `query_status() -> dict`
  - `query_summary() -> dict`

- `wepppy/rq/roads_rq.py`:
  - `run_roads_prepare_rq(runid: str) -> dict`
  - `run_roads_rq(runid: str) -> dict`

- `wepppy/microservices/rq_engine/roads_routes.py`:
  - queue-backed POST endpoints for prepare/run stages following current rq-engine auth/response contracts.

- `wepppy/nodb/redis_prep.py`:
  - `TaskEnum.run_roads = "run_roads"`
  - `TaskEnum.label(TaskEnum.run_roads) == "Run Roads"`
  - `TaskEnum.emoji(TaskEnum.run_roads) == "🚗"`

- `services/preflight2/internal/checklist/checklist.go`:
  - checklist key `roads`
  - completion rule depends on WEPP completion timestamp.

- `/workdir/wepppyo3/wepp_interchange`:
  - `combine_hillslope_pass_files(base_pass, road_passes, out_pass, strategy="phase1")` exported to Python binding.

Dependencies that must remain contract-compatible:

- `docs/schemas/rq-response-contract.md`
- `docs/schemas/weppcloud-csrf-contract.md`
- `wepppy/rq/job-dependencies-catalog.md` + `wctl check-rq-graph`
- route freeze artifacts and `tests/microservices/test_rq_engine_openapi_contract.py`.

---

Revision note (2026-03-23 22:45Z): Initial ExecPlan authored for full Roads phase-1 implementation with fixture-default commands, explicit file map, governance checks, risks, rollback, and acceptance criteria.
Revision note (2026-03-23 23:35Z): Updated artifact-layout contract from `_pups/roads/*` to `wepp/roads/{segments,runs,output}` so the watershed run at `wepp/roads/runs/pw0.run` can reference a single pass directory (`wepp/roads/output`) for both untouched baseline and Roads-combined hillslopes.
Revision note (2026-03-24 00:30Z): Added post-closeout regression fixes for explicit WBT raster resolution in Roads prepare, lowpoint decision observability fields/counts, upload-first Roads UI wording alignment, and updated fixture validation outcomes (`mapped` segments now observed on `clogging-starch`).
Revision note (2026-03-24 01:25Z): Added Milestone 4 execution-fidelity closeout (real single-OFE segment runs and road-only soil OFE outputs), failed-run summary persistence for watershed rerun errors, and refreshed full validation outcomes (`2491 passed, 34 skipped`).
Revision note (2026-03-24 01:29Z): Refreshed remaining ExecPlan validation gates (npm, preflight checklist, route governance guards, broad-exception guard, and doc lint) after final Roads fidelity/observability changes.
Revision note (2026-04-10 16:40Z): Added closeout rollback validation outcomes and archived ExecPlan from `prompts/active/` to `prompts/completed/`.
