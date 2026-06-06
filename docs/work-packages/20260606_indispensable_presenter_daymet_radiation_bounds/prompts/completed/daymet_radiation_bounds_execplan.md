# ExecPlan: Close the `indispensable-presenter` Daymet Radiation Boundary Defect

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to
date as work proceeds.

This plan is maintained in accordance with
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

The observed-Daymet climate producer in WEPPpy generated radiation values for
`/wc1/runs/in/indispensable-presenter` that downstream openWEPP rejected as
outside its physical radiation bound. After this work, an operator or validation
agent can rebuild or revalidate that run and either see contract-compatible
radiation reach openWEPP, or see a precise fail-closed/branch-out explanation
that identifies the non-WEPPpy owner.

The work must not make invalid radiation acceptable by clipping it silently. The
desired observable outcome is either a tested WEPPpy producer fix or a
falsifiable handoff naming the owning boundary.

If Daymet is proven to be the genuine source of over-TOA radiation, the intended
producer-side correction is bounded normalization: clamp only affected daily
radiation rows to the computed maximum clear-sky/TOA daily radiation for that
date/location, record original value, bound, date, station/run context, and
normalization reason, and cover the rule with an ADR plus regression tests.

## Progress

- [x] (2026-06-06 20:01 UTC) Created work-package scaffold, tracker, initial
  evidence artifact, and this active ExecPlan.
- [x] (2026-06-06 20:01 UTC) Identified the concrete producer path:
  `build_observed_daymet()` copies `df["srad(l/day)"]` into CLI `rad`.
- [x] (2026-06-06 20:01 UTC) Captured initial static stats:
  source `srad(l/day)` max `989.1975619287764`; generated CLI `rad` max
  `989.0`.
- [x] (2026-06-06 21:03 UTC) Reproduced the downstream source-bound mechanism
  against saved `indispensable-presenter` artifacts: `1990-02-18` source
  `486.398513 Ly/day`, generated rounded CLI `rad=486`, baseline `sunmap.r3`
  bound `453.068716 Ly/day`.
- [x] (2026-06-06 21:03 UTC) Preserved existing WBVAL03
  evidence if direct rerun is unavailable.
- [x] (2026-06-06 21:03 UTC) Established the correct radiation-domain
  authority as baseline `sunmap.r3` horizontal daily potential and compared it
  to the
  Daymet-derived values for the failing dates.
- [x] (2026-06-06 21:03 UTC) Classified ownership as WEPPpy observed-Daymet
  producer-boundary normalization for genuine over-TOA Daymet source rows.
- [x] (2026-06-06 21:03 UTC) Added ADR-0006 for the
  source-bound normalization rule.
- [x] (2026-06-06 21:03 UTC) Added regression tests and implemented bounded
  normalization before CLI `rad` publication.
- [x] (2026-06-06 21:03 UTC) Validated real-run normalization on
  `indispensable-presenter`: 53 affected rows, post-normalization max excess
  over bound `0.0`.
- [x] (2026-06-06 21:03 UTC) Ran focused validation:
  `tests/nodb/test_climate_build_helpers.py` (`18 passed`) and additional
  climate suites (`29 passed`).
- [x] (2026-06-06 21:03 UTC) Updated package disposition artifacts.
- [x] (2026-06-06 21:07 UTC) Moved this ExecPlan to `prompts/completed/` and
  closed package lifecycle docs.

## Surprises & Discoveries

- Observation: The `indispensable-presenter` run is observed-Daymet mode, not a
  pure stochastic CLIGEN run.
  Evidence: `climate.log` contains `climate.catalog_id -> observed_daymet` and
  `running _build_climate_observed_daymet`.
- Observation: CLI radiation appears to be a direct rounded copy of Daymet
  `srad(l/day)`.
  Evidence: `daymet_1990-1995.parquet` has `srad(l/day)` max
  `989.1975619287764`; `wepp_cli.parquet` has `rad` max `989.0` on the same
  dates.
- Observation: The WBVAL03 blocker is a true baseline source-bound exceedance.
  Evidence: `1990-02-18` original Daymet-derived source value is
  `486.398513 Ly/day`, generated rounded CLI `rad=486`, and baseline
  `sunmap.r3` at latitude `43.73` is `453.068716 Ly/day`.
- Observation: Applying the bounded normalization to the saved
  `indispensable-presenter` Daymet artifact affects 53 rows and leaves
  post-normalization max excess over bound at `0.0`.
  Evidence:
  `docs/work-packages/20260606_indispensable_presenter_daymet_radiation_bounds/artifacts/execution_evidence.md`.

## Decision Log

- Decision: Investigate and classify the producer chain before editing
  production code.
  Rationale: The defect could be a WEPPpy conversion error, invalid upstream
  source value, temporal mismatch, or downstream bound mismatch. Silent clipping
  would hide the owning mechanism.
  Date/Author: 2026-06-06 20:01 UTC / Codex.
- Decision: Clamp genuine Daymet over-TOA source values to maximum clear-sky/TOA
  radiation after evidence proves source ownership.
  Rationale: Over-TOA source radiation is physically invalid for the WEPP CLI
  boundary, but observed-Daymet mode is still operationally valuable. A bounded,
  provenance-recorded normalization preserves the physical invariant without
  weakening openWEPP guards or hiding the source defect.
  Date/Author: 2026-06-06 20:55 UTC / User/Codex.

## Outcomes & Retrospective

Executed and closed. WEPPpy now computes the baseline `sunmap.r3` daily
horizontal potential for observed-Daymet CLI publication, normalizes only
over-TOA `srad(l/day)` rows to that bound, preserves source values and
provenance in the Daymet parquet, and writes a per-build CSV artifact when any
rows are normalized.

The concrete `indispensable-presenter` blocker is resolved at the producer
boundary: the `1990-02-18` source row that previously published rounded
`rad=486` is normalized to `453.068716 Ly/day`, which publishes rounded
`rad=453` and satisfies the downstream `radly <= sunmap.r3` guard.

Focused validation passed. Remaining work is outside this package: regenerate
or rebuild downstream openWEPP validation inputs from corrected WEPPpy climate
artifacts, then resume WBVAL03.

## Context and Orientation

WEPPpy owns run orchestration, climate generation, and generated WEPP input
files. openWEPP owns its simulation kernel and fail-closed runtime contracts.
The observed failure was detected by openWEPP, but the climate artifact was
produced by WEPPpy.

The reproduction run is:

    /wc1/runs/in/indispensable-presenter

The key run artifacts are:

    /wc1/runs/in/indispensable-presenter/climate/wepp.cli
    /wc1/runs/in/indispensable-presenter/climate/daymet_1990-1995.parquet
    /wc1/runs/in/indispensable-presenter/climate/wepp_cli.parquet
    /wc1/runs/in/indispensable-presenter/climate.log
    /wc1/runs/in/indispensable-presenter/climate.nodb

The producing code path begins in
`wepppy/nodb/core/climate.py::_build_climate_observed_daymet`. That method
selects the watershed centroid, station metadata, and year range, then calls
`wepppy/nodb/core/climate_build_helpers.py::build_observed_daymet`. The helper
retrieves Daymet data, writes `daymet_<start>-<end>.parquet`, runs CLIGEN to
produce a baseline CLI, and replaces CLI `rad` with Daymet
`df["srad(l/day)"]`.

The current openWEPP symptom to preserve is:

    CLIM-RUNTIME-E-017: runtime context symbol radly=486 is out of domain
    allowed 0 <= radly <= baseline sunmap horizontal daily potential (rpoth/r3)

The package evidence artifact is:

    docs/work-packages/20260606_indispensable_presenter_daymet_radiation_bounds/artifacts/initial_radiation_evidence.md

## Plan of Work

First, preserve the failure evidence. Read the current run artifacts and the
openWEPP WBVAL03 disposition. Record exact dates, radiation values, units, and
the downstream failing symbol. If direct openWEPP rerun is available locally,
rerun the smallest command that reproduces `CLIM-RUNTIME-E-017`; otherwise cite
the existing WBVAL03 evidence as the downstream reproduction.

Second, trace the producer chain. Read `build_observed_daymet()`, the Daymet
retrieval/conversion implementation under `wepppy/climates/daymet/`, and
`ClimateFile.replace_var()` under `wepppy/climates/cligen/`. Confirm whether
`srad(l/day)` is computed as daily total shortwave energy in langleys per day
and whether dates align exactly with generated CLI rows.

Third, establish authority for the bound. Use local Daymet radiation docs in
`wepppy/climates/daymet/solar_radiation_readme.md`, WEPP CLI format docs under
`wepppy/weppcloud/routes/usersum/input-file-specifications/climate-file.spec.md`,
and the openWEPP WBVAL/radiation source-boundary artifacts. The worker may read
openWEPP source/contracts, but must not edit openWEPP from this package.

Fourth, classify ownership. Use evidence to choose exactly one:

- WEPPpy producer defect: conversion, unit, daylength, temporal alignment, or
  CLI publication is wrong.
- Upstream Daymet/source input defect: WEPPpy accurately publishes a source
  value that violates the accepted physical/domain contract.
- openWEPP bound/contract defect: WEPPpy publishes valid WEPP CLI radiation and
  the downstream bound is too strict or mismatched to the producer's unit.

Fifth, land the appropriate outcome. If WEPPpy owns the defect, write a focused
regression test that fails before the fix and passes after. Then implement the
smallest producer-side correction or typed fail-closed validation. If Daymet is
proven to be the genuine source of over-TOA values, implement bounded
normalization to the computed maximum clear-sky/TOA daily radiation instead of
closing as an external HOLD. If openWEPP owns the mismatch, update package
disposition with a branch-out work package name, owner, and exact acceptance
criteria.

## Concrete Steps

Work from `/workdir/wepppy`.

1. Refresh local status and evidence:

       git status --short
       sed -n '1,28p' /wc1/runs/in/indispensable-presenter/climate/wepp.cli
       sed -n '1,60p' /wc1/runs/in/indispensable-presenter/climate.log

2. Inspect source and CLI parquet statistics:

       .venv/bin/python - <<'PY'
       from pathlib import Path
       import pandas as pd
       root = Path('/wc1/runs/in/indispensable-presenter/climate')
       source = pd.read_parquet(root / 'daymet_1990-1995.parquet')
       cli = pd.read_parquet(root / 'wepp_cli.parquet')
       print(source[['year', 'yday', 'dayl(s)', 'srad(W/m^2)', 'srad(l/day)']].nlargest(12, 'srad(l/day)').to_string(index=False))
       print(cli[['da', 'mo', 'year', 'julian', 'rad']].nlargest(12, 'rad').to_string(index=False))
       PY

3. Read producer implementation:

       sed -n '1440,1495p' wepppy/nodb/core/climate.py
       sed -n '225,276p' wepppy/nodb/core/climate_build_helpers.py
       rg -n "srad\\(|srad\\(l/day\\)|dayl|retrieve_historical_timeseries|replace_var" wepppy/climates/daymet wepppy/climates/cligen wepppy/nodb/core

4. Establish the accepted domain:

       sed -n '1,140p' wepppy/climates/daymet/solar_radiation_readme.md
       sed -n '100,170p' wepppy/weppcloud/routes/usersum/input-file-specifications/climate-file.spec.md
       sed -n '1,220p' /workdir/openWEPP/docs/work-packages/20260606-wbval03-snowmelt-wb-closure-defect-closure-001/artifacts/disposition.md

5. Implement only after ownership is proven:

   - If conversion/unit handling is wrong, add a focused test around the
     conversion or producer helper and correct the formula.
   - If publication/date alignment is wrong, add a fixture that proves the bad
     mapping and correct the date/index handling.
   - If source input violates the contract because Daymet genuinely supplies
     over-TOA values, add ADR-backed bounded normalization before CLI
     publication. Clamp only affected rows to the computed maximum clear-sky/TOA
     daily radiation and record date, units, original value, computed bound, and
     provenance.
   - If source input violates another non-normalizable contract, add typed
     validation before CLI publication so the invalid source fails closed with
     date, units, value, and bound evidence.
   - If openWEPP owns the mismatch, do not edit WEPPpy production code; write a
     branch-out handoff with the exact openWEPP contract/bound target.

6. Update docs before closure:

   - `package.md`
   - `tracker.md`
   - `artifacts/initial_radiation_evidence.md` or a new disposition artifact
   - this ExecPlan
   - `PROJECT_TRACKER.md`

## Validation and Acceptance

Acceptance requires evidence, not just a passing test.

If WEPPpy owns and fixes the defect:

- A regression test fails against the previous producer behavior and passes
  after the fix.
- A rebuilt or revalidated `indispensable-presenter` climate artifact no longer
  supplies radiation outside the accepted domain, or fails closed before
  generating invalid CLI.
- For genuine Daymet over-TOA source rows, generated CLI `rad` equals the
  computed maximum clear-sky/TOA bound for affected dates, unaffected rows
  remain unchanged, and an artifact records original values and normalization
  provenance.
- The package records before/after dates, values, units, and command outputs.
- No silent clamp, broad fallback, or guard weakening is introduced.

If WEPPpy does not own the defect:

- The disposition names the owner boundary and cites the exact evidence.
- A follow-up package is named with a defect ID, observed failure, suspected
  mechanism, files/contracts to inspect, and acceptance target.
- WEPPpy production code remains unchanged except for optional diagnostics that
  do not alter behavior.

Targeted validation commands should include the smallest relevant subset, then
broaden if production code changed:

    wctl run-pytest tests/nodb/test_climate_build_helpers.py --maxfail=1
    wctl run-pytest tests/nodb/test_climate_artifact_export_service.py --maxfail=1
    wctl run-pytest tests/climate/test_cligen_peak_intensity_contract.py --maxfail=1
    wctl doc-lint --path docs/work-packages/20260606_indispensable_presenter_daymet_radiation_bounds --path PROJECT_TRACKER.md

If shared climate code changes, also run:

    wctl run-pytest tests/nodb/test_climate_build_router_services.py --maxfail=1
    wctl run-pytest tests/nodb/test_user_defined_cli_parquet.py --maxfail=1

## Idempotence and Recovery

Reading run artifacts is safe and repeatable. Do not mutate
`/wc1/runs/in/indispensable-presenter` until the mechanism is classified and the
package has a safe rebuild or repair plan. If the run artifact disappears,
continue from the preserved evidence artifact and create a minimal fixture from
the captured rows.

Production edits should be additive and test-backed. If a proposed fix requires
formula, threshold, unit-conversion, or fallback behavior changes, add or update
an ADR before merge per
`docs/standards/parameterization-adr-standard.md`.

## Artifacts and Notes

Primary artifact:

    docs/work-packages/20260606_indispensable_presenter_daymet_radiation_bounds/artifacts/initial_radiation_evidence.md

Create a separate disposition artifact before closure if the final outcome is
more than a small tracker update.

## Interfaces and Dependencies

No new external dependencies are expected. Use existing WEPPpy climate
retrieval, CLIGEN parsing, parquet inspection, and `wctl` test wrappers. The
package may inspect sibling openWEPP files for evidence, but all WEPPpy package
edits must stay in `/workdir/wepppy` unless the user explicitly authorizes a
cross-repo package.
