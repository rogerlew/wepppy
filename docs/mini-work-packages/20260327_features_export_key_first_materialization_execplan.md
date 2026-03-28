# Features Export WP-8 Key-First Carrier Materialization Rewrite

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md` and must be maintained in accordance with that template.

## Purpose / Big Picture

This work package replaces the current geometry-first merge behavior in `features_export` with a key-first DuckDB materialization path that is correct, maintainable, and fast. After this plan, default baseline exports should produce exactly two spatial carrier layers (`subcatchments`, `channels`) with carrier-grain feature counts, and should complete in seconds on small watersheds rather than minutes.

The user-visible outcome is straightforward: selected datasets are merged by canonical ids into one table per carrier/scope/context, geometry is attached one time at the end, and resulting row counts match expected carrier entities (for example, `66` subcatchments and `27` channels on `clogging-starch/disturbed9002-wbt-mofe`).

## Progress

- [x] (2026-03-28 23:42Z) Implemented temporal-wide carrier materialization for `event` and `yearly` modes via new collaborator `wepppy/nodb/mods/features_export/temporal_wide_materializer.py`; event/yearly outputs now keep carrier geometry normalized and pivot temporal tokens into measure column names.
- [x] (2026-03-28 23:42Z) Fixed geometry-key mismatch for `wepp_id` layers by prioritizing layer candidate keys over carrier defaults in `join_planner.resolve_geometry_key` (`WeppID` now selected over `TopazID` when contracts require it).
- [x] (2026-03-28 23:42Z) Replayed operator payload shape for `wepp.interchange.hill_wat` event export and verified normalized output on `/wc1/runs/cl/clogging-starch`:
  - manifest: `/wc1/runs/cl/clogging-starch/export/features/jobs/debug-wide-hill-wat-20260328d/manifest.json`
  - artifact: `/wc1/runs/cl/clogging-starch/export/features/artifacts/ffde6721cfde4869ad4475b87f97890f/features_export.gpkg`
  - layer `clogging-starch-sbs_map-subcatchments`: `row_count=66`, `feature_count=66`
  - temporal wide columns present: `p_2015_01_15_mm`, `p_2015_01_16_mm`, `q_2015_01_15_mm`, `q_2015_01_16_mm`, plus identity columns.
- [x] (2026-03-28 23:42Z) Bumped export cache/version markers to invalidate stale long-format artifacts:
  - cache marker: `features-export-wp12-temporal-wide-v1`
  - manifest generator version: `features-export-wp12-temporal-wide`
- [x] (2026-03-28 23:42Z) Re-ran required validation gates after temporal-wide + key-resolution fixes:
  - `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1` -> `75 passed`
  - `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1` -> `4 passed`
  - `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1` -> `10 passed`
  - `wctl run-npm test -- features_export` -> `14 passed`
- [x] (2026-03-27 23:40Z) Confirmed current regression behavior and root cause from live artifacts/job manifests (`391,930` subcatchment rows and `35,292` channel rows from multiplicative key joins).
- [x] (2026-03-27 23:40Z) Updated `wepppy/nodb/mods/features_export/specification.md` with the normative key-first/geometry-last contract and explicit no-feature-flag rollout stance.
- [x] (2026-03-27 23:40Z) Authored this WP-8 ExecPlan with concrete milestones, file targets, and acceptance checks.
- [x] (2026-03-28 03:18Z) Implemented collaborator split under `wepppy/nodb/mods/features_export/`: `discovery.py`, `join_planner.py`, `duckdb_materializer.py`, `geometry_carriers.py`, `manifest_builder.py`.
- [x] (2026-03-28 03:18Z) Replaced production hot path in `service.py` with key-first DuckDB carrier-core materialization + single geometry attach boundary; retained legacy helper path only for non-carrier passthrough layers.
- [x] (2026-03-28 03:22Z) Implemented canonical carrier geometry canonicalization (one row per key with deterministic dissolve for benign duplicate geometry rows).
- [x] (2026-03-28 03:23Z) Wired discovered source units through key-first path into manifest output metadata and kept discovery-driven UI/planner contracts intact.
- [x] (2026-03-28 03:29Z) Completed required validation gates and live run-path evidence capture (cold/warm runtimes + exact 2-layer `66/27` counts on `clogging-starch/disturbed9002-wbt-mofe`).
- [x] (2026-03-28 03:34Z) Added explicit WP-8 cardinality regression tests in `tests/nodb/mods/test_features_export_service.py` for conflicting duplicate keys (fail) and benign duplicate keys (deterministic collapse).
- [x] (2026-03-28 03:35Z) Final required command outcomes:
  - `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1` -> `53 passed`
  - `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1` -> `4 passed`
  - `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1` -> `10 passed`
  - `wctl run-npm test -- features_export` -> `12 passed`
  - `wctl doc-lint --path wepppy/nodb/mods/features_export/specification.md` -> pass
  - `wctl doc-lint --path docs/mini-work-packages/20260327_features_export_key_first_materialization_execplan.md` -> pass

## Surprises & Discoveries

- Observation: `H.wat.parquet` carries OFE-level daily rows (`ofe_id`) so naive event pivot by `{wepp_id,date}` can still produce conflicting duplicate slices.
  Evidence: direct DuckDB inspection on `/wc1/runs/cl/clogging-starch/wepp/output/interchange/H.wat.parquet` showed duplicate `{wepp_id,year,month,day_of_month}` slices with varying `Q` across OFEs.
- Observation: Selecting terminal OFE (`max(ofe_id)`) before event pivot resolves deterministic hillslope slice representative rows and preserves one-row-per-feature output after wide pivot.
  Evidence: `debug-wide-hill-wat-20260328d` artifact contains `66` rows/`66` features with fully populated date-suffixed measure columns.
- Observation: Carrier-first geometry key ordering caused sparse/null-heavy event exports for `wepp_id` datasets when both `TopazID` and `WeppID` existed in geometry.
  Evidence: manifests for failing jobs reported `carrier_key_column=TopazID` for `wepp.interchange.hill_wat`; after precedence fix, event export normalized to expected feature counts.
- Observation: Existing cache entries can preserve pre-fix long-format artifacts even after materialization logic changes.
  Evidence: replaying the original payload hit prior artifact `19f2cc28078c415c8e6410c29c810ed9` until version markers were bumped.
- Observation: Current row explosion is deterministic many-to-many multiplication, not random instability.
  Evidence: For `subcatchments.WGS.geojson`, per-key multiplicities `n_i` satisfy `sum(n_i^4) = 391,930`, which exactly matches broken export row counts.
- Observation: Source WEPP metric tables already exist at expected carrier grain (`66` hillslope rows, `27` channel rows), so blowup is introduced by merge strategy, not source volume.
  Evidence: Direct counts from `/wc1/runs/cl/clogging-starch/wepp/output/interchange/loss_pw0.hill.parquet` and `loss_pw0.chn.parquet`.
- Observation: Runtime pain is dominated by writing oversized geometry containers after cardinality explosion.
  Evidence: `features_export.gpkg` around `311 MB` with multi-minute to 20+ minute runtimes on small watershed requests.
- Observation: Key-first carrier-core union without geometry-key filtering can still overproduce non-spatial rows (`120`/`52`) even after duplicate-safe joins.
  Evidence: Initial WP-8 cold run produced expected feature counts (`66`/`27`) but larger row counts before intersecting carrier-core keys with canonical geometry keys.
- Observation: Intersecting carrier-core keys with canonical geometry keys restored strict carrier-grain row counts while preserving selected measures.
  Evidence: Final run-path evidence on `manual-wp8-cold-v2-*` manifests and artifacts shows `row_count == feature_count` for both layers (`66` and `27`).
- Observation: Carrier cardinality safety needed explicit test cases because previous service helper tests still encoded permissive fanout behavior.
  Evidence: Added focused regression tests for `materialize_layer_attributes` duplicate-key handling and revalidated full required gate (`53` python tests).

## Decision Log

- Decision: For `event`/`yearly` carrier layers, materialize temporal outputs as wide columns at carrier geometry grain instead of long-row geometry duplication.
  Rationale: Keeps export layers normalized to canonical feature counts and makes downstream GIS/table consumption tractable for temporal comparisons.
  Date/Author: 2026-03-28 / Codex
- Decision: Resolve event OFE duplicates by selecting terminal OFE (`max(ofe_id)`) per `{join_key, temporal_token}` before pivoting.
  Rationale: WEPP hillslope interchange daily tables are OFE-grained; selecting a deterministic outlet representative resolves one-to-many slices without silent many-to-many fanout.
  Date/Author: 2026-03-28 / Codex
- Decision: Prioritize layer-derived join candidates when resolving canonical geometry key.
  Rationale: Contract-defined source keys (`wepp_id`) must override carrier defaults (`TopazID`) to avoid null-heavy mismatches and preserve deterministic key alignment.
  Date/Author: 2026-03-28 / Codex
- Decision: Bump export cache marker and manifest generator version for temporal-wide rollout.
  Rationale: Prevent cache-hit reuse of stale long-format artifacts produced before event/yearly wide-materialization contract changes.
  Date/Author: 2026-03-28 / Codex
- Decision: Make key-first/geometry-last materialization the only production path for WP-8 (no temporary flag).
  Rationale: This feature has not shipped in acceptable form and a dual-path rollout would preserve complexity and failure risk without user value.
  Date/Author: 2026-03-27 / Codex
- Decision: Enforce strict carrier-key cardinality invariants and fail explicit many-to-many hot-path joins.
  Rationale: Silent row multiplication is both correctness and performance failure; explicit failure is easier to diagnose and safer than degraded outputs.
  Date/Author: 2026-03-27 / Codex
- Decision: Refactor `service.py` into clear collaborators before deep optimization tweaks.
  Rationale: Maintainability is part of this request; decomposition lowers future thrash when schemas evolve downstream.
  Date/Author: 2026-03-27 / Codex
- Decision: Treat canonical carrier geometry keyset as the authoritative final row domain for spatial outputs.
  Rationale: Carrier-core union can include keys without geometry; final spatial layers must match canonical carrier entities and expected feature counts.
  Date/Author: 2026-03-28 / Codex
- Decision: Fail required-source key resolution and conflicting duplicate-key payloads as explicit `materialization_error`.
  Rationale: Silent source skipping or fanout masks schema drift and reintroduces correctness/performance regression risk.
  Date/Author: 2026-03-28 / Codex
- Decision: Bump cache marker to `features-export-wp11-key-first-v2`.
  Rationale: Force regeneration after key-first rollout and geometry-domain tightening so stale pre-WP-8 artifacts are never served.
  Date/Author: 2026-03-28 / Codex

## Outcomes & Retrospective

WP-8 is implemented and validated end-to-end.

Delivered outcomes:
- Production `features_export` hot path now materializes key-first carrier cores in DuckDB and attaches geometry exactly once from canonical carrier geometry.
- Temporal `event` and `yearly` outputs now reshape to wide measure columns so exported geometry remains at canonical carrier feature counts.
- Event-mode OFE-grained daily sources now resolve deterministic per-slice representatives (`max(ofe_id)`) before wide pivoting.
- Explicit cardinality guards now fail unresolved duplicate-key conflicts as `materialization_error` instead of allowing Cartesian growth.
- Canonical carrier geometry is reduced to one row per key (deterministic dissolve on benign duplicate geometry rows), then used to bound final spatial row sets.
- Default baseline export on `clogging-starch/disturbed9002-wbt-mofe` now emits exactly two layers with carrier-grain counts:
  - `clogging-starch-sbs_map-subcatchments`: `66`
  - `clogging-starch-chan_map-channels`: `27`
- Required validation gates all passed after implementation (pytest route/microservice/nodb + Jest + doc lint).
- Runtime evidence on the target run is materially improved and cache behavior is correct:
  - cold cache: `4.017s` (`cache_hit=false`)
  - warm cache: `0.443s` (`cache_hit=true`)

Residual follow-on:
- Non-carrier passthrough layers still rely on the existing legacy helper path; carrier layers (the hot path and default baseline) are fully key-first/geometry-last.

## Context and Orientation

`features_export` currently spans planner + service + writer layers under `wepppy/nodb/mods/features_export`, with UI payload integration through `wepppy/weppcloud/routes/run_0/run_0_bp.py` and client behavior in `wepppy/weppcloud/controllers_js/features_export.js`. Existing service behavior materializes geometry-backed frames per dataset, then merges those frames for consolidated carriers. Repeated joins across duplicated keys in geometry sources produce multiplicative row growth and very slow geopackage writes.

For WP-8, "carrier" means the output geometry family (`sbs_map-subcatchments` or `chan_map-channels`) for a concrete tuple `{context, selector_id, scope}`. "Carrier core table" means the DuckDB-built attribute table keyed by canonical ids before geometry is attached.

## Plan of Work

Milestone 1 establishes strict contracts and module boundaries. Update `wepppy/nodb/mods/features_export/contracts.py` and related planner/service contracts so carrier-key expectations, join cardinality policy, and geometry attachment semantics are explicit and testable. Add collaborator modules:

- `wepppy/nodb/mods/features_export/discovery.py`
- `wepppy/nodb/mods/features_export/join_planner.py`
- `wepppy/nodb/mods/features_export/duckdb_materializer.py`
- `wepppy/nodb/mods/features_export/geometry_carriers.py`
- `wepppy/nodb/mods/features_export/manifest_builder.py`

Milestone 2 replaces the hot path in `wepppy/nodb/mods/features_export/service.py`. Build one DuckDB carrier core table per carrier tuple from discovered source schemas and resolved temporal/column selectors. Ensure each source contributes at most one row per effective carrier key before joining. Detect unresolved many-to-many joins and fail with canonical `materialization_error`.

Milestone 3 implements canonical carrier geometry attach. Build deterministic one-row-per-key geometry tables for subcatchments/channels and join these once to carrier core tables. Remove geometry-first repeated-merge behavior from production path.

Milestone 4 hardens discovery-driven schema metadata for UI and request validation. Ensure labels/descriptions/units come from discovered parquet metadata and source docs where available, and remain robust as downstream schemas change.

Milestone 5 finalizes regression/performance validation and evidence. Include run-path checks on `/wc1/runs/cl/clogging-starch` confirming exactly two layers with `66/27` features and materially reduced runtime.

## Concrete Steps

From `/workdir/wepppy`:

1. Implement collaborator modules and contract wiring:
   - edit/add files under `wepppy/nodb/mods/features_export/` listed in Plan of Work.
2. Replace service merge path:
   - edit `wepppy/nodb/mods/features_export/service.py` to call key-first materializer and single geometry-attach boundary.
3. Update manifest/planner/UI payload integration:
   - edit `wepppy/nodb/mods/features_export/manifest.py`, `wepppy/weppcloud/routes/run_0/run_0_bp.py`, and `wepppy/weppcloud/controllers_js/features_export.js` as needed.
4. Add/expand tests:
   - `tests/nodb/mods/test_features_export_planner.py`
   - `tests/nodb/mods/test_features_export_service.py`
   - `tests/nodb/mods/test_features_export_exporters.py`
   - `tests/microservices/test_rq_engine_features_export_routes.py`
   - `tests/weppcloud/routes/test_pure_controls_render.py`
   - `tests/weppcloud/routes/test_run_0_openet_admin_gate.py`
   - `wepppy/weppcloud/controllers_js/__tests__/features_export.test.js`
5. Run validation gates:
   - `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`
   - `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1`
   - `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1`
   - `wctl run-npm test -- features_export`
6. Run run-path acceptance checks:
   - trigger default baseline features export on `clogging-starch/disturbed9002-wbt-mofe`.
   - verify manifest has exactly two layers (`*-sbs_map-subcatchments`, `*-chan_map-channels`).
   - verify feature counts `66` and `27`.
   - record end-to-end runtime (cold and warm cache).

## Validation and Acceptance

WP-8 is accepted when all statements below are true:

- Default baseline export path is key-first and geometry-last with no feature flag path split.
- Export layer count for baseline defaults is exactly two carriers (`subcatchments`, `channels`).
- Carrier row/feature counts match expected entity counts on `clogging-starch/disturbed9002-wbt-mofe`: `66` subcatchments and `27` channels.
- Multiplicative row growth regressions are prevented by explicit cardinality enforcement tests.
- Discovery-driven schema metadata remains functional in UI and column-selection contracts.
- Required test and npm commands in Concrete Steps pass.
- Runtime on the small-watershed default export is materially reduced (target: low-seconds cold, near-instant warm cache) and evidence is documented in this plan.

## Idempotence and Recovery

All edits are additive or local refactors and can be reapplied safely on a clean branch. If an intermediate refactor breaks service behavior, keep collaborator interfaces stable and restore service call sites incrementally while running focused tests after each milestone. If run-path validation fails, preserve failing manifest/artifact ids in this file before retrying so regressions remain reproducible.

## Artifacts and Notes

Evidence to capture during implementation:

- Before/after manifest snippets showing layer ids and feature counts.
- Before/after runtime measurements for `clogging-starch/disturbed9002-wbt-mofe`.
- Test command outputs for all required validation gates.
- Any discovered key-cardinality edge cases and the chosen handling rule.

Captured WP-8 evidence:
- Cold run (`cache_hit=false`, `4.017s`):
  - job: `manual-wp8-cold-v2-20260328032436983011`
  - manifest: `/wc1/runs/cl/clogging-starch/export/features/jobs/manual-wp8-cold-v2-20260328032436983011/manifest.json`
  - artifact: `/wc1/runs/cl/clogging-starch/export/features/artifacts/fc619cb38cd24db6a4a845adbb1a641d/features_export.gpkg`
  - layers:
    - `clogging-starch-sbs_map-subcatchments` row/feature count `66`
    - `clogging-starch-chan_map-channels` row/feature count `27`
- Warm run (`cache_hit=true`, `0.443s`):
  - job: `manual-wp8-warm-v2-20260328032441217614`
  - manifest: `/wc1/runs/cl/clogging-starch/export/features/jobs/manual-wp8-warm-v2-20260328032441217614/manifest.json`
  - artifact reused: `/wc1/runs/cl/clogging-starch/export/features/artifacts/fc619cb38cd24db6a4a845adbb1a641d/features_export.gpkg`

## Interfaces and Dependencies

No new third-party dependency is planned. DuckDB is the required merge engine for carrier core assembly. Interfaces must remain explicit and stable:

- planner/service contract must carry resolved carrier tuple metadata (`context`, `selector_id`, `scope`, `carrier`, `effective_join_key`).
- materializer output must expose deterministic column mapping and key cardinality diagnostics for manifest reporting.
- geometry carrier module must return one geometry row per effective key.
- UI discovery payload must include discovered `label`, `description`, `display_unit`, and required-column lock metadata.

## Revision Notes

- 2026-03-27 (Codex): Created WP-8 ExecPlan after identifying deterministic many-to-many row explosion in current WP-7 merge path and after updating `specification.md` to require key-first/geometry-last materialization with no temporary feature flag.
- 2026-03-28 (Codex): Implemented WP-8 key-first collaborators + service rewrite, enforced explicit cardinality guardrails, captured required validation evidence, and recorded run-path cold/warm results with final `66/27` carrier counts.
