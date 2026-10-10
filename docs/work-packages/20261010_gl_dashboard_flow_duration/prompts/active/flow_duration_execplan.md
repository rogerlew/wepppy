# Add flow-duration comparisons to the GL dashboard


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
The operator authorized commit, execution, forest stack restart and integration
on 2026-10-10. Implementation starts after the reviewed checkpoint ancestor exists. This is the active plan for this package, not other repository plans.

## Purpose / Big Picture


A user opens Flow duration curve in the GL dashboard, chooses totalwatsed
hillslope streamflow or routed channel outlet discharge, and compares baseline
and Omni flow distributions. Switching linear/logarithmic exceedance x-axis
changes presentation without changing flow values or the sample population.
Scenario names/colors match existing Omni graphs. The graph shares the existing
minimized/split/fullscreen host and does not borrow calendar playback behavior.

## Progress


- [x] (2026-10-10 20:28 UTC) Inspect graph loaders, renderer, state and candidate daily schemas.
- [x] (2026-10-10 20:28 UTC) Read-only source inventory on eighty-five-synthetic plus undisturbed.
- [x] (2026-10-10 UTC) Scaffold package, draft contract, decision register and validation plan.
- [x] (2026-10-10 UTC) Record daily/filter/hover decisions and research ranking/data quality.
- [x] (2026-10-10 UTC) Accept independent records, scientific defaults and ADR-0085; rain-on-snow was initially visibly unavailable (removed by final operator decision).
- [x] (2026-10-10 UTC) Independent contract reviews passed; checkpoint ancestor c63f2cc52.
- [x] (2026-10-10 UTC) Implement daily loader, ownership/outlet metadata, renderer and controls.
- [x] (2026-10-10 UTC) Validate source-to-graph correctness, loader performance, keyboard inspection and isolation.
- [ ] Complete independent reviews, documentation and delivery evidence; record deployment separately.

## Surprises & Discoveries


The existing outlet stream graph uses annual summaries. It cannot provide daily
flow-duration observations. totalwatsed3 has daily Streamflow depth, whereas
chanwb contains routed daily outlet volume; chnwb and event peaks mean different
things. The renderer's existing log toggle applies to boxplot y, and its line
renderer expects a shared years array. New independent probability coordinates
need a bounded renderer extension and correct inverse-log hover handling.

Final checks exposed shared parent topology in standalone Omni children, a stale
activation failure that could clear a newer graph, and coverage labels that could
omit missing leading days after warm-up. Bounded fixes and regression fixtures
cover these paths. Source ownership remains exact even with shared topology.

Both actual source files exist for the baseline and undisturbed example, each
with 16,437 rows across 1980–2024. That project has no zero hillslope-streamflow
days, so it cannot establish intermittent-flow correctness. Dashboard scenario
catalog presence alone does not establish child source readiness, and Query
Engine scenario overlays require source-ownership checks to prevent false parity.

## Decision Log


2026-10-10, operator: request source radios, linear/log exceedance x-axis and
Omni labels/colors. These are confirmed scope. Codex: reuse current graph/query
infrastructure; remaining calculation choices remain proposals until accepted.
The [requirements register](../../notes/requirements.md) records alternatives,
including accepted daily means, units, independent records and plotting positions.

2026-10-10, operator: daily resolution; default first two years excluded; same
Year selection as return periods; no seasonal filters or CSV; hover discharge and
probability; optional rain-on-snow checkbox. Rationale: familiar warm-up control
and direct inspection without extra seasonal/export scope. Codex recommends
Weibull P = 100m/(N+1), largest daily flow rank 1, preserving ties and zeros.
For [4, 2, 2, 0], proposed probabilities are [20, 40, 60, 80] percent. Missing days
are counted and omitted, never filled; malformed/negative/infinite values and
duplicate dates invalidate that scenario. These scientific policies are accepted and require an ADR. Rain-on-snow
classification remains open; the dashboard has no existing Unitizer preference support.

## Outcomes & Retrospective


Implementation is present after checkpoint c63f2cc52. Forest stack was restarted
with the installed development wctl preset. Targeted tests, independent final
reviews and browser numerical integration pass. Full Python sanity is running.
No model outputs or persisted schemas were changed. All three existing GL smoke
failures reproduce with checkpoint JavaScript and are documented separately.

## Context and Orientation


Work at `/home/workdir/wepppy`. Read nearest AGENTS before editing. Current
canonical dashboard spec is `docs/ui-docs/gl-dashboard.md`. Graph registrations
live in `wepppy/weppcloud/static/js/gl-dashboard/config.js`; loaders, identity and
colors in its `graphs/graph-loaders.js`; canvas rendering in
`graphs/timeseries-graph.js`. `state.js`, `ui/graph-mode.js`, the orchestrator
`wepppy/weppcloud/static/js/gl-dashboard.js` and template
`wepppy/weppcloud/templates/gl_dashboard.htm` own activation and layout.

Daily sources are `wepp/output/interchange/totalwatsed3.parquet` (Streamflow mm,
Area m²) and `wepp/output/interchange/chanwb.parquet` (Outflow m³, Chan_ID,
Elmt_ID). They must be projected through existing scenario-aware Query Engine
requests. Derive the watershed outlet from established topology/translation,
never a guessed channel index. Avoid joining independently ranked scenario
flows by date after constructing the distribution.

## Plan of Work and Milestones


Milestone 1 resolves the register's open requirements. Verify the daily date
identity, outlet mapping, unit conversion and coverage on actual Parquets.
Decide ranking/ties and write a hand-computed oracle containing zeros and ties.
Amend `docs/ui-docs/contracts/gl-dashboard-flow-duration-contract.md` with exact
accepted behavior; prepare an ADR for equations/defaults and a package contract
decision artifact. Obtain two independent read-only reviews, resolve findings,
and commit these as an ancestor before source edits. Record revision in tracker.

Milestone 2 implements the smallest loader and renderer extension. Project only
necessary daily columns and outlet rows, validate complete populations despite
query limits, preserve scenario ownership, and compute each curve independently.
Reuse stable scenario identity/display-name/color helpers. Add a numeric
probability graph payload with independent series coordinates and sample/period
metadata instead of misusing years. Keep probability transforms/ticks/hover
isolated from existing time-series and boxplot behavior. Register the graph,
source radios and x-scale controls through current state/activation conventions.
Use linear/log transforms of the same data; ensure late responses cannot replace
newer selections. Add Year selection with a two-year exclusion default, plus
hover discharge/probability. Do not add seasonal filters or CSV export. Add the
optional rain-on-snow exclusion only with a verified classification contract.

Milestone 3 proves semantics through actual readers, payloads and visible UI.
Use toy populations plus actual daily fixtures, including missing-child sources,
unequal periods, leap days, all-zero/constant records, invalid values and duplicate
dates. Exercise both sources/scales, no Omni and several scenarios, named/palette
colors, rapid switches, layout and keyboard interactions. Measure long records
and many scenarios before deciding whether server aggregation or rendering
reduction is necessary; any reduction must preserve full-population ranking.

Milestone 4 runs appropriate gates and independent correctness/security review,
updates dashboard user/module documentation and this package, and records exact
local/environment validation. Deploy only through the applicable environment
workflow when authorized; verify the running workers and actual URL, not just
bind-mounted source. Close the package and move this plan to completed only when
implementation acceptance is satisfied.

## Concrete Steps


For this scaffold, run `wctl doc-lint --path docs/work-packages/20261010_gl_dashboard_flow_duration`
and lint the draft contract and PROJECT_TRACKER individually. For implementation,
use `wctl run-npm lint`, `wctl run-npm test`, targeted Query Engine/route pytest
if those change, and `wctl run-pytest tests --maxfail=1` for substantive code.
Use the existing GL Playwright suite through `wctl run-playwright`; read
`wepppy/weppcloud/static-src/tests/smoke/AGENTS.md` and use the stored dev-agent
credentials without printing secrets. Select exact new tests after implementation
paths are known; do not claim a placeholder test command has passed.

## Validation and Acceptance


Given an accepted population [4, 2, 2, 0], a fixture must prove exact counts,
zero retention and the accepted tie/probability formula. Both x scales must
produce the same curve values and metadata. Verify source volume conservation
for any conversion to discharge. On actual baseline plus Omni data, independently
read projected source values, compute the oracle, compare graph payload/tooltip
and visible hover values. A screenshot or HTTP 200 alone is insufficient.

No source change may alter child identity, colors, units or zero handling
silently. Missing one child's Parquet must yield its unavailable state, not the
parent curve. No-date-overlap, invalid dataset and all-zero cases have distinct
accepted outcomes. Existing graph modes, sliders, map scenarios and charts must
pass their regression tests. Record realistic query time, payload size, browser
render time and memory with source hashes/revision for reproducibility.

## Idempotence and Recovery


Scaffolding changes documentation only. Planned graph reads existing output;
do not regenerate models or repair source data to make a graph appear. Retry
failed reads through the existing query path and surface clear graph status.
Revert only this package's implementation for rollback, preserving unrelated
working-tree edits and generated docs_index.json. Avoid introducing stored
artifacts unless separately justified and contracted.

## Artifacts and Interfaces


Keep discovery under notes; retain review dispositions, numerical oracles,
source manifests, performance results and browser/hover evidence under artifacts.
Use `postQueryEngineForScenario(payload, scenarioPath)` with scenario in the
POST body and existing authorization. No new Flask query wrapper, service or
plotting dependency is needed. Promote accepted durable requirements into the
canonical draft contract before checkpoint approval; this plan is execution
history, not lasting normative authority.

Revision: initial scaffold 2026-10-10, preserving confirmed scope separately from
unresolved scientific and interaction decisions.

Revision: 2026-10-10 follow-up records operator daily/warm-up/hover scope and
scientific recommendations; removes the rejected CSV and seasonal proposals.

Operator decision update (2026-10-10): each scenario uses its own available
eligible record, for performance; no common valid-date intersection. Show each
period and N. Other recommendations accepted: fixed m³/s, Weibull ranking,
retained ties/zeros, disclosed missing-day exclusions and invalid-record errors;
hillslope/linear-x/linear-y defaults; baseline plus available Omni with existing
visibility behavior; baseline output scope only; existing persistence conventions.
Rain-on-snow defaults unchecked and uses shared excluded dates when enabled;
classifier, mask construction and event-window definition remain to verify.
This optional mask does not impose a shared flow record. These decisions
supersede earlier proposals; source checks, ADR and independent review remain.

Revision: final operator decision on 2026-10-10 removes the rain-on-snow control
and explanation because no verified classifier is available. Updated the durable
contract, ADR, controls and browser expectation together.
