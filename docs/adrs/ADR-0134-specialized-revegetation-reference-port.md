# ADR-0134: Preserve specialized revegetation reference semantics

Status: accepted; implemented and validated in local undeployed revision 7.

## Decision provenance

- Decision venue: this Codex task, 2026-11-03 UTC (2026-11-02 America/Los_Angeles).
- Participants present: operator Roger Lew and Codex.
- Decision owner: Roger Lew; specialized scientific semantics belong to Anurag
  Srivastava. No claim that Anurag attended or reviewed this implementation.
- Implementer: Codex, with independent review gates.
- Explicit direction: “preserve reference. that is anurag's domain”.

## Decision and exact delta

Adopt the bound reference's 9005 hydraulic and RAP vegetation behavior only in
the specialized lanes of undeployed 261029. The
[specialized consumer contract](../schemas/specialized-revegetation-consumer-contract.md)
contains the field/mode matrix, equations, constants, units, activation and
compatibility exceptions. Source authority is model `2e5928702` from the separate
revegetation repository, not a similarly named generic release. Preserve existing
ordinary modes and revision-6 PMET/FC/HK corrections.

Before: selected 261029 misbinds the seven-field header, reads a restrictive record
twice and lacks specialized cover consumers. After: correct field/record binding
plus the reference's distinct cover-dependent conductivity, layer feedback,
canopy/biomass/root/LAI and fire-residue sequence. This is an adopted specialized
parameterization, not just parser repair or evidence of field calibration.

Preserve recurring anniversary fire comparisons, differing comparison/assignment
cover quantities, crop-wide specialized root-depth mutation and logarithm/clamp
ordering. Do not infer scientific corrections. Protocol reconciliation changes
calendar validation, band binding, date serialization and stale flags so the
intended current scenario reaches that unchanged specialized numerical sequence.

## Rationale and alternatives

The operator assigns scientific ownership to Anurag and requests compatibility.
Correcting suspected fire/canopy/root rules would change that model without its
owner's decision. A 9003 minimum-only extension implements the wrong hydraulics.
Copying the whole divergent branch would erase unrelated selected-release repairs.
An isolated specialized growth routine and bounded other consumer changes retain
reference arithmetic while keeping ordinary consumers intact.

## Evidence and risk

[Bound source/binary and actual reader evidence](../work-packages/20261102_mofe_input_producer_audit/artifacts/mipa03_reference_discovery.md)
and [producer discrepancies](../work-packages/20261102_mofe_input_producer_audit/artifacts/mipa03_producer_protocol_review.md)
precede implementation. Discriminating actual-consumer and full-history evidence
must follow; no old gate result is reused as a fresh revision-7 result.

Inherited reference behavior can increase canopy, depend on OFE processing order,
or fail on log(0). Preserve and disclose those limits; do not claim universal
heterogeneous correctness, field validity or full water conservation. Rollback
uses retained matched revision-6 binaries/sidecars and prior reports; old passes
must never be mixed with new watershed execution. No default switch, deployment,
Windows release, installed Rust promotion or existing-project regeneration.

Implementation evidence: [MIPA-03 execution](../work-packages/20261102_mofe_input_producer_audit/artifacts/20261103_specialized_consumer_execution.md). The reference graphics disturbance-age F10.5 overflow is also retained and disclosed; changing its output format is outside this port.
