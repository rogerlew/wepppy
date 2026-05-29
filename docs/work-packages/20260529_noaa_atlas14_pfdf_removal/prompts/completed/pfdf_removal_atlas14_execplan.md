# ExecPlan: Remove `pfdf` and Ship WEPPpy-Owned NOAA Atlas 14 Client

Outcome: Completed implementation and validation for Atlas 14 client ownership cutover; `pfdf` runtime dependency removed.

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, WEPPpy no longer depends on GPLv3 `pfdf` to fetch NOAA Atlas 14 frequency CSVs. WEPPpy now owns a narrow Atlas 14 client implementation sourced from publicly documented NOAA PFDS endpoint contracts. User-visible behavior remains unchanged at the climate exporter boundary: NOAA output is optional, and climate build completion does not fail on NOAA no-coverage or transient unavailability.

## Progress

- [x] (2026-05-29 20:25 UTC) Created work-package scaffold and active ExecPlan.
- [x] (2026-05-29 20:25 UTC) Mapped `pfdf` usage/dependency surfaces in runtime code, tests, and dependency manifests.
- [x] (2026-05-29 20:40 UTC) Captured NOAA Atlas 14 endpoint contract notes from public docs and live endpoint responses.
- [x] (2026-05-29 20:45 UTC) Implemented WEPPpy-owned Atlas 14 client module with deterministic URL/parameter handling and NOAA-style artifact rendering.
- [x] (2026-05-29 20:46 UTC) Cut over `ClimateArtifactExportService.download_noaa_atlas14_intensity` to the in-repo client.
- [x] (2026-05-29 20:50 UTC) Updated unit/integration tests and NOAA docs for the new client boundary.
- [x] (2026-05-29 20:50 UTC) Removed `pfdf` dependency entries and validated cleanup.
- [x] (2026-05-29 20:57 UTC) Ran targeted validations and documented outcomes in tracker.

## Surprises & Discoveries

- Observation: NOAA PFDS provides a stable scrape endpoint (`/cgi-bin/new/cgi_readH5.py`) returning JS-style assignments (`result`, `quantiles`, `upper`, `lower`, metadata) that are easier to parse than rendered print-page HTML.
  Evidence: Live request to `https://hdsc.nws.noaa.gov/cgi-bin/new/cgi_readH5.py?lat=39.0&lon=-105.0&type=pf&data=intensity&units=metric&series=pds` returned deterministic assignment payload.

- Observation: Runtime use of `pfdf` was isolated to one production-path import in `wepppy/nodb/core/climate_artifact_export_service.py`.
  Evidence: Repo search confirmed no other production-path imports after cutover.

## Decision Log

- Decision: Keep replacement scope limited to Atlas 14 downloader behavior used by climate artifact export.
  Rationale: Directly resolves licensing concern with minimal blast radius and no unrelated refactors.
  Date/Author: 2026-05-29 / Codex.

- Decision: Preserve optional NOAA artifact behavior and existing retry/no-coverage contract.
  Rationale: Existing operator/user workflows assume NOAA failures are non-fatal to climate build completion.
  Date/Author: 2026-05-29 / Codex.

- Decision: Implement client against NOAA `cgi_readH5.py` response contract instead of scraping rendered HTML tables.
  Rationale: Simpler and more deterministic parsing, explicit field contracts, and straightforward conversion into existing NOAA artifact shape consumed by WEPPcloud routes.
  Date/Author: 2026-05-29 / Codex.

## Outcomes & Retrospective

Completed as planned.

Outcome summary:
- Added WEPPpy-owned Atlas 14 client: `wepppy/climates/noaa/atlas14.py`.
- Added NOAA client package export: `wepppy/climates/noaa/__init__.py`.
- Replaced runtime `pfdf` import in climate exporter with in-repo client.
- Removed `pfdf` dependency from `docker/requirements-uv.txt`.
- Updated NOAA test/doc surfaces to new client path and public API references.
- Added deterministic unit tests for client boundary (`tests/climates/noaa/test_atlas14_client.py`).
- Preserved existing climate exporter retry/no-coverage semantics via existing wrapper logic.

Validation summary:
- `wctl run-pytest tests/climates/noaa/test_atlas14_client.py --maxfail=1` -> `4 passed`
- `wctl run-pytest tests/nodb/test_climate_artifact_export_service.py --maxfail=1` -> `12 passed`
- `wctl run-pytest tests/climates/noaa/test_atlas14_download.py --maxfail=1` -> `4 skipped` (network-gated as expected)
- `wctl check-test-stubs` -> pass
- `wctl run-pytest tests --maxfail=1` -> unrelated baseline failure (`tests/nodb/test_ron_fetch_dem_copernicus.py::test_fetch_dem_uses_copernicus_backend_when_scheme_is_copernicus`, `Ron._cellsize` AttributeError)

## Context and Orientation

Key touched files:

- Runtime cutover:
  - `/home/workdir/wepppy/wepppy/nodb/core/climate_artifact_export_service.py`
- New owned client:
  - `/home/workdir/wepppy/wepppy/climates/noaa/atlas14.py`
  - `/home/workdir/wepppy/wepppy/climates/noaa/__init__.py`
- Test/doc updates:
  - `/home/workdir/wepppy/tests/nodb/test_climate_artifact_export_service.py`
  - `/home/workdir/wepppy/tests/climates/noaa/test_atlas14_client.py`
  - `/home/workdir/wepppy/tests/climates/noaa/test_atlas14_download.py`
  - `/home/workdir/wepppy/tests/climates/noaa/README.md`
- Dependency manifest:
  - `/home/workdir/wepppy/docker/requirements-uv.txt`

Public API references used:
- `https://www.weather.gov/owp/hdsc_faqs`
- `https://hdsc.nws.noaa.gov/cgi-bin/new/cgi_readH5.py?...`

## Plan of Work

Plan executed end-to-end. No further implementation steps remain for this package.

## Concrete Steps

Executed commands (from `/home/workdir/wepppy`):

- `wctl run-pytest tests/climates/noaa/test_atlas14_client.py --maxfail=1`
- `wctl run-pytest tests/nodb/test_climate_artifact_export_service.py --maxfail=1`
- `wctl run-pytest tests/climates/noaa/test_atlas14_download.py --maxfail=1`
- `wctl check-test-stubs`
- `wctl run-pytest tests --maxfail=1`

## Validation and Acceptance

Acceptance criteria met:
- Runtime climate exporter no longer imports `pfdf`.
- Climate exporter behavior contract remains compatible for success/retry/no-coverage paths.
- Dependency manifest no longer includes `pfdf`.
- NOAA test/docs now point to WEPPpy-owned client and public NOAA references.

Residual note:
- Full-suite run still stops on unrelated baseline Ron failure documented above.

## Idempotence and Recovery

Migration was additive-first and completed safely. If NOAA endpoint contract drifts later, the owned client now provides a single deterministic boundary for updates.

## Artifacts and Notes

- Package root: `docs/work-packages/20260529_noaa_atlas14_pfdf_removal/`
- Tracker: `docs/work-packages/20260529_noaa_atlas14_pfdf_removal/tracker.md`

## Interfaces and Dependencies

No new external dependency added. Client uses existing `requests` dependency and standard library parsing/writing.

## Revision Notes

- 2026-05-29 / Codex: Initial ExecPlan authored.
- 2026-05-29 / Codex: Completed implementation, validation, and closure documentation.
