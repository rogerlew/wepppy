# Standalone Parquet CSV CLI contract

Status: Ratified for standalone evaluation at the M0 checkpoint; implementation pending.
Owner: Roger Lew. Package: [Parquet CSV CLI](../work-packages/20261118_parquet_csv_cli/package.md).

## Authority and scope

The 2026-11-18 instruction to commit and implement the package authorizes the
standalone evaluation and routine implementation choices within its stated scope.
It does not authorize WEPPpy runtime integration. Two independent reviews and a
checkpoint ancestor commit remain mandatory before source implementation. This
contract governs the standalone tool only, with no HTTP/authentication semantics.

## Compatibility

Version 1 supports one immutable local flat Parquet file with uncompressed or
Snappy columns; signed/unsigned integers, float32/float64, booleans and UTF-8
strings are supported. Physical index columns named `__index_level_0__` or listed
in valid pandas index metadata are omitted. Labels append ` (units)` from field
metadata unless that suffix already occurs. Preserve input row and column order.
Duplicate projected labels and zero remaining columns are rejected explicitly.
The oracle collapses duplicate names through Python dictionaries; v1 excludes
that lossy case rather than silently corrupting or changing its output. This is
an integration-blocking compatibility exclusion. A valid zero-row file produces a header line.

The oracle is `parquet_tables.py` plus the unfiltered batching loop in
`_download.py` at revision dff2f29f74158857da3b0c313e7ec7194501ed76. CSV is UTF-8,
comma-delimited, minimally quoted, double-quote escaped, with LF record endings.
Nulls and NaNs become empty cells; booleans are `True`/`False`; integers retain
exact decimal values; float32 is promoted to float64 before Python-compatible
shortest formatting, including signed zero, infinities and exponent spelling.
The supported corpus must match oracle bytes, not merely approximate floats.
Empty strings and embedded CR/LF follow Python csv.writer behavior. Metadata
parsing must preserve the oracle's handling of absent/invalid pandas metadata;
non-UTF-8 units use its lossy decode policy. Unsupported schemas fail explicitly.

Nested values, binary, decimals, date/time, extension types, encrypted/external
column files and other codecs are excluded from v1. Filter evaluation and archive
extraction are excluded adapters: a caller can pass an already materialized
supported Parquet file, but the CLI never accepts or ignores a filter parameter.
These exclusions block any successor integration that requires those variants.
No production compatibility claim is made for excluded data.

## CLI interface

Linux x86-64 only for this evaluation. Executable `parquet_csv_cli --version`
returns `parquet_csv_cli 0.1.0`. Conversion accepts exactly these unique flags:
`--request-root PATH --max-memory-bytes N --max-cpu-seconds N --max-output-bytes N`.
The private root contains staged `input.parquet`; the CLI creates `output.csv`
exclusively with mode 0600. Unknown/duplicate/missing flags are errors. Supplied
limits must be positive and no greater than ADR-0148 ceilings. The root must be
owned by the effective UID and inaccessible to group/other users. The caller
must ensure no concurrent writer with the same authority; this is not a sandbox.

Apply OS limits before opening or decoding input. Resolve staged input beneath
the private root without symlinks using the existing owned pinned-directory openat/O_NOFOLLOW preflight
pattern. Scan bounded footer/page/dictionary structures before upstream decoding
and reuse the same opened descriptor. Check identity and input digest after
conversion. Never open URLs or external column files. Partial `output.csv` is not
success; direct CLI callers discard the private root after nonzero exit.

Success stdout is exactly one bounded JSON object with keys `version` (1),
`status` (`ok`), `rows` (nonnegative integer), `bytes` (positive integer), and
`input_sha256` (64 lowercase hex characters), followed by LF. No file contents
enter control output. Successful stderr is empty. Exit 2 denotes invalid arguments,
3 rejected input/schema, 4 resource rejection, and 5 I/O failure. Handled failures
emit one fixed-code JSON object on stderr with `version`, `status` (`error`) and
`code`; stdout is empty. OS signal termination may have no JSON; the harness
reports it explicitly as child failure. The finite CLI error codes are `arguments`, `input_rejected`, `resource_limit`,
and `io_error`, corresponding to exits 2, 3, 4 and 5. Preflight rejection maps to
`input_rejected`; OS limit failure maps to `resource_limit`. The harness exposes
`busy`, `source_rejected`, `staging_timeout`, `provenance_invalid`, `spawn_failed`,
`timeout`, `diagnostic_overflow`, `protocol_error`, `child_failed`, `output_invalid`,
`io_error`, and the four CLI codes. Cleanup failures are `cleanup_failed`; hold
the slot on failed cleanup rather than claiming reclaimed capacity.
Diagnostics contain no source data or
unbounded library error text. Maximum captured bytes: 4096 per stream.

## Python harness interface and ownership

`Converter(binary, provenance, scratch_root, limits=Limits())` supplies
`await convert(source) -> Artifact`. `Artifact` contains a private completed path,
row/byte counts, input digest, wall time and child resource metrics and offers
explicit cleanup/context management. It never returns CSV bytes. A typed
`ConversionError` has a stable code, bounded diagnostics and no sensitive payload.
`asyncio.CancelledError` remains cancellation after complete cleanup.

A binary-adjacent versioned provenance file records SHA-256 of the binary and
complete Rust source/Cargo manifest/lock inventory. Validate inventory against
this checkout and binary identity before launch; no automatic build or fallback.
Provenance JSON has exactly `version` (integer 1), `binary_sha256` (64 lowercase
hex), `sources` (object mapping normalized relative POSIX paths to 64 lowercase
hex hashes). Paths are relative to the tool root, cannot contain `..`, empty
components, backslashes or absolute paths, and must exactly equal the current
inventory `rust/Cargo.toml`, `rust/Cargo.lock`, and every regular `rust/src/**/*.rs`.
Reject symlink inventory members, unknown/duplicate keys, booleans as integers,
missing/extra files, invalid hashes and all mismatches. A sidecar is source/build
identity evidence, not a signed attestation from an independent builder.
Trusted caller owns the binary and scratch parent; same-UID malicious replacement
is outside the authority model and must not be described as contained.

The harness stages a regular source into a fresh mode-0700 request directory,
using bounded reads and a 512 MiB ceiling. Reject final symlinks/nonregular files;
caller authorization of ancestor paths remains its responsibility. Check source
identity before/after staging, then chmod the private snapshot read-only. Reject
mutation rather than silently mixing versions. Artifact input hash describes the
snapshot consumed, not a later live file. Stage checks are supporting integrity,
not protection against a malicious writer sharing the same UID.

Admission is two nonblocking file-lock slots shared by all converters using the
same scratch root, including separate Python processes. Excess requests fail
`busy`; no wait queue. Hold a slot through staging, conversion, cleanup and the
artifact lifetime; release on explicit artifact cleanup. Thus completed but
unconsumed output also counts against scratch capacity. Different scratch roots
are separate budgets; no host-wide or WEPPpy-wide claim is made.

Use fixed argv without a shell, minimal environment and a new process group.
Supervise process exit and both bounded output drains concurrently. On overflow,
timeout, exception or cancellation, kill the group and reap the child, including
repeated cancellation and cancellation during spawn. Remove the entire owned
request directory on failure before releasing admission. On success verify strict
JSON types/keys, exit code, output regular-file identity/size and digest agreement
before returning the artifact. Caller owns downstream serving and cleanup.

## Resource envelope

See [ADR-0148](../adrs/ADR-0148-parquet-csv-evaluation-resource-envelope.md).
Ceilings: 512 MiB input, 2 GiB CSV, 1 GiB child address space, 120 CPU seconds,
180 wall seconds for conversion, 180 seconds for staging, 64 open files, zero
core dumps, two admitted invocations/artifacts per scratch root. User-selected
memory/CPU/output/wall limits may only tighten ceilings. Fail explicitly if OS
limits cannot be installed. Set all numerical-library thread counts to one.

Structural preflight: 1 MiB footer, 64 KiB page header, 8 MiB compressed or decoded
page, 4 GiB cumulative decoded page bytes, 10 million rows, 128 row groups,
64 physical columns, 200,000 pages, 100,000 dictionary entries, and bounded compact
protocol nesting/container counts inherited from the reviewed scanner. Decode
batches contain at most 8192 rows; batch size is not an allocation bound.
Retain parent plus child peak-memory evidence; parent must not buffer CSV.

The file-size rlimit and a counted writer independently enforce output bytes;
input cap and admission bound live admitted scratch to 5 GiB total across two slots,
excluding small control files. Disk-full errors must clean partial artifacts.
Only owned request directories are deleted. Crash recovery is explicit: abandoned
scratch after harness SIGKILL is a known operator-cleanup obligation; automatic
cross-process deletion is excluded. Abandoned scratch is outside the live cap;
a killed parent may also leave a child running until its own CPU limits terminate
it (wall supervision is gone). Operators must reconcile live children and remove
abandoned request directories before reusing
a root after a crash. Never reuse stale output as success.

## Acceptance

Freeze a three-file real-project corpus: clogging-starch pass_pw0.events and
chnwb, and mipa-awake-20261102 H.wat (3,004,240 rows), with hashes and schema
inventory. Add synthetic boundary fixtures for every supported type and rejected
variant. At least three measured warm repetitions per method/file, a separately
labeled advisory cold run (no global cache eviction), two concurrent conversions,
and repeated cancellation/exhaustion tests are required. Record sample counts;
small-sample tails are descriptive, not statistical p95 guarantees.

Go requires byte parity on supported oracle fixtures and real corpus, all lifecycle
and resource tests passing, median end-to-end Rust+harness latency at least 2x
faster than current Python on each real file, and child plus parent peak RSS
no more than 512 MiB on each file. Compare incremental native PyArrow too, retaining
its formatting/precision discrepancies; no Rust-over-PyArrow speed claim is required.
Record input staging and process startup in end-to-end time, and output readback
outside timing for all methods. No silent acceptance-threshold relaxation.

Independent correctness and security reviews must have no unresolved medium/high
findings. A failed criterion is no-go or explicitly incomplete evaluation. A go
only supports a separately authorized WEPPpy integration package; no routes,
authentication, service configuration, production data or deployment change here.
