# ADR-0052: Staley M3 upstream terrain definition

## Status

Accepted engineering terrain formula by user on 2026-09-08 America/Los_Angeles.
Engineering recommendation: require genuine 10 m for initial M3 support;
no production enforcement is implemented.

## Decision provenance

- Decision venue: user/Codex workspace conversation, 2026-09-08,
  America/Los_Angeles; exact conversation time not retained.
- Participants present: requesting user and Codex.
- Decision owner: requesting user.
- Implementer: Codex; registered Rust command and both Python bindings.
- Authorized direction: owned WBT terrain tooling and empirical 10 m/30 m study.
  The user explicitly adopted maximum upstream raw elevation minus outlet
  elevation and authorized continuation. No 30 m policy was accepted.

## Change summary and recommendation

There is no existing postfire M3 runtime contract to replace. Adopt a new
D8 upstream quantity H = maximum upstream raw elevation minus outlet raw
elevation, including the outlet. Compute A from contributing cell count and
projected meter cell area, and T = H/sqrt(A). Keep supplied conditioned routing
separate from the raw measurement surface. This decision defines a
physical quantity; equivalence to Staley calibration remains unproven.

## Rationale and alternatives

Maximum-minus-outlet is nonnegative, uses the actual assessment outlet, and
can be computed in an owned linear-time traversal. Highest-source-minus-outlet
can exclude internal raw maxima. Catchment maximum-minus-minimum can measure
a depression above the assessment outlet. The alternatives agree on monotonic
paths but disagree under conditioning. The pinned pfdf reference fails an
analytical descending-chain check and cannot select between them. Do not
adopt its anomalous behavior merely to match outputs.

## Evidence

See [terrain contract](../work-packages/20260908_staley_m3_wbt_terrain/artifacts/terrain_contract.md)
and [pinned diagnostics](../work-packages/20260908_staley_m3_wbt_terrain/artifacts/reference_parity.md).
The manuscript and public USGS material leave the raw-elevation choice
unresolved by primary evidence alone. The user explicitly selected the proposed
quantity as the engineering contract after reviewing the analytical failure.

## Risk and rollback

A changed terrain definition can change every probability and threshold.
No production integration, model availability, live data mutation, or default
resolution change is authorized by this proposal. Revisit the proposal when
calibration-method evidence becomes available. The additive tool can be withdrawn without migrating existing runs; no
production M3 integration or binary installation occurred.
The predeclared 24-pair study supports the conservative 10 m recommendation:
controlled effects reach 10.598 probability points and 12.479% inverse-threshold
change. Do not infer a universal size exemption. See the
[resolution decision](../work-packages/20260908_staley_m3_wbt_terrain/artifacts/resolution_decision.md)
for criteria sensitivity and population limits.

The accepted terrain tool initially supports WGS84 UTM meter GeoTIFFs, requires
an explicit meter-elevation declaration and includes a conservative propagated
edge/NoData coverage flag. Study-only conditioning uses FillDepressions with
a 0.00001 m flat increment; area averaging, 0.02/0.1/1 km2 nested selection,
90 m nearest-channel search and diagnostic F/S values are recorded in the
predeclared protocol. These are implementer-selected evaluation controls, not
production defaults or publication-prescribed cutoffs.
