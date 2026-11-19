# Channel extent security review

## Scope and verdict

The independent security reviewer examined the authenticated route, config
authority, local GeoJSON resolution, geometry parsing, controlled error paths
and the watershed lock used by Upload DEM and the channel worker. Security
impact is high because the route now opens an application asset before
enqueueing. The reviewer approved the recheck with zero unresolved medium or
high findings.

## Findings and closure

| Finding | Severity | Disposition |
| --- | --- | --- |
| The saved map can diverge from an uploaded DEM when settings are saved or another upload arrives before the worker. | Medium | Admission validates the installed raster bounds where the policy applies. The worker checks the raster it consumes under the existing watershed lock. A test deliberately misaligns the saved map and raster and replaces the uploaded DEM after enqueue. |
| Geometry loading on the request event loop can delay other work. | Low | The route runs filesystem and geometry validation in the existing Starlette thread pool. |
| A channel job can apply submitted WBT option overrides before rejecting a changed extent at execution. | Low | Synchronous rejections occur before settings or readiness changes. Execution rechecks before channel products are touched, and the expected worker failure keeps the previous map overlay bytes. |

## Surface checks

- The existing JWT and run authorization and route config match precede the
  validator. The configured policy comes from the run rather than the request
  body or the overlay field.
- The resolver accepts the supported local static reference forms, checks
  canonical containment after symlink resolution and requires a regular
  GeoJSON asset. Disallowed traversal, absolute paths, external references,
  broken assets and symlink escape report a safe configuration error.
- The asset tree is application-owned. No run mutation can write it through the
  changed code. Unset and `none` paths bypass geometry and DEM metadata reads.
- The CRS accepts a bounded set of geographic identifiers. Unknown data and
  unreadable assets fail with a safe message, with no raw parser or path
  details in the HTTP response.
- Job info redacts expected exceptions and exposes the safe code and message.
  Worker and application telemetry provide run/job or error correlation.
- Authorization, secrets, queue wiring, external delivery and infrastructure
  use their existing mechanisms.

## Validation evidence

The [correctness evidence](20261119_correctness_review.md) covers the recorded
state matrix, native uploaded DEM consumption and the actual map artifact.
The native test used isolated Redis, private RQ queues and disposable runs.
There was no production activation.
