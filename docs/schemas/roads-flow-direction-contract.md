# Roads WBT flow-direction contract

Status: implemented and locally validated (2026-10-26); production deployment pending.

## Scope and decision

Roads requires WBT delineation. Its downslope tracing consumes native Whitebox
D8 direction rasters (`dem/wbt/flovec.tif` or the corresponding VRT), not TOPAZ
direction rasters. TOPAZ-style subcatchment identifiers do not imply TOPAZ flow
direction encoding. No backend selector, raster-value guessing, DEM conditioning,
channel snapping or change to routing eligibility is authorized by this repair.

Normalize Whitebox directions in the owned native adapter before the existing
Peridot TOPAZ tracer: NE=1->3, E=2->6, SE=4->9, S=8->8, SW=16->7,
W=32->4, NW=64->1, N=128->2. Use the existing Peridot conversion. The public
PyO3 function retains TOPAZ behavior by default and gains an explicit keyword-only
`wbt=False` argument for backward compatibility. The WBT-only Roads caller always
passes `wbt=True`. This is a representation correction, not a new hydrologic
formula, physical parameter, or fallback heuristic.

## Compatibility and errors

Do not mutate the original raster or create a persistent converted raster.
Convert the loaded native buffer. Preserve return keys, channel detection,
distances, slopes, loop/edge/step-limit guards and invalid-direction behavior.
Empty/invalid directions remain explicit trace termination; missing rasters,
invalid seeds and incompatible shapes retain existing exceptions. Unsupported
non-WBT Roads projects remain rejected. A newer caller requires the paired native
release; an old module must fail visibly rather than silently use wrong encoding.

Roads that have no receiving subcatchment/channel remain excluded under existing
preparation rules. Correctly connected roads previously skipped due to encoding
must proceed through profile execution, PASS combination and published Roads
reports. Baseline outputs and original project data remain unchanged.

## Acceptance

Test every Whitebox direction against independently specified raster neighbors,
including overlapping codes 1/2/4/8, and preserve existing TOPAZ callers. Exercise
actual GDAL rasters through the rebuilt Python extension, negative directions,
loops, edges, max steps and seed/shape validation. Controller regression must
prove `wbt=True` reaches the native boundary.

On an isolated copy of clogging-starch, roads-seg-000001 and 000020 through 000023
must reach channels and execute. Expected channels are 204 and 154 respectively.
The four low points on subcatchment NoData (000034, 000035, 000038, 000039) remain
excluded. Validate fresh profile inputs, PASS files, watershed completion, current
receipt and segment summary rows, preserving baseline and source hashes. These
checks establish local/environment validation; deployment and original-project
repair require their own evidence.
