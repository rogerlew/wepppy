# Correctness review: MOFE ET and Dp area weighting

## Metadata and user outcome

- Reviewer: independent `/root/contract_review_a`; contract also reviewed by
  `/root/contract_review_b` before checkpoint `9651d7af6`.
- Date: 2026-10-20. Native implementation: `5e42716230dd6f02d218bfbe10509d501edb93a8`.
- Authority: [water aggregation contract](../../../schemas/hillslope-water-aggregation-contract.md),
  Features Export specification, output-scope and report-cache contracts.
- User outcome: correct local-area ET/Dp in report, event/comparison map, and
  feature exports; explicit unavailable/error behavior for invalid observations.
- Security triage: no new authentication, access, transport or privilege surface.

## State and failure evidence

| State | Required behavior | Evidence |
| --- | --- | --- |
| Source absent, retained summary | Historical unverified access under existing guard | Report freshness regressions |
| Source populated, old semantic marker | Atomic corrected rebuild even with matching hashes | Real native writer cache test |
| Empty source/selection | Existing empty schema/columns, no fabricated depths | Native, CSV, export tests |
| Populated unequal/sparse/mapped OFEs | Daily volume/area then temporal reduction | Native/export oracle and real-project receipt |
| Invalid Area or infinite components | Explicit native/export error; unavailable dashboard ET | Real writer/materializer/SQL regressions |
| Missing joined WAT observation | Retain geometry and null metric | Partial/empty join regressions |
| Callable obsolete native writer | Reject missing marker, retain previous published bytes | Native writer with marker-stripping boundary test |
| Unsupported mixed AgFields cardinality | Existing explicit join rejection | Scope limitation, no new join algorithm |

## Findings and disposition

| ID | Severity | Finding | Resolution |
| --- | --- | --- | --- |
| COR-01 | High | Guessed joined WAT column suffixes could use another source's Area/date | Record actual collision renames and source identity at join; collision regression |
| COR-02 | Medium | Unmatched left-joined WAT rows treated as invalid observed Area | Filter by actual WAT source identity; preserve missing metrics and geometry |
| COR-03 | Medium | Requested missing event dates dropped from output schema | Preserve ordered selector tokens and null columns for empty pivots |
| COR-04 | Medium | ET-only selection hid opposing infinite components as NaN/zero | Validate hidden Ep/Es/Er whenever ET selected; conflicting-infinity regression |
| COR-05 | Medium | Missing primary-table dates discarded valid joined WAT dates | Reduce local stream first; retain its keys independently of generic dates; all three modes tested |

All five findings are resolved. Reviewer independently repeated COR-04 and
confirmed `MaterializationContractError`; repeated COR-05 probes return ET5/Dp7 in all three modes. Native single-OFE state and exact
signed-integer row-group geometry proof pass review; unsupported metadata uses
the projected key scan, with full value validation in the main pass. CSV adapter
retains annual rows, headers, divisor, scope and optional Parquet behavior.

## Artifact evidence chain

Intent and canonical input contracts precede implementation. Regression fixtures
exercise actual writers, generated SQL in DuckDB, joins/reducers, and serialized
CSV/Parquet/GeoJSON ZIP members. The isolated real project supplies unchanged
H.wat bytes to the final release library and compares every hill/year against
independent daily SQL, then verifies report/export consumption. The native release
manifest binds source-file and library hashes. Report attempts remain under normal
project paths; existing canonical archive/restore regression verifies bytes and
provenance. Live authenticated browser/download acceptance passed: all455 report/event
rows match independent source SQL; four downloads match retained artifact hashes.
See `20261020_live_validation.json` and `20261020_live_oracle.json`.

## Verdict

Code correctness: **pass**, no open high or medium findings. Final package
acceptance is conditional on completed quality-gate disposition and live HTTP
readback after the development reload. No production deployment or historical
repair is established by this review.
