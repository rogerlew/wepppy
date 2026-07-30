# DOM-05 Channel Delineation Field Matrix

**Status**: Canonical DOM-05 contract; DOM-05A complete; SURF-14A bounded
amendment pending
**Date**: 2026-07-28 UTC

| Field group | Intended rendered/request contract | Durable boundary | Initial evidence |
| --- | --- | --- | --- |
| DEM mode and source | selected extent/upload mode and map inputs submit canonical request keys | fetch-Dem RQ chooses the selected source before channel build | controller and RQ mutation tests |
| Uploaded DEM | `input_upload_dem` accepts GeoTIFF and reflects uploaded state | Watershed retains the uploaded filename for upload mode | template and fetch-Dem RQ tests |
| MCL and CSA | rendered ids/names are `input_mcl` and `input_csa`; both controllers normalize them to canonical JSON keys `mcl` and `csa` | `build_channels_rq` passes both to `Watershed.build_channels` | actual-template, controller, and RQ tests |
| Stream pruning | selected `stream_pruning_method` submits its canonical token | worker persists the selected pruning method before build | controller/RQ evidence to add or confirm |
| Depression smoothing | DOM id `input_wbt_fill_or_breach`, submitted name `wbt_fill_or_breach`; exact choices are Fill/`fill`, Breach/`breach`, Breach (Least Cost)/`breach_least_cost`, and Topaz Conditioning Algorithm/`topaz`; the selected persisted token reloads rather than being replaced by a later config default | worker persists a validated non-null override before build; `topaz` invokes WBT `TopazConditionDem` with explicit maximum obstruction width 2 and then uses the unchanged WBT flow/channel stack; null retains stored state; only new `disturbed9002_wbt` initialization changes from `breach_least_cost` to `topaz`, while existing runs and all other configs retain their stored/configured values | REM-05 render/controller/RQ regression plus DOM-05A contract, dispatch, persisted-legacy reload, config, and installed-binary evidence |
| Successful conditioning diagnostics (DOM-05B complete) | no new submitted field; after successful channel delineation, the durable channel report renders separate labeled measures in a dedicated Terrain Conditioning Diagnostics section immediately below and styled like the map Summary table; method, maximum raise/cut, affected DEM area, and method-specific outcomes remain scannable rather than collapsed into prose; flat-routing increments remain separately attributed | each WBT method writes the sidecar in `docs/schemas/wbt-conditioning-diagnostics-contract.md`; the report route revalidates the run-scoped sidecar, while the worker validates identity and measurements, cleans invalid output, publishes reduced job metadata, and supports trigger and polling presentation; invalid diagnostics use the specified controlled error | DOM-05B four-tool fixture runs, parser/cleanup, RQ propagation, both-controller completion regressions, and channel-report field rendering |
| Least-cost distance | `wbt_blc_dist` renders/reloads and both controllers include its integer value in the payload; visibility changes with least-cost breach mode | worker persists the value before compatible WBT build | actual-template, controller, and RQ tests |

## Exclusions

DOM-05A adds only the `topaz` token and changes only the
`disturbed9002_wbt.cfg` new-run default. Existing persisted runs, the three
legacy algorithms, other configurations, authorization, CSRF, queue topology,
NoDb schema, and downstream WBT flow/channel algorithms remain unchanged.
Read-only map presentation belongs to DOM-04A/DOM-04B unless it directly
changes this form's submitted configuration.

SURF-14A is a separate bounded post-delineation amendment. It adds persisted
WBT `boundary_touch_behavior = warn|error` after subcatchment edge detection,
with legacy missing state hydrating to `warn`. It does not change this matrix's
conditioning choices, Topaz width, config default, D8/channel algorithms,
outlet, or edge geometry. See
`../../20260729_user_preferences_wbt_boundary/`.

## Result

DOM-05 found no new production mismatch. Direct tests cover the actual rendered
form, both controller payloads, and the worker's persistence order for the
scoped durable values. REM-05 remains the inherited depression-smoothing
conformance repair. DOM-05A is the additive contract authority for TOPAZ
conditioning and is complete with its reviewed checkpoint and release
evidence. SURF-14A remains pending as the bounded boundary-policy authority.
