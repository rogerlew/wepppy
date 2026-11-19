# ADR-0148: Separate native soil input capacity from calculation layers

Date: 2026-11-18
Status: Accepted for implementation; release validation pending.

## Context

The 200 mm split makes Zepol's ten SSURGO horizons eleven and triggers the Python
capacity guard. Historical native readers silently discard excess records. A
full October 2026 national inventory finds 22 raw horizons, at most twenty after
necessary current validity filters, and five actual selected map-unit profiles
with 21 generated records. Eleven is insufficient nationally. Increasing global
`mxnsl` also changes calculation/output storage, including fixed output offsets.

## Decision

Set separate native reader scratch capacity `mxhzin=23`; keep `mxnsl=10`, depth
clipping/extension, property aggregation and physical formulas unchanged. Keep
all supported source horizons; explicitly reject counts above 23. Declare
integer input capacity in both digest-bound release sidecars. Python writers
and final native invocation enforce the selected executable's capacity. Absent
capability declarations mean ten; malformed or mismatched pairs fail explicitly.
Preserve historical binaries, defaults, saved selections and uploaded-file
admission/preservation behavior. No global relaxation for historical binaries.

## Rationale and alternatives

Twenty-three covers every observed raw source horizon plus one property-copying
split, without relying on present validity exclusions. Twenty-one is the exact
current-writer minimum but couples native capacity to those exclusions. Eleven
addresses only the initial incident. Global mxnsl expansion changes unrelated
state/output layouts. Merging or dropping horizons changes source properties;
minimum conductivity is not introduced. Larger arbitrary limits lack a measured
requirement. Future releases beyond 23 fail clearly and require a new evaluation.

## Validation, risk and rollback

Validate 21/22/23 records, reject 24, mixed OFEs, eight native formats, real Puaulu
and Zepol, bounds checks, analytical aggregation, old-input parity, matched-role
watershed runs, all native release gates, Python raw/prepared/Disturbed/channel
paths and uploaded preservation. Run an isolated original project under the real
workflow and inspect fresh outputs. Test executable downgrade against existing
oversized soils. Do not confuse source capacity with vertical resolution or a
new modeled depth. Retain prior executable pair and input/output provenance;
rollback must regenerate compatible inputs or fail explicitly, never truncate.

## Decision provenance

Venue: operator/Codex conversation, 2026-11-18 America/Los_Angeles.
Participants: operator and Codex. Decision owner: operator, who authorized the
agreed plan and its work-package execution. Implementer: Codex. Change summary:
new selected native release supports 23 input records; historical capacity ten
and calculation capacity ten remain unchanged. No deployment/default migration
is inferred from accepting this implementation decision.

## Evidence

[National inventory](../investigations/2026-11-18-ssurgo-input-capacity/assessment.md),
[eleven-horizon evaluation](../work-packages/20261118_native_soil_input_capacity/artifacts/evaluation.md),
and [implementation package](../work-packages/20261118_soil_input_capacity_23/package.md).
