# ADR: RUSLE `scenario_sbs` Surface-Rock Partition for `C`

Status: Accepted  
Date: 2026-05-27  
Review Date: 2027-05-27

## Context

The current `scenario_sbs` pathway uses static severity lookup defaults for RUSLE
`C` and does not expose an explicit surface-rock partition control. In rocky
settings, this can treat lookup bare fractions as fully exposed erodible soil,
which overstates erosion where surface armor is substantial.

`RUSLE2` guidance places surface rock in cover-management (`C`) logic, while
profile coarse fragments belong in soil erodibility/permeability (`K`) logic.
For `scenario_sbs`, this adjustment should not depend on RAP artifacts.

## Decision

Add a user-facing `scenario_sbs` parameter:

- `rock_fraction_of_sbs_bare` in `[0, 1]`

Use it to partition lookup-derived SBS bare fraction:

- `fg_lookup = clamp(fg_lookup_pct / 100, 0, 1)`
- `bare_lookup = 1 - fg_lookup`
- `r_sbs_bare = clamp(rock_fraction_of_sbs_bare, 0, 1)`
- `bare_exposed = bare_lookup * (1 - r_sbs_bare)`
- `fg_effective_pct = 100 * (1 - bare_exposed)`
- `C = exp(-0.04 * fg_effective_pct)`

Provide `auto` defaulting with proxy source precedence:

- first from run-scoped SSURGO `cosurffrags` proxy columns in
  `soils/soils.parquet`
- fallback to top-horizon `cfvo`
- final fallback to `0.0`

Convert proxy total-surface cover into SBS control space (fraction of SBS bare):

- `rock_fraction_of_sbs_bare_default = clamp(surface_rock_cover_proxy_0_1 / bare_lookup_mean_0_1, 0, 1)` when `bare_lookup_mean_0_1 > 0`
- `rock_fraction_of_sbs_bare_default = 0.0` when `bare_lookup_mean_0_1 <= 0`

The SBS rock adjustment is explicitly RAP-independent: no RAP raster retrieval
or RAP-year dependency is required for `scenario_sbs`.

## Decision Provenance (Required for Parameterization Changes)

Decision Venue: Codex user request thread, 2026-05-27 PDT  
Participants Present: User, Codex  
Decision Owner(s): User / WEPPcloud operator request  
Implementer(s): Codex

## Change Summary

Old behavior:

- `scenario_sbs` had no explicit surface-rock partition control.
- Lookup bare implicitly behaved as exposed bare in SBS `C` outcomes.

New behavior:

- `scenario_sbs` includes `rock_fraction_of_sbs_bare`.
- SBS lookup bare is partitioned into exposed-soil and protective-rock
  components before `C` calculation.
- `auto` default uses `cosurffrags` first, then `cfvo`, then `0.0`, normalized
  into SBS bare-fraction control space.

## Rationale

- Aligns SBS with canonical RUSLE placement of surface rock in `C`.
- Improves directional realism on stony post-fire and disturbed landscapes.
- Keeps SBS contract independent from RAP-specific data dependencies.
- Reuses existing proxy hierarchy while preserving explicit user override.

## Alternatives Considered

1. Leave SBS unchanged and rely only on `K` profile-rock effects - Rejected.
   This misses protective surface armor in the `C` pathway.
2. Reuse RAP-specific rock control in SBS mode - Rejected. This creates
   unnecessary RAP coupling for SBS workflows.
3. Require field-entered rock fraction only (no `auto`) - Rejected for now.
   Operationally too brittle where field measurements are unavailable.

## Consequences

- Positive:
  - More defensible SBS `C` behavior in armored terrain.
  - Clear RAP-independent scenario contract.
  - Provenance can distinguish user-entered versus proxy-derived defaults.
- Risks:
  - `auto` remains a proxy prior and can misestimate local true surface rock.
  - Cross-layer contract updates are required (UI/API/runtime/tests).

## Evidence

- Spec update: `wepppy/nodb/mods/rusle/specification.md`.
- Work package: `docs/work-packages/20260527_rusle_sbs_surface_rock_partition/package.md`.
- Existing related ADR for observed RAP mode: `docs/adrs/ADR-0003-rusle-observed-rap-surface-rock-partition.md`.

## Risk and Rollback Notes

- Monitor sensitivity with `rock_fraction_of_sbs_bare = 0.0`, `auto`, and
  field-informed values.
- If proxy defaults are unstable, rollback path is to keep the SBS control but
  disable `auto` and require explicit numeric entry.

## Implementation Notes

- Manifest metadata should record effective SBS rock-fraction value and source
  (`user`, `auto:cosurffrags`, `auto:cfvo`, or fallback marker).
- UI should explicitly warn users that `auto` is an estimate and field/local
  rock-cover verification is preferred.
