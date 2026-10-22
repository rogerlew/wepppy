# Independent geometry review and expanded modeled domain

> Superseded allocation proposal: Roger subsequently directed full modeled MOFE
> area accounting without geographic overlap. This artifact is retained as research
> history; it is not an implementation requirement or current approval blocker.

**Date**: 2026-10-22 UTC  
**Reviewers**: accounting_contract_review, integration_contract_review (read-only)

## Confirmed UM1 geometry

The primary audit in `inspect_footprints.py` was independently checked against
native UTM polygons, avoiding a WGS round trip. All 66 modeled hillslope IDs
are present; no invalid or missing hillslope polygons explain the findings.

| Class | Road corridor area (m²) |
| --- | ---: |
| Within baseline hillslope polygons | 2129.281024 |
| Within channel-class raster polygons | 141.038728 |
| Outside watershed boundary | 1855.240934 |

Only segment 900001 has meaningful outside-boundary area. Hillslope polygons
(441844 m²) and channel-class polygons (7416 m²) partition the watershed boundary
(449260 m²) exactly. Channel raster cells are not physical channel area: modeled
channel areas sum about 1553.45 m². The 141 m² must not be charged to a neighboring
hillslope or called external watershed area.

About 1583 m² of the road/hillslope overlap belongs to hills other than the
receiving target. Thirty of 34 segments have some off-target intersection, but
one is a numerical sliver; 29 exceed 0.01 m². Prefer area-based evidence.

Flat-cap, mitre-join buffers and EPSG:32610 define this diagnostic footprint
convention. Grid-vs-ground length differs about 0.0384%; do not equate polygon
area and serialized WEPP modeled area without recording their conversion.

## Operator decision

Roger selected: “ideally we expand the modelled footprint to include the roads
area”. The package therefore retains outside-road response by expanding the
modeled contributing footprint. It does not clip exterior portions or silently
call them unrepresented external inflow. Subtract only actual overlap from
baseline hillslope representation. Road area not already represented contributes
new modeled area, whether outside the boundary or in channel-class cells without
baseline hillslope WAT. This is a hillslope-plus-roads accounting domain; channel
water-budget closure remains separately assessed.

Earlier fixed-baseline-area statements are superseded. Geographic ownership,
routing target, modeled area, and delineated watershed area remain distinct.
The approximately 1996 m² new geometric coverage is preliminary, not a finalized
serialized model denominator.

## Underconstrained rutted footprints

The integration reviewer verified that channel-associated outslope-rutted runs
have no recorded fill/buffer bearing, side-of-road, endpoints, or polygons.
`roads.py::_derive_buffer_profile_from_feature_or_defaults` returns dimensions
and provenance only; channel-associated runs bypass tracing. The slope writer's
constant 180-degree aspect is abstract, not measured geographic orientation.
For non-channel rutted profiles, buffer length uses the complete trace while a
separate fill length is inserted before it. Assigning fill to the first part of
that trace and shortening buffer would change existing admitted geometry.

Native non-channel trace provides row/column coordinates, but the present Roads
manifest retains summary values. These coordinates can be retained or retraced
for geometrically defined corridors. Existing outslope-unrutted replacement
remains its contained-hillslope strip/remainder model; it does not prove measured
contributor polygons.

There is no complete geographic union for all current rutted cases without a
placement rule or additional geometry. The operator has been asked to choose
explicit footprint inputs for area-corrected rutted runs versus an explicitly
legacy rutted scope. Do not invent bearings, reject valid existing workflows
without approval, or claim the universal implementation complete before this
boundary is resolved.

## Review disposition

Geometry audit accepted as diagnostic evidence with the projection and corridor
limitations above. Commit authority and expanded-domain scope are approved.
Final contract approval is still pending the rutted geometry policy, full
allocation/precision rules, and two reviews of the completed contract. Neither
reviewer has approved the earlier superseded contract for implementation.
