# Study tracker

Status: Closed, 2026-10-08 21:34 UTC.

Completed nearest-cell PRISM 1991–2020 800 m normals acquisition for all nine hillslopes. January precipitation grid parity passed at every cell. Executed production localization with cached normal inputs, emitted 90 distinct climates, verified exact seed replay, and completed all 180 paired WEPP cases. Validated 2,344,980 daily water-balance rows and independently recalculated all 792 metric rows. All 88 indexed prior-study artifacts remain unchanged.

## Findings and decisions

PRISM localization corrects the forest precipitation deficit and substantially improves forest seasonal ET. Clipping improves pooled seasonal RMSE in 36/36 comparisons but annual ET bias in only 6/36. Retain native stochastic production behavior and existing observed-forcing policy; no UI switch added. A future PRISM dewpoint-normal treatment must be declared separately. Full rationale and caveats are in [results](artifacts/results.md); durable policy is in [client design](../../dev-notes/prism-800m-client-design.md#required-validation-before-publishing-a-cache-entry).

CLIGEN has final statistical quality diagnostics in 69/90 climates. Preserve all seeds; the 21 diagnostic-free climates retain the pooled RMSE preference at seven sites. This limits inference, not execution integrity. Production's zero-probability wet-day handling is retained. Parameter rows other than P/T localization, including station dewpoint and metadata, are unchanged.

## Verification

Output hashes, calendars, finite values, input precipitation readback, treatment isolation, fixed nonclimate fixtures, terminal completion, independent metrics, and visual figure review passed. Scripts and retained evidence are under `artifacts/`; large raw outputs are under `/home/workdir/wepppy-scratch/prism-stochastic-dewpoint-20261008`. No source-project edits, production code changes, deployments, new dependencies, or OpenET key access.
