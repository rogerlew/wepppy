# Tracker - Features Export Legacy Exports Cutover (Prep Details + Geopackage)

> Living document tracking progress, decisions, risks, and verification for the legacy export replacement cutover.

## Quick Status

**Started**: 2026-03-29  
**Current phase**: Complete (Phase 8 Closed)  
**Last updated**: 2026-03-29  
**Active ExecPlan**: `prompts/active/features_export_legacy_exports_cutover_execplan.md`  
**Next milestone**: None (package ready for archive/closeout)

## Task Board

### Ready / Backlog
- None.

### In Progress
- None.

### Blocked
- None.

### Done
- [x] Authored work-package scaffold (`package.md`, `tracker.md`, `prompts/active/*`) (2026-03-29).
- [x] Updated `wepppy/nodb/mods/features_export/specification.md` with new download-route, publication-registry, and packaging contracts (2026-03-29).
- [x] Phase 1 implemented: canonicalized features-export job download route to `/export/features/job/{job_id}/download` and updated route tests (2026-03-29).
- [x] Phase 2 implemented: publication registry (`export/features/published/index.json`) and published download resolution with stale checks (2026-03-29).
- [x] Phase 3 implemented: legacy rq-engine endpoints and post-run hooks rewired to features-export profile execution (`prep-wepp`, `prep-details`) (2026-03-29).
- [x] Phase 4 implemented: artifact bundles reduced to payload members + `manifest.json`; profile/provenance bundle members removed (2026-03-29).
- [x] Phase 5 complete: targeted automated test matrix executed and passing (2026-03-29).
- [x] Phase 6 complete: manual e2e parity/timing evidence captured on `clogging-starch` run and published registry resolved (2026-03-29).
- [x] Phase 7 complete: human approval gate artifact authored with explicit go/no-go checklist (2026-03-29).
- [x] Phase 8 complete: human GO executed, legacy modules removed, dead callsites cleaned, and final regressions passed (2026-03-29).

## Timeline

- **2026-03-29** - Package created to complete legacy prep/geopackage cutover into `features_export`.
- **2026-03-29** - Spec updated with canonical job/published download routes and publication registry contract.
- **2026-03-29** - Phase 1 route change landed in `rq_engine/export_routes.py` and corresponding microservice tests passed.

## Decisions

### 2026-03-29: Canonical job download route includes explicit `job` segment
**Context**: Existing `/export/features/{job_id}/download` path is ambiguous and should not remain as long-term contract.

**Options considered**:
1. Keep existing route and add aliases.
2. Replace with explicit route segment (`/export/features/job/{job_id}/download`).

**Decision**: Option 2.

**Impact**: Route semantics are clearer; clients avoid ambiguity between job and profile publication lookups.

---

### 2026-03-29: Published downloads are profile-scoped and registry-backed
**Context**: End users need stable, composable links while cache/artifact internals remain content-addressed.

**Options considered**:
1. Derive published links directly from cache hash/artifact id.
2. Add one publication registry as source of truth for profile IDs.

**Decision**: Option 2 (`export/features/published/index.json`).

**Impact**: Stable user-facing links, explicit profile ownership, and clean decoupling from cache key internals.

---

### 2026-03-29: Legacy module deletion requires explicit human approval gate
**Context**: Deleting `gpkg_export.py` and `prep_details.py` is high impact and irreversible without quick rollback.

**Options considered**:
1. Delete immediately after route rewiring.
2. Gate deletion on parity + e2e evidence and explicit maintainer approval.

**Decision**: Option 2.

**Impact**: Safer cutover with accountability and evidence-first retirement.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Legacy workflow behavior drift after cutover | High | Medium | Parity matrix + manual e2e proof before approval gate | Mitigated |
| Publication registry stale entries serve wrong artifact | High | Medium | Validate registry against current cache/dependency fingerprints on read | Mitigated |
| Existing callers still using compatibility download route | Medium | Medium | Search and migrate callsites, add focused route tests, remove compatibility only after proof | Mitigated |
| Legacy module import dependencies break removal | Medium | Medium | Run targeted import/callsite audit before deletion and patch dependent modules | Mitigated |

## Verification Checklist

### Automated validation
- [x] `wctl run-pytest tests/nodb/mods/test_features_export_service.py --maxfail=1`
- [x] `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py tests/microservices/test_rq_engine_export_routes.py --maxfail=1`
- [x] `wctl run-pytest tests/rq/test_features_export_rq.py tests/rq/test_wepp_rq_pipeline.py --maxfail=1`
- [x] `wctl run-pytest tests/rq/test_wepp_rq_stage_post.py --maxfail=1`
- [x] `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1`
- [x] `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1`
- [x] `wctl run-npm test -- features_export`

### Manual/e2e validation
- [x] Run `prep-wepp` and `prep-details` publication paths on representative run(s) and capture job IDs, artifact paths, and timings.
- [x] Validate publication resolution for each canonical profile through `resolve_published_artifact_path`.
- [x] Validate legacy entry points are rewired to `features_export` profile execution (route/service tests + code inspection).

### Approval and retirement
- [x] Human approval artifact recorded in `artifacts/` before deleting legacy modules.
- [x] `wepppy/export/gpkg_export.py` and `wepppy/export/prep_details.py` removed after approval.
- [x] Full regression command(s) executed and captured in tracker notes.

## Progress Notes

### 2026-03-29: Package authoring and spec alignment
**Agent/Contributor**: Codex

**Work completed**:
- Created work-package scaffold under `docs/work-packages/20260329_features_export_legacy_exports_cutover/`.
- Authored `package.md` scope and success criteria including explicit human approval gate.
- Updated features-export specification with:
  - canonical job download route (`/export/features/job/{job_id}/download`),
  - published profile download route (`/export/features/published/{profile}/download`),
  - publication registry source-of-truth (`export/features/published/index.json`),
  - artifact packaging simplification (payload + `manifest.json` only).

**Blockers encountered**:
- None.

**Next steps**:
- Implement Phase 2 backend publication registry + published download route and add route/service tests.

**Test results**:
- `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1` (pass; `14 passed`).
- `wctl run-pytest tests/rq/test_features_export_rq.py --maxfail=1` (pass; `3 passed`).

### 2026-03-29: Phase 2-7 implementation through human gate
**Agent/Contributor**: Codex

**Work completed**:
- Added publication registry contract implementation in `features_export.service`:
  - `export/features/published/index.json` load/write helpers,
  - canonical published profile normalization (`prep-wepp`, `prep-details`),
  - publish helper with cache/dependency fingerprint capture,
  - stale-publication validation on resolve.
- Added published download route:
  - `GET /api/runs/{runid}/{config}/export/features/published/{profile}/download`.
- Rewired legacy endpoints in rq-engine to features-export profile execution:
  - `/export/geopackage` -> `prep-wepp` (publish),
  - `/export/geodatabase` -> `prep-wepp` + `format=geodatabase` (non-published),
  - `/export/prep_details` -> `prep-details` (publish).
- Rewired completion hooks to features-export profile execution/publication:
  - `_post_gpkg_export_rq`, `_post_prep_details_rq`.
- Removed profile/provenance files from artifact bundles; bundle now contains payload members + `manifest.json`.
- Fixed profile contract bug discovered during e2e:
  - removed invalid `tabular` block from `profiles/post-wepp.yml` (`geopackage` profile must not carry tabular selectors).
- Authored gate artifacts:
  - `artifacts/code_review.md`
  - `artifacts/qa_review.md`
  - `artifacts/e2e_validation_summary.md`
  - `artifacts/human_approval_gate.md`

**E2E evidence highlights**:
- Representative run: `/wc1/runs/cl/clogging-starch` (`disturbed9002-wbt-mofe` config token).
- `prep-wepp`:
  - cold `4.082s` (`cache_hit=false`), warm `0.426s` (`cache_hit=true`),
  - artifact `export/features/artifacts/011569b7ad684960a50bdb9c4c458cd3/features_export.geopackage.zip`.
- `prep-details`:
  - cold `1.729s` (`cache_hit=false`), warm `0.447s` (`cache_hit=true`),
  - artifact `export/features/artifacts/3103f9e47b1146d1a60c66cb4275ad0b/features_export.parquet.zip`.
- Published registry path:
  - `/wc1/runs/cl/clogging-starch/export/features/published/index.json`
- Detailed evidence: `artifacts/e2e_validation_summary.md`.

**Blockers encountered**:
- None remaining. Human approval is now the only gate before Phase 8 deletion.

**Validation results**:
- `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py tests/microservices/test_rq_engine_export_routes.py --maxfail=1` (pass; `21 passed`).
- `wctl run-pytest tests/nodb/mods/test_features_export_service.py --maxfail=1` (pass; `56 passed`).
- `wctl run-pytest tests/rq/test_features_export_rq.py tests/rq/test_wepp_rq_pipeline.py --maxfail=1` (pass; `8 passed`).
- `wctl run-pytest tests/rq/test_wepp_rq_stage_post.py --maxfail=1` (pass; `9 passed`).
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1` (pass; `4 passed`).
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1` (pass; `10 passed`).
- `wctl run-npm test -- features_export` (pass; `22 passed`).

### 2026-03-30: Follow-up profile and run-results export UX adjustments
**Agent/Contributor**: Codex

**Work completed**:
- Switched canonical prep-details profile (`profiles/prep-details.yml`) from Parquet to CSV.
- Added published-profile aliases:
  - `prep-wepp-geodatabase` for published FileGDB downloads,
  - `prep-wepp-gpkg-gdb` as orchestration profile for one-run post-WEPP dual publication.
- Implemented service publish orchestration + geodatabase co-creation from produced GeoPackage payload (no second profile materialization run).
- Updated post-run completion hooks and sync run path to use `prep-wepp-gpkg-gdb` for post-WEPP completion exports.
- Updated rq-engine `/export/geodatabase` to prefer published `prep-wepp-geodatabase`; fallback path now triggers dual-profile publish once and then serves the published geodatabase artifact.
- Added WEPP Run Results "Exports" section links in `wepp_reports.htm`:
  - Prep Details
  - Post WEPP Geopackage Features Export
  - Post WEPP Geodatabase (ESRI) Features Export
  with link resolution via published registry relpaths and run-scoped download endpoint.

**Validation status**:
- Pending rerun after follow-up changes (service/microservice/wepp route/doc lint gates).

### 2026-03-30: Published download filename contract and run-results link routing
**Agent/Contributor**: Codex

**Work completed**:
- Updated published download naming contract to `<runid>.<canonical-profile>.<format>.zip` in rq-engine profile download route responses.
- Updated WEPP Run Results export links to point directly at published profile download routes:
  - `/rq-engine/api/runs/{runid}/{config}/export/features/published/prep-details/download`
  - `/rq-engine/api/runs/{runid}/{config}/export/features/published/prep-wepp/download`
  - `/rq-engine/api/runs/{runid}/{config}/export/features/published/prep-wepp-geodatabase/download`
- Added route-test coverage for canonical and alias profile filename normalization.

**Validation results**:
- `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1` (pass; `18 passed`).
- `wctl run-pytest tests/microservices/test_rq_engine_export_routes.py --maxfail=1` (pass; `6 passed`).
- `wctl run-pytest tests/weppcloud/routes/test_wepp_bp.py --maxfail=1` (pass; covered in combined run with features routes).

### 2026-03-29: Phase 8 GO execution and legacy module retirement
**Agent/Contributor**: Codex

**Work completed**:
- Executed approved destructive cleanup after maintainer GO:
  - deleted `wepppy/export/gpkg_export.py` and `wepppy/export/prep_details.py`,
  - deleted companion stubs `wepppy/export/gpkg_export.pyi` and `wepppy/export/prep_details.pyi`.
- Removed residual dead imports/callsites:
  - `wepppy/export/__init__.py`,
  - `wepppy/export/__init__.pyi`,
  - `wepppy/rq/wepp_rq.py`,
  - `wepppy/nodb/mods/ag_fields/ag_fields.py`.
- Confirmed no runtime code references to removed modules remain (docs-only references remain historical).

**Validation results**:
- `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py tests/microservices/test_rq_engine_export_routes.py tests/rq/test_wepp_rq_pipeline.py tests/rq/test_wepp_rq_stage_post.py --maxfail=1` (pass; `141 passed`).
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1` (pass; `4 passed`).
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1` (pass; `11 passed`).
- `wctl run-npm test -- features_export` (pass; `22 passed`).

**Closeout status**:
- Human gate transitioned from pending to GO executed in `artifacts/human_approval_gate.md`.
- Package is complete and ready for archive/closure.
