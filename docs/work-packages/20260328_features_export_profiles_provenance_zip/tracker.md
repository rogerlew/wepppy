# Tracker - Features Export Profiles + Provenance Zip Packaging

## Quick Status

**Started**: 2026-03-28  
**Current phase**: Complete  
**Last updated**: 2026-03-29  
**Completed ExecPlan**: `prompts/completed/features_export_profiles_provenance_zip_execplan.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Updated features-export specification with profile UX and zip/provenance packaging contract.
- [x] Added built-in profile module and source files (`post-wepp.yml`, `prep-details.yml`).
- [x] Updated run-page bootstrap/template/controller profile UX and renamed units label to "Unitzer Selections".
- [x] Added rq-engine profile resolve endpoint and tests.
- [x] Refactored service packaging to produce final zip bundle containing payload members + manifest/profile/provenance files.
- [x] Extended manifest fields for profile/provenance relpaths and bumped cache export version marker.
- [x] Updated affected pytest/Jest suites and passed targeted validations.
- [x] Fixed zip artifact retention regression and download-link new-tab behavior; added regression coverage and reran validation matrix.

## Decisions
- 2026-03-28: Keep writer-level behavior unchanged and enforce final artifact contract in service packaging so all formats share one bundle/provenance path.
- 2026-03-28: Preserve `features_export:defaults:loaded` event emission for preset profile loads to maintain existing consumer compatibility while introducing `features_export:profile:loaded`.
- 2026-03-28: Cache-hit compatibility for legacy artifacts is handled by cache key version bump rather than mixed-format migration logic.

## Verification Checklist
- [x] `wctl run-pytest tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_manifest.py tests/microservices/test_rq_engine_features_export_routes.py tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_run_0_openet_admin_gate.py --maxfail=1`
- [x] `wctl run-pytest tests/nodb/mods/test_features_export_exporters.py tests/nodb/mods/test_features_export_manifest.py --maxfail=1`
- [x] `wctl run-npm test -- features_export`

## Progress Notes

### 2026-03-28 - End-to-end completion
- Completed profile loading foundation (`profiles.py`) and built-in profile files under `wepppy/nodb/mods/features_export/profiles/`.
- Replaced legacy defaults button flow in `features_export_pure.htm` and `features_export.js` with:
  - quick profile buttons,
  - profile text paste + resolve action,
  - retained clear selection as separate action.
- Added run-page bootstrap fields (`profiles`, `profile_buttons`, `default_profile_key`) and profile resolve route URL.
- Added rq-engine route `POST /api/runs/{runid}/{config}/export/features/profile/resolve` with canonical validation/error behavior.
- Implemented final service-level bundle packaging:
  - all downloads are zip artifacts,
  - zip includes payload members, `manifest.json`, `profile.yml`, built-in profile files, and provenance `README.md`.
- Updated manifest and cache version marker contract.
- Updated and passed backend/frontend tests.

### 2026-03-29 - Closeout stabilization
- Root-caused `Not Found` download failures to cleanup logic deleting the final zip artifact when writer output and bundle path were identical.
- Patched service cleanup retain list to include final bundle path and added zip-writer regression coverage.
- Updated result download link rendering to use direct download behavior (no `_blank` tab), with Jest assertion coverage.
- Re-ran package validation matrix:
  - `wctl run-pytest tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_manifest.py tests/microservices/test_rq_engine_features_export_routes.py tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_run_0_openet_admin_gate.py --maxfail=1`
  - `wctl run-pytest tests/nodb/mods/test_features_export_exporters.py tests/nodb/mods/test_features_export_manifest.py --maxfail=1`
  - `wctl run-npm test -- features_export`
