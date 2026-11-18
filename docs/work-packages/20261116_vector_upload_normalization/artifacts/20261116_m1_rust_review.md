# M1 bounded GeoParquet CLI review

Date: 2026-11-16  
Reviewer: independent `m1_rust_review` correctness reviewer  
Scope: uncommitted M1 `geoparquet_parser_cli` candidate following M0 ancestor
`1aebebfe0`  
Verdict: **PASS — no open High, Medium or Low finding; all eight initial
findings are closed.**

The exact candidate `Cargo.lock` SHA-256 is
`ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13`,
matching the dependency-evaluation lock. On the remediated snapshot,
`cargo test --locked --offline` passes 30 tests, including all 49 Parquet entries
in the 53-file corpus, and strict Clippy and `cargo fmt --check` pass. Independent
regeneration produced all retained fixtures byte-for-byte; the final corpus has
41,987 total bytes and
manifest SHA-256
`f879e3a8c81581c5ddd1d4bdc5a10ef1c0af2fa9f780b1b846730e4fb03f41f5`,
matching the receipt. The release binary SHA-256 is
`fe3f08e8a251478d7cf78fdc623a76edd28899948e269c49b5e79fc89e31616a`.
The corpus check establishes current-corpus disposition; the direct boundary
tests and resource receipt establish the ADR's exact-limit guarantees below.

## Initial findings

| ID | Severity | Finding | Required disposition | Status |
| --- | --- | --- | --- | --- |
| VUN-M1-RUST-01 | High | The owned footer scan applies one generic `max_container=131_072`, then constructs `SerializedFileReader` before enforcing the ADR's 64-column and 128-row-group ceilings (`src/preflight.rs:47-64`). A sub-1 MiB footer can therefore declare tens of thousands of schema elements, row groups, or column chunks and make the upstream metadata decoder allocate their vectors before `validate_metadata()` runs. This is the same forbidden control-order class as the dependency finding, only at smaller counts. | Extend the owned Compact-Thrift pass to retain container counts by field path and reject before upstream decode: root schema elements (root plus at most 64 primitives), row groups (128), columns per row group (64), and bounded metadata lists. It must also reject nested schema structure at this stage rather than after upstream schema construction. Add edge and limit+1 fixtures for each path and memory evidence under the parser limit. | Closed in final re-review |
| VUN-M1-RUST-02 | High | The 2,000,000 JSON-value and 16 MiB IPC limits are enforced only after all rows, property maps, geometry arrays and strings have been retained in memory; `serde_json::to_vec` then allocates the full encoded payload before checking its length (`src/main.rs:169-233`, `src/main.rs:468-471`). Sixty-four mostly-null columns across 100,000 rows can create 6.4 million retained `Value` entries while page declarations remain within 128 MiB. This bypasses the ADR's requirement to count before parent allocation/serialization and can consume the 384 MiB envelope. | Maintain the JSON value and encoded-byte budgets incrementally during row/property/WKB construction, reject before pushing the value that crosses either cap, and serialize through a bounded writer or prove an exact precomputed size before allocation. Preflight the aggregate declared value fanout where possible. Add 2,000,000/2,000,001-value and 16 MiB edge/limit+1 tests with RSS evidence. | Closed in final re-review |
| VUN-M1-RUST-03 | High | Path containment is checked by `canonicalize()`, but `preflight::open()` later performs `symlink_metadata(path)` followed by an ordinary `OpenOptions::open(path)` on the original path (`src/main.rs:175-199`, `src/preflight.rs:31-43`). A same-UID writer can swap the entry after either check and make the parser open a symlink or out-of-root file. Neither `O_NOFOLLOW` nor descriptor-relative containment is used. The post-open identity comparison checks only length against the earlier path metadata and does not close that race. | Open the input with no-follow/descriptor-relative semantics and derive containment/type/identity from that descriptor, or pass an already-open inherited descriptor from the private launcher. Add a deterministic swap/symlink race negative test. The launcher must also prove the snapshot cannot be modified in place during decode. | Closed in final re-review; M2 private-root lifecycle qualification is a separate integration gate |
| VUN-M1-RUST-04 | Medium | Page preflight does not reconcile declared state completely. It does not sum row-group rows to file rows, sum page values to column values, require actual decoded row count to match metadata, verify dictionary-to-data transition against `data_page_offset`, reject overlapping/reused column ranges, keep page ranges before the footer start, or reject extra page-specific headers. A page only needs the required header for its type; contradictory dictionary/V1/V2 headers can coexist (`src/preflight.rs:111-168`, `src/preflight.rs:191-283`). These gaps leave malformed inputs to upstream behavior and can turn a hostile mismatch into a panic or accepted cardinality drift. | Reconcile every row/value/page declaration and exact range before row decode, require one matching page-specific header, then compare actual decoded rows/bytes to the preflight ledger. Add a mutation for every mismatch and assert stable rejection before the upstream page decoder where applicable. | Closed in final re-review |
| VUN-M1-RUST-05 | Medium | The accepted 3D profile is not implemented consistently. GeoParquet 3D geometry declarations such as `Polygon Z` are rejected because only bare type names are admitted (`src/main.rs:308-320`, `src/main.rs:433-443`), while multipart WKB accepts children whose 2D/3D dimensionality differs from the parent because only the base type is compared (`src/wkb.rs:122-188`). Mixed-dimensional GeoJSON can therefore be emitted even though correctly declared 3D input is rejected. | Normalize and validate the specification's admitted 2D/3D geometry type strings, carry expected dimensionality through multipart recursion, and add valid 3D plus mixed-dimension negative controls for every multipart family. | Closed in final re-review |
| VUN-M1-RUST-06 | Medium | Scalar schema admission does not match the contract's JSON-compatible integer profile. INT8/INT16 and unsigned INT32/INT64 logical annotations are rejected because numeric properties require `ConvertedType::NONE`, even though row conversion has unsigned variants (`src/main.rs:344-401`). Conversely, `orientation` and `bbox` GeoParquet metadata are accepted without validating their value/type, so malformed or future semantics are silently ignored (`src/main.rs:289-306`). | Define and test the exact logical-type matrix for signed/unsigned JSON integers and validate every admitted GeoParquet metadata field; reject unknown or malformed semantics before row decode. | Closed in final re-review |
| VUN-M1-RUST-07 | Medium | Output publication creates an exclusive partial, but final `fs::rename` can replace a destination created after `validate_paths()` and no no-replace operation protects the final name (`src/main.rs:175-201`, `src/main.rs:510-538`). The direct resource boundary also checks serialized bytes without the trailing newline while `RLIMIT_FSIZE` is exactly the payload cap, so an exact-cap payload can terminate on the newline instead of returning the stable limit error (`src/main.rs:153-159`, `src/main.rs:511-529`). | Publish with atomic no-replace semantics (and directory sync if durability is claimed), count the newline in the IPC limit, and add destination-race, partial cleanup, exact-cap and cap+1 tests. | Closed in re-review |
| VUN-M1-RUST-08 | Medium | The manifest test asserts only success versus failure. It does not assert the stable error, enforcement stage, no upstream-decoder entry, or edge/limit+1 behavior required by M0. There are no valid DATA_PAGE_V2, 3D/big-endian WKB, scalar logical-type, same-length mutation, no-follow race, output-failure, exact threshold, or measured near-ceiling tests (`src/main.rs:568-620`). | Expand direct Rust tests to cover every admitted branch and every hostile fixture's exact stable result/stage, plus the ADR boundary matrix and resource measurements. | Closed in final re-review |

## Remediation re-review

The current remediation was reviewed against the contract, ADR-0145, exact
dependency lock and retained corpus. Disposition of every original finding is:

| ID | Re-review disposition | Current evidence |
| --- | --- | --- |
| VUN-M1-RUST-01 | **Closed (High)** | `preflight.rs:54-93` records Compact-Thrift containers and schema fields, enforces root-plus-64 primitive schema elements, 128 row groups and 64 columns per row group, and rejects nested schema structure before `SerializedFileReader::new` at line 95. The generic scanner ceiling is also reduced to 8,192. The final exact/+1 suite covers the applicable structural boundaries. |
| VUN-M1-RUST-02 | **Closed (High)** | `main.rs:230-290` maintains cumulative JSON-value and encoded-byte budgets for each decoded row and rejects before pushing it into the retained parent vectors. The fixed 1,024-byte envelope reserve plus exact per-row serialization bounds final serialization, and `write_payload` counts the framing newline. The final suite supplies exact-cap and RSS evidence. |
| VUN-M1-RUST-03 | **Closed (High)** | `preflight.rs:119-172` opens the private-root basename with descriptor-relative `openat`, `O_NOFOLLOW`, `O_NONBLOCK` and `O_CLOEXEC`, then derives regular-file identity from the descriptor. In addition to size/mtime/ctime identity checks, the owned SHA-256 implementation hashes the opened descriptor before preflight and again after decode (`preflight.rs:44-105`; `main.rs:301-309`). The symlink, same-length mutation and SHA-256 known-vector tests pass. M2 must still prove private-root lifecycle ownership in the image. |
| VUN-M1-RUST-04 | **Closed (Medium)** | The final remediation reconciles file/row-group/column/page value counts, column ranges and overlap, the first actual data-page header with `data_page_offset`, and decoded row cardinality (`preflight.rs:216-286`, `316-455`; `main.rs:215-217`, `292-294`). It rejects contradictory page-specific headers; requires flat-schema V2 `num_rows == num_values`; checks V2 level lengths; propagates the codec into page scanning; requires body-size equality for UNCOMPRESSED and V2 `is_compressed=false`; reconciles page/header uncompressed totals with footer metadata; and bounds aggregate pages and uncompressed bodies. For Snappy compressed branches, the exact locked Parquet 60.1.0 decoder also verifies actual decompressed length equals the preflighted declaration. Direct V2 and boundary tests close the retained-code defect and evidence requirement. |
| VUN-M1-RUST-05 | **Closed (Medium)** | GeoParquet declarations admit the ` Z` suffix (`main.rs:564-576`), observed declarations retain dimension (`main.rs:254-260`), and WKB recursion carries expected base type and dimensions through multipart children (`wkb.rs:124-218`). A mixed-dimension negative unit test passes. |
| VUN-M1-RUST-06 | **Closed (Medium)** | The schema matrix now admits signed and unsigned integer annotations on their valid physical types (`main.rs:482-500`). Column metadata is allowlisted; orientation is type/value checked and bbox is checked for 4/6 finite ordered values (`main.rs:386-454`). |
| VUN-M1-RUST-07 | **Closed (Medium)** | Publication uses Linux `renameat2(RENAME_NOREPLACE)`, fsyncs the file and parent directory, removes a partial on failure and writes mode 0600 (`main.rs:600-677`). The newline participates in the byte limit. The destination-preservation and newline-cap tests pass. |
| VUN-M1-RUST-08 | **Closed (Medium)** | The final suite has 30 passing tests and a byte-reproducible 53-file/49-Parquet corpus. The retained stable-stage matrix covers every hostile class; valid/malformed uncompressed and Snappy V2, multiple-row-group, scalar/property, CRS, big-endian/3D WKB, same-descriptor mutation, symlink, no-replace and output framing paths are exercised. Direct production-path exact/+1 tests cover 100 MiB input, 1 MiB footer, 128 row groups, 64 KiB Compact page headers, 8 MiB page bodies, 128 MiB decoded bytes, the cumulative 200,000-page ledger, 100,000 dictionary entries, 64 KiB GeoParquet metadata, 4 MiB WKB values, 250,000 vertices, JSON depth 16, 2,000,000 JSON values and literal 16 MiB IPC/output publication. The trusted temporary runner creates real GeoParquet at 100,000/100,001 rows and 64/65 columns; independent execution reproduced exact acceptance and stable +1 rejection. Its 100,000-row control ran under the 384 MiB parser address-space limit, consumed 519,350 input bytes and published a read-back 5,989,092-byte/100,000-feature envelope in under one second. The three last gaps close because the WKB test invokes the same `within_size_limit` predicate used before traversal, the depth test invokes `count_json`, and the IPC test actually writes an exact 16 MiB file and rejects +1 without publication. No M1-applicable ADR numeric boundary remains untested. |

No High, Medium or Low implementation/evidence finding remains. The M1 Rust CLI
correctness gate passes.

## Confirmed strengths and residual evidence

- The production lock matches the reviewed dependency graph exactly.
- The owned scanner executes before upstream footer metadata construction, and
  page headers are scanned before row iteration with field-specific schema,
  row-group, column, page and byte/count reconciliation.
- Page body sizes, codecs, encodings, dictionary order/count, WKB byte/vertex
  limits, finite coordinates, JSON depth, output `create_new`, bounded stable
  stderr and post-decode descriptor identity/content digest are present.
- A cloned `File` keeps page decoding on the opened inode. Descriptor identity
  plus before/after SHA-256 catches same-length in-place mutation at the M1
  boundary; M2 still has to prove private-root ownership and process lifecycle.

This implementation review does not assess the future Python launcher, exact
image, workflow retention/admission, publication or deployment. It also does not
substitute for the still-required M1 resource and exact-boundary evidence.
