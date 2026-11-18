# WEPPpy Parquet CSV integration contract

Status: scaffold; operator-approved cutover policy, detailed M0 checkpoint pending.
Implementation conformance: not implemented. Owner: Roger Lew.
Package: [integration](../work-packages/20261118_parquet_csv_wepppy_integration/package.md).

## Authority and cutover policy

The 2026-11-18 operator request authorizes execution of the implementation package
on `codex/parquet-csv-cli-package`. The integration MUST cut over
immediately to the Rust converter with asynchronous Python supervision. The
request does not authorize production deployment.

The integrated release has exactly one Parquet-to-CSV execution path. All
supported CSV export requests use the native converter from the first request
served by that release. No feature flag, opt-in, percentage rollout, shadow mode,
backend selector, environment toggle or per-schema legacy branch is permitted.

There is no fallback to Python/PyArrow/pandas CSV serialization. A missing binary,
invalid provenance, unsupported input, resource limit, timeout, protocol error or
child failure returns an explicit contracted failure; none invokes the old exporter.
Remove superseded production conversion helpers and imports when the routes are
wired. A test-only oracle may remain outside the production execution path.

Rationale: the operator selected a single, deterministic cutover after the
standalone evaluation succeeded. Dual implementations and deployment knobs would
retain the expensive path and make behavior depend on environment or failure mode.

## Configuration ownership

The CSV integration exposes no environment-variable-facing configuration.
Executable/provenance locations, scratch location, concurrency, resource ceilings,
timeouts and other converter settings are fixed, source-controlled values with
one documented authority. No request parameter can override those settings.
Tests may inject dependencies explicitly without creating a production override.

Inventory existing environment reads affecting CSV exports, including
`BROWSE_PARQUET_FILTERS_ENABLED` and `BROWSE_PARQUET_EXPORT_MAX_ROWS`. Replace
CSV-specific configuration dependence with reviewed code-owned behavior/values;
do not retain a legacy environment override behind the new adapter. Amend the
shared filter contract for the CSV surface at M0, while preserving separately
owned preview, filtered-Parquet download and D-Tale behavior. Existing unrelated
authentication, site-prefix and service configuration is not removed wholesale.
M0 must record exact constants and compatibility impact before wiring.

## Compatibility and route coverage

Preserve authorized request URLs, filenames, media types, unit labels, row/column
order, null/float/boolean/string formatting and physical-index projection within
the ratified compatibility matrix. Preserve `pqf` validation, operator semantics
and error outcomes; distinguish valid empty unfiltered files from no filter matches.
The current filter contract requires 422 for no matches and 413 for its row cap.

Cover run, culvert and batch CSV exports for `.parquet`, `.geoparquet` and `.pq`,
including case handling. Classify archive/file-like branches by actual reachability
and current retirement policy before committing to adapters. Support every still
reachable authorized representation; do not revive retired virtual archive access.
Raw Parquet and raw archive bytes retain ordinary authorized download behavior.

Standalone v1 exclusions are migration gaps, not permission to break valid exports.
Inventory real schemas/codecs/metadata and filtered behavior before implementation.
Extend the native path for required cases before cutover, or obtain an explicit
bounded contract exception. Never solve a gap with a Python serialization branch,
silent dropped data, ignored filters or routing only easy files to Rust.

## Zero-trust decoding and IPC

Apply the [standalone zero-trust policy](parquet-csv-cli-contract.md#zero-trust-input-policy)
to every input, regardless of WEPPpy origin. Authorization, containment and PII
checks precede staging or subprocess work. Retained-original raw-byte protections
keep precedence. Source consistency is separate from model freshness; do not add
model-state locks or eligibility gates to generic downloads.

All Parquet decoding for a CSV request, including schema-dependent filter work,
must occur behind the bounded child boundary. Do not first decode/filter an
untrusted file in the web worker and then call the CLI to serialize it. The parent
may validate bounded filter syntax and stage authorized bytes without decoding.
Any needed filter/input protocol extension must be specified, versioned and reviewed
before code changes; do not invent it during route wiring.

Retain strict UTF-8 JSON control responses, exact keys/types/version, duplicate-key
and nonfinite-number rejection, bounded streams, exit/status agreement and exact
binary/source provenance. The current CLI uses fixed argv with closed stdin;
this scaffold does not silently replace it with bidirectional JSON or raw SQL IPC.
CSV contents stay in a completed file, never a whole-output Python bytes object.

## Admission, serving and recovery

Admission is shared across all browse workers that serve these routes, not a
semaphore or two-slot pool per worker. Reuse the existing lock-slot design on one
fixed private scratch root where filesystem semantics permit. The wepp1 overlay
currently starts eight browse workers; test actual cross-process contention.
Count staging, conversion and completed-but-unconsumed artifacts against capacity.
Account for active replicas/hosts explicitly; do not claim a host-wide bound from
unrelated roots. Do not add a queue or service without evidence and separate scope.

Finalize and validate the CSV before sending successful HTTP headers. Stream the
completed file with bounded memory. Hold ownership/admission until response close
or disconnect, then clean exactly the owned artifacts. Test slow readers, response
errors, cancellation during staging/spawn/serving and repeated cancellation.
Do not rely solely on a happy-path background task to reclaim capacity.

Resolve parent death, worker recycling and restart recovery before integration
acceptance. Retain capacity until owned children stop; reconcile orphan children
before removing scratch. Never delete another worker's active files, reuse stale
output or silently fall back. Check actual Gunicorn/ASGI/proxy deadline behavior
against child/staging/serving budgets. Resource changes require ADR provenance.

## Failure and observability contract

M0 must specify every converter-code-to-HTTP-status/body/header mapping, including
busy admission, malformed/unsupported input, source mutation, limits, timeouts,
missing executable, bad provenance, bad IPC, I/O and cleanup failure. Preserve
existing authorization/404/filter outcomes and the
[browse failure envelope](browse-filesystem-contract.md#failure-observability).
Do not return an empty CSV, false 404 or partial success for conversion failure.
After headers are sent, terminate a failed stream and log its request ID; do not
attempt to replace it with a JSON response.

Record safe request correlation, outcome, input/output size, rows, duration,
resource metrics, cancellation and capacity signals without source contents or
credentials. Name the artifact inventory and visibility/retention policy before
implementation; reconcile private ephemeral scratch with the artifact-observability
standard rather than asserting an implicit exception. Keep raw authorized files
inspectable when CSV representation fails.

## Build, rollout and acceptance

Build the locked CLI in the actual WEPPpy image workflow and install it with its
provenance and required source identity at fixed paths. Do not copy a host-only
binary into an incompatible runtime or borrow shape-converter environment knobs.
Build/startup/deployment preflight must reject a missing or mismatched required
artifact; do not take unrelated raw downloads down merely to represent a conversion
error. M0 must distinguish deployment readiness from request failure semantics.

Immediate cutover means one backend in the accepted release, not bypassing tests
or deploying during scaffold work. Use the existing Compose/wctl and
`scripts/deploy-production.sh` mechanics when rollout is separately authorized.
Recovery is an explicit rollback of the entire release through that workflow,
not automatic per-request fallback or an environment switch.

Acceptance requires exact-image HTTP byte readback on real projects under
production-equivalent UID/GID, mounts, permissions, umask and orchestration;
negative authorization/containment tests; bounded-memory concurrent/slow-client
checks; no legacy-path execution; independent correctness/security reviews; and
operator/developer/user documentation. Run focused checks during implementation.
Run the broad repository suite only after integration is wired, per the operator's
prior instruction; do not run it for this documentation scaffold. Record source,
contract, binary/image and test identities and distinguish local validation from
deployment. Detailed M0 decisions and review disposition precede implementation
in a standalone checkpoint ancestor commit.

## Temporary representation retention (approved 2026-11-18)

The operator explicitly approved deletion of staged input copies, completed and
partial CSV files, and IPC files after download, failure or crash recovery. This
is the exact exception to the artifact-observability retention rule for this
workflow. Original project Parquet files remain visible and archivable through
the existing browse/archive paths. No new persistent project CSV is created.

Rationale supplied by the operator: "the .csv could become stale but users
wouldn't realize it". Generate every CSV from the source staged for that request;
never reuse a previous conversion or leave a CSV that could be mistaken for a
current model output. Retained CSVs would also imply automatic generation: users could interpret their
absence as a failed or missing model output. CSV is an on-demand download
representation, not an expected project artifact. This preserves the existing
transient download behavior.

Retain request-correlated outcome, available input/output hashes and sizes, rows,
resource metrics and failure codes in service logs under existing log retention.
A failure before hashing or child completion records unavailable measurements
explicitly; it must not invent a digest or successful output. Logs contain no
Parquet cells, filter values, credentials or full private paths. Temporary files
are outside project archives and disappear only under proven ownership. Failure
to clean up holds capacity and produces an explicit diagnostic.

## Integration implementation checkpoint

The following details supersede draft obligations above once the two independent
reviews are dispositioned and the checkpoint is committed. Conformance is pending.

### Fixed runtime ownership and limits

The sole production supervisor lives in `wepppy/microservices/parquet_csv/`;
`browse/parquet_csv.py` owns the HTTP adapter. Evaluation imports the production
supervisor rather than carrying a second implementation. The binary is
`/usr/local/bin/parquet_csv_cli`, sidecar `/opt/parquet-csv/provenance.json`, and
source inventory `/opt/parquet-csv/rust/`. The common WEPPpy Dockerfile builds the
locked crate and installs all three together. No runtime compilation/download,
PATH search, environment override or optional dependency bypass is permitted.

Shared scratch is `/tmp/wepppy-parquet-csv`, owner-only mode 0700. Two persistent
lock files `slot-0.lock` and `slot-1.lock` govern exactly two corresponding
`slot-0` and `slot-1` request directories. Lock files are never removed or replaced.
Each child inherits its parent's locked descriptor. Close descriptors to release
ownership; never explicitly unlock an inherited open-file-description lock.
Acquire a slot before staging or reclaiming that slot's abandoned directory.
A locked slot is never scavenged by age or PID. Staging, child work and serving
all occupy the same slot. The budget is per shared scratch filesystem/container,
not per worker or universally per host. All eight wepp1 browse workers share it.
Replicas with separate filesystems each add their own two-slot budget.

ADR-0149 sets 30 seconds staging, 120 seconds conversion wall time, 100 CPU seconds
and 600 seconds serving time. Admission does not queue. Preserve the standalone
512 MiB input, 2 GiB output, 1 GiB address-space and structural ceilings. Thus two
slots admit at most 5 GiB staged/output payload and 2 GiB child address space,
plus bounded metadata and web workers. Retained failed scratch occupies its fixed
slot until safe recovery; it cannot accumulate unbounded request directories.

The child installs an independent wall alarm before input work, and sets Linux
parent-death SIGKILL with a comparison against the supplied expected parent PID
after installation to close the pre-installation race. The inherited lock survives
parent death until the child stops. A subsequent holder cleans only that slot
before reuse. Kernel-uninterruptible I/O may delay termination; the inherited
lock deliberately preserves capacity until actual exit. No daemon is needed.

Gunicorn's Uvicorn worker timeout is a heartbeat, not the conversion deadline.
Thirty plus 120 seconds leaves margin under the shortest current Caddy first-byte
read timeout (three minutes for culvert/batch); real image validation must prove
responsive worker heartbeat and timeout behavior. No proxy configuration change
is included. Serving holds the slot until final ASGI send or cleanup following
error, disconnect, cancellation or serving deadline. Do not rely on a background
task alone. CSV retains full-response behavior: ignore Range/conditional request
headers, do not add multipart/range caching semantics, and send Content-Length,
text/csv with UTF-8 charset, and a safely encoded attachment filename.

### Input and representation compatibility

The retained inventory covers 156 files from two real projects plus a feature
GeoParquet export. Maximum observed input is 51,199,048 bytes, 3,004,240 rows and
100 row groups. Native additions required before cutover are null arrays,
timezone-free timestamps, binary WKB with the `geoarrow.wkb` annotation, and ZSTD
compression. Timestamp output must match Arrow-to-Python string formatting,
including nanoseconds; binary output must match Python bytes repr. Only the
recognized WKB annotation may bypass the standalone unknown-extension rejection;
no geometry parsing is needed. Test signed timestamps and binary escaping.
Preserve primitive CSV formatting, units and index projection from CLI v1.
For duplicate projected unit labels, preserve the existing dictionary semantics:
repeat the last physical value associated with that label in each corresponding
output position. Unfiltered raw duplicate field names retain their existing ambiguity
failure. Filtered exports preserve DuckDB physical-name disambiguation (for
example `x,x` becomes `x,x_1`), including collisions with existing suffixed
names; filter selection and source-schema unit lookup follow the existing
DuckDB oracle. Differential fixtures must cover this distinct filtered state. An all-index projection preserves the existing header-only newline,
with zero output rows, while still validating/decoding every input field.

Types/codecs outside the ratified flat compatibility matrix remain explicit
unsupported-input failures; discovery of a valid required export outside it is
a release blocker requiring a contract amendment, never permission to silently
remove columns or use Python. Decimal/nested/date/timezone cases are not claimed
validated by the current corpus. Empty supported files return a header-only CSV.
Unsupported metadata/type validation applies even to omitted index fields.

Run, culvert and batch use the same native adapter for `.parquet`, `.geoparquet`
and `.pq`, case-insensitively. The NoDir branch resolves ordinary directories;
route it through the same authorized contained filesystem path, not an archive
adapter. Preserve retired archive errors. Its current omission of `pqf` is
classified as existing filter-contract nonconformance: all CSV routes must apply
requested filters. Authorization, missing file and retained-original raw-byte
precedence stay before conversion. Resolve authorized in-scope symlinks before
staging with O_NOFOLLOW; preserve approved Omni parent/group containment rules.

### Filter and strict JSON protocol amendment

Native protocol v2 retains closed stdin, bounded one-object stdout/stderr and
fixed argv. It adds required `--parent-pid`, `--admission-fd` and
`--max-wall-seconds` arguments. `request.json` is a regular owner-only no-follow
file in the private request directory, limited to 131072 bytes.
Serialize compact UTF-8 with ensure_ascii=False; the larger private bound
accommodates numeric normalization/wrapper growth from a valid external payload. Its exact shape is
`{"version":2,"filter":null}` or the same with a normalized filter tree. Each condition additionally carries `number`,
a finite JSON number or null, computed using Python float parsing in the parent
to preserve Unicode digits and underscore numeric literals. The child requires
this value only for numeric comparisons; null then fails validation. Filter
physical fields before output projection. Reject
unknown/duplicate keys, trailing content, BOM/invalid UTF-8, nonfinite numbers,
wrong types and excessive nesting in both parent and child. No SQL crosses IPC.
All response versions become 2; success keys otherwise remain the v1 set.

CSV filtering is always available with a fixed 2,000,000 matched-row cap;
legacy environment flags/caps continue to govern non-CSV surfaces only. Bound
encoded pqf length to 87384 bytes and decoded JSON to 65536 bytes before parsing;
retain depth 6, nodes 50, field 128 and value 512 bounds. Parent validates syntax;
child validates schema fields/types and evaluates selection before serialization.
The child's fixed-tree parser validates independently even for trusted parent IPC.

Use the existing DuckDB filter as the test oracle: numeric comparisons cast data
and finite literals to DOUBLE (including int64 rounding); null and NaN never
match numeric comparisons, infinity data may match. Null never matches any
condition; Contains on numeric NaN retains DuckDB text `nan` matching. Contains compares simple Unicode lowercase of
DuckDB VARCHAR rendering, not CSV rendering: booleans are lowercase, float32 is
rendered at its own precision. Unicode probes include dotted I and Greek sigma.
Nested groups preserve SQL WHERE null behavior. Numeric-only operators on other
types and unknown fields fail validation. No matches is distinct from an empty
unfiltered file. Validate the schema even when the file has zero rows.

Handled child errors retain exact keys `version,status,code`; add exit 6
`validation_error`, exit 7 `no_rows_matched_filter`, exit 8
`parquet_filter_row_limit_exceeded`. No free-form diagnostics/paths or filter
values are published. Syntax errors may preserve the existing optional node path;
child schema errors use a safe generic validation message. Validate exit/code
agreement and exact success output metadata before HTTP success headers.

### HTTP outcomes and readiness

Missing source remains 404; auth/containment/PII responses retain precedence.
Converter failures return error.message/code/details with safe authored text,
request_id and X-Request-Id. Prefix internal converter codes with `parquet_csv_`;
filter codes retain their existing names. Fixed mapping:

| Converter outcome | HTTP status |
| --- | --- |
| busy | 503, Retry-After: 1 |
| validation_error, no_rows_matched_filter | 422 |
| parquet_filter_row_limit_exceeded, resource_limit, input_too_large | 413 |
| input_rejected, source_rejected | 422 |
| source_changed | 409 |
| timeout, staging_timeout | 504 |
| provenance_invalid, spawn_failed | 503 |
| arguments, io_error, protocol_error, diagnostic_overflow, child_failed, output_invalid, cleanup_failed | 500 |

Unexpected boundary failures retain the standard correlated 500 envelope. After
headers, abort the stream and log the request ID. Native SIGALRM maps to timeout/504; other unrecognized signals map to
child_failed/500. Cancellation is preserved after
owned cleanup, not translated into a successful CSV or fallback.

Image build/preflight validates provenance and performs an actual conversion and
CSV readback under the service identity. A missing required artifact blocks release
readiness. Request-time failures remain scoped to CSV, leaving authorized raw
Parquet downloads available. Exact-image HTTP validation must use the shared
scratch, eight-worker topology, production-equivalent identity/mounts/umask and
real source files before release readiness can be claimed. No live deployment is
authorized by this package. Rollback is of the whole release through the canonical
Compose deployment entry point, never an environment switch or Python fallback.

### Approved metadata exception (2026-11-18)

The operator explicitly chose "Reject invalid UTF-8 metadata" after reviewing
the old lossy unit-label behavior and the absence of this case in all 156
inventoried files. The integrated converter rejects it with input_rejected/422;
raw authorized Parquet remains downloadable. Do not add a metadata rewriter or
second decoder solely to retain silent byte dropping. This is an approved bounded
compatibility exception, not a claim of byte parity for these inputs. Preserve
native parity for duplicate projected labels separately as specified above.
