# DOM-05 Channel Delineation Field Matrix

**Status**: Covered behavior; documented pending a named revision
**Date**: 2026-07-28 UTC

| Field group | Intended rendered/request contract | Durable boundary | Initial evidence |
| --- | --- | --- | --- |
| DEM mode and source | selected extent/upload mode and map inputs submit canonical request keys | fetch-Dem RQ chooses the selected source before channel build | controller and RQ mutation tests |
| Uploaded DEM | `input_upload_dem` accepts GeoTIFF and reflects uploaded state | Watershed retains the uploaded filename for upload mode | template and fetch-Dem RQ tests |
| MCL and CSA | rendered ids/names are `input_mcl` and `input_csa`; both controllers normalize them to canonical JSON keys `mcl` and `csa` | `build_channels_rq` passes both to `Watershed.build_channels` | actual-template, controller, and RQ tests |
| Stream pruning | selected `stream_pruning_method` submits its canonical token | worker persists the selected pruning method before build | controller/RQ evidence to add or confirm |
| Depression smoothing | DOM id `input_wbt_fill_or_breach`, submitted name `wbt_fill_or_breach`, selected token reloads | worker persists a non-null override before build | REM-05 render/controller/RQ regression |
| Least-cost distance | `wbt_blc_dist` renders/reloads and both controllers include its integer value in the payload; visibility changes with least-cost breach mode | worker persists the value before compatible WBT build | actual-template, controller, and RQ tests |

## Exclusions

This audit does not change hydrologic algorithms, defaults, allowed tokens,
authorization, CSRF, queue topology, or NoDb schema. Read-only map presentation
belongs to DOM-04A/DOM-04B unless it directly changes this form's submitted
configuration.

## Result

DOM-05 found no new production mismatch. Direct tests cover the actual rendered
form, both controller payloads, and the worker's persistence order for the
scoped durable values. REM-05 remains the inherited depression-smoothing
conformance repair.
