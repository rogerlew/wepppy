# Features Export Profiles + Provenance Zip Packaging

**Status**: Closed 2026-03-29

## Overview
This package delivers the profile-driven Features Export UX and artifact packaging contract refresh. It replaces legacy "Load Defaults" behavior with built-in `.yml` profiles, adds profile-text resolution, and standardizes all feature-export downloads as zip bundles that include replay/provenance metadata.

## Objectives
- Replace legacy defaults button flow with profile-driven controls (`Post Wepp`, `Prep details`, pasted profile text).
- Add server-side profile text parse/normalize endpoint with canonical validation behavior.
- Make all export downloads zip artifacts that include payload members plus `manifest.json`, `profile.yml`, built-in profile files, and provenance `README.md`.
- Ensure cache behavior remains correct under zip-wrapped GeoPackage/Geodatabase artifacts.
- Update/extend tests across service, rq-engine, run-page routes/templates, and controller JS.

## Scope

### Included
- `wepppy/nodb/mods/features_export/specification.md` contract updates.
- Built-in profile module + profile files under `wepppy/nodb/mods/features_export/profiles*`.
- Run-page bootstrap/template/controller updates for profile UX.
- RQ-engine profile resolve route.
- Service/manifest/cache-key changes for zip+provenance profile bundles.
- Regression tests for backend + frontend changes.

### Out of Scope
- New data-layer families or non-profile feature additions.
- Deployment workflow changes.
- Legacy prep-details route restoration (superseded by profile path).

## Success Criteria
- [x] Run-page control exposes quick profile buttons and profile-text load action.
- [x] Profile text can be resolved via rq-engine route and applied client-side.
- [x] All export results download as zip artifacts.
- [x] Zip artifact contains payload member(s), `manifest.json`, `profile.yml`, built-in profiles, and `README.md` provenance.
- [x] Cache key/version marker updated for packaging contract change.
- [x] Targeted backend/frontend test matrix passes.

## Validation Targets
- `wctl run-pytest tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_manifest.py tests/microservices/test_rq_engine_features_export_routes.py tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_run_0_openet_admin_gate.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_features_export_exporters.py tests/nodb/mods/test_features_export_manifest.py --maxfail=1`
- `wctl run-npm test -- features_export`

## Deliverables
- Updated specification and profile source-of-truth files.
- Profile resolve rq-engine endpoint.
- Zip/provenance/profile-bundle artifact packaging behavior in service path.
- Updated route/template/controller tests and service/manifest tests.

## Completion Summary (2026-03-28)
- Added built-in profile support (`profiles.py`, `profiles/post-wepp.yml`, `profiles/prep-details.yml`) and exported profile helpers from `features_export.__init__`.
- Updated run-page bootstrap/template/controller to replace `Load Defaults` with profile actions and profile-text loading.
- Added `POST /api/runs/{runid}/{config}/export/features/profile/resolve` route.
- Refactored cache-miss packaging flow to produce final zip bundle containing payload members, `manifest.json`, `profile.yml`, built-in profiles, and provenance `README.md`.
- Extended manifest payload with `profile_relpath`, `profile_bundle_relpaths`, and `provenance_readme_relpath`.
- Bumped export cache version marker to invalidate pre-bundle artifacts.
- Validation matrix passed (113 pytest tests in targeted suite + JS features_export suite + exporter/manifest suite).

## Closeout Stabilization (2026-03-29)
- Fixed a service cleanup regression that could delete the final zip artifact when writer output path matched bundle path, causing run-page `download/.../features_export.*.zip` links to return `404 Not Found`.
- Added regression coverage for zip-writer retention so the final packaged artifact remains on disk.
- Updated features-export result link rendering to remove `target="_blank"` and use direct download behavior (`download` attribute), with Jest coverage to prevent reintroduction.
- Re-ran the full package validation matrix after the fix.
