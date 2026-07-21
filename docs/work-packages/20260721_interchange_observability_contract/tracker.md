# Tracker - Interchange Parser Observability Contract

## Quick Status

**Timezone**: UTC  
**Started**: 2026-07-21 18:46 UTC  
**Current phase**: Closed
**Last updated**: 2026-07-21 19:03 UTC
**Next milestone**: Observe production logs after release deployment.
**Security impact**: `none`  
**Dedicated security review**: no  
**Security artifact**: N/A

## Task Board

### In Progress

None.

### Ready / Backlog

None.

### Blocked

- None.

### Done

- [x] Scoped the production defect and created the package, tracker, and active ExecPlan (2026-07-21 18:46 UTC).
- [x] Audited all native reader admission paths; repaired ten silent candidate-loss paths and documented the remaining intentional-empty contracts (2026-07-21 19:03 UTC).
- [x] Added current 27-field CHNWB support, strict native summaries, and Python structured logging (2026-07-21 19:03 UTC).
- [x] Parsed the original production source to a disposable artifact: 34,192,070 source rows and 34,192,070 Parquet rows (2026-07-21 19:03 UTC).
- [x] Passed native and WEPPpy focused validation; published governance and closed the package (2026-07-21 19:03 UTC).

## Timeline

- **2026-07-21 18:46 UTC** - Package created after production investigation found 34,192,070 raw CHNWB records and an empty `chnwb.parquet`.
- **2026-07-21 19:03 UTC** - Rebuilt native parser wrote a disposable 1.0 GB Parquet artifact with all 34,192,070 source records; package closed without replacing production output.

## Decisions Log

### 2026-07-21 18:46 UTC: Replace silent loss with explicit parser contracts

**Context**: The current parser checks for exactly 22 tokens and silently continues for all other candidate rows. The current WEPP-Forest producer emits 27 fields.

**Decision**: Treat any data-looking row after a recognized table header as a contract-bearing candidate. The parser must either accept it under a documented layout or return `InterchangeError::Parse` with path, line, expectation, and preview. An intentional empty dataset must be explicit and separately tested.

**Impact**: Existing silent partial or zero-row outputs become observable failures, preventing invalid artifacts from entering reports and exports.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|---|---|---|---|---|
| Legitimate format variants are rejected | Medium | Medium | Model variants explicitly in fixtures and define supported layouts before coding | Open |
| Large-run parser checks affect runtime | Low | Low | Use constant-time token/accounting checks and benchmark against the affected 8.8 GB input | Open |
| Some readers intentionally return empty output | Medium | Medium | Audit and document each no-data contract; test it independently from malformed input | Open |

## Hardening Signal Log

- **Baseline health signals**: `chnwb.txt` has 34,192,070 data records; `chnwb.parquet` has zero rows.
- **Post-change health signals**: disposable reparse accepted 34,192,070 rows in 137 row groups; `candidate_records=accepted_records=34,192,070`, `rejected_records=0`.
- **Danger signals observed**: silent row discard hides contract drift from operators.
- **Temporary callus register**: none.

## Verification Checklist

- [x] Native WEPPpyo3 tests pass (82 library, 17 tc_out integration).
- [x] WEPPpy interchange test passes (6 tests).
- [x] Affected run CHNWB reparse has matching source and Parquet row counts.
- [x] Malformed fixtures fail contextually.
- [x] Documentation lint passes for all touched Markdown files.

## Progress Notes

### 2026-07-21 18:46 UTC: Production evidence and package start

**Agent/Contributor**: Codex

**Work completed**:

- Confirmed the run uses `wepp_260430` and a source-compatible 27-field CHNWB layout.
- Confirmed the native parser requires exactly 22 tokens and writes a zero-row Parquet file when all rows are skipped.
- Created the package contract and began the reader inventory.

**Next steps**:

1. Classify every `continue`/empty-output path in the native interchange readers.
2. Define the shared admission/accounting API and repair CHNWB first.
