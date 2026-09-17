# Forest restart and nervous-mesquite M1 acceptance

Completed 2026-09-17 UTC (2026-09-16 Pacific). Scope was the user-authorized forest
restart and named M1 rerun, with preserved prior assessment and scientific inputs.
No production code, credentials, stack configuration, or unrelated projects changed.

## Runtime and job

Installed development preset: wctl, docker/docker-compose.dev.yml. Ran wctl restart
with default, batch and fork-archive queues empty and no started jobs. Restarted
services report fresh start times; web login returned HTTP 200 and preflight returned
OK. Redis, PostgreSQL and download reported healthy. New worker heartbeats cover
all three queues. Build-only containers exited successfully as expected.
No Redis flush, git pull/reset, production deploy, or input rebuild was performed.

Runtime HEAD was c0bf57cf3ff0907f80cdad3bb68e50ad315af5d3, with unrelated shared
checkout changes recorded in [runtime-state.log](runtime-state.log), not a clean
release claim. All 26 engine fingerprints in the new attempt match local source.

The authenticated browser submitted M1 with the existing NOAA design-rainfall choice:
job 7583d48c-014f-46e8-9e55-cb09f948f68c, accepted attempt
b9b523bda3f34ca684b7790145d4e43c. Worker execution was 03:31:17–03:31:30 UTC.
The new result is current and remains selected after reload.

## Result checks

Soil source: NRCS-derived STATSGO fine-earth Kf; policy statsgo_kffact_1995_cog2025_v1;
predictor schema 3. Mean Kf is 0.1393960061975289. Common coverage is 77,667/77,669
cells (99.99742%). Two excluded cells remain explicitly reported.

Independent raster means and Staley coefficients reproduce all 8,067 event rows,
12 design rows, 3 inverse rows, and 416 CSV curve rows across 15/30/60-minute and
English-unit exports. At I15 = 24 mm/hour, modeled probability is 72.1915%.
The 50% likelihood intensities are 19.0053, 15.2502 and 12.1182 mm/hour for
15, 30 and 60 minutes. These reproduce the preceding Kf acceptance; this rerun is
not evidence of exact agreement with different USGS basin geometries.

Browser checks passed for curve duration changes, SI/English units, keyboard scenario
selection, mobile rendering, modeled/disaggregated event labels, source browsing,
CSV download and reload. Desktop screenshots were visually inspected. NOAA Atlas 14
is labeled as design rainfall; project events retain their climate provenance.
Published events/design/inverse parquet, manifest and validity mask match both the
new attempt and HTTP downloads. Downloaded curve CSV equals the displayed export.

Numerical evidence: [numeric validation](nervous-mesquite_numeric_validation.json),
[publication validation](publication_validation.json),
[browser evidence](browser/nervous-mesquite/evidence.json),
[job](browser/nervous-mesquite/job.json),
[desktop screenshot](browser/nervous-mesquite/report-si.png),
[mobile screenshot](browser/nervous-mesquite/report-mobile.png).

## Preservation and recovery

Before execution, 524 inventoried files were archived and verified, covering all
protected inputs and the complete existing post-fire module/state. Archive:
/wc1/runs/ne/nervous-mesquite/archives/nervous-mesquite.postfire-preserved.20260917T032842Z.zip.
It contains 238,324,512 bytes; SHA-256
1987eb49ada540644878ad87cd88cfbe927abf6dc27742f708093d2cf12b978b.
This is a scoped evidence archive, not a full-project restore ZIP.

All previous attempt files remain byte-identical, including accepted attempt
0ea9c1f5b0964b22ba7f1b457c1a6c9f and the earlier legacy assessment. All 387 protected
scientific inputs remain unchanged. climate.nodb differs only in _nodb_mtime;
no climate data or scientific settings changed. No SBS/dNBR, soils, RUSLE, POLARIS,
terrain or watershed reconstruction was performed. See
[preservation](nervous_preservation.json) and [archive manifest](baseline_archive.json).

## Retained operational findings

The generic RQ endpoint catalog omits post-fire operations. An initial discovery
schema request failed before submission; the registered OpenAPI route and existing
browser control then completed successfully. Retained first-attempt evidence is in
browser/discovery-failure and browser-discovery-failure.log. Smallest follow-up:
register post-fire operations in generic discovery; no model redesign is indicated.

The installed rq-info --detailed option is unsupported; its wrapper rebuilds worker
registry metadata before the option error. Queue checks used direct read-only Redis
queries afterward. No jobs were canceled. Neither finding blocked the completed run.
