# Stochastic dewpoint study tracker

Status: Closed 2026-10-08 (existing-station research baseline).

## Completed

- Located nine frozen GridMET-study fixtures and four-product OpenET evidence.
- Located the three original station files and vendored CLIGEN binary metadata.
- Registered ten fixed seeds and month-of-year comparisons.
- Froze 30 distinct daily climates and verified exact same-seed replay.
- Logged 454 unmet internal generator quality targets across 26 realizations;
  retain all seeds and separately inspect the four diagnostic-free realizations.

## Completed execution and analysis

- All 180 cases and 2,344,980 daily rows pass calendars, input isolation,
  output hash/finite-value checks and precipitation readback.
- Seasonal-cycle RMSE and monthly distribution distance favor clipping in 36/36
  pooled comparisons; cycle MAE favors clipping in 35/36.
- Four diagnostic-free Walla Walla realizations give the same RMSE/distribution
  direction in 12/12 comparisons; cycle MAE improves in 11/12.
- Seasonal figure rendered and visually inspected; station mismatch quantified.

## Decision and follow-up

Keep native stochastic production behavior and the clipping treatment in the
research harness. Defer a general UI option pending location-matched climate
evaluation and investigation of generator diagnostics. See
[results](artifacts/results.md#recommendation-and-follow-up) and the current
[climate design note](../../dev-notes/prism-800m-client-design.md).
