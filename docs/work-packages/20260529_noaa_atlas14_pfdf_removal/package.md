# PFDF Removal and Native NOAA Atlas 14 Client

**Status**: Closed (2026-05-29)
**Timezone**: UTC

## Overview

This package removes the `pfdf` dependency from WEPPpy due GPLv3 licensing risk while preserving existing NOAA Atlas 14 artifact behavior in climate post-build export. The implementation will replace `pfdf.data.noaa.atlas14` with a WEPPpy-owned Atlas 14 client authored from publicly available NOAA/PFDS API documentation and observable endpoint contracts.

The replacement must preserve current behavior contracts: NOAA Atlas 14 remains optional, climate build success is not blocked by NOAA unavailability, and existing retry/backoff environment controls continue to work.

## Objectives

- Remove direct runtime dependency on `pfdf` for NOAA Atlas 14 downloads.
- Author and ship a WEPPpy-owned Atlas 14 client module using publicly available API documentation.
- Preserve existing `download_noaa_atlas14_intensity` behavior and output contracts.
- Remove `pfdf` from dependency manifests used by this repository.
- Update tests/docs to validate and describe the new ownership boundary.

## Scope

### Included

- Add a WEPPpy-owned NOAA Atlas 14 client module (target location to finalize during implementation discovery).
- Replace `from pfdf.data.noaa import atlas14` usage in `wepppy/nodb/core/climate_artifact_export_service.py` with the new client.
- Preserve call-site contract values currently used by climate artifact export:
  - `statistic='mean'`
  - `data='intensity'`
  - `series='pds'`
  - `units='metric'`
  - existing timeout and retry/backoff environment behavior.
- Update/expand tests in:
  - `tests/nodb/test_climate_artifact_export_service.py`
  - `tests/climates/noaa/test_atlas14_download.py`
  - `tests/climates/noaa/README.md`
- Remove `pfdf` from `docker/requirements-uv.txt` and any other live dependency manifests that include it.
- Add/update developer documentation for the Atlas 14 client contract and public API references.

### Explicitly Out of Scope

- Broad refactors of unrelated climate export artifacts.
- UI/reporting contract changes for downstream NOAA CSV consumers.
- Introducing a generic multi-provider weather client abstraction.
- Rewriting historical NOAA reference artifact content except where required for deterministic validation.

## Implementation Fidelity and Evidence (Required for modernization/migrations)

- **Fidelity target**: `faithful extraction`
- **Authoritative source path(s)**:
  - `wepppy/nodb/core/climate_artifact_export_service.py` (`download_noaa_atlas14_intensity`)
  - `tests/nodb/test_climate_artifact_export_service.py`
  - `tests/climates/noaa/artifacts/*.csv`
- **Cutover proof required**:
  - climate exporter still writes `climate/atlas14_intensity_pds_mean_metric.csv` when data is available,
  - retry/no-coverage/exhaustion behavior remains contract-compatible,
  - no runtime `pfdf` import remains in WEPPpy production path.
- **Acceptance evidence type**: `both` (fixture-based regression + live/API characterization where enabled)

## Stakeholders

- **Primary**: WEPPcloud operators and climate artifact maintainers.
- **Reviewers**: NoDb climate maintainers and dependency-governance maintainers.
- **Security Reviewer**: Not required by triage for this package.
- **Informed**: Storm Event Analyzer/report consumers relying on NOAA comparison CSVs.

## Success Criteria

- [x] No production-path imports of `pfdf` remain in WEPPpy runtime code.
- [x] NOAA Atlas 14 client implementation exists in-repo and is sourced from public API documentation/contract evidence.
- [x] `ClimateArtifactExportService.download_noaa_atlas14_intensity` preserves optional-artifact behavior and retry/no-coverage semantics.
- [x] `docker/requirements-uv.txt` no longer includes `pfdf`.
- [x] Updated tests cover success, transient retry, retry exhaustion, no coverage, and parameter/env override behavior through the new client boundary.
- [x] NOAA client docs/tests clearly capture public API references and expected request parameters.
- [x] Work-package tracker, ExecPlan, and root tracker entries are current.

## Parameterization ADR Gate

- **Parameterization change present**: `no`
- **ADR required**: `no`
- **ADR link(s)**: `N/A`
- **Decision provenance captured**: `yes`

Reference: `docs/standards/parameterization-adr-standard.md`

## Dependencies

### Prerequisites

- Public NOAA Atlas 14/PFDS documentation and endpoint contract references remain reachable.
- Existing Atlas 14 artifact fixtures under `tests/climates/noaa/artifacts/` remain available for characterization.

### Blocks

- Follow-up hardening that depends on a WEPPpy-owned Atlas 14 client (for example, richer diagnostics, endpoint failover, or typed parsers).

## Related Packages

- **Related**: [20260429_noaa_atlas14_retry_backoff](../20260429_noaa_atlas14_retry_backoff/package.md)
- **Follow-up**: Optional package for NOAA endpoint observability/contract drift monitoring if needed after cutover.

## Timeline Estimate

- **Expected duration**: 2-3 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium (dependency removal + external HTTP contract ownership).

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: Replaces an existing outbound HTTP dependency with an in-repo client for the same endpoint and data flow; no auth/session/secrets/public-route expansion.
- **Security review artifact**: `N/A`

## References

- `docker/requirements-uv.txt`
- `wepppy/climates/noaa/atlas14.py`
- `wepppy/nodb/core/climate_artifact_export_service.py`
- `tests/nodb/test_climate_artifact_export_service.py`
- `tests/climates/noaa/README.md`
- `tests/climates/noaa/test_atlas14_download.py`
- `tests/climates/noaa/test_atlas14_client.py`
- [NOAA HDSC FAQ (web scraping/API arguments)](https://www.weather.gov/owp/hdsc_faqs)
- [NOAA PFDS cgi endpoint example](https://hdsc.nws.noaa.gov/cgi-bin/new/cgi_readH5.py?lat=37.4000&lon=-119.2000&type=pf&data=depth&units=english&series=pds)
- [pfdf Atlas 14 API reference (historical behavior baseline)](https://ghsc.code-pages.usgs.gov/users/jking/pfdf/api/data/noaa/atlas14.html)

## Deliverables

- WEPPpy-owned NOAA Atlas 14 client module and integration at climate artifact export boundary.
- Updated test coverage proving contract-compatible behavior.
- Dependency manifest updates removing `pfdf`.
- Updated NOAA Atlas 14 test/documentation surfaces for the new client boundary.
- Work-package execution artifacts (tracker + ExecPlan + findings disposition if review produces findings).

## Follow-up Work

- Add automated endpoint contract drift checks if NOAA PFDS response format instability is observed post-cutover.
- Consider extracting a small shared HTTP retry utility only if duplicated logic emerges across multiple outbound climate clients.

## Kickoff Prompt

- Completed ExecPlan: `docs/work-packages/20260529_noaa_atlas14_pfdf_removal/prompts/completed/pfdf_removal_atlas14_execplan.md`

## Closure Notes

**Closed**: 2026-05-29

**Summary**: Replaced `pfdf` with a WEPPpy-owned Atlas 14 client at `wepppy/climates/noaa/atlas14.py`, cut over the climate artifact exporter to the new boundary, removed `pfdf` from `docker/requirements-uv.txt`, and updated NOAA tests/docs to reference the new in-repo implementation and public NOAA PFDS endpoint contracts.

**Validation evidence**:
- `wctl run-pytest tests/climates/noaa/test_atlas14_client.py --maxfail=1` (`4 passed`)
- `wctl run-pytest tests/nodb/test_climate_artifact_export_service.py --maxfail=1` (`12 passed`)
- `wctl run-pytest tests/climates/noaa/test_atlas14_download.py --maxfail=1` (`4 skipped`, network-gated as expected)
- `wctl run-pytest tests --maxfail=1` (`1 failed` on unrelated baseline: `tests/nodb/test_ron_fetch_dem_copernicus.py::test_fetch_dem_uses_copernicus_backend_when_scheme_is_copernicus`, `Ron._cellsize` AttributeError)
- `wctl check-test-stubs` (pass)

**Archive Status**: Package closed with artifacts and tracker retained in-place.
