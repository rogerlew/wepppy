# ADR-0105: Roads dashboard detachment aggregation and display

Status: Accepted; independent contract review complete, implementation pending  
Date: 2026-10-23

## Context

Roads summaries provide mean annual profile detachment and full modeled OFE area.
The dashboard currently has no road-segment result layer. Prepared road geometry
can correspond to multiple profiles; their abstract rectangular off-road areas
do not establish real mapped fill, buffer or land-use footprints.

## Decision

Draw prepared road centerlines only. Color each fully completed segment with
`10 * sum(soil_loss_kg) / sum(modeled_area_m2)` over distinct contributing profiles.
The factor ten converts kg/m² to metric t/ha; source masses are already annual,
so do not divide by duration again. Include mixed profiles with explicit full-profile
labels; exclude synthetic replacement remainder profiles from the road layer.
Partial lines remain uncolored; retain finite signed results with separate negative
states rather than silently clipping. No source-summary or model change.

Use the existing jet2 sediment/erosion palette, a linear zero-to-project-maximum
range for positive values and the existing maximum override interaction. Keep a
numeric legend and accessible text/table equivalent. Default overlay off in an
ordinary dashboard and on from Roads results. Scope switching is independent of
overlay visibility. Missing values are not zero; all-zero/constant data require
a usable, honest legend without invented measured variation.

## Decision Provenance

Decision Venue: operator conversation, 2026-10-23 Pacific; recorded
2026-10-24 05:32 UTC. Exact individual message times are unavailable.  
Participants Present: Roger Lew (operator), Codex (assistant).  
Decision Owner: Roger Lew.  
Implementer: none yet; contract preparation by Codex.

The operator rejected mapped MOFE fill/buffer/land-use areas, selected the existing
sediment/erosion palette, required an in-dashboard Roads-scope switch and accepted
the other presented recommendations.

## Change Summary and Rationale

Old behavior: no road-line metric or corresponding initial visibility/scaling.
New behavior: the display aggregation and defaults above. Area weighting avoids
the bias of averaging profile densities; a single diagnostic line avoids invented
profile geography. Full modeled area preserves upstream numerical semantics.
Existing colors retain visual familiarity. Project-specific linear scaling avoids
inventing universal erosion thresholds, but colors alone cannot compare projects.

## Alternatives Considered

An unweighted density average misrepresents differing modeled areas. Road-prism
normalization mislabels mixed profiles. Excluding every mixed profile hides valid
results. Inferred area polygons or channel-distance strips imply unproved geography.
Fixed cross-project thresholds lack an accepted basis; logarithmic scaling is not
selected. Automatic percentile clipping would hide extreme values.

## Evidence and Validation

Canonical behavior: [Roads dashboard contract](../schemas/roads-gl-dashboard-contract.md).
Numerical authority: [segment summary](../schemas/roads-segment-loss-summary-contract.md).
Review package: [Roads GL Dashboard](../work-packages/20261023_roads_gl_dashboard/package.md).
The current clogging-starch example has 39 prepared lines and 34 summary rows;
this supports one-to-one inslope feasibility only, not mixed-profile map validation.
Future checks must prove actual producer-to-browser values and accessible states.

## Risk and Rollback Notes

The line represents a modeled-profile diagnostic, not incremental road impact or
off-road geographic extent. Display must label that limitation. Different project
maxima produce incomparable colors without reading legends. Revert the new display
and selector if their semantics or authorization fail; retain producer artifacts,
existing scoped URLs and upstream contracts. No deployment or numerical repair is
authorized by this ADR.
