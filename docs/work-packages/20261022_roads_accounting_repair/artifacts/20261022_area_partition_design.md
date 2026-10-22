# Area-partition steering and unresolved model decision

> Superseded allocation proposal: Roger subsequently directed full modeled MOFE
> area accounting without geographic overlap. This artifact is retained as research
> history; it is not an implementation requirement or current approval blocker.

**Date**: 2026-10-22 UTC  
**Status**: Expanded scope approved 2026-10-22 20:30 UTC; detailed contract checkpoint pending

Roger responded to the additive accounting choice: “i'm wondering if we should
area corrrect the hillslopes so the roads area isn't double counted”. This raises
an area-partitioned modeling alternative to the draft boundary-injection policy.
Roger subsequently approved expanding the work package to this area-partitioned
modeling correction, including PASS reconstruction and routing validation.
The earlier boundary-injection draft is superseded. Commit authority is granted;
detailed geographic partition and precision rules remain checkpoint work.

## Confirmed evidence

UM1 completed channel-associated inslope contributors have modeled road area
4,127.124184 m² from width times length, versus baseline footprint 441,820.29 m².
Raw WAT rounds this road area to 4,127.15 m². Grouping those areas by current
receiving target gives 2,412.02 / 8,627.64 m² (27.96%) for WEPP ID 27 and
322.74 / 816.66 m² (39.52%) for ID 53. These are delivery assignments, not
validated geometric road ownership fractions.

Source: completed rows of `roads.nodb` last_run_summary.segment_execution_records;
baseline area from distinct `(wepp_id, ofe_id, Area)` in H.wat.parquet. Original
files were read only. Channel-associated UM1 profiles are single road OFEs;
other designs contain fill/buffer OFEs with additional modeled area.

## Defensible area-partition proposal

Partition geographic watershed area into nonoverlapping contributor footprints
and remaining baseline footprint. Scale baseline extensive quantities by
remaining represented area / original modeled area; include modeled contributors
once at their represented-area weights. Preserve each contributor's native OFE
identity during WAT reduction. Apply identical represented-area weights to PASS
before watershed routing, and to WAT local water volumes and terminal lateral.
Keep watershed footprint fixed. Record this as an area-weighting approximation,
not a rerun that resolves altered hillslope geometry or upstream hydrology.

Surface runoff routing attribution and geographic area ownership are separate
mappings. A road can cross one hillslope and discharge into another. Do not
subtract its entire area from the receiving target merely because the PASS
contributor is assigned there. Explicitly account for road/fill/buffer overlap
and overlapping contributor profiles; subtracting road pavement alone while
adding all buffer rainfall/percolation retains double counting.

Existing outslope-unrutted replacement already partitions strips and remainder;
preserve that model and replacement-supersedes-additive precedence. A new
additive partition must not subtract replacement area again.

## Existing mechanism and scope consequence

`wepppyo3/wepp_interchange/src/hill_pass_combine.rs` already implements
`combine_weighted_hillslope_pass_files` for AgFields. It scales extensive water,
sediment, components and hydrograph peaks by represented/model-header area,
recomputes derived quantities, checks closure and reparses output. A reviewed
Roads strategy can reuse that kernel; do not misuse the AgFields strategy marker
or introduce a Python PASS scaler.

This alternative changes generated PASS and watershed routing results, not only
report aggregation. It has explicit operator scope approval and still needs updated
canonical Roads construction/geometry contracts, an ADR, native tests, and
fresh watershed reruns on isolated copies. Current inputs cannot prove a
nonoverlapping geographic partition without additional geometry inspection.
No runtime implementation may proceed under the unratified boundary-injection
draft while this choice is unresolved.
