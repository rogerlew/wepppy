# Independent Rust CLI Correctness Review

Date: 2026-11-14

Reviewer: independent `reviewer` agent

Commit: `fe5ac7c1c`

Verdict: **FAIL / HOLD**. Critical 0; High 1; Medium 4; Low 0.

## User outcome

The covered GeoJSON and GeoParquet cases are locally valid, but the implementation
does not yet preserve all ratified valid states or the cancellation contract.
Highest supported claim: locally validated for the covered matrix.

## Findings

| ID | Severity | User/state surface | Finding | Required action |
|---|---|---|---|---|
| ICOR-01 | High | Cancellation and availability | Real parser execution blocks the single event loop in synchronous `communicate()`. The existing cancellation test substitutes `asyncio.sleep` and does not terminate a real parser group. | Use cancellation-safe asynchronous subprocess handling; prove client cancellation, descendant termination, scratch cleanup, and concurrent health. |
| ICOR-02 | Medium | Malformed record alignment | A two-record SHP with one SHX entry and one DBF record exits zero and silently publishes one feature. | Enforce exact SHP/SHX/DBF cardinality and index alignment. |
| ICOR-03 | Medium | DBF field names | Duplicate DBF names overwrite earlier values in the `BTreeMap`; a direct probe retained only the second value. | Reject duplicate/colliding field names deterministically. |
| ICOR-04 | Medium | Wide DBF numeric fields | A valid 20-digit zero-decimal numeric accepted by Fiona is rejected by the Rust `i64`-only path. | Preserve the ratified compatibility behavior or narrow the contract with explicit owner acceptance. |
| ICOR-05 | Medium | Semantic matrix | Cross-language goldens omit multipoint, M variants, logical values, deleted records, LDID encodings, and unsupported-value behavior required by M4. | Complete the matrix or explicitly narrow and approve the contract. |

## Validation

- Committed focused parser tests: 17 passed with 2 warnings.
- Independent malformed-record, duplicate-field, and wide-numeric probes
  reproduced the findings.
- No deployment or production correctness is claimed.

The generated-artifact boundary passes for the covered cases only. M6 correctness
approval and #656 closure remain blocked.
