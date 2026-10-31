# Next observation: particle-class mass closure

Status: scaffolded; source observation not executed; no behavioral fix proposed.
The DEPEND candidate remains unpromoted. Continue the active Roads ExecPlan,
whose physical-acceptance milestone prohibits unexplained accounting mismatch.

## Evidence and scope

Independent comparison of generated PASS and ELEMENT records finds particle
fractions summing above one beyond their printed uncertainty. The largest
retained downstream example is site / 1718465 / outunrut / gravel / low,
buffer-cap lane, 2012 day 302: fraction sum 1.00711 (print bound 0.000016).
Class concentration times event volume gives 17.077241792 kg; ELEMENT boundary
export is 16.9403551468 kg. Difference 0.1368866452 kg exceeds the combined
printing bound 0.0225151222 kg. Entire offending PASS EVENT and ELEMENT rows
match revision 3 exactly. This is a baseline limitation, not a DEPEND regression.
Previous finite/nonnegative particle checks did not test normalization and
class-mass closure. Do not describe them as proving those stronger properties.

## Portable paired inputs

`particle-closure-inputs.tar.gz` and `particle-closure-fixture.json` freeze the
full 16-year seed and original generated baseline control. Extract into an
empty directory, create output/ beside each runs/, and execute each p1.run.
Rehash every input and retain complete outputs. Their only consumed input
difference is the previously declared buffer upper-200-mm conductivity cap;
no new parameter changes or withheld materials are authorized by this fixture.
Promote the capsule or a deterministic generator into native tests before
making a new required native gate. Reproduce released and DEPEND-candidate lanes
separately; never silently combine numerical fixes.

## Observe before repair

Trace ENRICH entry/exit on the failing event: ldtop, lddend, theta, xtop,
xdetst, intlod, rillod before/after its nonnegative clamp, and incoming/output
fraction sums. Trace SLOSS avsole, runoff, efflen and sedcon through the same
event. Record OFE and simulation-calendar context. Require exact unobserved
output parity for each observation lane and paired control.

One source hypothesis is ENRICH's nonnegative rillod clamp followed by division
of all component contributions by ldtop: if lddend+intlod exceeds ldtop, the
resulting fractions may exceed one. This is unconfirmed until native states
and independent mass reconstruction establish the source. Do not normalize
fractions or clip sediment merely to make the audit pass.

## Acceptance and continuation

Retain printed-uncertainty bounds derived from actual fields, all failed rows,
and source-specific mass budgets. Identify every consumer of a confirmed shared
assumption. Only then declare the smallest single-mechanism repair and an ADR,
with independent equations and neighboring controls. Revalidate the full native,
Roads/downstream, Disturbed and Cedar evidence before combined release promotion.
The same-name undeployed 261029 preference remains conditional on these gates.
UI specification/layout remains human gated; Roads defaults stay unchanged.
