# Next development gates for general rock support

This is a concrete continuation specification. It does not promote a new native
parameter, automatically rewrite soils or authorize the Roads UI implementation.

## Surface observations and acquisition

Retain observation records before aggregation. Each record needs source/revision,
mapunit/component or sampling identifier, geometry/area support, road/fill/ditch/
buffer/range role, observation date, fragment-size limits, material kind, cover
basis (total area or exposed rock within bare), value and uncertainty/support
count. Missing, measured zero and excluded wood must be distinguishable. For
survey records retain low/representative/high cover, component proportion and
fragment-row key. Component proportion is not the same as measured footprint
area; do not multiply the two without a documented mapunit-to-run join.

Resume the exact four-material query in `fetch_surface_evidence.py` to a fresh
destination when NRCS access is restored. Independently inspect returned schema,
nulls, kinds and duplicate/component supports. Preserve source date separately
from the historical Roads material snapshot. A successful survey query supplies
priors, not measurements of engineered armor. No live data were returned in
this execution.

Before implementing a summary/parquet producer, decide whether each fragment
row partitions a size class or overlaps another class. Report supported area
and unknown area rather than calculating a reassuring average over observed
rows alone. Prefer explicit field observation for Roads roles. Retain original
rasters at their original resolution; aligned 30 m copies do not create 30 m
information. A low/high survey interval or SoilGrids quantile is not a calibrated
probability interval for surface cover.

## Persistent native surface protection

Map the current generic-cover intent before introducing a new compartment.
Existing crop cover can implicitly represent armor; adding explicit rock could
count that protection twice. For each native interrill/rill support, choose one
observable definition:

- measured exposed rock fraction E of total area, giving effective protected
  area equal to existing protected area plus E when their supports are disjoint;
- fraction r of the remaining exposed area that is rock, giving
  C_effective = C_existing + (1-C_existing)*r.

These equations describe area accounting only. They do not establish the right
friction, infiltration or detachment coefficients for rock. Do not claim that
substituting C_effective into a residue-calibrated equation validates rock's
mechanical effect. Keep rock outside residue biomass/decomposition and explicitly
specify whether cover is static or responds to burial/exposure; defer unsupported
dynamic armor evolution rather than invent rates.

An isolated source prototype must preserve exact zero-rock outputs across
crop/range, freeze/thaw and current Roads controls, maintain finite bounded area
fractions, and avoid changing profile RFG or landuse. Observe the destination
consumer terms before evaluating output magnitude. Separate interrill protection,
rill friction and infiltration hypotheses if one cover intervention would change
all three with unvalidated coefficients. Declare which endogenous hydraulic
responses may change; verify complete water/particle accounting rather than
requiring physically inappropriate runoff equality.

No prototype should become a default because it lowers sediment. Require
independent model review, role-relevant evidence, the original full-period Roads
panel including passing/opposite controls, and general Disturbed/watershed
regressions before promotion. The six withheld Roads materials remain withheld
until the original protocol admits them.

## Profile water capacity and retention

The 586-layer ordering result clears one read-only feasibility check. Next derive
an explicit stock/flux contract across SCON, GRNA, both water-balance routines,
INFPAR, percolation, lateral drainage and freeze/thaw. Record each consumer's
volume basis, layer support and execution clock. Native CPM, air correction and
dry-water coordinates must be applied exactly once. Preserve displaced water as
a named flux when a capacity contracts; never clip an occupied stock away.

Actual-source scalar fixtures must cover zero rock, high rock/native caps,
near-limit dry/field water, no input water, saturation overflow, freezing/thawing
and changing fine-earth density. Keep static initialized porosity as the first
hypothesis; dynamic porosity refresh is a different mechanism. Reject a candidate
if it creates water, invalidates ordered limits or needs a new arbitrary bound.
Only after source/scalar review should a full-period native behavioral comparison
start. The current source/binary is unchanged.

Separately reconcile SSURGO whole-soil volumetric water, source fine-earth density,
fragment volume, current capped-mass inverse and downstream native correction.
Use original source horizons and retained generated output, not only corrected
summary values. Porous fragments may store water; a nonporous dilution correction
is a model assumption, not universal field truth. Do not combine retention,
capacity and surface-cover changes into one candidate.

## Regional and lifecycle compatibility

Obtain the exact BC SIFT COFRAG and BD metadata for the consumed dataset before
changing it. Generic field guides suggest volume but do not establish the actual
prepared-record basis. Any repair needs emitted-file and native-consumer checks,
including absent density and existing caps. Do not broaden the SoilGrids fix to
SSURGO, uploaded or legacy mass fields.

Keep prior artifacts reproducible. New model/input versions must document which
rebuilds change values, retain old outputs until rebuilt and carry parameter
provenance. User-facing controls require their own approved specification and
layout; the current work adds no UI, hidden automatic migration or deployment.
