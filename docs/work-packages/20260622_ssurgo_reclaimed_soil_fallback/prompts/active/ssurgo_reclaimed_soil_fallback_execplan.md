# Fix SSURGO Reclaimed Soil Conversion and Fallback Transparency

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document follows `docs/prompt_templates/codex_exec_plans.md`. It is self-contained enough for a contributor with only this repository checkout to implement and validate the work.

## Purpose / Big Picture

WEPPcloud should use current SSURGO/gNATSGO soil map units when they exist. In a production run for `hard-line-foothold / disturbed9002`, Topaz IDs 573 and 581 were mapped to current reclaimed Fairpoint MUKEYs, but WEPPcloud rejected those soils as having "no horizons" and silently substituted an unrelated valid Shelocta-Latham MUKEY. After this plan is implemented, the Fairpoint MUKEYs `3294459`, `3294460`, and `3294461` build valid WEPP soil files, and any remaining invalid-soil substitution is visible in run artifacts instead of hidden.

## Progress

- [x] (2026-06-22 18:28 UTC) Created the work package and initial ExecPlan from production investigation evidence.
- [ ] Draft ADR-0008 for restrictive-layer and fallback behavior.
- [ ] Add deterministic Fairpoint fixture data and failing tests for MUKEYs `3294459`, `3294460`, and `3294461`.
- [ ] Implement the SSURGO-to-WEPP conversion fix.
- [ ] Implement additive fallback transparency for raw dominant MUKEYs and substitution reasons.
- [ ] Update documentation and run validation gates.
- [ ] Complete QA review and disposition findings.

## Surprises & Discoveries

- Observation: The production issue is not an old raster or stale tabular cache. The run used `ssurgo/gNATSGSO/2025`, and the raw raster-selected MUKEYs for Topaz 573 and 581 include Fairpoint reclaimed MUKEYs.
  Evidence: `soils/ssurgo.tif.meta` in run `hard-line-foothold` records WMesque source `/geodata/ssurgo/gNATSGSO/2025/.vrt`; raster-mask checks showed `3294459`, `3294460`, and `3294461` dominate the affected hillslopes.

- Observation: Fairpoint rows are current in live NRCS SDA and present in the run-local SQLite cache.
  Evidence: `component` rows for `3294459`, `3294460`, and `3294461` have `muname` values `Fairpoint silt loam, ... reclaimed`.

- Observation: The converter marks Fairpoint invalid because the first valid horizon has `ksat_r < 2.0 um/s`, which sets the restrictive layer before any WEPP layers are counted.
  Evidence: Fairpoint logs show `found 2 layers`, `horizons mask: [True, True]`, `identified 0 layers`, and `Validity: no horizons`.

## Decision Log

- Decision: Treat the work as a conversion/fallback bug, not a raster replacement.
  Rationale: Both production 2025 gNATSGO and gSSURGO rasters contain Fairpoint MUKEYs in the affected area.
  Date/Author: 2026-06-22 18:28 UTC / Codex.

- Decision: Require a parameterization ADR before merge.
  Rationale: The fix changes how a threshold affects generated WEPP layers and how fallback substitutions are applied or reported.
  Date/Author: 2026-06-22 18:28 UTC / Codex.

## Outcomes & Retrospective

Implementation has not started. At package creation, the desired outcome is defined as valid Fairpoint generated soil outputs plus observable fallback provenance.

## Context and Orientation

The core conversion code is in `wepppy/soils/ssurgo/ssurgo.py`. `SurgoSoilCollection` fetches SSURGO tabular rows and constructs `WeppSoil` objects. A `Horizon` wraps one NRCS `chorizon` row. `WeppSoil._analyze_restrictive_layer()` scans valid horizons and uses the `res_lyr_ksat_threshold` value, currently `2.0` in SSURGO units of micrometers per second, to decide where a restrictive layer begins. `WeppSoil.valid()` requires `num_layers > 0`.

The gridded WEPPcloud build path is in `wepppy/nodb/core/soils.py`, method `_build_gridded()`. It retrieves a SSURGO/gNATSGO raster, builds WEPP soils for all raster MUKEYs, computes each hillslope's dominant raster MUKEY, then replaces any dominant MUKEY that did not produce a valid WEPP soil with the run's most common valid MUKEY. Today that replacement overwrites the original dominant MUKEY in `domsoil_d` and `ssurgo_domsoil_d`, so users cannot see that a substitution occurred.

The target production evidence comes from run `hard-line-foothold / disturbed9002` on `wepp1`. Topaz IDs 573 and 581 had final disturbed soil `2451115-silt loam-forest`, but the raw raster values in those hillslopes were mostly `3294459`, `3294460`, and `3294461`, which are Fairpoint reclaimed map units.

## Plan of Work

First, draft `docs/adrs/ADR-0008-ssurgo-reclaimed-soil-restrictive-layer-fallback.md`. The ADR must decide the exact behavior for a valid mineral profile whose first valid horizon is below the restrictive-layer threshold. The package expectation is that such a profile must not collapse to zero WEPP layers. A conservative candidate behavior is to keep the first valid horizon as a low-conductivity WEPP surface layer and only allow a restrictive-layer break after at least one valid layer has been emitted. The ADR must also decide whether invalid dominant soils continue to substitute by default or fail in selected cases; if substitution continues, raw provenance must be recorded.

Next, add deterministic tests before changing behavior. Create a fixture or helper under `tests/soils/` that provides SSURGO-like component and horizon rows for MUKEYs `3294459`, `3294460`, and `3294461`. Do not depend on live NRCS network access in CI. The fixture must include the Fairpoint major component at 95 percent and two horizons: `A` from 0 to 9 cm with `ksat_r=0.1`, and `C` from 9 to 152 cm with `ksat_r=0.014`, along with the other fields needed by `Horizon.valid()`. Add tests proving current behavior fails before the fix and passes after it.

Then modify `wepppy/soils/ssurgo/ssurgo.py`. Keep the edit narrowly scoped to restrictive-layer analysis and validity. Do not weaken `Horizon.valid()` merely to force all rows valid. The goal is to represent valid low-conductivity horizons, not to hide missing data. The generated `.sol` writer must receive at least one valid layer for each Fairpoint MUKEY, and logs should no longer say `Validity: no horizons` for these three MUKEYs.

After the conversion fix, update fallback transparency in `wepppy/nodb/core/soils.py`. Preserve the pre-substitution dominant MUKEY dictionary from `identify_mode_single_raster_key()` before replacements occur. Add only backward-compatible state and artifacts. A reasonable implementation is a new serialized dictionary for raw dominant SSURGO MUKEYs plus a substitution dictionary keyed by `topaz_id` containing original MUKEY, replacement MUKEY, and reason. If adding `soils.parquet` columns, make them nullable and additive. Add legacy-load defaults for old `soils.nodb` files.

Finally, update docs, validation evidence, and QA review. `wepppy/soils/ssurgo/ssurgo.md` should describe first-horizon restrictive handling and fallback provenance. `wepppy/soils/README.md` should mention that generated artifacts can distinguish raw SSURGO dominant MUKEYs from final model-ready soil assignments when substitutions occur. Complete `artifacts/qa_review_findings.md` and disposition every finding in the tracker.

## Concrete Steps

Work from `/workdir/wepppy`.

1. Draft the ADR:

       cp docs/adrs/ADR-template.md docs/adrs/ADR-0008-ssurgo-reclaimed-soil-restrictive-layer-fallback.md

   Fill in the required parameterization provenance fields from `docs/standards/parameterization-adr-standard.md`. Link the ADR from `package.md` and `tracker.md`.

2. Add Fairpoint tests:

       wctl run-pytest tests/soils/<new_fairpoint_test>.py --maxfail=1

   Before the fix, expect the Fairpoint tests to fail because the generated `WeppSoil` has zero layers or is invalid. After the fix, expect all three MUKEYs to build valid `.sol` outputs.

3. Implement the conversion fix in `wepppy/soils/ssurgo/ssurgo.py`. Re-run:

       python -m py_compile wepppy/soils/ssurgo/ssurgo.py
       wctl run-pytest tests/soils/<new_fairpoint_test>.py --maxfail=1

4. Add fallback transparency tests and implementation in `wepppy/nodb/core/soils.py`. Re-run:

       python -m py_compile wepppy/nodb/core/soils.py
       wctl run-pytest tests/nodb/<new_fallback_test>.py --maxfail=1

5. Run combined targeted tests:

       wctl run-pytest tests/soils/<new_fairpoint_test>.py tests/nodb/<new_fallback_test>.py --maxfail=1

6. Update docs and run doc lint:

       wctl doc-lint --path docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/package.md
       wctl doc-lint --path docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/tracker.md
       wctl doc-lint --path wepppy/soils/ssurgo/ssurgo.md
       wctl doc-lint --path wepppy/soils/README.md

7. Complete QA review. Save the review in `docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/artifacts/qa_review_findings.md`, update the tracker with finding dispositions, and rerun any tests required by accepted findings.

## Validation and Acceptance

The package is accepted when a human can see these behaviors:

- Running the Fairpoint tests builds valid WEPP soils for `3294459`, `3294460`, and `3294461`.
- Generated Fairpoint `.sol` descriptions include Fairpoint/reclaimed map unit names and no Shelocta-Latham fallback.
- The test for a first valid horizon below the restrictive threshold shows at least one WEPP layer is emitted.
- The gridded fallback test proves raw dominant MUKEYs are preserved separately from final substituted model-ready MUKEYs.
- Legacy runs without new fallback-provenance fields still load.
- Targeted tests pass, and full `wctl run-pytest tests --maxfail=1` passes or an unrelated existing blocker is documented.

## Idempotence and Recovery

All changes should be additive and test driven. Test fixtures should be deterministic and safe to re-run. If a generated temporary run directory is used in tests, create it under pytest's temporary directory and clean it through fixture teardown. Do not mutate production run directories while implementing this package. If an ADR decision changes mid-implementation, update this ExecPlan, `package.md`, and `tracker.md` before continuing.

## Artifacts and Notes

Production investigation evidence to preserve in review notes:

    Run: /geodata/wc1/runs/ha/hard-line-foothold
    Config: disturbed9002
    Source raster: ssurgo/gNATSGSO/2025/
    Topaz 573 raw top MUKEYs: 3294459, 3294460, 3294461
    Topaz 581 raw top MUKEYs: 3294460, 3294459, 536184, 536155, 3294461
    Final observed soil: 2451115-silt loam-forest
    Fairpoint invalid log signature: found 2 layers; horizons mask [True, True]; identified 0 layers; Validity: no horizons

## Interfaces and Dependencies

Do not add new external dependencies. Use existing Python test tooling and `wctl run-pytest`.

Expected code interfaces after implementation:

- `wepppy.soils.ssurgo.ssurgo.WeppSoil.valid()` returns `True` for valid Fairpoint reclaimed profiles represented by MUKEYs `3294459`, `3294460`, and `3294461`.
- `wepppy.nodb.core.soils.Soils` exposes additive raw/fallback provenance without breaking existing `domsoil_d` and `ssurgo_domsoil_d` consumers.
- Any new NoDb fields have defaults in `_post_instance_loaded`.
- Any new parquet columns are additive and nullable.
