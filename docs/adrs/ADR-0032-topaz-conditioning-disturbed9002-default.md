# ADR-0032: Topaz Conditioning for disturbed9002 WBT

Status: Accepted

Date: 2026-07-30

## Context

The WBT channel pipeline currently offers generic fill, breach, and least-cost
breach conditioning. Investigation of a waterbody-adjacent outlet showed that
conditioning choice can materially change the local drainage direction.
`weppcloud-wbt` now contains a source-faithful Rust translation of TOPAZ FILDEP
and RELIEF with exact stage parity across seven golden cases, including
irregular NoData and an NLCD-water-masked production DEM.

## Decision

Add `topaz` as an explicit Channel Delineation conditioning value backed by WBT
`TopazConditionDem`. Use its default maximum obstruction width of 2. Change the
new-project default only in `disturbed9002_wbt.cfg` from
`breach_least_cost` to `topaz`.

## Decision Provenance

Decision Venue: Codex API workspace thread, 2026-07-29 18:24 PDT; exact request
retained in the DOM-05A contract decision

Participants Present: requesting WEPPcloud operator; Codex

Decision Owner(s): requesting WEPPcloud operator (personal identity and
external issue identifier not exposed to the agent by the API context)

Implementer(s): Codex

## Change Summary

Old behavior: new `disturbed9002_wbt` runs initialized
`fill_or_breach = "breach_least_cost"`.

New behavior: new `disturbed9002_wbt` runs initialize
`fill_or_breach = "topaz"` and create `relief.tif` with TOPAZ-compatible FILDEP
and RELIEF. Existing runs, other configs, and downstream flow/channel
algorithms are unchanged.

## Rationale

The TOPAZ-compatible method has exact empirical parity with the historical
algorithm and directly addresses the conditioning discrepancy that motivated
the work. Width 2 matches historical WEPPpy TOPAZ controls and is the most
thoroughly validated mode.

## Alternatives Considered

1. Retain least-cost breach as the disturbed9002 default - rejected because it
   does not reproduce TOPAZ conditioning and was implicated in the observed
   drainage discrepancy.
2. Make TOPAZ conditioning the global WBT default - rejected because the
   operator requested one config and other workflows have not approved output
   drift.
3. Replace one legacy token - rejected because an additive value preserves
   backward compatibility and makes provenance explicit.

## Consequences

New `disturbed9002_wbt` channel builds may produce different drainage,
watersheds, and derived model inputs than least-cost breach. That change is
intentional. Existing artifacts and persisted project selections do not change.
The runtime now requires a WBT binary containing `TopazConditionDem`, and the
integration pins `max_obstruction_width=2` explicitly.

## Evidence

- `/workdir/weppcloud-wbt/docs/work-packages/20260729_topaz_condition_dem_parity_hardening/artifacts/validation.md`
- `docs/work-packages/20260729_topaz_conditioning_wepppy_integration/artifacts/2026-07-30_contract_decision.md`
- Seven exact FILDEP/RELIEF cases totaling 5,037,306 valid case-cells.

## Risk and Rollback Notes

Release must install and verify the owned WBT binary before enabling the token.
Rollback is triggered by binary discovery failure, parity failure, unexpected
run-scoped output, or material production delineation regression. The safe
first rollback restores only `disturbed9002_wbt.cfg` to
`breach_least_cost` while retaining additive `topaz` compatibility for existing
projects. Full token/code/binary removal requires separately authorized,
audited, lock/cache-safe migration and proof that no persisted `topaz` remains.

## Implementation Notes

Do not add a silent fallback. Contract tests must cover render, request,
persistence, dispatch, config initialization, legacy compatibility, and
generated output from the installed binary.
