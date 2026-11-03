# MIPA-03 decision preparation: specialized consumer compatibility

Status: proposed decision boundary, 2026-11-03 UTC. Not a ratified checkpoint
or implementation ancestor. The operator authorized the continuation through
the handoff; a material scientific interpretation remains unresolved.

## Verified starting point

WEPPpy starts at `3e4e80c6d`; selected native default-branch checkout starts at
`4f0728984`. Retained revision-6 pairs and sidecars match the handoff hashes.
The [reference discovery](mipa03_reference_discovery.md) binds model source
`2e5928702` to a committed historical specialized binary identical to the
installed `wepp_reveg_2e59287`. Historical compiler flags lack a modern sidecar;
compiled reader probes separately verify the inspected source behavior.

The [producer review](mipa03_producer_protocol_review.md) records direct writer
reproductions. Ordinary two-OFE 9005 writer output, read by compiled selected
`input.for` blocks, binds texture enums 3/1 into `lkeff` instead of 0.7/1.7.
The duplicate restrictive read then fails on OFE 2's header. Evidence is under
`/wc1/holdouts/mipa-native-r7-20261103/soil-baseline`.

## Concrete unresolved choice

The specialized reference is not just a parser. It includes distinct 9005
conductivity interpolation, RAP growth/root changes and residue burn-down.
Existing canonical contracts preserve producer transforms but do not settle
these inconsistent reference numerical branches:

| Boundary | Exact reference behavior | Alternative requiring an explicit decision |
| --- | --- | --- |
| Fire date | Post-fire canopy branch requires both year at/after fire year and day-of-year at/after fire day, including every later year | A chronological comparison stays post-fire throughout subsequent years |
| Transformed moderate/high forest | Compare canopy against shrub+perennial+annual, then assign TREE | Select one consistent cover limit and compare/assign that same quantity; the intended quantity is not established |
| Shrub/perennial | Compare canopy against one band, then assign the sum of three bands | Choose a consistent limit, which changes vegetation/ET behavior |
| Canopy domain | Clamp at 1 before computing log(1-canopy), clamp at .999 only later | Decide domain behavior explicitly; do not invent an epsilon or silently move a numerical threshold |

For example, a July fire makes a January date in the following year take the
reference pre-fire canopy branch. For transformed forest with canopy .4,
shrub+grasses .3 and tree .6, the branch increases canopy to .6. These are direct
branch illustrations, not measured full-history outputs or approved corrections.

The pending operator question asks whether to preserve exact historical numerical
rules with documented limits, or prepare corrected semantics for review. The
latter needs a concrete choice of cover limit before implementation; it does not
authorize the agent to invent one. Preserve all selected non-9005 arithmetic,
FC/HK ownership and PMET behavior regardless of that answer.

## Contract amendment and compatibility work

The forthcoming standalone checkpoint must amend durable contracts outside this
package in both repositories and include an ADR for the specialized numerical
port. Applicable existing authority includes MOFE input identity, native MOFE
coefficients, whole-soil water capacity, input/upload admission and binary lifecycle.
Two independent read-only checkpoint reviews must precede production edits.

Reconcile seven-field headers, single restrictive records and producer LITTER/BARE
order. Preserve exact numeric OFE identity and annual band identity. Define accepted
calendar/date syntax, absent fire state, cleared flags, populated/malformed inputs,
and retained failure artifacts before editing preparation or native readers.
The source reference's ignored year labels and fixed 20-OFE/50-year arrays do not
automatically become target contracts. Existing uploaded-version admission and
configured executable defaults remain fixed.

The 9005 port must explicitly account for reference conductivity interpolation,
its .99 saturation factor, RAP bypass of generic adjustments, and assignment to
the first two layer conductivities. Copying the whole divergent `infpar` or `grow`
would change unrelated modes and is outside scope. No new formula is selected here.

## Regression and release acceptance

Retain actual-reader failures and use committed fixtures/generators for final
native gates. Exercise distinct textures/hydraulics, unequal layers, numeric OFEs
2/10, one/multiple OFEs, multiple years, fire boundaries, transformed/untransformed
cover, missing/extra/malformed records, daily/hourly consumers and unaffected
controls. Observe both read state and dynamic operands; prove observer neutrality.
Quantify runoff, ET, drainage, storage and vegetation effects without treating an
unsupported successful baseline exit as a numerical oracle.

Use complete canonical preparation on a supported disposable fork with deliberate
specialized RAP state; the prior awake-versatility workflow is not that acceptance
case. Bind identities, mounts, settings and presence-file consumption. Validate
the final matched Linux pair through installed selection, native outputs,
interchange and reports. Preserve revision-6 binaries and frozen publication;
revision 7 needs fresh gates, disclosure review, visual inspection and byte checks.
No deployment, default switch, Windows release, Rust promotion or bulk regeneration.

## Current disposition

Discovery and failing baselines are complete enough to expose the decision;
implementation and release are incomplete. No canonical numerical amendment has
been ratified and no production source has changed. Independent discovery reviews
are not substitutes for the required contract, implementation, QA and security
reviews. The active plan and tracker retain the pending work.
