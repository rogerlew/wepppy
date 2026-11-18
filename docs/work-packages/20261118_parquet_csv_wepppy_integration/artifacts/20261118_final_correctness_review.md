# Correctness and User-Experience Review - native CSV integration

## Metadata

Reviewer: `csv_contract_correctness`, independent read-only review, 2026-11-18.
Scope: browse CSV routes, native filters/serialization, async ownership, packaging
and deployment preflight at `c433c6ee3`. Authority:
[canonical integration contract](../../../schemas/parquet-csv-integration-contract.md).
Related review: [security](20261118_final_security_review.md).

## User Outcome

Existing CSV links generate the contracted fresh representation through one native
backend. CSV is temporary and original Parquet remains available. Busy, invalid
filter/input, resource, timeout, provenance and internal failures use the canonical
finite error table; no request falls back to Python. This is proactive replacement,
not an incident repair. Every reachable run, culvert, batch and ordinary-directory
CSV consumer is wired; retired archive traversal remains retired.

## Valid-State Matrix

| State | Required behavior | Evidence |
| --- | --- | --- |
| Original absent / scratch never used | Existing 404 precedence; lazily create private scratch | Browse/security tests, native fresh-root tests |
| Empty Parquet / all-index projection | Header-only CSV, no invented rows | Native empty/schema/index tests |
| Populated project | Same headers, units, rows and values | 46-file exact oracle parity, actual HTTP bytes |
| Supported legacy | Primitive/null/timestamp/WKB/ZSTD, duplicate projection and filter semantics preserved | Focused compatibility matrix and real-file inventory |
| Malformed/hostile | Bounded explicit failure, no fallback, original raw availability | Strict IPC, malformed metadata/page/ZSTD, image negative probes |

Request combinations are independently covered: run/culvert/batch/directory;
filtered/unfiltered/no-match; range ignored; authorization/containment denial;
complete/send-failure/disconnect/cancel/deadline. This is not an exhaustive claim
for every possible Parquet type, input shape or deployment environment.

## User-Reachable Error Policy

| Condition | Result | Contract rationale |
| --- | --- | --- |
| Shared slots occupied | 503, Retry-After | No unbounded queue |
| Filter invalid/no match | 422 | Existing filter error contract |
| Resource/filter row cap | 413 | Fixed bounded native envelope |
| Malformed/unsupported source | 422; raw available | Includes explicitly approved invalid UTF-8 rejection |
| Source changes | 409 | Do not serve a mixed snapshot |
| Deadline | 504 before headers; abort after headers | Finite ownership lifetime |
| Missing/tampered native artifact | 503 | Required dependency, no fallback |
| IPC/I/O/cleanup failure | 500 or logged post-header failure | Explicit failure, retained capacity if cleanup is unsafe |

## Generated Artifact Evidence Chain

| Stage | Evidence | Result |
| --- | --- | --- |
| Request intent | Actual CSV HTTP URL plus focused filter AST cases | Pass |
| Persisted state | N/A: on-demand representation; no new project state | N/A |
| Staged input | Exact source SHA bound to native consumed-input SHA | Pass |
| Executable input | Local/image provenance source inventory and binary hashes | Pass |
| Fresh output | 46-file hash/byte parity; bounded benchmark output | Pass |
| User-facing output | Eight-worker HTTP readback, including 444,752,939-byte CSV | Pass |

Actual-project evidence uses authorized immutable copies. Highest claim: locally
implemented, wired and exact-image validated. Target-host configuration/proxy and
production acceptance remain a deployment gate; no live project was mutated.

## Findings

| Finding | Required correction | Status |
| --- | --- | --- |
| Mixed duplicate casts, Unicode and timestamp formatting | Preserve oracle behavior, including VT and NaT | Resolved |
| Empty name collisions and deep pandas metadata | Match valid states; explicit bounded rejection for invalid states | Resolved |
| Destination I/O classification and diagnostic gaps | Correct finite error and outcome/hash retention | Resolved |
| Real dictionaries and 79-column exports exceeded initial limits | Reviewed contract ancestors; bounded thresholds and exact/+1 tests | Resolved |
| Restrictive operator umask and build-owned scratch | Explicit synthetic fixture modes; remove build-only scratch | Resolved |

## Review Checks and Verdict

Canonical intent, valid-state/error matrices, real native boundaries, actual HTTP
bytes, partial-state cleanup and explicit compatibility exceptions reviewed.
Gate: PASS; unresolved high/medium/low findings: 0/0/0. Source sign-off:
`csv_contract_correctness`, 2026-11-18. Final image evidence was independently
reviewed; broad-suite disposition is recorded in validation.md. Production release
still requires the canonical deployment gates and separate authorization.

## Artifact Observability Gate

The operator explicitly approved deleting conversion copies, IPC and CSV after
serving/failure/recovery while retaining original Parquet and correlated diagnostic
hashes, sizes, outcomes and resource metrics. The canonical contract's
"Approved transient-storage exception" records scope and rationale: persistent
CSVs could become stale and imply automatic model generation. Actual image logs
prove success-hash retention. No new project archive member exists to restore;
archive/restore coverage for temporary CSV is therefore N/A by approved exception.
