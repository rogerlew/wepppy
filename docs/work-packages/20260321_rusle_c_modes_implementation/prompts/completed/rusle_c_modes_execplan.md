# RUSLE C Modes: `observed_rap` and `scenario_sbs`

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This package delivers the missing RUSLE `C` factor implementation in `wepppy` using the two locked source modes from `wepppy/nodb/mods/rusle/specification.md`: `observed_rap` for current-condition RAP cover and `scenario_sbs` for disturbed-only static burn-severity scenarios. After completion, `wepppy` can produce auditable run-scoped `C` artifacts, lookup metadata, and DEM-aligned disturbed-family rasters without waiting for the future full `Rusle` controller.

User-visible outcome: a caller can run a focused `C` integration step, inspect `wd/rusle/c.tif`, inspect the `rusle/manifest.json` metadata for the mode used, and, for `scenario_sbs`, inspect the DEM-aligned `disturbed_class.tif` and lookup copy that explain how each pixel was classified.

## Progress

- [x] (2026-03-21 18:10Z) Reviewed root/NoDb/test/package instructions and the current RUSLE, Disturbed, RAP, and landuse implementation surfaces.
- [x] (2026-03-21 18:20Z) Authored the package brief, tracker, and this active ExecPlan.
- [x] (2026-03-21 18:35Z) Implemented shared `C` formula helpers, the runtime lookup substrate, and manifest helper modules.
- [x] (2026-03-21 18:45Z) Implemented `observed_rap` DEM-aligned computation, manifest writes, and catalog updates.
- [x] (2026-03-21 18:55Z) Implemented `scenario_sbs` disturbed-family raster generation, normalized SBS handling, lookup-copy artifact writes, and catalog updates.
- [x] (2026-03-21 19:10Z) Added targeted regression tests for formulas, nodata/masking, RAP band handling, lookup behavior, alignment, normalization, burn-only handling, non-burnable policy, and artifact writes.
- [x] (2026-03-21 19:20Z) Passed targeted `RUSLE C` tests and changed-file gates.
- [x] (2026-03-21 19:25Z) Completed Milestone 4 correctness review with no unresolved high/medium findings.
- [x] (2026-03-21 19:30Z) Completed Milestone 5 QA review with no unresolved high/medium findings.
- [x] (2026-03-21 19:40Z) Passed the full `wctl run-pytest tests --maxfail=1` sanity gate.
- [x] (2026-03-21 19:50Z) Closed package docs, archived the ExecPlan, and synchronized root tracking docs.

## Surprises & Discoveries

- Observation: The repo does not yet contain a full `Rusle` NoDb controller, but both `LS` and `K` are already shipped as focused integration runners under `wepppy/nodb/mods/rusle/`.
  Evidence: Existing modules `wepppy/nodb/mods/rusle/ls_integration.py` and `wepppy/nodb/mods/rusle/k_integration.py`.

- Observation: The Disturbed workflow’s current SBS remap is hillslope-based for WEPP management generation, which is insufficient for raster `RUSLE C`.
  Evidence: `wepppy/nodb/mods/disturbed/disturbed.py` updates `landuse.domlc_d` by TOPAZ hillslope key rather than writing a gridded disturbed-class raster.

- Observation: The `observed_rap` contract must preserve bare-ground values above `100` long enough for the formula clamp to act after subtraction; masking those values as nodata is incorrect.
  Evidence: Initial targeted test failure on `test_run_rusle_c_factor_observed_rap_writes_artifacts_manifest_and_catalog`, resolved by narrowing RAP nodata masking to true sentinel values.

## Decision Log

- Decision: Implement `C` as a focused `run_rusle_c_factor(...)` integration layer first, matching the existing `LS`/`K` delivery pattern.
  Rationale: This package is Milestone 5 only; the future full `Rusle` controller remains separate scope.
  Date/Author: 2026-03-21 / Codex.

- Decision: Use the disturbed mapping JSON plus explicit canonical-family normalization to build `scenario_sbs` inputs instead of reusing hillslope-level disturbed assignment.
  Rationale: The specification explicitly requires a DEM-aligned gridded disturbed-class raster and forbids keying by hillslope-only or raw treatment-suffixed classes.
  Date/Author: 2026-03-21 / Codex.

- Decision: Fail fast on unsupported unmasked classes or missing required lookup rows.
  Rationale: Root `AGENTS.md` and the RUSLE specification both require explicit failures over hidden recovery paths.
  Date/Author: 2026-03-21 / Codex.

## Outcomes & Retrospective

Delivered outcomes:

- Added new `wepppy/nodb/mods/rusle/` modules:
  - `c_formula.py`
  - `c_lookup.py`
  - `c_manifest.py`
  - `c_integration.py`
- Added the runtime lookup substrate:
  - `wepppy/nodb/mods/rusle/data/rusle_c_lookup.csv`
- Updated `wepppy/nodb/mods/rusle/__init__.py` exports with the new `C` helpers and integration runner.
- Added targeted tests:
  - `tests/nodb/mods/test_rusle_c_formula.py`
  - `tests/nodb/mods/test_rusle_c_lookup.py`
  - `tests/nodb/mods/test_rusle_c_integration.py`
- Completed dedicated review artifacts:
  - `artifacts/milestone4_review.md`
  - `artifacts/milestone5_qa_review.md`
  - `artifacts/final_validation_summary.md`

Validation retrospective:

- Targeted `RUSLE C` suite passed (`19 passed`).
- Changed-file broad-exception enforcement passed.
- Code-quality observability completed in observe-only mode.
- Full WEPPpy sanity gate passed (`2429 passed, 34 skipped`).

The package achieved the intended purpose: `wepppy` now has an auditable, run-scoped `C` integration layer for both locked v1 modes without waiting for the future full `Rusle` controller.

## Context and Orientation

Current state relevant to this task:

- `wepppy/nodb/mods/rusle/specification.md` locks the v1 `C` behavior:
  - `observed_rap`: `fg = clamp(100 - bare_ground_pct, 0, 100)`, `C = exp(-0.04 * fg)`, neutral non-surface terms.
  - `scenario_sbs`: disturbed-only static lookup by canonical disturbed family plus `sbs_class`, no time axis, burn only `forest`, `shrub`, and `tall_grass`.
- `wepppy/nodb/mods/disturbed/README.md` documents the static management defaults that back the initial `scenario_sbs` lookup table.
- `wepppy/wepp/management/data/disturbed.json` is the landuse-to-disturbed mapping source of truth that must be reused to derive canonical disturbed families from the landuse raster.
- `wepppy/nodb/core/landuse.py` exposes the run landuse raster at `Landuse.lc_fn`.
- `wepppy/nodb/core/ron.py` exposes the DEM at `Ron.dem_fn`.
- `wepppy/nodb/mods/disturbed/disturbed.py` already crops SBS rasters to the DEM grid using `raster_stacker(...)`, which is the existing alignment pattern to preserve.
- `wepppy/nodb/mods/rusle/ls_integration.py` and `wepppy/nodb/mods/rusle/k_integration.py` are the existing model for focused factor-integration runners that emit run-scoped artifacts and `rusle/manifest.json`.

Terms used in this plan:

- “DEM-aligned” means the raster has the same grid shape, transform, and coordinate reference system as `Ron.dem_fn`.
- “Canonical disturbed family” means the normalized class family used for lookup keys:
  - `forest`
  - `shrub`
  - `tall_grass`
  - plus explicit non-burnable/unburned families such as `bare`, `short_grass`, and `agriculture_crops` where the spec requires them.
- “SBS” means Soil Burn Severity. A normalized SBS 4-class raster uses:
  - `0` unburned
  - `1` low
  - `2` moderate
  - `3` high
  - `255` nodata

## Plan of Work

Milestone 0 is complete. The package scope, file structure, and failure policy are locked in the package brief and tracker.

Milestone 1 adds shared `C` helpers under `wepppy/nodb/mods/rusle/`. This includes the direct formula logic for converting bare ground to `fg`, converting `fg` to `C`, loading the runtime `rusle_c_lookup.csv`, canonicalizing disturbed families, and validating the lookup table.

Milestone 2 implements `observed_rap` in a focused integration runner. The runner will open the RAP multiband raster, align required bands to the DEM grid, compute `fg` from the bare-ground band, write `rusle/c.tif` plus a supporting `rusle/c_fg.tif`, update `rusle/manifest.json`, and refresh catalog entries for the written artifacts.

Milestone 3 implements `scenario_sbs`. The runner will align the landuse raster to the DEM grid, normalize landuse-to-disturbed semantics using `wepppy/wepp/management/data/disturbed.json`, write `rusle/disturbed_class.tif`, normalize or export the SBS raster into a 4-class DEM-aligned form, apply the static lookup rules, write `rusle/c.tif`, copy the lookup used into the run directory for auditability, update the manifest, and refresh catalog entries.

Milestone 4 is a dedicated correctness review pass over the changed source files, tests, manifest contract, and explicit failure paths. All high/medium findings must be resolved before moving on.

Milestone 5 is a dedicated QA review focused on regression coverage, fixture quality, markers, and validation completeness. All high/medium findings must be resolved before closeout.

Milestone 6 runs the required validation gates, updates the package docs and RUSLE specification milestone status, archives this plan under `prompts/completed/`, and synchronizes `AGENTS.md` plus `PROJECT_TRACKER.md`.

## Concrete Steps

Run commands from `/workdir/wepppy`.

1. Create and maintain the work-package docs.

    wctl doc-lint --path docs/work-packages/20260321_rusle_c_modes_implementation

2. Implement the new `RUSLE C` modules and lookup substrate.

    wctl run-pytest tests/nodb/mods/test_rusle_c_formula.py tests/nodb/mods/test_rusle_c_lookup.py tests/nodb/mods/test_rusle_c_integration.py --maxfail=1

3. Run changed-file gates and full sanity.

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl run-pytest tests --maxfail=1

4. Lint touched docs before closeout.

    wctl doc-lint --path AGENTS.md
    wctl doc-lint --path PROJECT_TRACKER.md
    wctl doc-lint --path docs/work-packages/20260321_rusle_c_modes_implementation
    wctl doc-lint --path wepppy/nodb/mods/rusle/specification.md

## Validation and Acceptance

The work is accepted when all of the following are true:

- `observed_rap` computes `C` from the exact locked formula and writes auditable artifacts.
- `scenario_sbs` writes a DEM-aligned `disturbed_class.tif`, applies only the allowed burnable families to SBS severity, and enforces the non-burnable policy exactly.
- Missing required lookup rows or unsupported unmasked classes fail with explicit errors.
- Targeted tests cover formulas, nodata/masking, RAP band handling, lookup behavior, alignment, normalization, burn-only application, non-burnable policy, and artifact writes.
- Dedicated correctness review and QA review artifacts exist with no unresolved high/medium findings.
- Required validation gates and doc-lint commands pass.

## Idempotence and Recovery

- The integration runner should overwrite its own run-scoped `rusle/` artifacts deterministically so repeated runs stay safe.
- Lookup loading and raster alignment must not mutate upstream source files; they only read source rasters and write run-local copies.
- If a validation step fails, fix the code or docs and rerun the same command; no destructive repository reset is required.

## Artifacts and Notes

Package artifacts will live under `docs/work-packages/20260321_rusle_c_modes_implementation/artifacts/`:

- `milestone4_review.md`
- `milestone5_qa_review.md`
- `final_validation_summary.md`

Runtime artifacts expected under `wd/rusle/`:

- `c.tif`
- `c_fg.tif` for `observed_rap`
- `disturbed_class.tif` for `scenario_sbs`
- `sbs_4class.tif` for `scenario_sbs`
- `c_lookup_used.csv` for `scenario_sbs`
- `manifest.json`

## Interfaces and Dependencies

The implementation must define:

- `wepppy.nodb.mods.rusle.c_formula.compute_fg_from_bare_ground_pct(...)`
- `wepppy.nodb.mods.rusle.c_formula.compute_c_from_fg_pct(...)`
- `wepppy.nodb.mods.rusle.c_lookup.normalize_disturbed_family(...)`
- `wepppy.nodb.mods.rusle.c_integration.run_rusle_c_factor(...)`

Dependencies:

- `rasterio` for reading/writing/reprojecting rasters.
- `wepppy.all_your_base.geo.raster_stacker` and `SoilBurnSeverityMap` where existing raster-normalization behavior is the repository standard.
- `wepppy.query_engine.activate.update_catalog_entry` for audit/catalog surfacing.
- No new external libraries.

---
Revision Note (2026-03-21, Codex): Initial active ExecPlan created for RUSLE `C` mode implementation, review, QA, and closeout.
Revision Note (2026-03-21, Codex): Completed Milestones 1-6, recorded review/QA/validation artifacts, and prepared the plan for archive under `prompts/completed/`.
