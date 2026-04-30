# NOAA Atlas 14 Climate Artifact Retry and Backoff Hardening

Outcome: Completed implementation and targeted validation for bounded NOAA retry/backoff; later review disposition tightened timeout default preservation and regression coverage.

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, climate builds will be more resilient to transient NOAA PFDS outages when exporting `atlas14_intensity_pds_mean_metric.csv`. Users will see fewer runs missing NOAA comparison data due to short-lived upstream `503` or network failures, while climate builds will continue to complete successfully when NOAA is persistently unavailable.

The observable outcome is straightforward: a transiently failing NOAA request should succeed on a later retry within the same climate build attempt, and final retry exhaustion should still preserve current non-fatal behavior with clearer logs.

## Progress

- [x] (2026-04-29 21:50 UTC) ExecPlan authored and linked from package tracker.
- [x] (2026-04-29 21:50 UTC) Incident baseline captured from `/wc1/runs/bo/bovine-clipboard/climate.log` (`503 Service Unavailable`).
- [x] (2026-04-29 21:50 UTC) Retry parameterization precedents reviewed (status2, preflight2, Overpass, run_hillslope).
- [x] (2026-04-30 05:35 UTC) Implemented retry loop + helper parameterization in `wepppy/nodb/core/climate_artifact_export_service.py`.
- [x] (2026-04-30 05:38 UTC) Added deterministic retry regressions in `tests/nodb/test_climate_artifact_export_service.py`.
- [x] (2026-04-30 05:42 UTC) Ran targeted validation and recorded evidence in tracker + ExecPlan.
- [x] (2026-04-30 06:05 UTC) Dispositioned independent reviewer findings: restored default timeout to `30s`, expanded parameterization regressions, and moved ExecPlan to `prompts/completed/`.

## Surprises & Discoveries

- Observation: The failure was transient; the same NOAA query URL returned `200` when manually retried later.
  Evidence: `curl https://hdsc.nws.noaa.gov/cgi-bin/new/fe_text_mean.csv?...` returned `200` and NOAA Atlas header content after the logged failure window.

- Observation: Current NOAA download call uses `timeout=30`, while installed `pfdf.data.noaa.atlas14.download` signature default timeout is `10`.
  Evidence: Local signature introspection from `.venv` reported `timeout: Optional[timeout] = 10`.

- Observation: Existing tests needed explicit `time.sleep` monkeypatching once retries were introduced, otherwise deterministic retry tests would incur real delays.
  Evidence: New NOAA retry tests capture sleep sequence assertions (`[1.0]`, `[1.0, 2.0]`, and `[]`) while completing in the targeted suite runtime.

## Decision Log

- Decision: Keep NOAA artifact optional and non-fatal after retry exhaustion.
  Rationale: Existing contract and UI behavior treat NOAA file as optional; this package is reliability hardening, not contract tightening.
  Date/Author: 2026-04-29 / Codex.

- Decision: Use bounded exponential backoff rather than unbounded or fixed delay.
  Rationale: Local precedent across services uses bounded exponential schemes; bounded retries protect climate build latency.
  Date/Author: 2026-04-29 / Codex.

- Decision: Proposed default timing profile is `timeout=30s`, `attempts=3`, `base=1s`, `cap=8s`.
  Rationale: This profile aligns with local retry cadence norms (1s base from status2/preflight2, bounded cap pattern from Overpass) while limiting worst-case added wall-clock time.
  Date/Author: 2026-04-29 / Codex.

- Decision: Implement NOAA retry timings as environment-backed parsed values with bounded minimums.
  Rationale: This preserves sane defaults while allowing operational tuning without code edits, matching repository precedent in status2/preflight2 and overpass config handling.
  Date/Author: 2026-04-30 / Codex.

## Outcomes & Retrospective

Implemented as planned.

Outcome summary:
- `download_noaa_atlas14_intensity` now retries transient failures with bounded exponential backoff and logs attempts/backoff/exhaustion context.
- Final retry policy defaults: `timeout=30s`, `total_attempts=3`, `base=1.0s`, `cap=8.0s` (`WEPPPY_NOAA_ATLAS14_*` overrides available).
- `ValueError` no-coverage path remains immediate non-retryable and non-fatal.
- Deterministic regressions now cover transient recovery, retry exhaustion, no-coverage no-retry behavior, env timeout propagation, cap-hit backoff, and invalid-env fallback.
- Targeted validation succeeded: `12 passed`; docs lint succeeded: `4 files validated, 0 errors, 0 warnings`.

## Context and Orientation

The implementation touches the climate artifact boundary that runs after CLI generation:

- `/workdir/wepppy/wepppy/nodb/core/climate_artifact_export_service.py`
  - `export_post_build_artifacts()` triggers NOAA download.
  - `download_noaa_atlas14_intensity()` currently makes one call to `atlas14.download(...)` and returns `None` on failure.

- `/workdir/wepppy/tests/nodb/test_climate_artifact_export_service.py`
  - Existing tests cover success, no-coverage (`ValueError`), and generic failure.
  - New tests should validate retry sequencing and bounded exhaustion.

Retry parameter precedent references used for timing:

- `/workdir/wepppy/services/status2/internal/config/config.go`
  - defaults: base `1s`, cap `30s`, max retries `5`.
- `/workdir/wepppy/services/status2/internal/server/server.go`
  - exponential backoff, bounded by cap.
- `/workdir/wepppy/services/preflight2/internal/server/server.go`
  - bounded exponential retry loop.
- `/workdir/wepppy/wepppy/topo/osm_roads/overpass.py`
  - Python bounded exponential backoff for HTTP failures.
- `/workdir/wepppy/wepp_runner/wepp_runner.py`
  - bounded exponential retry with jitter for transient timeout recovery.

## Plan of Work

Milestone 1 updates retry orchestration in `download_noaa_atlas14_intensity`. Introduce a small internal retry helper that classifies transient errors as retryable and applies bounded exponential delays between attempts. Keep no-coverage (`ValueError`) as immediate non-retryable return.

Milestone 2 adds deterministic tests in `tests/nodb/test_climate_artifact_export_service.py`. Simulate controlled failure-then-success and failure-until-exhaustion with monkeypatched `atlas14.download` and `time.sleep` capture so assertions verify attempt count and delay cadence.

Milestone 3 validates behavior and logs. Run targeted pytest suite and verify that retry paths emit attempt context and that climate build semantics remain non-fatal on exhaustion.

## Concrete Steps

Working directory: `/workdir/wepppy`.

1. Implement retry logic in climate artifact exporter.

    cd /workdir/wepppy
    rg -n "download_noaa_atlas14_intensity|atlas14.download|timeout=" wepppy/nodb/core/climate_artifact_export_service.py

2. Add tests for retry success and retry exhaustion.

    cd /workdir/wepppy
    rg -n "download_noaa_atlas14_intensity" tests/nodb/test_climate_artifact_export_service.py

3. Run targeted tests.

    cd /workdir/wepppy
    wctl run-pytest tests/nodb/test_climate_artifact_export_service.py --maxfail=1

4. Lint modified docs.

    cd /workdir/wepppy
    wctl doc-lint --path docs/work-packages/20260429_noaa_atlas14_retry_backoff --path PROJECT_TRACKER.md

## Validation and Acceptance

Acceptance requires all of the following:

- A transient failure followed by success produces NOAA CSV in the same run path.
- Retry exhaustion returns `None` and does not raise an unhandled exception.
- No-coverage `ValueError` remains immediate non-retryable behavior.
- Logs include retry attempt index and final exhaustion summary when applicable.
- Updated tests pass for modified module.

## Idempotence and Recovery

The change should be safe to run repeatedly:

- If NOAA file already exists, function returns existing path with no retries.
- Retry loop is bounded and deterministic; it cannot spin indefinitely.
- On exhaustion, behavior remains `None` return (current contract).

If a step fails mid-implementation, revert only the in-progress retry helper edits and keep baseline tests green before retrying.

## Artifacts and Notes

Keep validation evidence in package tracker progress notes:

- `docs/work-packages/20260429_noaa_atlas14_retry_backoff/tracker.md`

Capture:
- targeted pytest output summary,
- retry delay sequence observed in test hooks,
- confirmation that no-coverage path remains immediate.

## Interfaces and Dependencies

Interface expectations at completion:

- `ClimateArtifactExportService.download_noaa_atlas14_intensity(climate)` still returns `Optional[Path]`.
- Return contract remains:
  - `Path` on success,
  - `None` on no-coverage or exhausted transient failure.
- No external caller signatures change.

Dependency expectations:

- `pfdf.data.noaa.atlas14` remains the downloader dependency.
- Retry policy is implemented in WEPPpy boundary code, not in pfdf.

## Revision Notes

- 2026-04-29 / Codex: Initial ExecPlan authored with scoped retry timings and precedent rationale.
- 2026-04-30 / Codex: Completed implementation/test milestones, captured final retry parameterization contract, and recorded targeted validation evidence.
