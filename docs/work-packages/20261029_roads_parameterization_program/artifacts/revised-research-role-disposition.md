# R-09: research capsule versus production role representation

**Disposition:** confirmed representation incompatibility for transplanting old `outunrut` capsules into the canonical production geometry; no demonstrated role-order defect in `builder_bridge.inject` or the three inspected frozen histories. Do not splice their soils into a production profile by OFE position. No source edits, model calls, historical reclassification or reserved-material use occurred.

## Exact producer and readback

`revised-research-role-readback.json` binds three actual r7 modern seed capsules under `/wc1/runs/ro/roads-parameterization-program-20261103/engine-seeds-v3/cases/`: `meaningful_high`, `passing_same_signature`, and `underprediction_less_supply`. All are `outunrut`. Actual soil/slope/management SHA256 values match the seed declaration. Each soil has land uses `[bare,bare,forest]`; each management's initial assignments explicitly read `[ROAD,FILL,FOREST]` in OFE order. This is not a landuse/road/fill management deck.

Their actual common slope file SHA256 is `f79d4739fe7fa1fdd7157c53dd6eaae661c4729b228e42bead741a9d6c66b8d3`: width 43.1052293811319 m and OFE lengths 5.60, 4.57, 39.62 m. Management SHA256 is `6ed3319bd1bce803b0cd2efbf631765b6d6e1f00bd2534f59358df11f9ecb31c`.

The original producer is `development_matrix.py:execute`: it copies the corresponding FSWEPP-matched reference slope/management, then calls `builder_bridge.inject(..., (1,2,3))` for this benchmark representation. The actual original development-matrix records retained under `/workdir/wepppy/out/roads-parameterization-program-20261030/development-matrix-v1/matrix-v1/` record `order=[1,2,3]`, `road_index=0` for all three checked cases. Their record paths and hashes are retained in the readback JSON.

The reference geometry producer is the historical `docs/work-packages/20261029_roads_soil_benchmark/artifacts/benchmark.py:slope_text`. It initializes road length/width/grade at 60.96 m/3.96 m/4%; for `outunrut` it transforms that **first road OFE**, then appends the 4.57 m fill and 39.62 m buffer. `execute_case` selects the `3outunr` management family. Thus labeling these old slope rows as “upstream landuse / road / fill” solely because the design string is `outunrut` would itself be a role attribution error.

Both `development_pilot.py` and `development_matrix.py` explicitly describe matched FSWEPP three-OFE geometry and distinguish actual production-builder/project validation. The matrix's unconditional `(1,2,3)` is consistent with its chosen reference representation. These historical scripts are not a universal production adapter.

## Current canonical representation and helper behavior

Current `tests/roads/roads_matrix.py:ARRANGEMENTS` and the Roads validation-suite contract use production unrutted orders `(3,1,2)` and `(3,1,2,3)`: upstream landuse / road / fill, optionally downstream landuse. They call the production slope/management/soil writers with that order.

`builder_bridge.py:inject` selects forest only where the supplied role is 3, otherwise bare; it finds the road with `order.index(1)` and applies road erosion/header/cap treatment at that index. Its own canonical matrix driver obtains the actual `record['ofe_order']` from `tests.roads.roads_matrix.prepare`, then passes that order into `inject`. Therefore canonical order `(3,1,2)` correctly yields `[forest,bare,bare]` with road index 1. The helper does not infer roles from a design string or require road index 0. Its retained 294-case bridge result is builder/readback evidence, explicitly not native validation.

## Consequences and smallest future action

Frozen seed/full-panel outputs remain evidence for their declared inputs and reference comparison. This finding neither reverses old experiment classifications nor makes those profiles current geographic production validation. Numerical accounting certificates concern those executable decks; role names in any later interpretation must follow their actual soil, slope and management provenance.

The new canonical sensitivity harness must use canonical builders and read back each role order. Excluding the old unrutted capsule from direct canonical-geometry transplantation is justified. If a later generated-soil production comparison is needed, prepare a new declared canonical profile using its actual `ofe_order`, call the existing helper with that order, and verify matching soil/management/slope roles and native behavior. This would be a new experiment, not a repair or rewrite of the old histories. It needs no new role-mapping abstraction or blind OFE permutation.

Scope of this disposition is the three named capsules and their demonstrated producer path. It does not certify every historical script or field interpretation. There is no confirmed active reusable-builder defect requiring a source change from this finding.
