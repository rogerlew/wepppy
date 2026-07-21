# Native Reader Admission Audit — 2026-07-21

## Method

Reviewed every reader under `wepp_interchange/src` for post-header `continue`, width
checks, numeric conversion, and zero-row publication. A line is either an explicitly
documented non-data line or a candidate; candidate conversion errors must be returned as
`InterchangeError::Parse`.

## Findings and Remediation

| Reader | Candidate contract | Finding | Result |
| --- | --- | --- | --- |
| `chnwb.rs` | 22 legacy or 27 current whitespace fields after `OFE` header | Exact-22 gate silently skipped every current record and published an empty Parquet file. | Fixed: accept 22/27 only; reject other widths, absent header, and zero accepted rows. |
| `chanwb.rs` | 10 fields after `Year` header | Wrong widths were silently skipped. | Fixed: contextual rejection plus absent-header/zero-row failure. |
| `chan_peak.rs` | 6 fields after channel-peak header | Wrong widths were silently skipped. | Fixed: contextual rejection. Header-only output remains an intentional empty schema case. |
| `ebe.rs` | 10 legacy or 11 current numeric-leading fields | Numeric malformed widths were silently skipped. | Fixed: contextual rejection. |
| `soil.rs` | Recognized watershed SOIL header width | Nonblank post-header text without a numeric OFE was silently skipped. | Fixed: contextual rejection; blanks and separators remain non-data. |
| `hill_ebe.rs` | Recognized EBE header width | Wrong-width data rows were silently skipped. | Fixed: contextual rejection. |
| `hill_wat.rs` | Recognized WAT header width | Wrong-width data rows were silently skipped. | Fixed: contextual rejection. |
| `hill_soil.rs` | Recognized SOIL header width, including fixed-width recovery | Failed fixed-width recovery was silently skipped. | Fixed: contextual rejection. |
| `hill_loss.rs` | LOSS class rows with the documented measurement width | Short records were silently skipped. | Fixed: contextual rejection. |
| `tc_out.rs` | `C` channel records with at least 9 fields | Short or nonnumeric channel identifiers were silently skipped in outlet discovery and conversion. | Fixed: shared contextual validation; `H` hillslope records and headers remain deliberate filters. |
| `pass.rs`, `hill_pass.rs` | PASS event labels and documented continuation records | Existing reader returns contextual errors for malformed event/header candidates. | No silent candidate-loss path found. |
| `loss.rs` | Identified watershed LOSS table rows | Existing table parser rejects malformed data and uses explicit section boundaries. | No silent candidate-loss path found. |
| `hill_element.rs` | Fixed-width element rows after two nonempty heading lines | Existing fixed-width and numeric conversion paths return errors. | No silent candidate-loss path found. |
| `hill_hbp.rs` | Binary magic/version/directory/payload records | Existing bounds, checksum, and decode validation returns errors. | No silent candidate-loss path found. |

## Intentional Empty Contracts

- Bulk hillslope writers publish a schema-only Parquet file when the caller supplies an
  empty source list. This is a caller-level no-input contract, covered by existing tests.
- `chan_peak.rs` can publish a schema-only artifact after a recognized header with no peak
  records. It is not used to represent rejected candidates.
- `tc_out.rs` returns no output path when the source has no channel records; hillslope (`H`)
  records are intentionally outside this outlet-channel dataset.

All other table readers now fail on a recognized header with no accepted candidate when
their output requires data, or preserve only the explicit no-input contracts above.
