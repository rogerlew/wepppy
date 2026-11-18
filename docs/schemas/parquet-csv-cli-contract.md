# Standalone Parquet CSV CLI contract

**Status**: Draft for ratification; implementation pending; no production effect.
**Owner**: Roger Lew
**Work package**: [Parquet CSV CLI](../work-packages/20261118_parquet_csv_cli/package.md)

## Scope and authority

This proposed contract covers only a standalone Rust converter and asynchronous
Python harness. It grants no HTTP access, run authorization, production integration
or deployment authority. Ratification requires the package's contract checkpoint;
this draft alone must not be used to begin implementation. Production integration
requires a separately authorized successor after standalone acceptance.

## Proposed observable behavior

An invocation consumes one caller-authorized immutable local Parquet source,
converts supported columns in batches, and writes CSV incrementally into private
scratch. The harness returns a completed artifact reference plus bounded metadata;
it never loads the whole CSV into memory. Output becomes successful only after
conversion and file finalization. Partial output must not be presented as complete.
Input is never modified; unrelated output cannot be overwritten.

Preserve contracted row/column order, units in header labels, omission of physical
pandas index columns, empty cells for null and NaN values, quoting/newlines/Unicode,
and approved numeric/date/time representations. Byte-level differences must be
explicitly accepted rather than hidden behind parsed-value comparisons. The
existing Python exporter is the discovery oracle, not authority to invent behavior.

## Input and state matrix to ratify

| State or variant | Required contract decision and evidence |
| --- | --- |
| Missing source | Explicit bounded error; no output publication |
| Valid zero-row source | Header behavior and metadata projection parity |
| Ordinary populated source | Fresh CSV readback; row/cell and formatting parity |
| Legacy metadata/index columns | Units, index omission and ordering parity |
| Filtered export | Exact selection contract or explicit deferred adapter; no silent unfiltered export |
| Archived/file-like source | Staging/descriptor ownership or explicit exclusion; source remains intact |
| Nested/binary/date/decimal values | Exact supported types and formatting; rejection policy for unsupported types |
| Codec and schema variants | Inventory real project coverage before choosing crate features |
| Malformed/oversized source | Pre-allocation checks and explicit resource-bounded failure |
| Source changes or symlink replacement | Immutable opened-input ownership and race policy |
| Existing output or scratch exhaustion | Preserve unrelated data; fail without successful partial artifact |
| Cancellation, timeout, child failure | Terminate/reap group, drain diagnostics, clean owned partial output |

## Process and resource contract

Python owns asynchronous launch, admission, timeout and cleanup. Rust performs
synchronous local conversion without a shell or network access requirement. The
child receives only required environment and descriptors. Process separation is
a failure boundary, not a claim of containment from all inherited authority.

Set decoder allocation, memory, CPU time, wall time, output/scratch bytes, file
count/descriptors and concurrency bounds. Define units, enforcement mechanism,
interaction, startup validation and resource-exhaustion error for each. Batch row
counts alone cannot bound dictionary/page decompression allocations. Admission
must remain held until process-group cleanup finishes. Declare the exact scope
of concurrency control; do not claim aggregate WEPPpy service enforcement here.

A private completed file is preferred over piping CSV directly to an HTTP client:
it permits failure before success publication and separates conversion from slow
readers. The harness must define artifact ownership and explicit deletion after
consumption; no cross-request cache is included.

## Interface checkpoint still required

Before implementation, specify exact argv, source/output descriptor or path rules,
versioned result/diagnostic schema, permitted fields and byte limits, exit-code
mapping, invalid-result handling, binary identity/provenance and harness API.
The intended harness result carries artifact location, row/byte counts and bounded
metrics; CSV data and secrets must not enter diagnostics or JSON control messages.
No HTTP status mapping or run permission changes are part of this contract.

## Acceptance and unresolved values

Ratify a corpus manifest, supported types/codecs, formatting policy, exact wire
schema, numeric resource envelope/ADR, and numerical performance acceptance
before implementation. Compare the current exporter, incremental native PyArrow
CSV and Rust through the harness under identical conditions. Require independent
CSV readback, whole-process-tree peak memory, CPU/wall time, scratch/output bytes,
concurrency/cancellation and valid near-limit success. Numbers are deliberately
unset in this scaffold; unresolved values keep the implementation gate closed.

A standalone go verdict requires all ratified correctness, performance, lifecycle
and security criteria. It is only prerequisite evidence for a future integration
decision, never permission to wire routes or deploy the binary.
