# NOAA Atlas 14 Retry Backoff Hardening for Climate Artifact Export

**Status**: Open (2026-04-29)  
**Timezone**: UTC

## Overview
Run `bovine-clipboard/disturbed9002_wbt` completed climate generation but missed `climate/atlas14_intensity_pds_mean_metric.csv` because NOAA PFDS returned `503 Service Unavailable` during a single download attempt. This package adds bounded retry with exponential backoff for transient NOAA failures so short upstream outages are less likely to suppress NOAA comparison artifacts.

The change must preserve the current contract where NOAA Atlas 14 remains optional and climate build completion is not blocked by permanent NOAA unavailability.

## Objectives
- Increase success rate for NOAA Atlas 14 artifact export during transient upstream failures.
- Use retry timing defaults aligned with existing repo precedent instead of introducing ad-hoc values.
- Keep NOAA artifact behavior optional (no fatal climate build failure when retries are exhausted).
- Add deterministic observability (attempt count, backoff delay, final outcome) to climate logs.
- Add regression coverage for retry success, retry exhaustion, and non-retryable paths.

## Scope
This package covers NOAA Atlas 14 download hardening in the climate artifact export boundary and associated tests/docs.

### Included
- Update `wepppy/nodb/core/climate_artifact_export_service.py` to:
  - retry bounded times on transient network/upstream failures,
  - apply exponential backoff between attempts,
  - keep `ValueError` no-coverage behavior non-retryable,
  - emit attempt-level log context.
- Parameterization baseline (subject to validation in this package):
  - per-attempt timeout: `30s`,
  - total attempts: `3`,
  - backoff base: `1s`,
  - backoff cap: `8s`.
- Add/adjust tests in `tests/nodb/test_climate_artifact_export_service.py` for:
  - success after transient failure(s),
  - exhaustion after bounded retries,
  - no-coverage immediate skip (no retries).
- Update work-package docs and root tracker entries with rationale and validation evidence.

### Explicitly Out of Scope
- Making NOAA Atlas 14 artifact required for climate build success.
- Adding a cross-repository generic retry framework.
- Modifying Geneva/Storm Event Analyzer rendering contracts beyond existing optional-file behavior.
- New UI controls for NOAA retry tuning.

## Stakeholders
- **Primary**: WEPPcloud operators and users relying on NOAA-vs-WEPP frequency comparison outputs.
- **Reviewers**: NoDb climate maintainers.
- **Security Reviewer**: Not required for this package scope.
- **Informed**: Geneva/Storm Event Analyzer maintainers.

## Success Criteria
- [ ] Climate artifact export retries transient NOAA failures using bounded exponential backoff.
- [ ] Retry defaults are explicitly justified using existing repository retry implementations.
- [ ] NOAA no-coverage (`ValueError`) remains non-retryable and non-fatal.
- [ ] Climate build still succeeds when NOAA retries are exhausted, with clear final log message.
- [ ] New regression tests cover retry success and retry exhaustion paths.
- [ ] Package docs and `PROJECT_TRACKER.md` capture behavior contract and rationale.

## Dependencies

### Prerequisites
- `pfdf.data.noaa.atlas14.download` remains the NOAA artifact download dependency.
- Existing climate artifact export sequencing remains unchanged (`wepp_cli.parquet` and `wepp_cli_pds_mean_metric.csv` exported before NOAA attempt).

### Blocks
- None. This package can execute independently.

## Related Packages
- **Related**: [20260422_watershed_centroid_persistence_hardening](../20260422_watershed_centroid_persistence_hardening/package.md)
- **Follow-up**: Optional package for configurable runtime retry knobs if operational tuning is later required.

## Timeline Estimate
- **Expected duration**: 1-2 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Low-Medium (latency and logging behavior changes in climate build boundary).

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: The package changes retry behavior and logging for an outbound NOAA call; it does not alter auth/session/secrets or introduce new public input surfaces.
- **Security review artifact**: `N/A`

## Hardening and Callus Softening (Required for incident/remediation packages)
- **Failure signature(s)**: `Failed downloading NOAA Atlas 14 intensity data` with `HTTPError: 503 Server Error: Service Unavailable` from NOAA PFDS in `/wc1/runs/bo/bovine-clipboard/climate.log`.
- **Related prior hardening efforts**: [20260422_watershed_centroid_persistence_hardening](../20260422_watershed_centroid_persistence_hardening/package.md).
- **Health signals**:
  - Higher rate of `Downloaded NOAA Atlas 14 intensity data` logs on first climate build attempt windows with intermittent NOAA instability.
  - Lower operator reports of missing `atlas14_intensity_pds_mean_metric.csv` when NOAA outages are brief.
- **Danger signals**:
  - Excessive climate-build latency inflation from retry loops.
  - Retry loops masking persistent upstream failures without actionable logs.
- **Observation window**: 14 days after deployment.
- **Temporary calluses introduced**: Bounded retry loop with conservative defaults (review after observation window).
- **Callus softening hypothesis (if applicable)**: If NOAA stability remains high and latency impact is measurable, consider reducing attempts or cap in a follow-up package.

## References
- `/wc1/runs/bo/bovine-clipboard/climate.log` - observed 503 failure for NOAA Atlas 14 download.
- `/workdir/wepppy/wepppy/nodb/core/climate_artifact_export_service.py` - NOAA artifact export boundary to harden.
- `/workdir/wepppy/tests/nodb/test_climate_artifact_export_service.py` - current regression surface for NOAA artifact export.
- `/workdir/wepppy/services/status2/internal/config/config.go` - retry defaults precedent (`1s` base, `30s` cap, `5` retries).
- `/workdir/wepppy/services/status2/internal/server/server.go` - exponential retry + jitter precedent.
- `/workdir/wepppy/services/preflight2/internal/server/server.go` - bounded exponential retry precedent.
- `/workdir/wepppy/wepppy/topo/osm_roads/overpass.py` - Python retry/backoff precedent (`0.5s` base, capped exponential).
- `/workdir/wepppy/wepp_runner/wepp_runner.py` - Python retry + jitter precedent for transient timeout recovery.

## Deliverables
- Hardened NOAA Atlas 14 download retry behavior in climate artifact export path.
- Regression tests covering retry success/exhaustion/non-retryable branches.
- Updated package docs, decision log, and validation evidence.

## Follow-up Work
- Optional runtime configuration knobs for NOAA retry values if operational tuning is needed.
- Optional lightweight run-health telemetry summarizing NOAA artifact success/failure rates.

## Closure Notes

**Closed**: YYYY-MM-DD

**Summary**: TBD

**Lessons Learned**: TBD

**Archive Status**: TBD
