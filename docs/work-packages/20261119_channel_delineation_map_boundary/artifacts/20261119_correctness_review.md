# Channel extent correctness and user experience review

## Scope and disposition

The independent correctness reviewer examined the policy checkpoint
`77dbafa04`, the channel submit route, common watershed builder, RQ error
delivery, both browser channel controllers and the acceptance tests. The
reviewer's source recheck approved the final extent calculation and reported
zero remaining medium or high findings.

The review identified four changes that are now in the candidate. Controlled
worker errors carry `details`. Invalid stored extents use the safe validation
error. Explicit CRS84 accepts the standard spellings. The end-user channel
guide describes how to retry. The review also found that transforming two
opposite UTM corners could omit about 22 m at an edge. The validator now uses
densified bounds across all four edges, with a real EPSG:32610 regression.

## Valid states and errors

| State | Outcome and evidence |
| --- | --- |
| Setting absent, empty, or legacy unset | The real config parser and policy tests verify bypass without asset resolution. |
| Explicit opt-out | The literal, quoted and case-insensitive policy is read intact. The bypass test rejects any attempt to resolve its absent asset. |
| Supported polygon or multipart boundary | The geometry tests cover disjoint, touching, overlapping, covered, hole and separated multipart cases. The tracked regional assets load, including NAD83 for Coeur d'Alene. |
| Installed DEM with stale map metadata | The mode 3 route cases use actual raster geometry in both directions. The RQ test uploads a new DEM before the worker and verifies the race cannot bypass the check. |
| Malformed bounds, policy or asset | Tests cover invalid extent and configuration codes, including missing, invalid, remote, escaped and malformed asset references. |

Existing request decoding errors remain in force. A valid request that misses
the boundary returns `channel_extent_outside_boundary`. A malformed effective
extent returns `invalid_channel_extent`. A bad required config reports
`invalid_channel_boundary_config`. Both channel controllers already render the
escaped message in the error summary. In an asynchronous rejection, job info
includes the error code and a correlation ID. The status stream includes the
message.

## Generated artifact evidence

In the isolated dev image, the real Upload DEM endpoint installed a 48 by 48
cell GeoTIFF as a VRT and reloaded its map from Ron. The test read the VRT source
references and raster values, then ran the actual channel submission, RQ
parent and child and installed WBT binary through disposable Redis. It read the
positive stream cells in the generated channel raster and verified that the
GeoJSON consumed by the map endpoint contained features. A disjoint resubmit
retained the channel readiness, saved extent and original GeoJSON bytes with
zero queued jobs. A replacement VRT after enqueue failed at the locked worker,
reported a sanitized job error and left the prior map overlay bytes intact.

Direct validation before channel writes was also exercised with WBT and TOPAZ,
using real NoDb state. Batch settings-only behavior is exercised by the
existing route regressions. Batch leaf coverage is through the same actual
NoDb builder and config path. The native artifact test used WBT and did not run
an entire Batch Runner project, a native TOPAZ build or a production browser.
The highest supported claim is locally validated.
