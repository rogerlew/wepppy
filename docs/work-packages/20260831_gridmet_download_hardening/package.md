# GridMET Download Client Hardening

**Status**: Closed (2026-08-31)
**Timezone**: UTC

## Overview

On 2026-08-26, production run `mdobre-massive-delusion` requested 376 annual
GridMET watershed subsets. The upstream THREDDS service returned 11 HTTP 502
and 25 HTTP 503 HTML bodies. The gridded client wrote those bodies directly to
final `.nc` paths, and climate construction later failed with `NetCDF: Unknown
file format`. An unchanged retry replaced some failures while producing or
retaining others.

This package hardens both GridMET acquisition boundaries: the JSON
single-location client and the NetCDF gridded-subset client. Valid upstream
data remains behaviorally compatible. Invalid or transient responses fail with
an actionable acquisition error and never become final artifacts.

## Objectives

- Validate HTTP status, payload shape, and requested GridMET content.
- Bound response bytes and NetCDF dimensions before downstream allocation.
- Apply bounded transient retry with explicit timeouts.
- Stage gridded downloads beside the destination and publish atomically only
  after NetCDF validation.
- Preserve an existing valid grid when every replacement attempt fails.
- Bound gridded request concurrency to reduce upstream pressure.
- Cover 502, 503, invalid JSON, HTML-as-NetCDF, truncated NetCDF, retry
  exhaustion, atomic publication, and valid single-point/grid responses.

## Hardening Hypothesis

If both acquisition boundaries validate complete requested content before
publication, transient upstream failures will either recover within three
attempts or fail without leaving a corrupt artifact. Health is zero malformed
final `.nc` files and exact point-date coverage; guardrails are bounded worker
occupancy, no permanent-4xx retries, and unchanged valid scientific outputs.
This package uses the stateless recurrence-triggered observation model defined
below rather than relying on a person to revisit an elapsed-time reminder.

## Scope

### Included

- `wepppy/climates/gridmet/gridmet_singlelocation_client.py`.
- `wepppy/climates/gridmet/client.py`.
- Gridded retrieval concurrency in
  `wepppy/nodb/core/climate_gridmet_multiple_build_service.py`.
- Hermetic tests, operator/developer documentation, and incident evidence.

### Explicitly Out of Scope

- Changing GridMET scientific variables, units, interpolation, formulas, or
  watershed bounding-box semantics.
- Introducing a new dependency, shared cross-run data cache, Zarr, OPeNDAP, or
  aggregated multi-year acquisition.
- Mutating the failed production run or requeuing its job as part of code
  implementation.

## Success Criteria

- [x] Single-location requests retry transient failures and reject malformed
  JSON/schema without exposing response bodies.
- [x] Gridded requests never publish HTML, truncated data, or a NetCDF missing
  the requested variable/coordinates.
- [x] A valid NetCDF is atomically published and an existing valid destination
  survives exhausted replacement attempts.
- [x] Gridded fan-out uses the ADR-approved concurrency ceiling.
- [x] Targeted and full repository validation pass.
- [x] Correctness, QA, and security reviews have no unresolved medium/high
  findings.

## Parameterization ADR Gate

- **Parameterization change present**: yes
- **ADR required**: yes
- **ADR link**: `docs/adrs/ADR-0028-gridmet-download-retry-concurrency.md`
- **Decision provenance captured**: yes

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: external HTTP responses cross a production egress and
  file-publication boundary.
- **Security review artifact**:
  `artifacts/2026-08-31_security_review.md`

## Hardening and Callus Softening

- **Failure signatures**: `OSError: [Errno -51] NetCDF: Unknown file format`;
  final `.nc` files containing `502 Proxy Error` or `503 Service Unavailable`.
- **Related precedent**: `docs/standards/hardening-lifecycle-standard.md` and
  `docs/work-packages/20260825_cap_runtime_deploy_hardening/` for validated
  atomic publication and recurrence-triggered closeout.
- **Health signals**: zero non-NetCDF final artifacts; transient failures retry
  within bounds; valid requests retain existing output behavior.
- **Danger signals**: unbounded retry, logging response bodies, partial final
  files, retrying permanent 4xx errors, or excessive upstream concurrency.
- **Observation model**: stateless and recurrence-triggered. Record local and
  Forest1 evidence; any later matching failure opens a new incident/package.
- **Temporary calluses introduced**: bounded retry only; it is a durable
  acquisition contract and has no date-based removal.

## References

- `wepppy/climates/gridmet/client.py` - annual gridded NCSS client.
- `wepppy/climates/gridmet/gridmet_singlelocation_client.py` - aggregated JSON
  single-location client.
- `wepppy/nodb/core/climate_gridmet_multiple_build_service.py` - annual
  variable/year fan-out.
- `docs/adrs/ADR-0028-gridmet-download-retry-concurrency.md` - parameter
  decision and rollback.

## Deliverables

- Hardened clients and focused regression suite.
- Parameterization ADR and canonical climate-client documentation.
- Review and validation evidence.

## Follow-up Work

- Evaluate aggregated multi-year gridded acquisition and a validated shared
  grid cache in a separate package with performance and parity evidence.
