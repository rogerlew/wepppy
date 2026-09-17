# Correctness and User-Experience Review — Daymet source preservation

## Metadata

Reviewer: Codex (implementation self-review); 2026-09-17 UTC, master.
Contract ancestor: aa4fbc502, following two independent contract approvals.
Scope: two Daymet builders, their direct persistence boundaries and regression tests.
Authority: climate-parquet-lineage-contract, “Daymet acquisition source preservation”; ADR-0006 source-preservation amendment. No security interface or permission change.

## User outcome

Acquired Daymet parquets retain original units and radiation. Generated CLI behavior remains unchanged. Normal rebuild is the recovery for historically mislabeled artifacts; no automatic mutation or magnitude-based conversion is introduced. Existing parsing, quality-guard and filesystem failures propagate as before; source and diagnostic CSV remain available after downstream failure.

## State and input matrix

| State | Required behavior | Evidence |
| --- | --- | --- |
| Source absent before acquisition | Write acquired values once | Single-location test and real build |
| Populated single-location source | Preserve physical units during conversion | Full DataFrame equality and actual PRN values |
| Populated interpolated source | Read without rewriting | Exact source-byte comparison |
| Legacy radiation provenance | Retain columns/bytes; honor original radiation source | Parameterized legacy test |
| Malformed/missing required columns or empty data | Existing parser/required-column behavior; no new fallback | No parsing or validation code changed; not exhaustively retested |
| Downstream CLI write fails | Preserve source and separate CSV | Injected write failure with real parquet/CSV I/O |

Input combinations exercised: single/interpolated; source radiation below/above bound; legacy/plain source; wind disabled in focused tests and enabled in real CLIGEN replay; successful/failed publication. This is bounded regression evidence, not a claim of exhaustive flag combinations.

## Checks and findings

- Canonical intent ratified and committed before implementation.
- Runtime change is one caller copy and removal of two writes; no exception, numerical formula, permission or enqueue changes.
- Three regression cases fail before the change and pass after; 42 focused tests pass.
- Real CLIGEN replay corrects source equality while preserving PRN and CLI bytes exactly. One-year replay does not bypass a quality failure; it does not negate the audited live 45-year warning.
- Archive/restore uses canonical filesystem implementation and verifies all generated members and restored bytes.
- Browser verifies existing source/CSV visibility and download hashes through normal authenticated access. This confirms the unchanged delivery paths using the existing live artifacts; it is not a live climate rebuild.
- No medium/high findings. Full suite passes: 8,983 passed, 99 skipped, 3,155 warnings.

## Artifact observability

Comparable inventory: existing Daymet acquisition parquet, PRN, CLI, station file, CLIGEN log and radiation CSV. No new hidden project artifacts or archive exclusions. Existing browser/download paths remain intact. Corrected generated files and original failing replay are retained in before/after evidence directories. Failure-injection tests preserve source and CSV. Canonical archive/restore receipt: archive_verification.json.

Browser's initial check failed because the climate listing is paginated; corrected traversal selects page 3, where both artifacts are listed. The initial failure log is retained; this was an audit-harness assumption, not a product defect.

## Verdict

Bounded correctness gate: pass. No open correctness findings. Full-suite disposition is recorded in the tracker.

Raw CLIGEN/PRN outputs and captured logs intentionally retain their original fixed-format whitespace for byte-parity evidence. The authored Markdown/Python/JavaScript whitespace check passes; raw-output whitespace is not normalized.
