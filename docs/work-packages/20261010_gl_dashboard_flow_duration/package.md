# GL dashboard flow-duration curves

Status: Implemented and validated on forest; full Python gate running, 2026-10-10.
Owner: Codex; decision owner: requesting operator.

## Purpose and confirmed scope

Add a Flow duration curve panel to the GL dashboard. Provide radio options for
hillslope streamflow from totalwatsed and channel outlet discharge. Offer linear
and logarithmic exceedance-probability x-axes. Support Omni scenarios using the
same baseline/child labels and scenario colors as existing dashboard graphs.
Daily sampling, default two-year warm-up exclusion, return-period Year selection
options, no seasonal filters, no CSV export, and hover discharge/probability are
confirmed. Rain-on-snow exclusion is omitted because no verified classifier is available.
The operator authorized execution, commit, forest restart and integration tests.

Durable requested scope is recorded in the [accepted contract](../../ui-docs/contracts/gl-dashboard-flow-duration-contract.md).
The [requirements register](notes/requirements.md) separates confirmed behavior,
proposals, and unresolved decisions. [Discovery](notes/discovery.md) records
source paths, actual-project observations, and scientific references.
Execute this package's [plan](prompts/active/flow_duration_execplan.md); reviewed
checkpoint ancestor is c63f2cc52.

## Implementation boundary

Reuse the dashboard graph panel, graph loader/query helpers, state store,
scenario catalog, display-name helper, palette, and graph layout controls.
Read daily Parquets through the existing Query Engine. Extend numeric x-axis
rendering with isolated probability formatting and transforms; do not represent
probabilities as calendar years. Do not add model runs or derive a curve from
annual summaries, storm peaks, or staged return-period event ranks.

First delivery is watershed-total hillslope flow versus the watershed channel
outlet, one selected source at a time. Per-hillslope curves, arbitrary channel
picking, observed-gage uploads, fitted probability distributions, return-period
analysis, confidence bands, and Omni contrasts are outside this delivery. CSV export and seasonal filters are explicitly excluded.

## Complexity budget

No new service, queue, datastore, dependency, privilege, or deployment topology.
Use owned DuckDB/Query Engine and existing canvas graph infrastructure. First
measure projected daily queries and local sorting on realistic long records
with several scenarios. Add server aggregation or draw decimation only if
retained workload evidence requires it; do not truncate the population before
ranking or distort tails. Keep scope limited to the new graph and shared seams
necessary to render it.

## Scientific and compatibility gates

The probability formula, tie convention, daily-flow conversion, date window,
missing-day treatment, and listed defaults are accepted. Record them in the
contract and a parameterization ADR before implementation/merge. No existing
model formulas or persisted Parquet schemas should change. Any later persisted
artifact proposal needs a compatibility and downstream-readback plan first.

Reuse baseline labels Undisturbed/Burned and exact child names. Scenario source
absence must never be presented as baseline data through Query Engine overlay
fallback. Readonly is not completion evidence. Preserve authorization, scenario
containment, map selections, and behavior of every existing graph.

## Evidence and security

Security impact: high under the repository's data-query boundary classification;
retain a dedicated security review before implementation closeout. Existing
Query Engine authorization and scenario resolution remain the boundary. Independent contract reviews passed and checkpoint c63f2cc52 preceded
production edits. Final correctness, QA and security reviews passed. Correctness review must independently verify valid absent,
empty, readonly, partial, legacy, and multi-scenario states.

Generated-artifact validation applies to consuming daily Parquets and producing
plotted curve data. Retain exact source paths and schemas, projected
sample values, population/rank oracle, graph payload and browser/hover readback. Include a real project with baseline plus Omni,
an intermittent/zero-flow fixture, and unequal-record scenarios. Confirm actual
source ownership for missing-child-data tests. Implementation and authenticated source-to-browser validation passed after
forest restart; see [validation evidence](artifacts/20261010_validation.md).

## Acceptance and handoff

Both source radios and both x scales work with baseline and multiple scenarios.
Every curve has an independently validated population/ranking; zeros, ties,
missing days and unequal periods follow the accepted contract. Labels/colors
match other Omni graphs across selection, source, axis, and layout changes.
No calendar slider, stale response, cache collision, or map selection changes
the wrong curve. Accessibility and mobile/fullscreen behavior are verified.
Targeted tests, full gates appropriate to implementation, real source-to-browser
checks, correctness/security reviews, user/developer docs, and any ADR complete
before declaring the feature delivered. Deployment is a separate recorded step.

Operator decision update (2026-10-10): each scenario uses its own available
eligible record, for performance; no common valid-date intersection. Show each
period and N. Other recommendations accepted: fixed m³/s, Weibull ranking,
retained ties/zeros, disclosed missing-day exclusions and invalid-record errors;
hillslope/linear-x/linear-y defaults; baseline plus available Omni with existing
visibility behavior; baseline output scope only; existing persistence conventions.
Rain-on-snow defaults unchecked and uses shared excluded dates when enabled;
classifier, mask construction and event-window definition remain to verify.
This optional mask does not impose a shared flow record. These decisions supersede earlier proposals. Source checks, ADR and independent
reviews are complete. The operator subsequently requested removing the unavailable rain-on-snow
control and explanation; both are omitted in this delivery.
