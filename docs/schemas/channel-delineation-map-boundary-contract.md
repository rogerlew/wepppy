# Channel delineation map boundary

Implementation conformance is pending.

## Configuration

The effective project config can set `[map] boundary_check` to one of three
values. The setting applies to channel delineation for both WBT and TOPAZ.

| Value | Requirement for the requested extent |
| --- | --- |
| `none` | Any extent admitted by the existing delineation workflow. |
| `intersects` | At least one point in common with the configured boundary. Edge and corner contact qualify. |
| `covers` | The entire extent is inside or on the edge of the configured boundary. A hole that overlaps the interior of the extent disqualifies it. |

With a configured `[map] boundary`, an omitted, blank or valueless
`boundary_check` defaults to `intersects`. Policy values are case-insensitive and
can be quoted. The effective config reader must preserve the literal `none`
policy rather than applying the legacy path sentinel to it. An unset boundary, including values the config reader normalizes
to unset, bypasses the spatial check. `none` also bypasses it without opening
the boundary asset. Use the effective persisted project config for both
settings. A run map can display an overlay from other sources, including a
Batch Runner target. Those overlays carry no delineation policy.

Existing supported boundaries are local polygon GeoJSON files under the
application-owned WEPPcloud static tree, which run callers cannot write. Accept `static/...` and `/static/...` references.
Require a regular asset within the canonical static root after resolving symlinks and reject remote or out-of-tree references.
Evaluate Polygon and MultiPolygon geometry, including polygon features in a
Feature or FeatureCollection, as a union with holes in a common geographic
coordinate system. Support GeoJSON's default WGS 84, explicit CRS84, geographic
WGS 84 and the NAD83 declaration used by the Coeur d'Alene asset. An unknown
policy, unusable asset, or unsupported geometry or coordinate reference system
is a project configuration error when the check applies. The deprecated
`salvage_logging` preset and its historical asset are outside the supported
asset inventory.

Use the actual extent supplied for channel processing. Map Bounds and drawn
extent use `map_bounds`, the map-object mode uses `map_object.extent`, and
Upload DEM uses the stored map extent established by the validated upload.
Bounds are west, south, east, north in longitude/latitude. Accepted requests
proceed using their full extent. Channel build entry points that operate on a
stored project map use that map's extent. A Batch Runner leaf uses its own
effective project config and processing extent. Base project submissions that
only save shared watershed settings have no channel processing extent.

## Admission response

Submit to `fetch-dem-and-build-channels` using the existing request schema.
When a spatial check applies, it precedes any channel request save, readiness
invalidation or enqueue for a real delineation request. A failure preserves
prior readiness and artifacts and permits retry. Existing request decoding errors remain in force. After decoding, the existing
RQ error envelope carries these outcomes.

| HTTP status | Error code | User action |
| --- | --- | --- |
| 400 | `channel_extent_outside_boundary` | Move or resize the extent to meet the policy, or upload a DEM whose extent meets it. |
| 400 | `invalid_channel_extent` | Select an extent with valid geographic bounds. |
| 500 | `invalid_channel_boundary_config` | Contact support. Internal asset paths and parser details stay out of user-facing errors. |

A direct channel build from persisted state applies the same policy before
changing channel artifacts. The channel worker rechecks the persisted extent
under the same watershed directory lock used by Upload DEM. The check concerns the request geometry. The WBT
DEM-edge policy independently evaluates the generated watershed against the DEM.
