# Restore dNBR upload and job status

## Purpose and context

The canonical project DEM has a statistics-only GDAL PAM sidecar. The upload
passes this internal DEM to the strict uploaded-raster decoder, which refuses
all sidecars. The Wallow uploaded IMG itself decodes successfully. Separately,
PFDF strips controlBase HTML and shares its message node with the job link;
terminal attempts are not reattached after reload.

## Progress

- [x] Diagnose project failure and UI causes.
- [x] Review bounded internal statistics metadata contract; checkpoint `7447e6243`.
- [x] Repair internal DEM preparation and standard status binding.
- [x] Focused tests, frontend gates, bundle, authenticated upload/reload check.

## Surprises & Discoveries

Failed job `0d4bc387-010e-44f7-8d3b-ef5f20691021` rejects `dem.tif.aux.xml`.
It contains only STATISTICS_* metadata. The real source IMG opens normally.
The PFDF adapter flattens div/span layout and overwrites the job hint.

## Decision Log

- Reuse RUSLE's controlBase adapter and dedicated ui.job_hint. Restore tracking
  of the latest attempt, including failures, without repeatedly resetting it.
- Keep uploaded files strict. Admit only bounded, structurally validated
  statistics-only PAM on internal local GeoTIFFs, with PAM disabled during reads.
  Stage a self-contained reference DEM using existing read_raster/prepare.
- No schema removal or rename. An internal prepared DEM is additive, included
  in accepted artifact signatures; existing attempts remain readable/retryable.

## Plan and validation

Use the existing production upload/model test with a real stats sidecar, plus
hostile/meaningful sidecar rejection tests. Verify DEM samples, support and grid
survive preparation. Keep uploaded dNBR sidecar refusal tests passing. Test
failed-state hydration and actual controlBase HTML/links, run npm lint/tests,
rebuild the bundle, and use the authenticated actual project to verify failure
reload before retrying the stored candidate through the UI. Do not run M1 or
change other user inputs. Rollback source edits leaves prior accepted artifacts
and failed attempts intact; do not edit their NoDb files manually.

Review found newly admitted external masks needed dependency snapshots and
raw-source hashes; fixed and tested appearance/removal/mutation. Shared job-status
and jobinfo callbacks now ignore superseded jobs, with resolve/reject race tests.

## Outcomes & Retrospective

Completed: actual stored Wallow retry finished in about 15 seconds; accepted
10 m raster covers 100% of the watershed with Auto scale 0.001. Failed and
successful job state/link/Details survive reload. All review findings closed.
136 focused raster tests, subsequent source-freshness regressions, and 861
frontend tests passed. Full Python suite remained on operator hold.

The controller stub previously hid markup loss and lifecycle races; use real
controlBase rendering and delayed-response regressions for these seams. Browser
functional checks passed; direct CDP capture succeeded after screenshot-helper
timeouts and the live control was visually inspected. See validation.
