# ADR-0085: Daily flow-duration comparisons

Status: Accepted and implemented
Date: 2026-10-10

## Context and decision

Add the first GL-dashboard daily flow-duration graph. Use each scenario's own
available daily record, default exclusion of its first two year groups, and
Weibull plotting positions P = 100m/(N+1) for descending ranks m=1..N. Keep ties
and zeros. Missing days/null/NaN flows are counted and omitted; invalid negative,
infinite/nonnumeric flows, duplicate or malformed dates and invalid conversion
areas invalidate that curve. Use fixed m³/s: totalwatsed3 Streamflow (mm) times
Area (m²) divided by 1000 and 86400; channel outlet Outflow (m³) divided by 86400.
Do not substitute event peaks or annual summaries. Defaults: hillslope source,
linear x and linear y; optional log x transforms positions only.

## Decision provenance

Decision Venue: Codex conversation, 2026-10-10, America/Los_Angeles; exact message
times unavailable. Participants Present: requesting operator and Codex.
Decision Owner: requesting operator. Implementer: Codex.
Operator selected independent records for performance, accepted other listed
recommendations, then authorized commit, execution, forest restart and integration.

## Change summary and rationale

Previously there was no FDC graph. This adds a read-only distribution of daily
mean discharge with independent sample counts and periods. Reuse return-period
Year selection options (all/first 1/2/5 excluded), graph colors and labels.
No seasonal filters or CSV export. Hover exposes flow and probability.

## Alternatives considered

Common valid-date intersection was rejected by the operator for performance.
Rank/N and midpoint plotting positions were considered; Weibull is an established
HEC option and has finite positive positions on log x. Zero removal/filling gaps
would bias the population. Unitizer integration and Roads are outside first scope.
No rain-on-snow thresholds are invented. The operator requested removing the
disabled control on 2026-10-10 because classification cannot be determined. A
future filter requires a verified classifier and shared event-date mask.

## Evidence

[Contract](../ui-docs/contracts/gl-dashboard-flow-duration-contract.md) and
[research](../work-packages/20261010_gl_dashboard_flow_duration/notes/probability-and-data-quality.md)
include primary sources and the [4,2,2,0] -> [20,40,60,80]% oracle.

## Consequences, risks and rollback

Different record periods may affect comparisons; show each period, N and missing
count. Warm-up can exhaust a short record. Zero/one-point curves stay valid.
No model files, persisted schemas or model parameterization are changed.
Disable/revert this graph if source identity or numerical validation fails;
retain existing graphs and outputs. Classifier delivery remains explicitly deferred.
