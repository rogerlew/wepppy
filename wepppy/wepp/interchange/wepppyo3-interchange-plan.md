# WEPPpyo3 Interchange Migration Plan (Retired)

## Status

This historical migration plan is superseded. The two-phase native acceleration
work completed on 2026-01-30, and the compatibility implementation was retired
on 2026-07-15 by the
[WEPPpyo3-only cutover work package](../../../docs/work-packages/20260715_wepppyo3_only_interchange/package.md).

The current normative contract is
[wepppyo3-interchange-spec.md](wepppyo3-interchange-spec.md), governed by
[ADR-0020](../../../docs/adrs/ADR-0020-require-wepppyo3-interchange.md).

## Delivered Migration

Phase 1 introduced the Rust/PyO3 crate, native Parquet infrastructure, calendar
handling, and watershed PASS, SOIL, LOSS, and channel-peak writers. Phase 2
added watershed EBE and water-balance writers, hillslope parsers, the WAT bulk
writer, and the native query catalog scanner.

The initial rollout retained Python report parsers as a compatibility path.
Operational evidence from the AgFields routing suite showed that this converted
native release defects into long-running, high-memory jobs. The final cutover
therefore added the remaining five hillslope bulk writers, TC_OUT, native PASS
hint discovery, and native EBE raw-channel auditing before deleting the Python
report parsers and primary Parquet fan-in.

## Locked Decisions

- The Python public facade remains stable for callers.
- WEPPpyo3 is required for report parsing and primary Parquet writing.
- Native import, symbol, parse, I/O, and write failures are terminal.
- Hillslope source order maps directly to Parquet row-group order.
- Climate discovery stays in WEPPpy; climate-table consumption and date
  construction stay in the native writers.
- Query, export, and derived-product code remains in WEPPpy unless separately
  migrated.
- Rollback restores a paired release; it does not enable a second parser.

## Historical Validation Evidence

The completed cutover package records the native release commits, artifact
SHA-256, focused and broad gates, generated-output smoke, local stack restart,
and two independent reviews. Future changes should update the normative contract
and create a new work package rather than extending this retired plan.
