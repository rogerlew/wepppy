# Gate 2.1 Review Disposition

**Disposition**: ACCEPTED — PHASE 2 AUTHORIZED
**Date**: 2026-08-08

## Reviewed Revisions

- WEPP-Forest `ea25ad79ef7dab20206bca095b2958786f5ae317`
- WEPPpy `578b5b1fe8897e0d1a6d427f9330db434c71f85b`

Gate 2.1 closes the outstanding instrumentation, replay, schema,
active-parity, fixture, and provenance findings.

Phase 2A, a stratified multi-hillslope pilot, is authorized immediately. The
complete Topanga candidate census is automatically authorized after the pilot
satisfies its declared data-integrity, routing-closure, event-pairing, and
candidate-bracketing checks.

Cross-site prevalence, snow-site, and OFE phases remain deferred under Gates 4
and 5.

## Phase 2A Scope

The pilot must include Hill 106 as the known-positive control and represent:

- burned and undisturbed strata;
- frequent and infrequent `surdra`;
- at least one observer-generated no-surplus runoff event;
- APPMTH- and HDRIVE-selected events;
- short and long downstream routing paths; and
- contrasting soils, Ksat, cover, and topographic positions.

Begin with the `±1%` first-horizon Ksat and `±0.01` paired-ground-cover
probes. Canopy and LAI probes follow after these mechanics pass.

## Automatic Exit Criteria

The full Topanga candidate census is authorized without another conceptual
review when the pilot demonstrates all of the following:

1. Every mutation has a valid manifest, realized value, terminal status, and
   input diff.
2. Baseline and mutant events are outer-joined, with absent events distinct
   from numerical zero.
3. A real observer-generated no-surplus packet validates.
4. Unmutated hillslopes remain unchanged.
5. Channels outside the declared downstream closure remain unchanged.
6. Every changed channel record lies on the target hillslope's downstream
   path.
7. Local, downstream, and outlet hydrographs have valid timestamps and
   volume consistency.
8. At least one known-positive candidate completes adaptive bracketing and
   frozen-event replay.
9. Storage, partitioning, and artifact retention are acceptable at projected
   full-census scale.
10. Any HDRIVE replay with routed-volume fraction below `0.95`, or any
    reported routing limit, is stopped and dispositioned rather than included
    silently.

Items 3 and 10 are required pilot observations, not grounds for retaining the
Phase 2 hold.

## Evidence Preservation

The existing `gate21-acceptance-report.json` remains unchanged. Its
`phase_2_census_authorized: false` field correctly records that the acceptance
command did not itself grant authorization; this review disposition grants it.
