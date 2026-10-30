# Roads OFE sediment and water-budget study

Status: complete; no production candidate accepted. Started 2026-10-30 00:07 UTC (2026-10-29 Pacific).

## Purpose and authorization

The operator authorized scaffolding and executing the next Roads sediment study.
Locate the remaining excess export in road, fill or buffer before tuning erosion
coefficients. Keep the exact `wepp_261026` and explicit 200 mm boundaries. An OFE
is one modeled slope element; this study uses road, fill and buffer in sequence.

## Frozen scope

Six profiles: site sandy-loam unrutted gravel/high; site clay-loam unrutted
paved/high; Birmingham clay-loam unrutted paved/low; site sandy-loam rutted
gravel/high; Denver loam rutted gravel/low; Charleston silt-loam vegetated-ditch
gravel/low. They span two unresolved roles failures, an unrutted climate contrast, a paired
design control, a low-runoff case and an agreeing case. These are diagnostic selections, not held-out validation.

For each profile run eight modern 9002 hydraulic combinations, one modern 9002
format-only anchor, and two matched legacy-input binary controls (WEPP2010 and
WEPP261026): 66 native runs. Freeze erosion coefficients at existing bare-road,
bare-fill and forest-buffer values across the factorial. Toggle only Ksat and
its adjustment controls per OFE between existing format-only and conditioned
preparations. No fitted coefficients, geometry or management changes.

Existing source inputs and completed studies remain immutable. New inputs,
outputs and analyses are retained at `/wc1/runs/ro/roads-ofe-budget-20261029-v2`
(the initial unsuffixed staging failure remains intact). Use native
per-element outputs with source-bound units and reconcile them before attribution.
Net contributions are not gross detachment or sediment-particle provenance.

## Compatibility, risk and complexity budget

No production data/schema/default/binary changes or deployment. Experimental
records are additive and isolated; original hashes must remain unchanged.
Security impact: none; no dedicated security review required. Complexity budget:
existing Python/Rust readers and a small study harness, no new dependencies or
infrastructure. Missing accounting fields must be reported rather than inferred
as gross detachment. A source audit precedes unit conversion and budget claims.

See [plan](prompts/completed/study_execplan.md) and [tracker](tracker.md).

## Findings

See the [report](report.md): 66 completed runs; surface hydraulic toggles do not
resolve the two selected site-climate unrutted failures. The buffer is a major
net source in both. Lower-boundary drainage/storage is the next diagnostic target.
Seven modern ELEMENT/report budgets and 22 event comparisons remain unreconciled;
precision bounds were not widened. No production candidate was accepted.

Repository checks: 12,151 passed, 298 skipped; docs lint and whitespace checks pass.
