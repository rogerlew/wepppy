# M1 Rust CLI Validation

Date: 2026-11-16  
Candidate binary SHA-256: `fe3f08e8a251478d7cf78fdc623a76edd28899948e269c49b5e79fc89e31616a`  
Cargo.lock SHA-256: `ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13`

## Direct gates

`cargo fmt --check`, `cargo test --locked --offline` and strict Clippy passed.
The suite has 30 tests and reconciles all 49 Parquet dispositions in the
53-file, 41,987-byte retained corpus. The manifest SHA-256 is
`f879e3a8c81581c5ddd1d4bdc5a10ef1c0af2fa9f780b1b846730e4fb03f41f5`.
It includes valid and malformed uncompressed/Snappy Data Page V2, two row
groups, Compact-Thrift exact/limit+1 row-group extraction, exact/+1 footer and
8 MiB page body, exact 128 MiB decoded-page and 200,000-page ledgers, exact/+1
JSON depth and values, 4 MiB WKB, 250,000 vertices, literal 16 MiB IPC/output,
the 100 MiB input edge, the 100,000-entry dictionary header and the 64 KiB
page-header read edge,
same-length mutation, symlink and no-replace edges.

The trusted temporary threshold runner additionally produced real GeoParquet
at 100,000 and 100,001 rows and 64 and 65 root columns. The exact controls
converted to 100,000 and one features; the +1 controls rejected at `row_limit`
and `footer_structure_limit`. The exact 100,000-row CLI probe consumed a
519,350-byte input, published a 5,989,092-byte envelope and completed in
0.728245 seconds. The entire runner completed in 1.42 seconds with 306,260 KiB
maximum RSS including PyArrow fixture generation and all child processes. It
retained no temporary inputs or outputs.

## Stable rejection matrix

The enforcement stage is the owned stage named by the stable code, except
`row_decode`, which is the bounded upstream decoder after owned page preflight.
No rejected probe published output.

| Fixture | Exit | Stable code / stage |
| --- | ---: | --- |
| missing-geo | 1 | `geo_metadata_missing` |
| version-unsupported | 1 | `geoparquet_version` |
| crs-null / crs-invalid | 1 | `crs_null` / `crs_invalid` |
| encoding-geoarrow | 1 | `geo_metadata_unsupported` |
| primary-column-missing | 1 | `primary_column` |
| nested-properties / schema-columns | 4 | `footer_structure_limit` |
| extension-metadata | 1 | `extension_metadata` |
| codec-gzip / encoding-delta | 1 | `codec` / `encoding` |
| WKB truncated/count/nesting/nonfinite | 1 | `wkb_invalid` |
| property-nonfinite | 1 | `property_value` |
| bad head/tail/PARE/truncated magic | 1 | `magic` |
| footer-size-bomb / footer-list-bomb | 4 / 1 | `footer_size` / `footer_structure` |
| external-path | 1 | `external_column` |
| encrypted column/footer | 1 | `encryption` |
| page-declared-expansion | 4 | `page_size` |
| page-actual-expansion | 1 | `row_decode` after bounded preflight |
| page-value-count | 1 | `page_encoding` |
| dictionary-value-count | 1 | `dictionary` (owned entry-count budget) |
| page-header-string-bomb | 1 | `page_header` |
| V2 row mismatch / Snappy flag mismatch | 1 | `page_header` |
| null-geometry | 1 | `geometry_empty` |

## Resource receipt

The release probe used the valid Snappy Data Page V2 control and the ratified
launcher limits: 384 MiB address space, 60 CPU seconds, 32 descriptors, 100 MiB
input, 16 MiB output, 100,000 features and 250,000 vertices per feature.

| Measurement | Result |
| --- | ---: |
| Exit / elapsed / user / system | `0` / `0.00 s` / `0.00 s` / `0.00 s` |
| Maximum RSS | 3,072 KiB |
| Input / output / total request scratch | 324 / 317 / 641 bytes |
| Feature count / observed decoded geometry | 1 / one finite Polygon |
| Output publication | exact JSON envelope, atomic no-replace |
| Descriptor ceiling | `RLIMIT_NOFILE=32`, applied before path parsing |
| Aggregate decoded-page ceiling | 128 MiB, checked before upstream decode |
| Aggregate page-count ceiling | 200,000, checked in the owned page ledger |

The resource probe is intentionally a deterministic control, not a claim that
small input exercises every ceiling. Exact and limit+1 branches are direct unit
or retained hostile-fixture assertions; the process limits are independently
applied by both the Rust CLI and Python launcher.
