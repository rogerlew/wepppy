# Features Export Legacy Exports Cutover (Prep Details + Geopackage)

**Status**: Closed (2026-03-29)

## Overview
Replace legacy post-WEPP export surfaces (`prep_details`, `geopackage`/`geodatabase`) with `features_export` while keeping user workflows functional and linkable. The cutover introduces explicit profile-aware publication routing (`prep-wepp`, `prep-details`) and removes artifact-bundled profile/provenance payload clutter. Legacy module removal is gated by an explicit human approval checkpoint after parity and end-to-end validation evidence is captured.

## Objectives
- Route legacy Prep Details and GeoPackage export flows through `features_export` execution paths.
- Standardize artifact retrieval on `features_export` download endpoints:
  - `GET /rq-engine/api/runs/{runid}/{config}/export/features/job/{job_id}/download`
  - `GET /rq-engine/api/runs/{runid}/{config}/export/features/published/{profile}/download`
- Add `export/features/published/index.json` as source-of-truth registry for published profile downloads.
- Remove per-artifact profile/provenance bundling (`profile.yml`, `profiles/*.yml`, `README.md`) while preserving manifest evidence.
- Validate parity and operational usability with automated tests and manual e2e run-path checks.
- Remove legacy modules (`wepppy/export/gpkg_export.py`, `wepppy/export/prep_details.py`) only after explicit human approval.

## Scope
This package covers backend routing, service/publishing metadata, legacy-flow compatibility, validation, and final retirement of legacy export modules.

### Included
- rq-engine route contract changes for features-export job/published downloads.
- Publication registry implementation and lifecycle rules (`export/features/published/index.json`).
- Legacy export endpoint and post-WEPP completion-hook migration to `features_export` profiles.
- Artifact packaging simplification to payload members + `manifest.json` only.
- Profile mapping for publication IDs: `prep-wepp`, `prep-details`.
- Focused test updates (`tests/nodb/mods`, `tests/microservices`, `tests/weppcloud/routes`, controller Jest tests as needed).
- Manual run-path evidence capture and human approval gate artifact prior to deletion.
- Deletion of legacy modules and dead callsites once approved.

### Explicitly Out of Scope
- Redesign of layer catalog semantics beyond what's required for prep/geopackage parity.
- New export formats or non-cutover feature enhancements.
- Broad Runs-page visual redesign unrelated to cutover behavior.
- Re-architecting cache-key/dependency fingerprint math outside publication-read validation needs.

## Stakeholders
- **Primary**: Features Export maintainers; WEPPcloud export workflow maintainers.
- **Reviewers**: NoDb, rq-engine, and route/controller maintainers.
- **Approvers**: Human maintainer approving deletion gate.
- **Informed**: Operations/support users who consume export artifact links.

## Success Criteria
- [x] Legacy prep/geopackage entry points produce correct artifacts via `features_export` (no legacy writer execution).
- [x] `job` download endpoint is canonical and operational; compatibility route removed.
- [x] `published/{profile}` download endpoint serves from `export/features/published/index.json` source-of-truth.
- [x] Published profiles `prep-wepp` and `prep-details` resolve to valid non-stale artifacts.
- [x] Artifact bundles contain payload members + `manifest.json` only.
- [x] Required automated suites pass.
- [x] Manual e2e evidence is captured for at least one representative run and reviewed.
- [x] Human approval gate is recorded before deleting `gpkg_export.py` and `prep_details.py`.
- [x] Legacy modules and dead callsites are removed after approval, with regression tests still passing.

## Dependencies

### Prerequisites
- Current `features_export` service/planner/materialization path (post WP-8/WP-9).
- Up-to-date `wepppy/nodb/mods/features_export/specification.md` reflecting cutover contract.
- Existing run fixtures and live run path(s) for manual validation.

### Blocks
- Full retirement of legacy post-WEPP export codepaths.
- Long-term documentation claiming complete legacy-export deprecation.

## Related Packages
- **Depends on**: [20260328_features_export_service_compliance_refactor](../20260328_features_export_service_compliance_refactor/package.md)
- **Related**: [20260329_features_export_live_run_matrix](../20260329_features_export_live_run_matrix/package.md)
- **Follow-up**: Potential package for publication-profile UX and retention-policy hardening.

## Timeline Estimate
- **Expected duration**: 3-6 focused sessions.
- **Complexity**: High.
- **Risk level**: Medium-High (cutover + deletion).

## References
- `wepppy/nodb/mods/features_export/specification.md` - canonical contract.
- `wepppy/nodb/mods/features_export/service.py` - orchestration and artifact handling.
- `wepppy/microservices/rq_engine/export_routes.py` - export API adapters.
- `wepppy/rq/wepp_rq_pipeline.py` and `wepppy/rq/wepp_rq_stage_post.py` - run completion hooks.
- `wepppy/nodb/core/wepp_run_service.py` - NoDb-side completion export toggles.
- `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/prep_details.htm` - legacy UI toggles.

## Deliverables
- Package scaffold and active ExecPlan.
- Implemented route/service cutover and publication registry behavior.
- Updated tests covering job/published download contracts and legacy replacement flows.
- Manual e2e evidence artifact(s) with concrete run IDs, job IDs, artifact paths, and timings.
- Human approval artifact documenting go/no-go decision for deletion.
- Post-approval removal commits deleting legacy modules and dead callsites.

## Follow-up Work
- Audit and prune any residual docs/UI text that references retired legacy exports.
- Add retention policy tooling for `export/features/artifacts` + `published/index.json` lifecycle if needed.
