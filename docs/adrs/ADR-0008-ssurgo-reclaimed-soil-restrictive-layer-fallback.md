# ADR: SSURGO Reclaimed Soil Restrictive Layer Fallback

Status: Accepted
Date: 2026-06-22

## Context

The 2025 gNATSGO raster can select reclaimed mine-land Fairpoint map units for
watershed elements that previously resolved to older Shelocta-Latham map units.
The affected Fairpoint MUKEYs `3294459`, `3294460`, and `3294461` have valid
SSURGO component and horizon data, but their first horizon has very low
`ksat_r`. The previous restrictive-layer rule marked that first horizon as the
restrictive layer, emitted zero WEPP soil layers, and caused the MUKEYs to be
treated as invalid. The gridded soil builder then substituted a different valid
soil without preserving the original raster-selected MUKEY.

The historical restrictive-layer rule is understood by the operator to have
come from Erin Brooks's Lake Tahoe WEPP calibration work. That precedent used
measured Tahoe Basin Soil Survey properties because default WEPP
pedotransfer functions were not appropriate for steep, rocky forest soils, and
it treated consolidated bedrock beneath Tahoe watersheds as a hydrologic lower
boundary. That is a different physical case from a reclaimed mine-land profile
whose first valid SSURGO horizon is itself a low-conductivity soil horizon.

## Decision

WEPPcloud will retain the first valid horizon as a WEPP soil layer even when its
`ksat_r` is below the restrictive-layer threshold. Restrictive-layer truncation
may start only after at least one valid horizon has been emitted.

The gridded `Soils` controller will also preserve raw SSURGO dominant MUKEYs in
`raw_ssurgo_domsoil_d` and record replacements in `ssurgo_substitution_d`.
Existing `domsoil_d` and `ssurgo_domsoil_d` remain final, WEPP-usable dominant
soil maps for backward compatibility.

## Decision Provenance (Required for Parameterization Changes)

Decision Venue: Codex work package execution, 2026-06-22 11:50 America/Los_Angeles
Participants Present: WEPPcloud operator/user, Codex coding agent
Decision Owner(s): WEPPcloud operator/user
Implementer(s): Codex coding agent

## Change Summary

Old behavior:
- Any valid horizon with `ksat_r < 2.0 um/s` could become `res_lyr_i`.
- If the first valid horizon met that condition, `num_layers` became `0`.
- The soil failed `WeppSoil.valid()` with `Validity: no horizons`.
- Gridded fallback replaced invalid dominant MUKEYs in `domsoil_d` without
  storing the original raster-selected MUKEY.

New behavior:
- `res_lyr_ksat_threshold` remains `2.0 um/s`.
- The first valid low-`ksat_r` horizon is retained as a WEPP layer.
- A later low-`ksat_r` horizon can still mark the restrictive layer and truncate
  the profile below the retained layer.
- Gridded fallback stores raw dominant MUKEYs separately and records each
  substitution with `raw_mukey`, `replacement_mukey`, and reason
  `invalid_dominant_mukey`.

## Rationale

The Fairpoint reclaimed map units represent current SSURGO mapping for the
reported watershed elements. Treating a valid first horizon as a zero-layer
profile makes the data unusable even though WEPP can model the low-conductivity
surface layer directly. Keeping one valid layer preserves the updated map unit
identity and avoids falling back to older neighboring soils.

Separate raw/final dominant maps let operators audit fallback behavior without
breaking downstream code that expects `domsoil_d` and `ssurgo_domsoil_d` to
reference generated `.sol` files.

## Tahoe Restrictive-Layer Interpretation

Brooks et al. (2016) evaluated WEPP in Lake Tahoe watersheds and built soil
inputs from measured Tahoe Basin Soil Survey properties rather than relying on
default WEPP pedotransfer functions for steep, rocky forest soils. The paper
also describes steep Tahoe watersheds underlain by consolidated bedrock and
uses baseflow/deep-percolation partitioning to reason about the lower boundary.

WEPPcloud interprets that precedent as support for truncating a modeled soil
mantle at restrictive material below at least one emitted soil layer, then
using the lower-boundary conductivity behavior (`kslast`) for the material
beneath the modeled profile. It is not interpreted as support for rejecting a
valid first mineral horizon and producing a zero-layer WEPP soil.

Local run evidence matches this distinction. The Blackwood/Lake Tahoe run
`/wc1/runs/ma/mammalian-ageism` has 231 hillslopes with restrictive profiles
but zero hillslopes that would have hit the prior first-horizon zero-layer
reassignment case. The reclaimed mine-land run
`/wc1/runs/ha/hard-line-foothold` has 73 restrictive-profile hillslopes, 71 of
which are first-valid-horizon cases that the previous rule would have rejected
and reassigned.

## Alternatives Considered

1. Lower or disable `res_lyr_ksat_threshold` for reclaimed mine lands - rejected
   because it changes the threshold semantics globally or requires a new
   classification rule.
2. Generate a synthetic placeholder layer above the restrictive horizon -
   rejected because it invents a horizon not present in SSURGO.
3. Change `ssurgo_domsoil_d` to raw MUKEYs - rejected because existing consumers
   rely on it matching generated WEPP soil files.

## Consequences

Fairpoint MUKEYs `3294459`, `3294460`, and `3294461` now produce valid WEPP
soil files with at least one layer. Profiles whose first valid horizon is below
the restrictive threshold will no longer be represented as zero-layer invalid
soils. Tahoe-style profiles with restrictive material below one or more valid
soil layers still truncate below the emitted soil mantle. The fallback
provenance fields are additive NoDb data and parquet columns; old NoDb payloads
are backfilled with `None` and `{}` defaults.

## Evidence

- Work package:
  `docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/`
- Reported production run:
  `https://wepp.cloud/weppcloud/runs/hard-line-foothold/disturbed9002/`
- Target watershed elements: Topaz IDs `573` and `581`
- Integrated regression MUKEYs: `3294459`, `3294460`, `3294461`
- Brooks, Dobre, Elliot, Wu, and Boll (2016), "Watershed-scale evaluation of
  the Water Erosion Prediction Project (WEPP) model in the Lake Tahoe basin":
  `https://research.fs.usda.gov/download/treesearch/50802.pdf`
- Tahoe comparison run: `/wc1/runs/ma/mammalian-ageism` has 231 restrictive
  profile hillslopes and zero prior-rule zero-layer reassignment cases.
- Reclaimed comparison run: `/wc1/runs/ha/hard-line-foothold` has 73
  restrictive-profile hillslopes and 71 prior-rule zero-layer reassignment
  cases.

## Risk and Rollback Notes

Risk: shallow, very low-conductivity profiles will now run instead of falling
back to a neighboring valid soil. Monitor generated soil logs for unexpectedly
high counts of retained first-horizon restrictive profiles.

Rollback: restore the previous `_analyze_restrictive_layer()` rule and remove or
ignore the additive provenance fields. Existing generated runs are unaffected
unless soils are rebuilt.

## Implementation Notes

Unit tests cover the three Fairpoint MUKEYs with deterministic SSURGO table rows
and verify that generated `.sol` files exist. NoDb tests cover raw dominant
MUKEY preservation, substitution records, and nullable summary fields.
