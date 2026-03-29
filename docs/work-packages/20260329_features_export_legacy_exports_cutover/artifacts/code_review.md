# Code Review - Features Export Legacy Cutover

Date: 2026-03-29
Reviewer: Codex (implementation self-review)

## Scope Reviewed
- `wepppy/nodb/mods/features_export/service.py`
- `wepppy/nodb/mods/features_export/manifest.py`
- `wepppy/nodb/mods/features_export/profiles/post-wepp.yml`
- `wepppy/microservices/rq_engine/export_routes.py`
- `wepppy/rq/wepp_rq_stage_post.py`
- `wepppy/nodb/core/wepp_run_service.py`

## Findings
1. High (fixed): Built-in `post-wepp` profile included `tabular` options while `format=geopackage`, causing validation failure for profile-backed legacy cutover execution.
   - Fix: Removed invalid `tabular` block from `profiles/post-wepp.yml`.

2. Medium (fixed): Service still emitted browse-path `download_url` and bundled profile/provenance files (`profile.yml`, `profiles/*.yml`, `README.md`) despite updated contract.
   - Fix: Switched to canonical job download URL and reduced bundles to payload members + `manifest.json`.

3. Medium (fixed): No publication registry implementation existed despite route contract and stale-publication requirement.
   - Fix: Added registry load/write/publish/resolve helpers, canonical profile normalization, and stale validation (`cache_key`, `request_hash`, `dependency_fingerprint`).

4. Medium (fixed): Legacy export endpoints and post-run hooks still directly called legacy exporter modules.
   - Fix: Rewired legacy routes (`geopackage`, `geodatabase`, `prep_details`) and post hooks (`_post_gpkg_export_rq`, `_post_prep_details_rq`) through features-export profile execution.

## Residual Risks
- Legacy module files still exist and are still imported by some untouched callsites (`wepppy/export/__init__.py` and any non-cutover codepaths). Deletion is intentionally deferred until human approval.
- Geopackage writer emits GDAL geometry-type warnings (POLYGON into MULTIPOLYGON layer). This is pre-existing behavior; artifacts are still readable.
