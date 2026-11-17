# M0 dependency and security checkpoint review

Date: 2026-11-16  
Reviewer: independent `dependency_security_resume` security reviewer  
Source: `05e3450fa7d3b24572e65161100670ae542a6ea8` plus the uncommitted
task-worktree M0 checkpoint documents  
Verdict: **HOLD for M0 checkpoint; conditional dependency acceptance**

## Findings

| ID | Severity | Finding and exploit path | Required closure | Status |
| --- | --- | --- | --- | --- |
| VUN-SEC-M0-01 | High | `parquet` 60.1.0's direct page reader trusts attacker-declared decoded sizes before application row limits. Under a 128 MiB address-space limit, `dictionary-value-count.parquet` attempted a 68,719,476,704-byte allocation and `page-declared-expansion.parquet` attempted 2,147,483,647 bytes; both aborted. | Before any upstream page/row decoder, scan the same opened immutable file descriptor with an owned bounded Compact-Thrift/page preflight. Enforce every ADR-0145 footer, header, compressed/uncompressed, page-type, encoding, dictionary, count, range and aggregate limit. Direct `SerializedFileReader` use on unpreflighted bytes is forbidden. Add exact-edge and near-limit controls showing the intended early rejection, then run M2 exact-image memory/CPU probes. | Open; dependency condition is normative, implementation pending |
| VUN-SEC-M0-02 | High | ADR-0145 remains Proposed and the exact aggregate resource invariant has not been ratified. Individually bounded page, IPC, canonical artifact, scratch and parent-object allocations can overlap. | Accept the ADR in the contract ancestor, then prove the aggregate envelope in the exact candidate image during M2. The inherited single-flight, 384 MiB parser address-space, 1.5 GiB container and process limits must not be raised. | Open |
| VUN-SEC-M0-03 | Medium | The canonical artifact-observability standard requires explicit approval before deleting the original binary project input. The checkpoint proposes deleting raw bytes while retaining canonical output and bounded receipts, but operator disposition is not recorded. | Record the operator's exact retention decision in the canonical contract and checkpoint before the ancestor commit. Preserve normalized rejected candidates as already specified. | Open |
| VUN-SEC-M0-04 | Medium | Canonical endpoint and shape-converter specifications are not yet amended. Without those amendments, extension admission, error mapping, receiving revalidation, no-fallback behavior and parser preflight remain draft-package intent. | Amend `docs/schemas/upload-endpoint-contract.md` and the shape-converter specification, cross-link ADR-0145 and the normalization contract, obtain the second required read-only contract review, and commit the standalone ancestor. | Open |
| VUN-SEC-M0-05 | Medium | Static fixture preparation does not prove that extension metadata, external column paths, encryption, unsupported codecs/encodings, WKB bombs, nonfinite values, CRS ambiguity, descendants, cancellation or converter bypass fail at the intended boundary. Some malformed files can be rejected later for an unrelated reason. | M1 tests must assert stable error class and enforcement stage for all retained fixture classes. M2/M3/M4 must prove process drainage, cleanup and receiving-boundary revalidation. | Open; expected after checkpoint |

No authentication, CSRF, JWT, run-scope, queue-topology or network-authority
change is authorized by the checkpoint. The proposed design preserves these
boundaries. Final review must reject a converter integration that makes raw
client paths, arbitrary URLs or parser options reachable.

## Exact dependency decision

Conditionally accept this exact production graph for M1 implementation:

- `parquet = 60.1.0`, `default-features = false`, features `snap` only;
- `serde_json = 1.0.145`; and
- the exact `Cargo.lock` whose SHA-256 is
  `ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13`.

This is acceptance to implement behind the owned preflight described in
VUN-SEC-M0-01. It is an explicit rejection of direct use of
`SerializedFileReader` or another `parquet` decoder on unpreflighted hostile
bytes. A graph, feature or version change reopens dependency review.

The host normal graph contains 29 external packages plus the evaluation binary.
All resolved normal-graph license expressions are permissive: Apache-2.0, MIT,
BSD-2-Clause, BSD-3-Clause, BSL-1.0, Unicode-3.0 or Unlicense combinations.
There are no native/system library dependencies. Default Arrow, encryption,
GZIP, Brotli, LZ4, Zstandard, CRC and general CLI/JSON features are disabled;
Snappy is the only compression feature. `parquet` reports MSRV 1.88, below the
candidate Rust 1.92.0 toolchain.

The locked graph retains unsafe code in the trusted computing base. Reachable
surfaces include `parquet` primitive/bit decoding and unchecked dictionary
index fast paths, `snap` bounds-checked pointer copies/SIMD, and ecosystem
allocation/SIMD crates such as `zerocopy`. Arrow-only unsafe paths are not
compiled by this feature selection. Rust safety therefore does not replace the
outer process, address-space, CPU, file-descriptor, output or container limits.

The retained RustSec scan used 1,509 advisories at database revision
`02e2517f457a359fc6d3440ea4560c8ea188fee8` and reports zero vulnerabilities and
zero warnings across the 64 lockfile packages. The scan is point-in-time; M2
must repeat it and scan the exact image. Upstream `arrow-rs` releases monthly
and describes 60.1.0 as a minor release. The rapid major cadence lowers API
stability; updates remain deliberate locked reviews rather than an automatic
range bump.

## Allocation source trace

The cached source archives are bound by SHA-256:

- `parquet-60.1.0.crate`:
  `806eaa0f1c0436dcb43bee8e6a82bf2efff90521a60172f8281cb9ef577b43a4`;
- `snap-1.1.2.crate`:
  `199905e6153d6405f9728fe44daace35f8f837bbf830bb6e85fbd5828709a886`.

`parquet` 60.1.0 improves footer handling. Its finite-slice Compact-Thrift
reader checks list element count against remaining bytes before reserving, and
the retained `footer-list-bomb` probe reports:

    Parquet error: Thrift list size 2147483647 exceeds remaining input length 0

That fix does not protect pages. In
`parquet-60.1.0/src/file/serialized_reader.rs`, `verify_page_size` verifies that
compressed bytes fit the remaining column chunk and only checks that decoded
size is nonnegative. `decode_page` then calls
`Vec::with_capacity(uncompressed_page_size)` before codec output is measured.
Dictionary `num_values` flows to the plain decoder, and row-buffer reads resize
from requested counts. The public crate API keeps its generated page-header
type private, so WEPPpy cannot configure a decoded-size ceiling on that reader.
The owned preflight must parse the admitted page-header subset independently;
wrapping the row iterator after construction is too late.

The same-descriptor invariant is required to avoid a check/use race: admit and
open one regular nonsymlink local file, preflight its footer and every referenced
column/page range, rewind or clone that same descriptor, verify unchanged
identity/size, then decode. Do not preflight one pathname and reopen another.

## Reproducible evaluation results

The evaluation-only probe is not production code. It built offline with the
locked graph under Rust 1.92.0. A release valid-Snappy control returned one row,
used about 3 MiB peak RSS, and produced a 1.7 MiB unstripped probe binary with
SHA-256 `85edb7d032271a41e01c20684f7cec091ba6c89b56ebb61f33b4f4a86874b96a`.
Its zero-test `cargo test` success is build evidence only.

The allocation probes ran as:

    timeout 3s prlimit --as=134217728 -- \
      target/debug/vector-upload-dependency-probe FIXTURE

Observed stderr was:

    memory allocation of 68719476704 bytes failed
    memory allocation of 2147483647 bytes failed

Both terminated by `SIGABRT` at roughly 4 MiB observed RSS because the address
space limit denied the request. This is useful dependency evidence and confirms
why row limits are insufficient. It is not an M2 exact-image aggregate-resource
or graceful-error test. M1 must turn these into bounded stable rejection before
allocation, and M2 must prove the complete launcher/container lifecycle.

## Threat-model disposition

The contract correctly rejects URLs, directories, datasets, external
`file_path`, encryption, native GeoArrow encodings, nested properties, extension
deserialization, unknown CRS and permissive parser fallback. It requires strict
data-only IPC, receiving-workflow revalidation, private scratch, process-group
drainage and exact binary provenance. These are adequate design controls if the
preflight invariant and retention decision are promoted into the canonical
ancestor.

Snappy expands into a caller-sized destination and its unsafe copies are guarded
by source/destination bounds in inspected source. It does not establish the
destination size policy. The owned preflight must compare Snappy's advertised
decoded length, Parquet's declared decoded length and ADR-0145's per-page and
aggregate ceilings before allocating; codec success must then match the exact
expected output size.

The separately retained 46-file corpus is suitable red input evidence after its
metadata correction. It remains `NOT_RUN` against a bounded candidate. M1/M2
must add near-limit valid controls, limit-plus-one cases, a mixed null/non-null
file, explicit projected CRS, multiple row groups and lifecycle harness cases.

## Checkpoint verdict

The exact dependency decision is complete enough to allow implementation once
the checkpoint itself passes. M0 does **not** pass yet because the resource ADR,
raw-input retention decision, canonical amendments and second contract review
remain open. No implementation, image or deployment acceptance is implied.

M2 exact-image overlap, cancellation, provenance, SBOM and vulnerability probes
are correctly deferred to M2 and are not retroactive prerequisites for choosing
the M1 dependency. The M0 dependency condition is narrower: the accepted
ancestor must prohibit any upstream decoder call until owned preflight has
validated the same immutable descriptor.

