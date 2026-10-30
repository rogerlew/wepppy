# ADR-0113: Native accepted-boundary water and current-event sediment accounting

- Status: Proposed; C3 water formulation rejected after validation; U2c event repair retained experimentally. No released binary or Roads default change.
- Date: 2026-10-30
- Decision venue: WEPPcloud Roads agent session, America/Los_Angeles.
- Participants: project owner and Codex; independent implementation/scientific agents review evidence.
- Decision owner: project owner authorizes ablation; scientific acceptance remains pending.
- Implementer: Codex.

## Context

The repaired `wepp_261029` rejects two generated-soil Roads fixtures because a
daily runoff calculation asks the hourly allocator for more water than exists.
The allocator's refusal is correct. Equivalent-plane calculation can recompute
upstream infiltration after that upstream soil's water balance has committed.
Later O2 traces establish melt-support compression as the causal defect in
the two retained failures; upstream GRNA already uses pre-event STOLD. See
[ADR-0114](ADR-0114-native-equivalent-melt-support-and-storage.md) for the narrower
corrective formulation. A separate late-return path enables sediment routing after current-event setup
was skipped, reusing prior-event coefficients and duration.

## Decision for this ablation

Retain the independently tested U2c current-event repair experimentally. Reject
and roll back C3 water processing: output accounting passed, but connected
hydraulic support, peak-area frames and incoming-sediment deposition did not.
No new release or Roads parameter default is accepted. Define separate local
water and connected hydraulic geometry contracts before another water mutation.

### Evaluated C3 water proposal (rejected)

The experiment tested the following formulation. For continuous hourly UI
hillslopes with no contour or irrigation system, use the same sequential boundary
calculation for every receiving OFE, independent of whether return is positive.
Use local melt, soil capacity and length, plus accepted upstream Hortonian input.
Normalize the upstream excess shape captured before return is added to its
accepted post-recession volume, using the existing effective-length conversion.
Merge that input after local interception; keep return and lateral water on the
existing hourly stock path. Keep local-only rainfall intensity and energy for
raindrop detachment. Preserve the existing calculation outside the explicitly eligible model domain.
Hortonian-only events within that domain intentionally use sequential accounting.

### Retained U2c event-state proposal

Require current-event erosion preparation before ROUTE/SLOSS. Preserve late water
and its source-time metadata, but do not route stale erosion state. Publish zero
meteorological duration for a confirmed late return source using a local value;
leave the shared global duration unchanged for legacy consumers such as furrow
irrigation. No parameter values, guard thresholds or acceptance bounds change.

## Rationale and alternatives

Clipping negative FIN, deleting incoming return, relaxing the inventory guard,
or adjusting soils would hide the native request defect. Pure-return separation
alone completes Birmingham but does not resolve mixed-source Charleston.
The original return-only scope proved discontinuous; the broader consistent scope
required its own scientific assessment. Clearing
global duration fixes the retained event but risks a later irrigation consumer;
the local publication value avoids that new dependency. A return-triggered
formulation was rejected: a 45-case native subproblem found up to 10.682542 mm
finite change at zero-to-positive return with unchanged Hortonian/local forcing.
Consistent receiving-element accounting removes the method switch; an arbitrary
epsilon would merely move it. Independent scientific review supports testing this
broader scope, not promotion without validation.

## Evidence and acceptance

Native canonical checkout: `/workdir/wepp-forest-release-20261009`.
Work package: `docs/work-packages/20261030-roads-native-accounting/` in that repo;
committed four-case reproduction: `755a15fbe`. Active incident:
`docs/ablation/20261030_roads_daily_coupling_and_event_state/`.
[Roads continuation](../work-packages/20261029_roads_parameterization_program/artifacts/continuation-findings.md)
records the original 840-case failure panel. The native plan requires frozen-input
replays, source accounting controls, native regression/watchlist gates and
independent review. Existing output audits are not complete water closure.

## Risks and rollback

The water candidate changes shared multi-OFE process behavior beyond Roads;
peak timing, deposition, storage coupling and legacy shared state require review.
An excess-flow shape is not a newly validated travel-time hydrograph. Existing
Hortonian transfer uses length scaling; variable-width closure is not established.
Reject any lane that fails stock/source conservation, generates rainfall energy
from runon, or changes excluded paths. Finalize each upstream segment before starting the
next receiver; preserve RDAT interval-versus-endpoint semantics. Independent review
caught and rejected a candidate that otherwise suppressed valid upstream erosion. Keep rejected lanes as evidence and restore
accepted source. Release promotion and UI implementation are separate decisions;
the UI specification/layout remains human-gated.


## Native ablation disposition — 2026-10-30

Canonical native package: `/workdir/wepp-forest-release-20261009/docs/work-packages/20261030-roads-native-accounting/`.
The separate U2c stale-event repair is retained for validation. C3 water changes
are rejected and rolled back despite 840/840 output-accounting passes: independent
controls demonstrate lost connected hydraulic support, inconsistent peak-area
normalization and skipped deposition when runon fully infiltrates. Cedar peak
+42.64% and sediment +35.05% with water +0.00212% require this hold.
C3 magnitude is 719/840, while literal-legacy attribution is 96/96. Neither is a
Roads default acceptance. Frozen inputs, candidates, review probes and Cedar figures
are retained in the native package. The water mechanism remains unresolved;
C4 diagnostic controls define the next geometry/accounting contract before another
behavioral patch. Keep wepp_261029 pinned, withheld materials unused, and parameter
tuning paused. The human gate on configuration specification/layout still applies.
