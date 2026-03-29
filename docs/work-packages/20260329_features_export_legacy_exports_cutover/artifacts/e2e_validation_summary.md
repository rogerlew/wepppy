# E2E Validation Summary (Phase 6)

Date: 2026-03-29

## Target Run
- Run root: `/wc1/runs/cl/clogging-starch`
- Run URL shape: `https://wc.bearhive.duckdns.org/weppcloud/runs/clogging-starch/disturbed9002-wbt-mofe/`
- Config token used for service execution: `disturbed9002-wbt-mofe`

## Validation Script
Executed with:
```bash
wctl run-python - <<'PY'
# executes prep-wepp + prep-details profiles twice each,
# publishes both profiles, and resolves published artifacts
PY
```

## Results

### `prep-wepp` (geopackage)
- Cold run job id: `gate-prep-wepp-run1-1774805093972`
- Warm run job id: `gate-prep-wepp-run2-1774805098644`
- Cold runtime: `4.082s`
- Warm runtime: `0.426s`
- Cold `cache_hit`: `false`
- Warm `cache_hit`: `true`
- Artifact relpath: `export/features/artifacts/011569b7ad684960a50bdb9c4c458cd3/features_export.geopackage.zip`
- Job manifest relpaths:
  - `export/features/jobs/gate-prep-wepp-run1-1774805093972/manifest.json`
  - `export/features/jobs/gate-prep-wepp-run2-1774805098644/manifest.json`
- Zip members: `features_export.gpkg`, `manifest.json`
- Layer counts from job manifest:
  - `clogging-starch-chan_map-channels`: `27`
  - `clogging-starch-sbs_map-subcatchments`: `12`

### `prep-details` (parquet)
- Cold run job id: `gate-prep-details-run1-1774805100860`
- Warm run job id: `gate-prep-details-run2-1774805103138`
- Cold runtime: `1.729s`
- Warm runtime: `0.447s`
- Cold `cache_hit`: `false`
- Warm `cache_hit`: `true`
- Artifact relpath: `export/features/artifacts/3103f9e47b1146d1a60c66cb4275ad0b/features_export.parquet.zip`
- Job manifest relpaths:
  - `export/features/jobs/gate-prep-details-run1-1774805100860/manifest.json`
  - `export/features/jobs/gate-prep-details-run2-1774805103138/manifest.json`
- Zip members: `channels.parquet`, `hillslopes.parquet`, `manifest.json`
- Layer counts from job manifest:
  - `clogging-starch-chan_map-channels`: `27`
  - `clogging-starch-sbs_map-subcatchments`: `66`

## Published Registry Evidence
- Registry path: `/wc1/runs/cl/clogging-starch/export/features/published/index.json`
- Registry schema version: `1`
- Profiles published:
  - `prep-wepp` -> `export/features/artifacts/011569b7ad684960a50bdb9c4c458cd3/features_export.geopackage.zip`
  - `prep-details` -> `export/features/artifacts/3103f9e47b1146d1a60c66cb4275ad0b/features_export.parquet.zip`
- `resolve_published_artifact_path(...)` succeeded for both canonical profiles.

## Notes
- During the first geopackage run, GDAL emitted geometry-type warnings (POLYGON into MULTIPOLYGON layer). Export still completed successfully and produced readable artifacts.
