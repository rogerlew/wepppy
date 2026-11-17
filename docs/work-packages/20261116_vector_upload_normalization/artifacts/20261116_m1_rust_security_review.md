# M1 GeoParquet Rust CLI security review

Date: 2026-11-16  
Reviewer: independent `m1_rust_security` security reviewer  
Scope: uncommitted M1 `geoparquet_parser_cli` implementation after M0 ancestor
`1aebebfe0`; no converter, image, workflow, publication or deployment review  
Verdict: **PASS — no unresolved High or Medium findings**

The findings table records the initial review snapshot. The focused disposition
later in this document supersedes its statuses for the remediated candidate.

## Findings

| ID | Severity | Exploit path and concrete evidence | Required remediation | Status |
| --- | --- | --- | --- | --- |
| VUN-M1-SEC-01 | High | The owned footer scan applies only generic depth, one-MiB binary and `131072`-element container bounds. It does not extract the FileMetaData schema or row-group list counts. `SerializedFileReader::new(...)` runs at `preflight.rs:62` before the 64-column, 128-row-group, scalar-schema and declared-row checks at lines 118-187. A hostile footer can therefore make the upstream decoder allocate and construct schema/row-group/column metadata above ADR-0145's exact ceilings before application validation. This violates the M0 condition that the owned footer/schema preflight precede every upstream decoder; the retained huge-list fixture only proves rejection above the generic 131072 bound, not at the accepted exact edges. | Extend the owned Compact-Thrift footer parser to extract and validate the exact FileMetaData structure before `SerializedFileReader`: schema nodes/root-plus-64 primitive children, at most 128 row groups, bounded column chunks, total and per-group rows, required metadata fields, external/encryption fields, offsets/ranges and list/string counts. Add exact-limit and limit-plus-one fixtures/tests proving rejection occurs before upstream construction. | Open |
| VUN-M1-SEC-02 | High | Output/value budgets are post-allocation. `parse_file` accumulates every property and full GeoJSON geometry in `Vec<Value>` at `main.rs:211-250`; only after the whole dataset is resident does `count_json` apply the two-million-value/depth ceiling at lines 263-275, and only `serde_json::to_vec` applies the 16-MiB payload ceiling at lines 510-513. Repetitive Snappy input may stay under the 100-MiB file and 128-MiB decoded-page caps while producing millions of coordinate/property JSON nodes and a payload far over 16 MiB, approaching the 384-MiB address-space limit before a stable rejection. The newly added RLIMIT_AS contains the process but, per ADR-0145 and the M0 review, is not a substitute for pre-allocation enforcement. | Maintain one cumulative JSON value/depth and serialized-byte budget while each row/WKB is decoded, before retaining the row in the parent vectors. Bound property string bytes and aggregate geometry coordinates. Prefer a bounded/streaming serializer or serialize each candidate row into a bounded counter before retaining it; the final serialization may duplicate no more than the already-admitted 16 MiB. Add compressed near-edge and limit-plus-one tests under the direct address-space limit. | Open |
| VUN-M1-SEC-03 | Medium | Declared count reconciliation is incomplete before row decoding. File `num_rows` is checked independently, but it is not compared with the sum of row-group rows; row-group rows are not reconciled to each column's `num_values`; and data-page V1/V2 value/row totals are not summed and compared with column metadata. An attacker can keep each individual declaration at or below 100000 while multiplying work across 128 row groups or many pages, or drive malformed-count paths in the upstream row reader. The main loop eventually stops at `max_features`, but only after upstream decoding has begun. | Use checked arithmetic to reconcile file, row-group, column and data-page totals during owned preflight. Bound aggregate page count across the file, reject overlaps and contradictory declarations, and add mismatch cases that must reject before `get_row_iter`. | Open |
| VUN-M1-SEC-04 | Medium | Page V2 level lengths are checked only against `compressed_page_size` (`preflight.rs:253-264`), not against both compressed and uncompressed body sizes as the contract requires. The scanner also does not require exactly one page-specific header matching `PageType`; it merely reads the expected paths while ignoring extra header fields. Column ranges are allowed through `file_len - 8` (`preflight.rs:158-160`) rather than stopping before the footer start, so a crafted range may overlap footer metadata. These malformed states can reach upstream page logic and panic or consume work outside the admitted page semantics. | Retain the footer start from trailer parsing and require every page body to end before it. For V2, require checked definition+repetition lengths to fit both body sizes, validate null/row/value relationships and compression semantics, and require one matching page-specific header with no contradictory headers. Add V2 level-length, mixed-header and footer-overlap negatives. | Open |
| VUN-M1-SEC-05 | Medium | The CLI does not atomically open the input without following symlinks. It canonicalizes and separately calls `symlink_metadata`, then uses ordinary `OpenOptions::open` (`preflight.rs:31-45`). A same-UID process can replace the path between those operations with a symlink or mutate the same inode in place; the final identity compares only device/inode/length (`preflight.rs:75-84`), so equal-length content mutation is undetected between preflight and decode. The intended M2 private mode-0700 request root and single-flight service materially reduce exploitability, but those controls are not yet implemented and the M1 binary alone does not establish the canonical same-immutable-descriptor invariant. | Open with no-follow semantics at one descriptor boundary, derive containment/regular identity from that descriptor, and ensure the launcher transfers an immutable private snapshot. Recheck a trusted source digest or content identity after decode, not only length/device/inode. Add symlink-swap and equal-length mutation lifecycle tests in M2. | Open |

## Lower-severity observations

- Direct output files inherited mode `0664` in the local mode-0700 test root.
  Parent-directory privacy currently prevents traversal, but explicit mode `0600`
  would preserve the IPC boundary if a directory mode regresses. `create_new`
  correctly rejects an existing partial symlink, and rename does not follow the
  final leaf.
- `RLIMIT_FSIZE` equals `max_payload_bytes`, while the writer appends a newline.
  An exactly-at-limit serialized payload can receive `SIGXFSZ` instead of the
  stable `payload_limit` response. Reserve the framing byte or omit it.
- The WKB parser bounds input bytes, nesting and vertices before vector growth and
  rejects nonfinite coordinates, M/SRID flags, trailing bytes and wrong multipart
  base types. Multipart child coordinate dimensions are not required to match the
  parent; add a negative test if uniform dimensionality is part of the admitted WKB
  profile.

## Positive evidence

- The production and evaluation Cargo locks both have SHA-256
  `ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13`.
  The graph remains Parquet 60.1.0 with defaults disabled/Snappy plus serde_json
  1.0.145.
- `cargo test --locked --offline` passed seven tests, including the 42 Parquet
  manifest dispositions. The two historical allocation fixtures now reject in
  owned page preflight instead of reaching their reproduced 64-GiB/2-GiB
  allocation requests.
- Owned page scanning uses checked offset arithmetic, per-page 64-KiB header and
  8-MiB body ceilings, a 128-MiB declared aggregate, encoding/codec allowlists,
  one dictionary before data, and bounded WKB traversal. Stable stderr contains
  only fixed codes.
- Direct resource limits are applied before path or file parsing, with at most
  384 MiB address space, 60 CPU seconds, 32 descriptors, no core and bounded file
  size. M2 must still provide the independent wall/process-group/drain boundary.

## Gate disposition

M1 is not security-acceptable at this snapshot. The exact dependency graph is
still conditionally accepted, but the implementation has not yet satisfied the
condition that exact semantic footer/page bounds precede upstream allocations,
and the JSON/output ceiling is not an incremental allocation boundary. Resolve
all High/Medium findings and request focused re-review before treating the CLI as
ready for shape-converter integration. This review makes no claim about the
candidate image, workflow retention/authorization, publication or deployment.

## Focused remediation re-review

The candidate was re-read after the footer, incremental-budget, page-ledger,
no-follow and output-publication remediations. The exact production lock still
has SHA-256
`ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13`,
matching the accepted evaluation lock.

| Finding | Focused disposition | Evidence |
| --- | --- | --- |
| VUN-M1-SEC-01 (High) | **Resolved.** | The owned Compact-Thrift scan now records container counts by field path and rejects schema elements above root-plus-64, row groups above 128, columns above 64 per row group, oversized key/value and encoding/path lists, encryption fields and non-flat schema shape before `SerializedFileReader::new`. The remaining scalar/range interpretation is bounded by the one-MiB footer and those structural ceilings, then completes before any page/row decoder. |
| VUN-M1-SEC-02 (High) | **Resolved.** | A cumulative value counter covers CRS, every candidate geometry and every property object before the row is retained. Each candidate row is serialized into a temporary bounded value and the cumulative retained-byte estimate is checked before push; no more than the admitted 16 MiB of row material reaches the final serializer. Final output includes the newline in its exact limit. Per-feature WKB remains bounded at 4 MiB and 250,000 vertices before coordinate growth. |
| VUN-M1-SEC-03 (Medium) | **Resolved.** | Checked reconciliation covers file rows versus summed row-group rows, each column's values versus its row group, data-page values versus its column, first data-page offset, column compressed/uncompressed extents, non-overlapping ranges, and decoded rows versus metadata. Checked `aggregate_pages` now rejects above 200,000 pages across the whole file in addition to the 100,000-per-column bound, before the next page header is read. |
| VUN-M1-SEC-04 (Medium) | **Resolved in source.** | Page bodies stop before the footer; V2 definition-plus-repetition bytes must fit both compressed and uncompressed declarations; flat-schema V2 rows must equal values; `is_compressed=false` requires equal body sizes; and UNCOMPRESSED columns require equal compressed/uncompressed declarations. V2 rows are consequently reconciled through the column value ledger. Contradictory V1, dictionary, index and V2 header kinds are rejected. Repeated occurrences of the same optional header field remain a low strictness issue: the owned and upstream decoders both use the last value under bounded headers, so this does not bypass a size or count check, but a future hardening pass should reject noncanonical duplicates. |
| VUN-M1-SEC-05 (Medium) | **Resolved for M1.** | Descriptor-relative `openat` with `O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC`, exact parent containment and regular-file verification close the symlink/FIFO and ordinary pathname swap paths. An owned SHA-256 pass now binds the opened descriptor before preflight; after row decode, identity is checked, the same descriptor is rehashed for exact equality, and identity is checked again. The same-length mutation regression now detects the changed digest even on a filesystem whose timestamps did not change. M2 must still prove the private single-flight snapshot lifecycle against concurrent same-UID access. |

### Final evidence finding

| ID | Severity | Evidence and required closure | Status |
| --- | --- | --- | --- |
| VUN-M1-SEC-06 | Medium | The deterministic corpus now retains a byte-reproducible valid V2 control, a malformed V2 control differing only at byte 19 (`num_rows` zigzag `1` to `2`), and a valid two-row-group control. Direct tests admit both valid branches, reject the mismatch, and check all 45 Parquet dispositions. The exact/+1 test exercises the same `enforce_count` function wired into footer row-group admission and aggregate page admission, proving inclusive 128/200,000 edges and rejection at 129/200,001 without constructing an attacker-sized fixture. Direct release probing confirmed the malformed V2 file exits 1 with stable `page_header` and no output, while valid V2 and two-row-group files emit one and two features respectively. All 49 manifest hashes and byte sizes match retained files. | Resolved |

Output publication concerns from the initial lower-severity observations are
closed: the partial is created no-follow with mode `0600`, publication uses
Linux `renameat2(RENAME_NOREPLACE)`, file and directory data are synced, partial
cleanup is attempted on failure, and the framing newline is included in both
the application and file-size ceilings.

### Re-review validation

- `cargo fmt --check`: passed.
- `cargo clippy --locked --offline --all-targets -- -D warnings`: passed.
- `cargo test --locked --offline`: passed all 17 tests, including the owned
  SHA-256 known vector, same-length mutation regression, valid/malformed V2,
  two-row-group control, and exact/+1 count test.
- A release binary accepted `polygon-1.1.0-snappy.parquet`, emitted a mode-0600
  347-byte payload with schema `geoparquet-parser-v1`, and left no partial.
  `page-declared-expansion.parquet` failed with stable `page_size`/exit 4 and
  `dictionary-value-count.parquet` failed with `page_range`/exit 1 without an
  output.
- The unit corpus check covers all 45 Parquet dispositions in the 49-entry
  retained manifest. `sha256sum --check --strict` passed every entry and a
  separate byte-size readback matched every manifest declaration.
- The rebuilt release binary accepted `data-page-v2-control.parquet` and
  `multiple-row-groups-control.parquet`, emitting mode-0600 payloads with one
  and two features. `data-page-v2-row-mismatch.parquet` failed at owned
  preflight with stable `page_header`/exit 1 and published no output.

### Focused gate disposition

The M1 bounded Rust CLI security gate is **PASS** with no unresolved High or
Medium findings. All prior source findings and the final direct-evidence gap are
closed. Exact-image resource overlap, private-snapshot/process lifecycle and
wall-time qualification remain M2 gates; this M1 disposition makes no claim
about integration, image publication or deployment.
