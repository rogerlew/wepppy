# Local RQ Acceptance — SSURGO Intelligent Fallback M4

**Date**: 2026-07-22 UTC  
**Environment**: local Docker Compose; `plastic-bundling` /
`disturbed9002`  
**Auth**: user-supplied short-lived run-scoped JWT; token value not recorded

## Preflight

- `wctl ps`: rq-engine, rq-worker, Redis, and dependent local services up.
- `wctl rq-info`: zero queued/executing jobs before the acceptance submission.
- No Redis flush occurred. A targeted rq-engine/rq-worker recreation was
  required after source changes because the running processes predated the
  implementation commit; Compose also recreated its Redis dependency.

## Contract Discovery and Guard

- Pipeline, readiness, build-soils schema/defaults/errors: HTTP 200.
- `rq_engine_build_soils` resolved defaults: `initial_sat=0.75`,
  `sol_ver=9002.0`, `clear_ssurgo_cache_on_rebuild=true`.
- Wrong config (`disturbed9001`) after targeted restart: HTTP 409,
  `run_config_mismatch`, no job ID, and zero queued/executing jobs.

The initial wrong-config probe before service recreation returned HTTP 200
because it reached a stale rq-engine process. That local job completed before
recovery. The incident confirms that deployment/restart is required before a
runtime acceptance claim; it is not evidence that the committed guard failed.

## Correct-Config Submission

- POST `build-soils`: HTTP 200; correlation ID
  `ssurgo-fallback-m4-build-20260722`; job ID redacted as `1d7e…1828`.
- Polling: `started` then terminal `finished` at 2026-07-22T18:30:29Z.

## Generated-Output Evidence

| Check | Result |
| --- | --- |
| `ssurgo_candidate_preparation` | `{ "status": "not_attempted", "affected_hillslopes": 0 }` |
| Candidate active manifest | absent |
| Raw/final dominant mapping | equal |
| SSURGO substitutions | 0 |
| `soils/soils.parquet` rows | 63 |
| Additive fallback columns | present |
| Every final MUKEY has a referenced `.sol` | true |

## Result

**M4 runtime no-op acceptance: PASS.** This run does not exercise local donor
selection because the watershed had no residual-invalid dominant MUKEY. The
package/release hold remains until the M3 adversarial/scoring corpus and M5
review-disposition closure are complete.

## Historical-Invalid Watershed Recheck

The operator supplied a separate short-lived scoped JWT for
`improvident-dyslexia`, the study's historical-invalid watershed. Its active
run config is `disturbed9002_wbt`.

- Discovery/defaults: HTTP 200; `initial_sat=0.75`, `sol_ver=9002.0`, and
  `clear_ssurgo_cache_on_rebuild=false`.
- POST `build-soils`: HTTP 200; correlation ID
  `ssurgo-fallback-known-invalid-20260722`; job ID redacted as `7f4a…6f0a`.
- Polling: terminal `finished` at 2026-07-22T18:39:01Z.
- Current result: 3,597 raw/final assignments agree; substitutions and local
  selections are both zero; `candidate_preparation=not_attempted`; no candidate
  manifest exists; all final MUKEYs have referenced soil files.

This confirms the empirical study's finding that the historical failures are
not reproducible under the current SSURGO source/cache/converter state. It is
runtime evidence for ordinary recovery and all-valid no-op behavior, **not** a
true-current-invalid local-vector-selection acceptance case.

## Current-Invalid Local Donor Acceptance

**Environment**: local Docker Compose; far-out-quiescence / disturbed9002_wbt
**Auth**: user-supplied short-lived run-scoped JWT; token value not recorded

This run contains dominant raw MUKEY 2712917, which remains invalid under the
current converter but retains an eight-field shallow-profile vector. Discovery
of pipeline/readiness/build-soils schema/defaults/errors returned HTTP 200; the
resolved defaults were initial_sat=0.75, sol_ver=9002.0, and
clear_ssurgo_cache_on_rebuild=false. wctl rq-info showed zero queued or
executing jobs before submission.

The first submission (job ID redacted as a642…6f75, terminal finished at
2026-07-22T19:21:16Z) exposed a candidate-artifact publication defect: source
and raster hashes agreed, but the CRS WKT returned by the crop primitive was
not byte-identical to the WKT serialized in the persisted GeoTIFF. Strict
provenance validation correctly rejected that artifact and selected the global
fallback. This was not acceptance evidence.

The publisher now reads metadata from the atomically persisted candidate raster
before recording its manifest, preserving strict validation without weakening
the artifact contract. A regression test simulates crop-versus-persisted CRS
serialization drift and proves the active artifact loads; focused fallback
tests passed 10/10. After an idle-queue preflight, a targeted local rq-worker
restart loaded the correction; no Redis flush occurred.

- Corrected POST correlation ID:
  ssurgo-local-donor-2712917-rebuild-20260722; job ID redacted as d3a9…691e;
  terminal finished at 2026-07-22T19:25:18Z.
- Candidate preparation: prepared, with 10 affected hillslopes and an active
  candidate manifest.
- Nine dominant hillslopes with raw MUKEY 2712917 selected policy
  ssurgo_local_vector_profile_v1; none selected global donor 2712884.
- Selected local donors: 2712901 for eight hillslopes and 2712931 for one.
  Seven selections first qualified at 250 m and two at 500 m.
- NoDb/Parquet raw and final assignments agree; all 13 final rows reference an
  existing .sol file.

**Result: PASS.** This is true-current-invalid RQ acceptance for the local
vector-profile path. It demonstrates conditional padded-map preparation,
persisted artifact provenance, bounded local support, selected-donor
materialization, and additive output provenance in the production worker path.
