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
