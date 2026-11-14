# Rust CLI Correctness Review

Date: 2026-11-14

Reviewer: Codex implementation self-review. Independent M6 approval remains
pending.

Disposition: PASS for the ratified local semantic matrix.

Evidence covers Point, LineString, Polygon, reversed orientation, Z Point, null
geometry/properties/date, MultiPatch GeometryCollection, integer/float/date DBF
values, UTF-8 numeric CPG label, CRS present/missing/invalid behavior, bounds,
GeoJSON, and GeoParquet metadata/readback.

The retained Fiona/GDAL oracle and Rust CLI matched all 50,000 representative
features after removal of Fiona's inactive `geometries: null` member. Integer DBF
fields are emitted as JSON integers and remain integer values in both output
formats. Fiona-compatible null date `00000000` remains null; non-null date values
must pass calendar validation.

Two compatibility regressions were found and fixed during the scoped suite:

- malformed `.prj` plus `same_as_shapefile` again preserves coordinates and
  reports invalid projection metadata without weakening invalid IPC WKT handling;
- counterclockwise polygon rings accepted by the prior path again convert as
  polygons rather than being rejected as orphan holes.

Final exact-image HTTP readback verified one Point at `[10.0, 20.0]`, property
`NAME=demo`, valid GeoJSON, a one-row GeoParquet artifact with primary geometry
column metadata, and empty request scratch.

No persisted schema or public response key changed. The Rust payload is internal
request scratch and parent/CLI ship together.
