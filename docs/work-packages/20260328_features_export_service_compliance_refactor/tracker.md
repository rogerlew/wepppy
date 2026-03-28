# Tracker - Features Export Service Compliance Refactor

## Quick Status

**Started**: 2026-03-28  
**Current phase**: Complete (all phases closed)  
**Last updated**: 2026-03-28  
**Completed ExecPlan**: `prompts/completed/features_export_service_compliance_refactor_execplan.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Package scaffold and active ExecPlan created.
- [x] Phase 1 complete: extracted legacy source-materialization flow into collaborator module.
- [x] Phase 2 complete: slimmed `_materialize_export_payloads` by delegating carrier core materialization to collaborator.
- [x] Phase 3 complete: removed dead wrappers and unused helpers from `service.py`.
- [x] Phase 4 complete: added missing carrier strict-required tests and closed validation gates.

## Decisions
- 2026-03-28: Execute all four phases in one contiguous package to avoid partial-state drift.
- 2026-03-28: Reuse strict required-source policy from `discover_layer_sources` for legacy path to eliminate duplicated policy branches.

## Verification Checklist
- [x] `wctl run-pytest tests/nodb/mods/test_features_export_service.py -k "required_source or discover_layer_sources or materialization_error or ensure_join_key" --maxfail=1`
- [x] `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`
- [x] `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1`
- [x] `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1`
- [x] `wctl run-npm test -- features_export`
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- [x] `wctl doc-lint --path docs/work-packages/20260328_features_export_service_compliance_refactor/package.md`
- [x] `wctl doc-lint --path docs/work-packages/20260328_features_export_service_compliance_refactor/tracker.md`
- [x] `wctl doc-lint --path docs/work-packages/20260328_features_export_service_compliance_refactor/prompts/completed/features_export_service_compliance_refactor_execplan.md`

## Progress Notes

### 2026-03-28 - Implementation complete
- Added `wepppy/nodb/mods/features_export/legacy_source_materializer.py` and moved legacy source merge orchestration there.
- Added `wepppy/nodb/mods/features_export/carrier_layer_materializer.py` and moved carrier source discovery/materialization/projection there.
- Updated `wepppy/nodb/mods/features_export/discovery.py` with `skip_vector_relpath` support to align legacy strict-source behavior without duplicating policy code.
- Refactored `wepppy/nodb/mods/features_export/service.py`:
  - `_materialize_export_payloads` now dispatches to collaborator materializers;
  - `_build_layer_frame_from_sources` now uses `build_legacy_merged_frame`;
  - removed dead wrappers and unused parquet helpers.
- Extended `tests/nodb/mods/test_features_export_service.py` with:
  - `discover_layer_sources` required `file_missing` branch,
  - `discover_layer_sources` required `unsupported_source_kind` branch,
  - service-level carrier-path `MaterializationContractError -> FeaturesExportServiceError(materialization_error)` translation.

### 2026-03-28 - Run-path evidence
- Target run: `clogging-starch/disturbed9002-wbt-mofe`
- Cold job: `manual-wp-service-compliance-cold-20260328045609019671`
  - runtime: `3.378s`
  - cache_hit: `false`
  - artifact: `export/features/artifacts/6f6fddc846554054a01eebcad52f0f51/features_export.gpkg`
  - manifest: `export/features/jobs/manual-wp-service-compliance-cold-20260328045609019671/manifest.json`
- Warm job: `manual-wp-service-compliance-warm-20260328045612397503`
  - runtime: `0.374s`
  - cache_hit: `true`
  - artifact: same as cold
  - manifest: `export/features/jobs/manual-wp-service-compliance-warm-20260328045612397503/manifest.json`
- Artifact layers/counts:
  - `clogging_starch_chan_map_channels`: `27`
  - `clogging_starch_sbs_map_subcatchments`: `66`
