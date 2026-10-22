# ADR-0102: Roads modeled-area response mixture with expansion

## Status

Proposed for independently reviewed contract checkpoint, 2026-10-22.
Operator scientific direction and task-scoped commit authority are granted;
implementation conformance and deployment remain pending.

## Decision

Use complete modeled MOFE areas, not geographic overlap. For each point-source
target, A is baseline area, C is total active contributor area, B=max(A-C,0)
is baseline represented remainder and T=B+C is modeled target area. Retain each
contributor at its full footprint; when C>A record expansion instead of clipping
roads. Existing replacement strips/remainders replace baseline without a second
subtraction and supersede additive sources for the same target.

Continuous-run area authority is stationary local WAT OFE area summed per native
profile. Single-storm ledgers use native PASS-header areas consistently. PASS
extensive quantities scale by represented area / serialized PASS source area;
WAT volumes scale by represented area / source WAT area. This explicitly
reconciles their serialization precision without changing unit-depth responses.
Unchanged sources remain unmodified; zero-road continuous water results preserve
baseline behavior. Reconstruct canonical PASS once from originals, rerun watershed,
and aggregate the same ledger in totalwatsed and average hillslope water reports.

The full contract is [Roads modeled-area accounting](../schemas/roads-water-accounting-contract.md).
Retain native topology until terminal Q/lateral selection. Preserve literal
TotalWatSed Q diagnostics separately from physical Q in equivalent report WAT.
Optional diagnostic joins retain source identity and support-area weights.

## Rationale and alternatives

The existing additive path includes full baseline response plus road MOFEs,
while totalwatsed also duplicates standalone PASS and omits baseline WAT.
A shared modeled-area ledger fixes the composition and reporting boundary.
Geographic union was considered but explicitly rejected by the operator as
unnecessary for this model. Current rutted profiles lack geographic fill/buffer
placement; no new geometry requirement or guessed placement is introduced.

Rejected retaining uncorrected baseline plus all road local fluxes: it duplicates
represented land. Rejected boundary-injection-only water reporting: the operator
selected full MOFE footprint accounting. Rejected clipping outside road response:
the operator requested expanded modeled area. Expansion is defined in model
space; it does not infer which land is geographically outside the watershed.

The max rule follows retaining all contributor areas while eliminating negative
baseline remainder. It does not assert physical hydrologic closure or recompute
residual baseline flow paths; it is a documented mixture of existing responses.

## Decision provenance

Venue: Roger/Codex task conversation, 2026-10-22 UTC.
Decision owner: Roger Lew. Implementer: Codex.
Roger authorized native/WEPPpy implementation and task-scoped commits, expanded
scope to PASS reconstruction and routing validation, requested inclusion of road
area in the modeled footprint, then clarified: “we should just keep the mofe
footprint areas” and questioned any geographic-overlap requirement.
Independent agents review the resulting exact contract; their reviews are
technical evidence, not substitutes for operator scientific authority.

## Evidence, compatibility and rollback

See the [investigation](../work-packages/20261022_roads_lateral_flow_investigation/diagnosis.md)
and [repair package](../work-packages/20261022_roads_accounting_repair/package.md).
Native weighted PASS is an existing owned mechanism. Roads must preserve its
legacy admission of differing particle diameters; AgFields validation is unchanged.
No baseline executable, native baseline default, queue or routing topology changes.

Retain original project artifacts and validate fresh reconstruction/routing on
scratch copies. No in-place historical repair or production rollout is authorized.
Rollback restores coordinated native/WEPPpy releases and regenerates from
originals; never scale already-combined PASS again. Provenance distinguishes old
unmarked results from corrected model-area results.
