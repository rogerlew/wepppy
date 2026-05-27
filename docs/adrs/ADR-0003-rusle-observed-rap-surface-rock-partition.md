# ADR: RUSLE `observed_rap` Surface-Rock Partition for `C`

Status: Accepted  
Date: 2026-05-27  
Review Date: 2027-05-27

## Context

The current `RUSLE` `observed_rap` implementation computes `C` directly from RAP
bare-ground percent:

- `fg = clamp(100 - bare_ground_pct, 0, 100)`
- `C = exp(-0.04 * fg)`

In rocky landscapes, RAP bare includes both exposed mineral soil and exposed rock.
`RUSLE2` guidance treats surface rock as protective ground cover in `C`, while
profile coarse fragments are handled in `K` logic.

Without a separate surface-rock term, `observed_rap` can overstate exposed-soil
fraction on armored hillslopes.

## Decision

Add a user-facing `observed_rap` parameter:

- `rock_fraction_of_rap_bare` in `[0, 1]`

Use it to partition RAP bare into exposed-soil and protective-rock fractions:

- `bare_rap = clamp(bare_ground_pct / 100, 0, 1)`
- `r_bare = clamp(rock_fraction_of_rap_bare, 0, 1)`
- `bare_exposed = bare_rap * (1 - r_bare)`
- `fg = 100 * (1 - bare_exposed)`
- `C = exp(-0.04 * fg)`

Provide an `auto` convenience default with source precedence:

- first from SSURGO `cosurffrags` (`sfragcov`) aggregated across the run
  footprint as a total-surface-rock proxy (`surface_rock_cover_proxy_0_1`)
- fallback to top-horizon `cfvo` (`surface_rock_cover_proxy_0_1 = clamp(cfvo_0_5cm_volpct / 100, 0, 1)`)
- final fallback to `0.0`

Convert proxy total-surface cover into the control domain (fraction of RAP bare
interpreted as rock):

- `rock_fraction_of_rap_bare_default = clamp(surface_rock_cover_proxy_0_1 / bare_rap_mean_0_1, 0, 1)` when `bare_rap_mean_0_1 > 0`
- `rock_fraction_of_rap_bare_default = 0.0` when `bare_rap_mean_0_1 <= 0`
- Multiplying by `bare_rap_mean_0_1` is intentionally rejected because it
  shifts the parameter into total-area space instead of fraction-of-bare space.

The `auto` value is explicitly documented as a proxy prior, not canonical
surface-rock truth.

## Decision Provenance (Required for Parameterization Changes)

Decision Venue: Codex user request thread, 2026-05-27 PDT  
Participants Present: User, Codex  
Decision Owner(s): User / WEPPcloud operator request  
Implementer(s): Codex

## Change Summary

Old behavior:

- `observed_rap` had no explicit surface-rock partition control.
- RAP bare was treated as exposed bare for `fg` calculation.

New behavior:

- `observed_rap` includes `rock_fraction_of_rap_bare` user control.
- `fg` now reflects overlap-consistent rock partitioning of RAP bare.
- `auto` default populates from SSURGO `cosurffrags` when available, with
  fallback to top-horizon `cfvo`.

## Rationale

- Aligns with canonical `RUSLE2` guidance: surface rock affects `C` (cover), not
  `K`.
- Preserves explicit user control where no robust spatial surface-rock raster
  exists.
- Keeps profile-fragment effects in `K` while avoiding double counting.
- Uses a surface-fragment dataset (`cosurffrags`) as primary proxy rather than
  profile volumetric fragments (`cfvo`) for the `C`-factor surface-cover path.

## Alternatives Considered

1. Keep RAP bare unchanged and rely only on `K` profile-fragment adjustment - Rejected. This mis-buckets protective surface armor into the profile-permeability path.
2. Require field-entered surface-rock cover only, with no default - Rejected. Scientifically strongest but operationally brittle for current run workflows.
3. Derive hard spatial surface-rock map automatically - Rejected for now. No defensible run-scoped data source is currently available in this stack.

## Consequences

- Positive:
  - Better directional behavior on stony, exposed hillslopes.
  - Clearer separation of surface-rock (`C`) vs profile-fragment (`K`) effects.
  - Explicit uncertainty labeling for proxy defaults.
- Risks:
  - `auto` defaults are still uncertain proxies; `cosurffrags` and `cfvo` can
    both misestimate true site-observed surface rock cover if not overridden.

## Evidence

- Spec update: `wepppy/nodb/mods/rusle/specification.md` (`C` contract,
  controls, source precedence, and validation updates).
- USDA-ARS RUSLE2 User’s Reference Guide:
  https://www.ars.usda.gov/ARSUserFiles/60600505/RUSLE/RUSLE2_User_Ref_Guide.pdf
- USDA-NRCS RUSLE2 Handbook:
  https://www.nrcs.usda.gov/sites/default/files/2022-10/RUSLE2%20Handbook_0.pdf
- USDA-NRCS National Soil Survey Handbook Part 618:
  https://directives.nrcs.usda.gov/sites/default/files2/1719846855/Part%20618%20Subpart%20A%20%E2%80%93%20General%20Information.pdf

## Risk and Rollback Notes

- Monitor sensitivity of `A` to `rock_fraction_of_rap_bare` (`0.0`, `auto`,
  and field-informed values).
- If proxy defaults produce unstable or implausible behavior, rollback path is:
  - keep user control,
  - disable `auto`,
  - require explicit user entry or `0.0` default until better surface data is
    available.

## Implementation Notes

- This ADR records the specification-level contract and defaulting policy.
- Runtime/controller implementation must emit manifest provenance for the
  effective rock-partition value and source (`user` vs `auto`).
