# M0 threat and lifecycle matrix

Status: ratified M0 controls and red corpus; runtime enforcement evidence pending.

| Threat / state | Boundary and required result | Required evidence |
| --- | --- | --- |
| Disguised file, malformed magic/footer | Receiving admission plus CLI trailer scan; bounded validation error | Tiny invalid/truncated files, no parser fallback |
| Footer list/string/schema expansion | Bounded compact-Thrift preflight before upstream allocations | Large declared counts in small files; RSS/CPU observation |
| Page/header expansion | Header scan, count/size/offset checks before library decode | Compressed and uncompressed declared-size bombs |
| Actual codec expansion | SNAPPY advertised-length validation and measured output; reject mismatch | Small encoded body with oversized decoded length |
| Dictionary/encoding expansion | Entry count, length and type accounting; unsupported delta encodings rejected | Dictionary count and byte-length bombs |
| External files, URLs, datasets, symlinks | One private regular immutable snapshot; file_path and encryption rejected | External path metadata, PARE, symlink, directory |
| Extension metadata / nested fields | Reject unsupported semantics before row construction | ARROW extension/schema, nested column, multiple geometry columns |
| WKB length, nesting, count bombs | Length budget before traversal; checked arithmetic and vertex budgets | Short buffer with huge counts; collections/deep nesting |
| Nonfinite geometry/properties | Full decode rejects NaN/Inf and invalid JSON scalars | Coordinates and scalar values; never trust claimed bounds |
| CRS missing/null/invalid | Missing means CRS84; null rejected; bounded known CRS resolved offline | CRS fixtures plus network-disabled image |
| Converter bypass / wrong workflow geometry | Receiving validator checks canonical content before publication | Direct API upload, line/polygon mismatch, missing field_id |
| Failed replacement | Private candidate validated before accepted resource/state change | Byte and semantic readback of prior resource after each failure |
| Absent / empty / populated / legacy state | Explicit valid outcomes; saved projects unchanged | First upload, empty collection rejection, replacement, legacy reload |
| Timeout / cancellation / repeated cancellation | Launcher owns process group until drained, then scratch cleanup | Live subprocess and descendant probes; repeat cancellation during drain |
| Concurrency / saturation | Existing single-flight admission remains; no cross-request file access | Concurrent valid/hostile requests and recovery |
| Missing binary / bad provenance / readiness | GeoParquet unavailable, no fallback | Tampered hash/sidecar and failed real canary |
| Failed/accepted project records | Existing visible canonical artifacts plus bounded attempt diagnostics | Browse/download and archive/restore readback |

Process tests cannot be represented by a Parquet byte fixture alone. The red
matrix must retain separate lifecycle harness cases; a file corpus does not
prove cancellation, descendants, concurrent isolation or filesystem replacement.

## Original and hostile upload retention disposition

The operator requires project recovery of complete within-limit original uploads,
SHA-256 conversion provenance, and preservation of failed/hostile files for
review and possible account-governance action. The receiving workflow retains
them under its attempt tree with neutral `.upload` suffixes, private modes and a
bounded receipt. Shape-converter scratch remains ephemeral after process drainage.

Quarantined originals are data-only/download-only evidence. Project browse and
archive paths must deny anonymous and authenticated non-owner public-run access and all preview, schema,
Parquet filtering/CSV, D-Tale, GDAL and archive-expansion interpretations; owner
or root downloads use octet-stream, attachment and nosniff. Receipts contain the
complete source SHA-256/size and verified account actor ID when available, never
tokens, session IDs, raw claims or client IP. Oversize partial uploads are deleted
and cannot claim a complete digest. No automatic ban or new ban datastore is
authorized; human-reviewed existing account governance owns any later action.

The four exact sensitive roots share a `vector_upload_attempts` path segment and
one classifier across run/Batch browse, inventories, tool dispatch and archive
access. A matched path then requires explicit run owner/root or existing Batch
project/group authority and cannot inherit ordinary authenticated public-run
read access. Archives containing evidence live under owner-authorized
`archives/private/` with hash-bound sensitivity sidecars. ADR-0145 caps each
run/Batch scope at 50 attempts, 1 GiB originals, 1.25 GiB live attempt data,
1.25 GiB sensitive archives and 2.5 GiB combined evidence. Existing Redis also
atomically bounds all projects to 100 GiB, each verified principal to 10 GiB, the
shared unattributed bucket to 1 GiB and eight in-flight reservations while
preserving 10 GiB filesystem free space. A 600-second project-scope lock
serializes local accounting, conversion and terminal state. Quota failure retains
existing evidence/state and invokes no converter. Shape-converter returns its
observed source SHA-256/size for exact receiver reconciliation.
