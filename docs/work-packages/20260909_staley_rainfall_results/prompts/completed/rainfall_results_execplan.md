# Build local rainfall adapters and M1 result catalogs


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Maintain Progress, Surprises & Discoveries, Decision Log and Outcomes &
Retrospective. Execution authorized by the user on 2026-09-09 Pacific; completed 2026-09-10 06:50 UTC (2026-09-09 Pacific).

## Purpose / Big Picture


A developer will combine an existing M1 predictor bundle with project Climate
artifacts to inspect probabilities for individual wet events, compare short-
return-interval design storms and calculate inverse rainfall thresholds. Local
queries support event browsing/detail for a later dashboard. This delivers real
local result artifacts, not UI, RQ, a public endpoint or production deployment.

## Progress


- [x] (2026-09-10 05:15 UTC) Review predecessor interface and validation evidence.
- [x] Inspect Climate frequency/event behavior and scaffold contracts/decisions.
- [x] Freeze local schemas and record ADR-0062; R01/R03–R07 execution disposition recorded.
- [x] Operator explicitly approved R02; unavailable sparse ranks and persisted-rank guard implemented.
- [x] Inventory genuine matching Climate inputs; implement bounded event/NOAA and supported-rank CLI adapters.
- [x] Implement all three result families, final manifests and bounded local queries.
- [x] Generate genuine Wallow CLI/NOAA evidence and historical unknown-T diagnostic; focused tests and correctness review pass.
- [x] Record full-suite evidence (8,244 passed, 77 skipped) and passing correctness/QA/security reviews.
- [x] Complete R02 edge acceptance: 62 focused tests, unchanged genuine result hashes and controlled sparse CSV roundtrip.
- [x] Final full suite: 8,273 passed, 77 skipped, 3,110 warnings in 912.43 s; exit 0.
- [x] Synchronize roadmap/specification/board, record outcomes and archive plan.

## Surprises & Discoveries

Genuine matching Wallow Climate artifacts are present locally: 36,524 daily
rows, 10,312 wet events, 100 simulation years and both CLI/NOAA frequency CSVs.
Project DEM/mask/outlet/SBS/K hashes match complete predecessor evidence.
Scalar prototype evaluated 30,936 probabilities in 0.230 seconds; materialized
results avoid repeating that cost for probability sorts. See source_inventory.json.


M1 has complete authentic Wallow acceptance; older partial evidence remains
useful for unavailable-state tests and must not be relabeled. The event helper
is an in-memory API, not a persisted-bundle validator. Climate's frequency CSV
rounds values, emits zero placeholders, and clamps unsupported duration ranks.
The shared rank helper assigns indices across the entire recurrence request,
so subset calls need parity checks. These are concrete adapter contract issues,
not grounds for silently modifying the Climate implementation.

## Decision Log

Operator response “YES”: R02 is approved. Unsupported positive ranks return
unavailable / insufficient_positive_samples; supported rows continue. Preserve
Climate clamping only in the rounded-CSV parity check. ADR-0062 and the canonical
contract record the decision before dependent implementation.

2026-09-09 Pacific initial execution: execute local stage 4 under the user request. Preserve all
existing sources; compatibility plan records additive outputs. R02 sparse-rank
deviation has been presented for explicit approval before dependent code.
Supported CLI ranks use the exact full Climate request context; unsupported
sparse ranks initially refused pending the response, superseded by the approved
R02 disposition above. Reopened tables reevaluate
scalar results because hashes alone cannot prove schema/scientific consistency.


2026-09-10 05:15 UTC: user requested review and next package. Scope is local M1
rainfall/results integration with existing predictor and Climate artifacts.
One watershed, accepted numerical policies and uncertainty rules remain fixed.
The 12-scenario matrix and sample policy require disposition; backend source and
inverse targets should be explicit so browser defaults can wait. No new model,
recovery simulation, NOAA event catalog or automatic upstream rebuild.

## Outcomes & Retrospective


Local implementation and genuine supported-input acceptance exist. Both sources
produce 30,936 event rows, 12 design rows and six inverse rows; event/inverse
hashes agree across sources. Historical unknown T retains 30,936 null
probabilities without dropping rainfall. Focused suite reaches 62 passing tests.
Correctness review closed all six medium findings; QA passes the approved
policy. The controlled R02 bundle preserves three unsupported 15-minute rows
without rainfall/probability, keeps supported other scenarios and reopens
correctly. All genuine source table hashes remain unchanged. All independent correctness, QA and security reviews pass. The final broad
suite passed 8,273 tests with 77 skips in 15:12, including all 62 focused cases.
Local stage 4 is complete; this plan is archived. Production publication, live
invalidation and dashboard delivery remain stages 5–7. Low-priority QA follow-ups
are row-validator readability and diagnostic context.

## Context and Orientation


Repository root is `/workdir/wepppy` (also `/home/workdir/wepppy`). Read root,
NoDb/module and tests AGENTS before relevant work. Baseline is `264b54845`;
existing dirty quality reports are unrelated. The canonical accepted contract is
`wepppy/nodb/mods/postfire_debris_flow/docs/rainfall_results.md`; the parent
specification defines accepted scientific intent, and implementation_roadmap.md
tracks delivery. Closed work packages are historical evidence, never editable
current authority.

`integration.evaluate_m1_scenarios(bundle, scenarios)` consumes explicit
(duration_minutes, rainfall_mm) pairs. It calls the accepted scalar engine and
returns null probabilities when point T/F/S is unavailable. The numerical engine
also has rainfall_threshold(model, duration_minutes, T/F/S keyword arguments,
target_probability) with available/unavailable/nonunique results. Read exact
signatures in `docs/staley2017_engine.md`; preserve numerical exceptions and
inverse semantics. No vectorized reimplementation is justified without evidence.

Version-1 M1 bundles identify source_kind, T/F/S with independent support,
source/prepared/tool hashes, warnings, grid/outlet and assessment provenance.
Load them under a new explicit local file contract before using the dict helper.
A status complete marker means processing completed, not all predictors are
available. Do not follow arbitrary provenance paths or assume upstream freshness.

`wepppy/nodb/core/climate_artifact_export_service.py` owns event parquet and CLI
frequency exports. `ClimateFile.as_dataframe(calc_peak_intensities=True)` already
provides intensities; do not reconstruct them. Canonical parquet columns are
peak_intensity_15, peak_intensity_30 and peak_intensity_60 in mm/hour. The exporter
also retains year, month/day and sim_day_index; define event identity from actual
rows with duplicates/missing dates considered. Wet rows use precipitation >0 in
the frequency precedent, then positive intensity ranks per duration.

The CLI frequency artifact is climate/wepp_cli_pds_mean_metric.csv. NOAA uses
atlas14_intensity_pds_mean_metric.csv under Climate.cli_dir. Both can be absent
after an otherwise successful climate build. Inspect actual metadata and current
readers via repository search; do not assume these files are simple rectangular
CSVs or implement an unvalidated schema from their names. Shared ranking is
`wepppy/all_your_base/stats/stats.py::weibull_series` with method pds. Its complete
request context and Climate year-count/rank fallback matter to numerical parity.

## Plan of Work


Milestone 1 ratifies a concrete local contract. Resolve register R01–R07 before
code changes that depend on them. Recommend 1/2/5/10 years at 15/30/60 minutes,
explicit frequency source, explicit inverse targets and unavailable rows for
unsupported combinations. Decide insufficient positive duration samples and
rank clamping explicitly; do not treat a speculative correction as accepted.
Record any estimator adaptation or unit/policy choice in a parameterization ADR.
Preserve Climate ownership; cross-owner executable changes need separate scope
and the applicable contract-first checkpoint, not a convenience refactor here.

Freeze source schemas/aliases, wet-row and per-duration validity, zero handling,
event identity, date semantics, all output columns/units, unavailable/error
vocabulary, file limits and publication behavior in the current contract. Record
an additive compatibility plan: new local outputs only; no mutation of Climate,
predictor bundle, NoDb or existing generated WEPP run artifacts. Read-only local
adapters do not establish browser defaults, auth, queue or live invalidation.

Inventory genuine existing Climate artifacts read-only, starting with Wallow's
source/evidence and canonical run root `/wc1/runs`. Verify actual overlap in run
identity and provenance; rainfall catalog applied to current predictors is a
scenario set, not necessarily observed postfire events. Include one genuine
NOAA CSV with identifiable station/location metadata if NOAA support is claimed.
Do not trigger downloads or send requests to people. Missing genuine source
evidence is a documented acceptance gap, not permission to label synthetic files
as authentic. Keep small lawful snapshots/hash provenance and controlled tests.

Milestone 2 implements narrow adapters in `rainfall.py` and result
composition in `results.py` under the module, adding collaborators only if useful.
Use current pandas/pyarrow/parquet dependencies and existing CSV parsing precedent.
Expose typed local input/output interfaces fixed in milestone 1. Validate bundle
and source schemas, expected hashes, allowed paths and resource bounds before
processing. Build stable event IDs from snapshot identity and original row ordinal
if that proposal is accepted; preserve ordinal before filtering/sorting. Retain
original climate dates/mode, explicitly marking synthetic labels. Do not force
simulation year labels into wall-clock dates or collapse duplicate dated rows.

Use full-precision intensities and convert once: accumulation_mm = intensity
mm/hour × minutes/60. The CLI design adapter must reproduce the Climate rank
method and full request context, then select requested intervals. Characterize
rounded CSV agreement separately and reject placeholder zeros as design inputs.
Apply the approved inadequate-sample policy with visible reasons; no implicit
NOAA fallback. NOAA design parsing validates units, duration/return-period labels,
metadata, duplicates and finite values; no frequency-to-event-date conversion.
Do not infer all storms are uniform or reconstruct a hyetograph from peaks.

Milestone 3 composes results. Reuse the M1/scalar interfaces for valid rainfall
and available predictors. Missing durations retain unavailable rows without
losing valid durations; missing predictors preserve rainfall rows and diagnostics.
Malformed structural inputs fail under the frozen boundary contract. Inverse
rows preserve available/unavailable/nonunique states and are source-independent.
No interval-to-probability conversion, duration aggregation or probability bounds.
Every result preserves area warnings, predictor/assessment identity, source kind,
canonical units and provenance. A fixed predictor snapshot applies to all events;
never interpret multidecade catalogs as postfire recovery or cumulative forecasts.

Prototype materialization versus on-demand evaluation on a representative catalog
before fixing query storage. One watershed eliminates any need for catchment
cross-products. Provide bounded local event listing/filter/sort/page and event
lookup returning all duration details. No public API or arbitrary user SQL.
Document deterministic ordering, ties, limits and unknown event behavior. Use
fresh caller-owned outputs and a final manifest after table/schema/hash checks;
failed runs leave documented incomplete output or clean staging. Existing results
and sources are preserved. Source mutations must prevent successful completion.

Milestone 4 validates the real workflow and closes. Combine authentic complete
Wallow predictors with genuine climate snapshots and generate inspectable event,
design and inverse artifacts plus example local queries. Also exercise historical
uncertain-T and controlled partial-F/missing-K states without weakening accepted
coverage policies. Verify sample rows against hand calculations and the scalar
engine, not a second copy of implementation logic. Preserve reproduction scripts,
input/output hashes, row counts, time/memory and local query latency evidence.

Tests cover all durations, intensity-to-accumulation conversion, explicit source
selection, missing NOAA, rounded CLI CSV/zero placeholders, insufficient positive
samples, shared-rank request parity, empty/dry catalogs, missing columns, negative/
nonfinite/zero values under policy, duplicate dates, synthetic year labels,
stable event IDs, source hash changes, malformed bundle/table metadata, incomplete
outputs, existing output protection and bounded deterministic queries. Required
file-safety checks use direct files; mocks alone do not prove boundary behavior.

Obtain independent correctness and dedicated security reviews; close medium/high
findings. Update canonical docs, roadmap and package tracker; do not claim stage
5 publication or stage 7 dashboard delivered. Archive only after actual acceptance
outputs/tests/reviews exist, recording any externally blocked evidence honestly.

## Concrete Steps


At repository root run git status --short and git rev-parse HEAD; preserve
unrelated dirty code-quality reports and remain on the current branch. Read the
contracts before runtime edits. Focused tests are
`tests/nodb/mods/test_postfire_debris_flow_rainfall.py` and
`tests/nodb/mods/test_postfire_debris_flow_results.py`. During implementation:

    wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_rainfall.py tests/nodb/mods/test_postfire_debris_flow_results.py --maxfail=1

Before handoff:

    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path wepppy/nodb/mods/postfire_debris_flow
    wctl doc-lint --path docs/work-packages/20260909_staley_rainfall_results
    git diff --check

Run applicable stub/API checks when exports change. Exact reproduction and query commands are recorded in artifacts/validation.md
and artifacts/reproduce.py. Focused/runtime/file-boundary validation is required
for this implementation; the original docs-only exception no longer applies.

## Validation and Acceptance


A developer can inspect every event's per-duration rainfall and conditional M1
probability, requested design scenarios and explicit inverse thresholds from
local artifacts. Results preserve unavailable reasons, source/assessment identity
and warnings. Query IDs/order survive filtering/pagination deterministically.
Authentic input/output evidence and a representative performance budget are
required; avoid arbitrary guessed latency/size gates without a measured baseline.
No derived value is mislabeled as annual probability or NOAA event observation.

## Idempotence and Recovery


Inputs are immutable local snapshots. Fresh result bundles and explicit final
markers prevent replacement of previous results; failed runs are reproducible
in a new directory. Do not modify existing Climate exports, predictor manifests
or source caches. Scope expansions into public transport/NoDb/RQ or upstream
Climate parameterization require explicit contracts and authorization first.

## Artifacts and Notes


Retain predecessor review, decisions/ADR, source inventory, compatibility plan,
reproduction scripts, example results/queries, performance and validation logs,
and independent reviews. Hash identities do not prove current controller state;
report this local limitation in the handoff. The final focused suite passes 62 tests; full-suite disposition is recorded
in artifacts/validation.md.

## Interfaces and Dependencies


Implemented local interfaces: `build_m1_results(inputs, output_dir, *,
frequency_source, return_intervals, durations, target_probabilities)`,
`open_results(path, *, expected_manifest_sha256)`,
`list_events(catalog, *, duration_minutes, min_probability=None,
max_probability=None, year=None, sort="row_ordinal", descending=False,
limit=100, offset=0)` and `get_event(catalog, event_id)`. Types, schemas and
limits are frozen in the current contract. Named query arguments must not become arbitrary SQL.
Reuse accepted M1/scalar libraries, Climate artifacts and existing tabular stack;
no external acquisition or new dependency. M3 schemas remain future work, with
an explicit model field suitable for additive extension rather than speculative
multi-model orchestration.

Revision note: initial scaffold follows completed M1 integration and exposes
Climate rounding, rank/sample and event-identity policies before implementation.

Revision note: execution produced local adapters/results, canonical schemas, ADR,
real source snapshots, query/performance evidence and independent reviews.
R02 was then explicitly approved and implemented with supported-rank checks at
composition and reopening. Final validation passed and the completed plan is archived.

Closure note (2026-09-10 06:50 UTC): all milestones completed within local M1
scope. R02 approval, six correctness-finding closures, genuine/controlled
outputs, reproduction commands, 62 focused passes and 8,273 full-suite passes
are retained with input/output hashes. No remaining package blocker.
