# SSURGO Intelligent Fallback Empirical Study

**Status**: In Progress (2026-07-21)
**Timezone**: UTC

## Overview

WEPPcloud currently replaces every residual-invalid dominant SSURGO MUKEY in a
run with the most common valid MUKEY. This package builds the evidence needed
to replace that watershed-global heuristic safely. It measures how often the
current converter cannot build a WEPP soil, separates missing-data and
nonphysical-input failures from profile-absence failures, and then evaluates
map-derived candidate evidence before any production fallback policy changes.

The completed pilot establishes a mapped-area baseline from the 2025 gNATSGO
raster: 40 of 2,048 area-weighted draws (1.95%) were unbuildable. The user has
approved expanding this research cohort to improve precision and failure-class
coverage.

## Objectives

- Produce a reproducible complete MUKEY coverage inventory for the supplied
  2025 gNATSGO raster.
- Expand the area-weighted empirical cohort from 2,048 to 12,288 independent
  mapped-pixel draws, preserving seed, source, converter configuration, and
  raw diagnostic provenance.
- Run a separate 2,048-draw unweighted-MUKEY cohort so rare MUKEY failures are
  not hidden by mapped-area weighting.
- Turn observed failure classes into deterministic fixtures and masked-valid
  candidate-selection experiments based on the SSURGO raster, not hillslope
  topology.
- Preserve existing fallback behavior until an ADR-approved policy has
  demonstrated improvement over the current watershed-global baseline.

## Scope

### Included

- `tools/ssurgo_empirical_study.py` and its tests: complete raster inventory,
  versioned diagnostic contract, and aggregate analysis helpers.
- Read-only NRCS Soil Data Access cohorts using current
  `SurgoSoilCollection`/`WeppSoil` conversion behavior.
- Aggregate empirical reports under `docs/investigations/` and non-versioned
  raw diagnostic artifacts outside git.
- Fixture design for observed `no_components`, `no_horizons`, missing required
  attributes, and nonphysical texture-balance cases.
- Raster-region adjacency and aligned elevation evidence design.
- Milestone 2 shadow-only, additive candidate evidence in `Soils` and
  `soils/soils.parquet`; final soil assignments remain unchanged.
- Milestone 3 read-only masked-valid evaluation rows and deterministic raster
  fixtures comparing local-majority evidence to the current global baseline.

### Explicitly Out of Scope

- Changing `Soils._build_gridded()` fallback selection or generated soil files.
- Introducing a new production default, score, threshold, imputation formula,
  or parameterization without a later ADR.
- Treating the 2025 cohort as a permanent national estimate without repeated,
  versioned source-data collection.
- Modifying production runs, SSURGO source rasters, or NRCS source data.

## Stakeholders

- **Primary**: WEPPcloud soil-model maintainers and operators.
- **Reviewers**: SSURGO/WEPP domain maintainers.
- **Security Reviewer**: N/A.
- **Informed**: Users whose gridded builds use SSURGO/gNATSGO soils.

## Success Criteria

- [x] Complete 2025 gNATSGO VAT inventory records 320,669 MUKEYs and
  8,745,483,151 mapped pixels.
- [x] Initial 2,048-draw mapped-area pilot reports outcomes, confidence
  interval, failure codes, and raw-field completeness.
- [x] 12,288-draw mapped-area cohort completes with no unclassified data-access
  failures and a reported confidence interval for combined unbuildable rate.
- [x] 2,048-draw unweighted-MUKEY cohort completes with separately reported
  MUKEY-prevalence results.
- [x] Milestone 1 returns deterministic local candidate pixel support from
  clustered bounds and proves it with synthetic raster fixtures.
- [ ] Deterministic fixtures cover all observed primary failure classes.
- [x] A map-region/elevation candidate experiment compares the current global
  fallback with local candidates in masked-valid trials (298 local cases; M4
  remains HOLD pending failure-class fixtures and an ADR-ready effect rule).
- [ ] No production fallback behavior changes without a parameterization ADR.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no for this research package; yes before any changed
  fallback policy, score, threshold, or repair rule.
- **ADR link(s)**: TBD if a production policy is proposed.
- **Decision provenance captured**: user approved expanded cohorts on
  2026-07-21 Pacific time; implementation records remain research-only.

Reference: `docs/standards/parameterization-adr-standard.md`.

## Milestone 2 Compatibility Plan

Milestone 2 adds `Soils.ssurgo_candidate_shadow_d`, a nullable mapping keyed
by string TOPAZ ID. Each record contains `raw_mukey`, `cluster_id`, cluster
bounds in EPSG:5070, `search_radius_m`, ordered `(mukey, pixel_count)` local
candidate support, `proposed_mukey`, `current_global_mukey`, and an explicit
exhaustion/reason value. Old `soils.nodb` files hydrate this field as an empty
mapping. `domsoil_d`, `ssurgo_domsoil_d`, `raw_ssurgo_domsoil_d`, and
`ssurgo_substitution_d` retain their current meanings and are never rewritten
by shadow evaluation.

`soils/soils.parquet` gains nullable additive columns representing the same
per-hillslope evidence. Existing consumers, including reports, DuckDB helpers,
exports, RQ dependency artifacts, and migration tools, locate the stable
logical parquet path and select required columns; they do not require an exact
closed schema. Regression coverage must prove old NoDb hydration defaults,
existing parquet columns/values are unchanged, new columns are null for
non-SSURGO or non-substituted hillslopes, and the generated sidecar contains
the shadow fields for an affected fixture run.

## Dependencies

### Prerequisites

- gNATSGO 2025 raster and VAT at
  `/wc1/geodata/ssurgo/gNATSGSO/2025/`.
- Read-only availability of the NRCS Soil Data Access tabular endpoint.
- Existing SSURGO converter and diagnostic scaffold.

### Blocks

- Evidence-backed intelligent fallback selection and its required ADR.

## Related Packages

- **Related**:
  `docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/`.
- **Related**:
  `docs/work-packages/20260705_ssurgo_fc_wp_sanitization/`.
- **Depends on**: current SSURGO converter and fallback-provenance behavior.

## Timeline Estimate

- **Expected duration**: 1-2 focused weeks.
- **Complexity**: Medium.
- **Risk level**: Medium; results influence later scientific parameterization
  decisions but this package does not change model inputs.

## Security Impact and Review Gate

- **Security impact triage**: none.
- **Dedicated security review required**: no.
- **Triage rationale**: research tooling reads an operator-supplied local raster
  and an existing public NRCS data source; it adds no route, auth, secret,
  queue, or production mutation surface.
- **Security review artifact**: N/A.

## Hardening and Callus Softening

- **Failure signature(s)**: residual-invalid SSURGO MUKEYs currently trigger
  watershed-global valid-MUKEY substitution.
- **Related prior hardening efforts**:
  `20260622_ssurgo_reclaimed_soil_fallback` and
  `20260705_ssurgo_fc_wp_sanitization`.
- **Health signals**: reproducible failure taxonomy, narrower confidence
  intervals, and candidate evidence that is visible without changing builds.
- **Danger signals**: source-data retrieval failures classified as soil-data
  failures; an opaque score or silent production selection change.
- **Observation window**: expanded cohorts plus masked-valid trial review.
- **Temporary calluses introduced**: none.
- **Callus softening hypothesis**: N/A; this package is discovery before a
  later mitigation decision.

## References

- `docs/planning/ssurgo-intelligent-fallback-strategy.md` - governing strategy.
- `docs/investigations/2026-07-21-ssurgo-intelligent-fallback-pilot/README.md`
  - initial empirical evidence.
- `wepppy/nodb/core/soils.py` - current gridded fallback behavior.
- `wepppy/soils/ssurgo/ssurgo.py` - current SSURGO conversion and validity.

## Deliverables

- Research CLI and regression tests.
- Initial and expanded cohort reports with non-versioned raw artifacts and
  versioned aggregate evidence.
- Deterministic failure fixtures and candidate-policy evaluation harness.
- A parameterization ADR only if evidence supports a future production policy.

## Follow-up Work

- A separate implementation package for an ADR-approved fallback policy.
- A source-version monitoring cadence if repeated cohorts show material drift.
