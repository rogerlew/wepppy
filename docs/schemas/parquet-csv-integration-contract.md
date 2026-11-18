# WEPPpy Parquet CSV integration contract

Status: scaffold; operator-approved cutover policy, detailed M0 checkpoint pending.
Implementation conformance: not implemented. Owner: Roger Lew.
Package: [integration](../work-packages/20261118_parquet_csv_wepppy_integration/package.md).

## Authority and cutover policy

The 2026-11-18 operator request authorizes scaffolding an implementation package
on `codex/parquet-csv-cli-package`. The intended integration MUST cut over
immediately to the Rust converter with asynchronous Python supervision. The
request does not execute that implementation or authorize production deployment.

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
