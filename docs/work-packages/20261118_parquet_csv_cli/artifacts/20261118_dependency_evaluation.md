# Standalone CSV dependency evaluation

Status: M0 candidate; conditional on contract reviews, preflight and runtime tests.
Observed 2026-11-18 UTC. Evaluation-only lock: `dependency-probe.Cargo.lock`.
Lock SHA-256: `b4eb3e3474fb51f035200359f798cc0c6219045a0bac0f06af96c5e71f0e69d8`.

## Precedent and capability overlap

The registry in `docs/standards/dependency-evaluation-standard.md` conditionally
accepts parquet 60.1.0 with Snappy only behind owned structural preflight for
GeoParquet uploads. This evaluation adds Arrow record batches for general flat
CSV conversion and does not transfer that approval. Existing PyArrow is the native
performance comparator; existing Python formatting is the byte oracle. The owned
shape-converter compact/footer/page preflight can be copied into the isolated
CLI with provenance and reviewed CSV-specific bounds. Existing production modules
will not be modified or imported at runtime.

## Candidate graph and cost

Exact direct candidates: parquet/arrow-array/arrow-schema 60.1.0,
csv 1.4.0, ryu 1.0.23, serde_json 1.0.145, libc 0.2.191. Parquet defaults disabled;
only `arrow` and `snap` enabled. The resolved lock has 83
third-party packages (including target-specific dependencies), plus the probe.
Arrow IPC and its FlatBuffers metadata reader arrive through the required Arrow
feature. No query engine, cloud storage, async Rust runtime, C++ toolchain, gzip,
Zstd or network client is requested. Build uses existing Linux x86-64 Rust 1.92
and a committed lock; parquet declares Rust 1.88 minimum in the inspected source.

Use the csv writer with an owned typed-cell formatter rather than Arrow CSV's
default formatting: Python float32 promotion, boolean case and null/NaN semantics
must match exactly. Ryu supplies shortest float digits; owned normalization
matches the Python exponent/decimal presentation contract. All behavior requires
oracle tests, including ties and boundary magnitudes; it is not yet verified.
Apache maintains Arrow/Parquet with a shared version family; pin versions to avoid
cross-version Arrow type incompatibility. csv/ryu/libc/serde_json add focused
serialization/system interfaces rather than a framework. Version changes require
lock review, source/build provenance and parity/lifecycle revalidation. This
bounded prototype does not assert a quantified bus factor or future maintenance
guarantee; record actual compatibility/binary-size costs at acceptance.

## Advisory evidence

Retained cargo-audit snapshot reports 0 known vulnerabilities
against advisory database commit `472a4c9a785030434f15d7da84964d60fbe789ab`.
It reports informational RUSTSEC-2026-0543: transitive chrono 0.4.45 unmaintained.
Chrono is required by Arrow's type support even though this v1 rejects date/time
exports. Do not suppress or report a clean-warning scan. This is retained
maintenance debt, not proof of exploitable reachability; security review must
assess it before go. Replacing Arrow's clock dependency is outside this package.

## Allocation and supply-chain boundaries

The existing reviewed scanner bounds footer list/string depth and sizes before
upstream metadata parsing, scans pages/dictionaries before decoding and prohibits
external/encrypted/nested data. Adapt its row/cumulative-byte bounds for real CSV
files and add direct empty-file coverage. Arrow IPC schema metadata parsing is an
additional upstream boundary: bound metadata via the footer ceiling, reject
unsupported extension/schema variants and enforce address-space/CPU limits before
all parsing. No claim of complete unsafe-code elimination is made: libc calls,
Arrow buffers, SIMD/decoder internals and FlatBuffers remain reachable.

Resource ceilings, same-descriptor identity/hash checks, hostile fixture tests and
actual process termination are mandatory defenses. Their implementation and
review evidence remain pending. Reproducible release binary size, parent/child
peak RSS, three-way benchmark and output parity belong to M1-M3, not this source
inspection. Native dependencies and licenses must be inventoried from the final
resolved Cargo metadata at build; do not infer final binary composition from
package names alone.

## Final implementation disposition

Standalone evaluation accepted after independent source reviews and direct
preflight/lifecycle/parity checks. The final lock is
`tools/parquet_csv_cli/rust/Cargo.lock`, SHA-256
`21f615ebc43c9d467cdbf84f3e21155e450fdda9ac6e506e42b0822e02e81800`.
It contains 81 third-party packages plus this crate. csv and csv-core were removed:
a small owned writer is needed for exact Python 3.12 quoting. No new dependency
replaces them. The original probe files above are historical, not the final graph.

See `dependency-final-inventory.json` for resolved versions, source registries and
license declarations; `dependency-final-audit.json` retains zero known
vulnerabilities and the unsuppressed Chrono maintenance warning. Binary size,
resource measurements and exact source/binary identity are recorded in the final
decision and validation artifacts. Rust 1.92 builds the locked release on Linux
x86-64 without adding a C++ toolchain or external service. Finite adversarial tests
and OS limits do not prove upstream decoder memory safety. Approval is limited
to this standalone evaluation; the maintenance warning and added Arrow metadata
surface must be reconsidered before production integration.
