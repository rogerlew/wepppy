# Dewpoint / OpenET study tracker

Status: Closed 2026-10-08 (research execution).

## Completed

- WEPP source and stochastic CLIGEN audits establish that `Td >= Tmin` is not
  an engine input requirement. Existing policy remains unchanged.
- Located retained GridMET humidity and prepared hillslope inputs at Topanga,
  Tiger-Mill and cryptic-beechnut. Located official OpenET API schema.
- User supplied credential path; secret stays outside artifacts.
- Official point and polygon access validated. Polygon API requires a GeoJSON
  FeatureCollection; the rejected single-Feature request is retained.
- Raw dewpoint reconstruction exactly matches the archived clipped values.
- Nine frozen hillslope fixtures, one pinned executable and 18 successful
  executions; 234,498 daily rows and paired input isolation validated.

## Completed analysis

- All 36 OpenET series contain 84 monthly values; no missing values.
- Clipping yields lower monthly MAE/RMSE in all 36 site–product comparisons,
  including low-snow months; annual ensemble MAE favors clipping in 63/63 pairs.
- Forest ensemble bias sensitivity retains the same ranking in all 12 cases.
- Monthly-series and seasonal-effect figures rendered and visually inspected.
- Source inputs remain unchanged. No production client, UI or default changes.

## Decisions

The [results](artifacts/results.md#decision-and-follow-up) recommend retaining
clipping and deferring a general disable switch. The current PRISM
[client design](../../dev-notes/prism-800m-client-design.md) records this decision
and its bounded rationale. Broader climate/observational validation and the
existing spatial temperature consistency exceptions remain follow-up research.
