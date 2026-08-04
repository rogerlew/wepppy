# Operator-only: Python reports (`wepppy.wepp.reports`)

Prefer the report classes under `wepppy.wepp.reports` when you need consistent tabular outputs (units, cache behavior, dataset requirements).

Do not use this reference for normal WEPPcloud web users unless you are operating the backend/export tooling on their behalf.

## What to use first

“First look” tables that usually answer 80% of questions:
- `OutletSummaryReport` – outlet delivery metrics
- `TotalWatbalReport` – watershed water balance totals/ratios
- `ChannelSummaryReport` / `HillSummaryReport` – spatial summaries
- `FrqFloodReport` – return-period / flood-frequency table (uses event maxima + totals)

The internal contract and catalog are documented in:
- `wepppy/docs/dev-notes/reports.md`
- `wepppy/docs/dev-notes/reports/report-catalog.md`

## Practical usage pattern

1. Resolve `run_dir` (see `references/operator-run-directory-layout.md`).
2. Confirm required interchange parquet assets exist under `wepp/output/interchange/`.
3. Instantiate the report against `run_dir`, then export as needed (DataFrame/CSV).

If the user wants a single CSV for downstream plotting, prefer exporting the report output rather than ad-hoc parsing of text outputs.
