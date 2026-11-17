# Correctness state matrix

Status: ratified M0 review input and red fixtures; candidate execution pending.
Reviewer: independent `source_review` agent, 2026-11-16.
Source checkpoint: `20261116_source_checkpoint.md` in this directory.

## Workflow acceptance states

Every successful format case must retain feature order, multipart grouping,
geometry coordinates/CRS, scalar properties, and workflow-generated meaning.
Use equivalent GeoJSON, Shapefile ZIP, and GeoParquet controls with distinct
feature labels/IDs so dropped or reordered features are observable.

| ID | State | Required observable result |
| --- | --- | --- |
| C01 | Roads: line and multiline with mapped design/traffic attributes | Upload success; reloaded path/hash/catalog/input CRS agree; parsed monotonic-segment artifact maps original attributes and locations |
| C02 | Roads: polygon/point/null/mixed geometries | Bounded 400; prior accepted GeoJSON, NoDb state and prepared artifacts remain unchanged |
| C03 | AgFields: Polygon/MultiPolygon with `field_id` and crop columns | Parsed canonical GeoJSON, attributes Parquet, reloaded schema and DEM-aligned field raster agree |
| C04 | AgFields: missing `field_id` | Bounded validation error before canonical GeoJSON/Parquet replacement |
| C05 | AgFields: duplicate `field_id` | Preserve warning/list behavior; do not silently introduce rejection |
| C06 | AgFields: point/line/null/mixed unsupported geometry | Reject before state/artifact replacement under intended polygon contract; current source lacks this check |
| C07 | Omni: polygons with labels and multiple contrast pairs, run | Ordered features produce equivalent selected Topaz IDs/labels in `build_report.ndjson`; expected run enqueue follows build |
| C08 | Omni: same polygons, dry-run | Same selection semantics, no run enqueue, saved inputs remain reloadable |
| C09 | Omni: malformed/binary rejection/unsupported geometry | Failure occurs before `parse_inputs`; old saved path/options and accepted artifact are unchanged for both routes |
| C10 | Omni: saved legacy GeoJSON path reuse without fresh upload | Existing workflow behavior preserved; raw binary path must not bypass converter |
| C11 | Batch: Polygon/MultiPolygon with string/integer properties | Resource snapshot/template state reload; actual per-watershed `dem/target_watershed.geojson` preserves geometry/properties plus runid/index |
| C12 | Batch: point/multipoint/line/multiline/collection/null/mixed | Reject all formats before same-name accepted resource replacement or registration |
| C13 | Existing saved Batch project containing legacy point resource | No automatic migration/deletion; new-upload polygon policy does not change generic collection reload |
| C14 | All: missing selected file | Preserve existing actionable required-upload response; Omni saved-path reuse remains valid |
| C15 | All: empty FeatureCollection | Explicit receiving rejection, no accepted replacement; no accidental success based only on converter parse |
| C16 | All: wrong extension/content, hostile MIME/filename | MIME/extension cannot bypass content checks; bounded response with existing error envelope |
| C17 | All: exact upload limit and limit+1 | Existing 10/10/100/30 MiB policies and Batch override enforced; oversize gives 413 |
| C18 | All: compressed input below cap, normalized output above cap | ADR-defined normalization cap enforced before receiver publication; input cap alone is insufficient |
| C19 | All: invalid auth/scope/feature, Roads missing CSRF | Reject before conversion/state work; bearer APIs remain CSRF-agnostic |
| C20 | All: concurrent upload/job/lifecycle mutation | Preserve existing request/job/NoDb ownership; no cross-request scratch/resource clobber |
| C21 | All: failure followed by valid retry | Fresh scratch; actionable previous error clears; accepted artifact/state and browser reload agree |
| C22 | All: accepted complete original | Owner/root browse and download recover byte-identical `.upload` artifact; receipt source size/SHA-256 and actor bind to the exact conversion; owner archive/restore preserves bytes and modes |
| C23 | All: rejected complete hostile original | Quarantined bytes and bounded receipt persist without accepted-resource mutation; no preview/schema/filter/CSV/D-Tale/GDAL/archive expansion or automatic retry can interpret the retained file |
| C24 | Public run with retained accepted/rejected attempt | Anonymous and valid authenticated non-owner browse, direct download, files/report/schema, tool dispatch and archive access cannot enumerate metadata or retrieve bytes; explicit owner/root retains access |
| C25 | Oversize upload and incomplete transport | Partial bytes are removed; receipt never claims a complete source SHA-256 and records `oversize_not_retained` only after authorized project attempt creation |
| C26 | Verified human/service actor and anonymous/pre-auth rejection | Receipt stores only canonical positive user ID or bounded registered subject/kind; no token/session/raw claims/roles/IP; pre-auth failures create no project evidence |
| C27 | Concurrent uploads/archives in different projects and repeated project creation | Existing-Redis atomic reservations enforce 100 GiB filesystem, 10 GiB verified-principal, 1 GiB shared-unattributed, eight in-flight and 10 GiB free-space bounds; exhaustion fails before bytes and preserves prior evidence/state |

## Parser and service rejection states

| ID | Input/lifecycle state | Required result/evidence |
| --- | --- | --- |
| P01 | Valid GeoParquet 1.0/1.1, omitted CRS | CRS84 interpretation, finite WGS84 longitude/latitude readback |
| P02 | Explicit `crs: null`, malformed CRS, unsupported/offline-grid CRS | Stable CRS rejection; no guessed coordinates or network lookup |
| P03 | Bad magic/footer, truncated Thrift/metadata/schema | Bounded parse rejection before dangerous allocation; retained resource metrics |
| P04 | Oversize metadata/schema depth/columns/row groups/rows | Limits enforced at each relevant boundary, not only after row decode |
| P05 | Declared/actual page decompression expansion | Preallocation checks and measured byte/memory limits; exact dependency behavior proven |
| P06 | External `file_path`, encryption, datasets/URLs/directories | Reject without external resource opens/network authority |
| P07 | Unsupported codec/encoding/extension metadata/nested property | Explicit contract rejection; no implicit deserialization or dropped data |
| P08 | WKB length/count/nesting/vertex bomb, nonfinite coordinate | Reject before unbounded traversal/allocation; no partial output |
| P09 | Timeout, cancellation, repeated cancellation, descendants | Process group drained before scratch/ownership release; bounded response |
| P10 | Malformed/oversize stdout or stderr, invalid IPC envelope | Fail closed and clean request scratch; no untrusted exception/path disclosure |
| P11 | Missing or changed binary/provenance/readiness failure | GeoParquet unavailable; no Python or alternate-parser fallback |
| P12 | Concurrent valid/hostile requests then recovery control | Enforced resource ceiling, isolated cleanup, valid control succeeds afterward |

## Evidence chain and review verdict

For each successful workflow case retain fixture hash and semantic manifest,
converter artifact readback, exact workflow-consumed bytes, reload through the
production reader, next generated artifact readback, and browser/API result.
For each failed replacement retain before/after bytes and saved state, plus
scratch/process cleanup. Job success, filename existence, mocked conversion and
metadata-only assertions do not establish equivalence.

Original-upload acceptance also requires direct byte/hash readback from the
project artifact and restored archive. Hostile-retention acceptance must exercise
the real browse/download/tool routes and prove they never parse or anonymously
expose quarantined `.upload` files. Receipt identity supports human abuse review;
it does not prove or authorize an account ban.

M0 source findings are in the source checkpoint. The Batch geometry decision is
resolved; implementation evidence is open. Contract/resource/dependency and red
fixture review must finish before the implementation ancestor checkpoint is
accepted. This document is a state matrix, not final correctness sign-off.
