# ADR-0073: Resolve thinning soil classes by prefix

Status: accepted 2026-09-25; implemented in `9a5eb0813`, locally validated.

## Context and decision

On wepp1, choice-feminist scenario `thinning_30_90`, prepared `p10.sol`
contains five OFEs with forest conductivity/erodibility and zero `ksatfac`/
`ksatrec`. Its intermediate soil records the MOFE 9002 missing-row fallback.
The lookup has `thinning,loam`, but the resolver returns `thinning_30_90`.
The soil lookup selection also serves single-OFE soil generation.

Resolve every class starting with case-sensitive `thinning` to `thinning`.
Keep the existing mulch suffix-to-burned-base resolution. Apply existing
effective lookup coefficients; introduce no new scientific values.
The normative rule is the
[treatment soil lookup contract](../schemas/disturbed-treatment-soil-lookup-contract.md).

## Decision provenance

- Venue: operator/Codex task conversation, 2026-09-25 UTC.
- Checkpoint recorded: 2026-09-25 15:41:58 UTC (`b63e738d0`), before implementation.
- Participants: requesting operator and Codex.
- Decision owner: requesting operator.
- Implementer: Codex.
- Approval: "scaffold and execute work-package to fix this please. it should
  match to any landuse that starts with \"thinning\" . the work-package should
  also check mulch".

## Change summary and alternatives

For the incident loam soils, conductivity in the upper 200 mm changes from
50 to 40 mm/h and `kr` from 0.00003 to 0.00004. MOFE 9002 recovery metadata
changes from zero to 1.3/0.3. Fortran 9002 does not use those last two fields;
the conductivity and erodibility differences remain consequential.

Reject enumerating current cover variants because the operator requires any
thinning prefix. Reject changing lookup CSV values or Fortran formulas because
the defect is lookup selection. Reject generic mulch remapping because it
would lose burned vegetation and severity parameters.

## Evidence, risks, and rollback

See [work package](../work-packages/20260925_disturbed_thinning_soil_lookup/package.md).
Risk: newly rebuilt thinning results change; old saved results remain stale.
Unusual custom names beginning with thinning deliberately resolve to thinning.
Rollback is reverting the bounded soil lookup change; this does not restore or
refresh already-generated inputs/results. Production repair requires a supported
rebuild, parameter readback, fresh model execution and output verification.
