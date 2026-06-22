# SSURGO Reclaimed Soil Conversion and Fallback Transparency

**Status**: Complete; unrelated full-suite blocker documented (2026-06-22)
**Timezone**: UTC

## Overview

WEPPcloud is selecting current Fairpoint reclaimed SSURGO map units from the 2025 gNATSGO raster, but the SSURGO-to-WEPP conversion rejects those soils because the restrictive-layer rule can leave zero usable WEPP layers when the first horizon has low saturated hydraulic conductivity. The gridded soil builder then silently replaces invalid dominant MUKEYs with the run's most common valid MUKEY, making current reclaimed mined-land areas appear as older Shelocta-Latham soils. This package fixes both behaviors: valid reclaimed profiles must not collapse to "no horizons", and any remaining fallback substitution must preserve and expose the original dominant MUKEY.

## Objectives

- Make reclaimed mined-land SSURGO profiles with valid tabular horizons produce valid WEPP soil files instead of being rejected as zero-layer profiles.
- Add regression coverage for integrated Fairpoint MUKEYs `3294459`, `3294460`, and `3294461`.
- Preserve the raw raster-selected dominant MUKEY for each hillslope before any invalid-soil fallback substitution.
- Record and expose any invalid-MUKEY substitution with original MUKEY, replacement MUKEY, and reason, without removing existing user-visible keys or columns.
- Update soil documentation and add a parameterization ADR for the restrictive-layer and fallback behavior changes.
- Require QA review with written finding disposition before package closure.

## Scope

### Included

- `wepppy/soils/ssurgo/ssurgo.py` reclaimed-profile conversion fix:
  - Audit `Horizon.valid()`, `WeppSoil._analyze_restrictive_layer()`, `WeppSoil.valid()`, and WEPP `.sol` writers for the zero-layer failure mode.
  - Ensure valid mineral profiles are not rejected solely because the first valid horizon is below the restrictive-layer `ksat_r` threshold.
  - Preserve physically explicit restrictive-layer behavior according to the required ADR decision.
- `wepppy/nodb/core/soils.py` fallback transparency:
  - Preserve pre-substitution gridded dominant MUKEYs in additive NoDb state.
  - Keep current build continuity for invalid soils unless the ADR explicitly chooses fail-fast for a subset of cases.
  - Record substitution details in a machine-readable run artifact and/or additive `soils.parquet` columns.
  - Ensure `ssurgo_domsoil_d` semantics are documented after the change; if a new raw-map dictionary is introduced, use an additive name such as `raw_ssurgo_domsoil_d` or `ssurgo_raw_domsoil_d`.
- Regression tests:
  - Unit tests for Fairpoint profile conversion using deterministic fixture data for MUKEYs `3294459`, `3294460`, and `3294461`.
  - Unit tests proving the first-horizon restrictive case produces at least one WEPP layer and no "Validity: no horizons" rejection.
  - NoDb/gridded builder tests proving invalid-MUKEY fallback preserves original MUKEY and substitution reason.
  - Integrated generated-output test that builds `.sol` outputs for `3294459`, `3294460`, and `3294461` and verifies the descriptions include Fairpoint/reclaimed map unit names, not Shelocta fallback names.
- Documentation:
  - Update `wepppy/soils/ssurgo/ssurgo.md` and `wepppy/soils/README.md` with the reclaimed-profile and fallback provenance behavior.
  - Add an ADR under `docs/adrs/` before merge because this package changes threshold/fallback behavior that affects generated model inputs.
- Review:
  - Complete a QA review artifact under `artifacts/qa_review_findings.md`.
  - Disposition every QA finding as accepted/fixed, rejected with rationale, or deferred with owner and follow-up.

### Explicitly Out of Scope

- Replacing the production gNATSGO/gSSURGO raster source.
- Reworking NRCS Soil Data Access queries beyond fields needed by existing SSURGO conversion.
- Changing unrelated SSURGO formulas, Rosetta estimates, erosion formulas, or `ksflag` semantics.
- Removing invalid-soil fallback globally unless explicitly approved in the ADR and covered by compatibility tests.
- Migrating old run directories before they rebuild soils.

## Implementation Fidelity and Evidence

- **Fidelity target**: bugfix with observable generated-output evidence.
- **Authoritative source path(s)**:
  - `wepppy/soils/ssurgo/ssurgo.py`
  - `wepppy/nodb/core/soils.py`
  - `wepppy/soils/ssurgo/ssurgo.md`
- **Cutover proof required**: a generated-output test must build valid WEPP `.sol` files for MUKEYs `3294459`, `3294460`, and `3294461`; a gridded fallback test must show raw dominant MUKEYs remain available after substitution.
- **Acceptance evidence type**: both fixture-only and generated-output. Live NRCS access may be used for an operator validation note, but CI tests must not require live NRCS network access.

## Stakeholders

- **Primary**: WEPPcloud users modeling reclaimed mined lands and disturbed watersheds.
- **Reviewers**: implementation agent, maintainer/operator, QA reviewer.
- **Security Reviewer**: not required unless implementation unexpectedly changes route/input/file access surfaces.
- **Informed**: maintainers of SSURGO conversion, NoDb soils state, disturbed soil modification, and generated run-artifact schemas.

## Success Criteria

- [x] `3294459`, `3294460`, and `3294461` build valid WEPP soil files from deterministic fixture data.
- [x] The Fairpoint tests prove at least one WEPP layer is emitted for the first-horizon restrictive case.
- [x] Generated `.sol` descriptions for `3294459`, `3294460`, and `3294461` include Fairpoint/reclaimed names and do not fall back to Shelocta-Latham.
- [x] Gridded invalid-soil fallback preserves raw dominant MUKEYs and records substitution details with original MUKEY, replacement MUKEY, and reason.
- [x] Existing consumers of `domsoil_d`, `ssurgo_domsoil_d`, and `soils.parquet` remain backward compatible.
- [x] Unit and integration tests pass with `wctl run-pytest` targeted at the new soil and NoDb tests.
- [x] `wctl run-pytest tests --maxfail=1` passes or an unrelated external blocker is recorded.
- [x] QA review artifact is complete and all findings are dispositioned.
- [x] Parameterization ADR is present, linked from this package, and records decision provenance.
- [x] Durable soil docs describe reclaimed-profile handling and fallback provenance.

## Parameterization ADR Gate

- **Parameterization change present**: yes
- **ADR required**: yes
- **ADR link(s)**: [ADR-0008](../../adrs/ADR-0008-ssurgo-reclaimed-soil-restrictive-layer-fallback.md)
- **Decision provenance captured**: yes.

This package changes how restrictive-layer thresholds affect generated WEPP soil layers and how invalid-dominant-soil fallback is applied or reported. That is model parameterization and fallback behavior under `docs/standards/parameterization-adr-standard.md`.

## Compatibility and Regression Plan

The fallback transparency work mutates run-scoped soil artifacts and possibly NoDb serialization. Keep the evolution additive and backward compatible:

- Do not rename or remove `domsoil_d`, `ssurgo_domsoil_d`, or existing `soils.parquet` columns without explicit operator approval.
- If raw dominant MUKEYs are serialized, add a new key and legacy-load default in `Soils._post_instance_loaded`.
- If `soils.parquet` gains columns, add only nullable/additive columns such as `raw_mukey`, `substituted_mukey`, or `substitution_reason`.
- Validate downstream propagation to generated run artifacts, including disturbed flows where `Disturbed.modify_soils` consumes final `domsoil_d`.
- Add regression tests for legacy `soils.nodb` files missing the new fields.

## Dependencies

### Prerequisites

- Completed project-local SSURGO cache package: [20260619_ssurgo_project_sqlite_cache](../20260619_ssurgo_project_sqlite_cache/package.md).
- Existing Fairpoint evidence from `wepp1` run `hard-line-foothold / disturbed9002`.
- Existing local test wrappers: `wctl run-pytest`.

### Blocks

- Reliable production interpretation of reclaimed mined-land SSURGO map units.
- Future cleanup of invalid-soil fallback behavior.

## Related Packages

- **Depends on**: [20260619_ssurgo_project_sqlite_cache](../20260619_ssurgo_project_sqlite_cache/package.md)
- **Related**: [20260522_ssurgo_corestrictions_kslast_viability](../20260522_ssurgo_corestrictions_kslast_viability/package.md)
- **Related**: [20260325_disturbed_lookup_hardening](../20260325_disturbed_lookup_hardening/package.md)

## Timeline Estimate

- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium-High.
- **Risk level**: High, because generated WEPP soil inputs and fallback provenance change.

## Security Impact and Review Gate

- **Security impact triage**: low
- **Dedicated security review required**: no
- **Triage rationale**: Planned changes are internal model-conversion and run-artifact behavior. No new public routes, auth/session handling, uploads/downloads, filesystem path inputs, queue wiring, subprocess execution, or secrets handling are expected.
- **Security review artifact**: N/A

If implementation changes route payloads, filesystem deletion/write surfaces beyond normal run artifacts, or queue behavior, retriage this package to `high` and add a dedicated security review artifact.

## Hardening and Callus Softening

- **Failure signature(s)**:
  - Fairpoint MUKEY logs show `found 2 layers`, `horizons mask: [True, True]`, then `identified 0 layers` and `Validity: no horizons`.
  - Topaz 573 and 581 in run `hard-line-foothold / disturbed9002` resolve to raw Fairpoint MUKEYs but final disturbed soil `2451115-silt loam-forest`.
- **Related prior hardening efforts**:
  - [20260619_ssurgo_project_sqlite_cache](../20260619_ssurgo_project_sqlite_cache/package.md)
  - [20260522_ssurgo_corestrictions_kslast_viability](../20260522_ssurgo_corestrictions_kslast_viability/package.md)
- **Health signals**:
  - Fairpoint MUKEYs build valid `.sol` files.
  - Logs no longer report "Validity: no horizons" for `3294459`, `3294460`, or `3294461`.
  - Rebuilt affected runs surface Fairpoint/reclaimed descriptions for relevant hillslopes.
  - Any remaining invalid-MUKEY substitutions are visible in run artifacts.
- **Danger signals**:
  - Low-conductivity first horizons are made unrealistically permeable.
  - All invalid soils are forced valid without defensible WEPP representation.
  - Downstream disturbed preparation loses compatibility with existing `domsoil_d` expectations.
- **Observation window**: 30 days after production deployment.
- **Temporary calluses introduced**: none planned.
- **Callus softening hypothesis**: Once substitutions are observable, a later package can decide whether some invalid-soil cases should fail explicitly instead of substituting.

## References

- `wepppy/soils/ssurgo/ssurgo.py` - SSURGO component/horizon conversion, restrictive-layer logic, and WEPP `.sol` writing.
- `wepppy/nodb/core/soils.py` - Gridded SSURGO build path and invalid-MUKEY substitution.
- `wepppy/soils/ssurgo/ssurgo.md` - Durable SSURGO conversion documentation.
- `wepppy/soils/README.md` - Soil subsystem overview and cache behavior.
- `tests/soils/` - SSURGO conversion and cache regression tests.
- `tests/nodb/` - NoDb soils build and serialization tests.
- `docs/standards/parameterization-adr-standard.md` - ADR requirement for threshold/fallback changes.
- `docs/work-packages/20260619_ssurgo_project_sqlite_cache/tracker.md` - Prior SSURGO cache investigation and ADR context.
- Brooks, Dobre, Elliot, Wu, and Boll (2016), "Watershed-scale evaluation of
  the Water Erosion Prediction Project (WEPP) model in the Lake Tahoe basin" -
  `https://research.fs.usda.gov/download/treesearch/50802.pdf`

## Deliverables

- Parameterization ADR for first-horizon restrictive-layer and fallback transparency behavior.
- Conversion code fix for reclaimed Fairpoint profiles.
- Additive fallback provenance state/artifacts.
- Unit and integrated generated-output tests for MUKEYs `3294459`, `3294460`, and `3294461`.
- NoDb compatibility tests for any new serialized fields or artifact columns.
- Updated soil documentation.
- QA review findings artifact with dispositions.

## Follow-up Work

- Consider a separate policy package for fail-fast vs substitution behavior across all invalid SSURGO MUKEY classes.
- Consider operator UI/report surfacing for raw-vs-final soil substitutions if users need direct visibility outside downloaded artifacts.
- Investigate unrelated route-test blocker:
  `tests/weppcloud/routes/test_wepp_bp.py::test_view_management_effective_returns_texture_specific_preview[clay-1.1-2.1-0.11]`.
