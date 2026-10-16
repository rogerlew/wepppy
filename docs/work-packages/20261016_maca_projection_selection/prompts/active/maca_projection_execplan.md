# Implement MACA selection and correct CCSM4 requests

This ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep Progress,
Surprises & Discoveries, Decision Log and Outcomes & Retrospective current.

## Purpose

Users can select a MACA climate model and emissions scenario above the future
year controls. A saved selection controls the generated climate instead of the
previous fixed GFDL-ESM2G/RCP8.5 request. CCSM4 requests use the provider's actual
ensemble member r6i1p1. An ensemble member identifies one simulation realization.

## Progress

- [x] Inspect current form/parser/builder/client and retain live CCSM4 diagnosis.
- [x] Draft canonical contract, ADR and preimplementation checkpoint.
- [ ] Obtain independent reviews and commit documentation checkpoint.
- [ ] Implement registry, client patch, parser/persistence, UI and build propagation.
- [ ] Validate generated artifacts, bounded live data, UI, regression and final review.

## Surprises & Discoveries

The client hardcodes r1i1p1 in every filename. Only CCSM4 failed the 40-pair
precipitation probe; changing its member to r6i1p1 passed all seven client
variables in both scenarios. The form already shows sections based on dataset
input metadata and serializes named controls; new JavaScript is not required
unless regression evidence exposes a missing integration point.

## Decision Log

On 2026-10-16 the operator authorized implementation. Preserve default and
existing capabilities. Use one combined selection, matching EDDE. Do not refactor
publication or add numerical corrections as part of this feature. Keep existing
run logs/PRN/CLI as outputs; no new artifact format is necessary for selection.

## Outcomes & Retrospective

Pending implementation and validation. No deployment is requested or claimed.

## Context and orientation

`wepppy/nodb/locales/climate_catalog.py` describes the Future dataset and visible
inputs. `wepppy/weppcloud/templates/controls/climate_pure.htm` renders shared
Pure UI controls; `controllers_js/climate.js` toggles and serializes them.
`wepppy/nodb/core/climate_input_parser.py` mutates Climate under a rollback-aware
lock. `climate.py` saves state and calls `climate_build_helpers.build_future`.
That helper currently calls only `retrieve_rcp85_timeseries` from
`wepppy/climates/downscaled_nmme_client.py`, writes ws.prn and invokes native
CLIGEN to write wepp.cli. The RQ route catches field validation before enqueue.

## Milestones and plan of work

First commit the reviewed checkpoint, including MACA contract, ADR and shared
contract pointers. Then add a dependency-free MACA catalog module with the 20
models, member mapping, 40 pairs, display labels, default and exact parsing.
Patch the client URL to use the resolved member. Retain wrapper signatures.

Next add Climate selection/default and options properties plus the stub surface.
Include the additive field in parser rollback; process it only for Future mode.
Validate before setting state and again at the build boundary. Extend the helper
with optional model/scenario arguments preserving prior callers and use generic
retrieve_timeseries. Log actual source selection. Update the Future catalog's
input list and help, and add a select before year inputs using the EDDE pattern.
Map selection errors to the current RQ validation response; do not change wiring.

Finally test request-to-disk-to-build propagation, malformed rollback, actual
URLs, and template order/selection. Use fixture source responses for deterministic
native CLI generation and read precipitation/dates from the output. Exercise a
bounded live CCSM4 full year with real retrieval and CLIGEN, retaining source
and output identity summaries. Read the exact wepp/runs/p*.cli copied by WeppPrepService.prep_climates; do not claim full WEPP execution if only climate generation was run.

## Concrete steps and validation

Work in `/home/workdir/wepppy`, without switching branch. Run focused tests via
`wctl run-pytest` for new MACA client/selection modules, climate parser/catalog/
facade helpers, climate RQ validation and Pure control rendering. Run
`wctl run-npm lint`, `wctl run-npm test`, stub checks for changed API surface,
docs lint and changed broad-exception enforcement. Run the broad pytest gate
after focused checks; report missing-browser/environment failures precisely.
Use existing Docker runtime for live Python/native generation, with scratch
paths outside canonical runs and bounded source dates. Inspect CLI/PRN values,
source URLs/member identity and visible selection behavior, not file existence.
Verify existing working/failed/completed status and normal browser/download
visibility for climate artifacts and logs. Roundtrip the generated artifacts and
climate.nodb through canonical archive_rq/restore_archive_rq, comparing bytes
and saved selection. Include Tmax/Tmin semantic readback alongside precipitation.

## Idempotence and recovery

No production mutations or bulk project migrations. Tests and probes use fresh
temporary directories. Failed probes leave diagnostic evidence; retry only when
the cause is understood. A rollback reader that ignores `_maca_projection`
would silently revert nondefault rebuilds, so retain selection-aware readers or
explicitly reset those projects before rollback. Preserve unrelated dirty files.

## Artifacts and interfaces

Retain checkpoint/reviews/test/live-output summaries under this package's
`artifacts/`; source-member diagnosis is in `docs/dev-notes/`. Shared registry
constants define the default and options; parsing returns the model and existing
client scenario token. Existing dependencies and serving endpoint are sufficient.

Initial plan authored 2026-10-16 UTC from the operator's accepted selection and
attribution decisions; implementation remains pending checkpoint review.
