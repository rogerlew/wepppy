# Correct MOFE ET and Deep-Percolation Consumer Aggregation


## Purpose / Big Picture


Users should see the same area-weighted evapotranspiration (ET) and deep
percolation (Dp) in hillslope reports, event maps, and feature exports. An
overland flow element (OFE) is one modeled segment of a hillslope; MOFE means
multiple OFEs on that hill. Raw water-file depths belong to each OFE, not to
the complete hill. This plan fixes three downstream consumers without changing
the WEPP simulation or its raw outputs.

The operator requested execution on 2026-10-20 after the scaffold turn.
M1-M5 are now authorized, including the necessary local contract checkpoint.
The package stays open until later implementation and validation are complete.
The mathematical intent is a correction, not a faithful preservation of the
known wrong sums. No surrogate production algorithm is planned.

## Progress


- [x] (2026-10-20 18:45 UTC) M0: record audit, scope, acceptance, and package scaffold.
- [x] (2026-10-20 18:45 UTC) M0: remove disabled raw balance/map from `new_report.Rmd`.
- [x] (2026-10-20 18:50 UTC) M0: documentation lint and link/readback checks pass;
  executable R statements are identical before and after inactive-only deletion.
- [ ] M1: canonical contracts, ADR, input/state matrices, independent reviews,
  committed contract checkpoint, and regression fixtures.
- [ ] M2: correct native report ET/Dp and cache compatibility.
- [ ] M3: correct both dashboard event ET queries.
- [ ] M4: correct Features Export ET/Dp spatial reduction.
- [ ] M5: fresh generated outputs, quality gates, independent correctness review,
  release/cache recovery handoff, and documentation.

## Surprises & Discoveries


Native report and Python facade tests currently enshrine unweighted sums.
Features Export uses a generic terminal-OFE reducer before temporal aggregation;
its runoff-oriented test is insufficient for local fluxes. TotalWatSed and the
daily Python loader already produce correct ET/Dp area averages and are
regression controls. The default R report's raw balance was disabled, not
formally removed across every legacy workflow.

The baseline two-OFE counterexample returned report ET/Dp 8/12 mm and export
6/8 mm, while the correct values are 5/7 mm. Dashboard SQL also implies ET 8 mm.
These prior observations need retained repeatable evidence during execution.

## Decision Log


2026-10-20 18:45 UTC: The operator requested scaffolding fixes 1-3 and deleting
the disabled raw balance in `new_report.Rmd`. Preserve the old standalone R
template and shared helper; their deletion was not requested.

2026-10-20 18:45 UTC: Weight local ET components and Dp by their own OFE area.
Reject depth sums, count-based averages, cumulative upstream areas, and
terminal-only selection because they cannot conserve the represented volumes.
Use field-specific aggregation so runoff/lateral routing contracts are retained.

2026-10-20 18:45 UTC: Preserve existing annual selection/divisor behavior in
this spatial correction. Record any independently discovered temporal defect
for separate disposition rather than silently expanding scope.

## Outcomes & Retrospective


Scaffold and disabled R cleanup only; four package documents and the project
tracker pass scoped documentation lint. Exact extracted executable R statements
match HEAD after removal of inactive chunks; no R rendering or broad tests were
needed for this comment-only cleanup. No ET/Dp consumer fix, candidate native
release, deployment, or existing-project repair has occurred. Update this
section at each milestone with the highest evidence-supported status.

## Context and Orientation


WEPPpy is `/workdir/wepppy`; native code is `/workdir/wepppyo3`. Read each
repository's `AGENTS.md`, plus applicable WEPPcloud, dashboard, NoDb, and tests
guidance before editing implementation. The root package directory is
`docs/work-packages/20261020_mofe_et_dp_area_weighting/`.

Raw `H*.wat.dat` is parsed by native `wepp_interchange/src/hill_wat.rs` into
`H.wat.parquet`, retaining OFE rows and Area in m². Ep, Es, Er and Dp are mm.
Native `totalwatsed.rs` converts them to m³ using depth * Area / 1000, sums, and
derives ET/Percolation mm by dividing by total area and multiplying by 1000.
WEPPpy `wepppy/wepp/interchange/hill_wat_interchange.py` offers an equivalent
daily per-hill reduction through `load_hill_wat_dataframe`.

The separate native `wepp_interchange/src/hillslope_watbal.rs` currently sums
depths by translated hillslope and water year. WEPPpy
`wepppy/wepp/reports/hillslope_watbal.py` caches those rows and feeds
`report_wepp_avg_annual_watbal` in
`wepppy/weppcloud/routes/nodb_api/wepp_bp.py`.

Dashboard `wepppy/weppcloud/static/js/gl-dashboard/data/wepp-data.js` builds
unweighted ET queries in `refreshWeppEventData` and `loadBaseWeppEventData`.
Features Export `wepppy/nodb/mods/features_export/temporal_wide_materializer.py`
selects terminal OFEs before reducing fields; `carrier_layer_materializer.py`
and `service.py` use it for tabular and geospatial products.

## Plan of Work


### M0: scaffold and inactive R cleanup


Create package, tracker, baseline audit note, and this plan; add a backlog entry
to `PROJECT_TRACKER.md`. Delete only the disabled hillslope raw-water-balance
calculation, its map chunk, and associated comments from
`weppcloudR/templates/scripts/users/chinmay/new_report.Rmd`. Confirm executable
R content is identical before and after. This does not change the default
report's already-visible output.

### M1: contracts and independent acceptance oracle


Before production changes, classify the discrepancies against current canonical
contracts. Read `docs/standards/contract-first-change-standard.md` and prepare
`artifacts/20261020_contract_decision.md` (use actual execution date if later).
Record the starting revisions, normative delta, operator scope, compatibility,
security triage, and test matrix. Create a current contract such as
`docs/schemas/hillslope-water-aggregation-contract.md` if no existing canonical
contract covers this behavior; reconcile it with the Features Export
specification and existing UI/report contracts. Create an ADR in `docs/adrs/`
for the changed aggregation formulas with decision provenance.

Obtain the two independent read-only reviews and committed ancestor checkpoint
required by that standard before UI-coupled implementation. The execution request authorizes the necessary local checkpoint commit, but
does not authorize production deployment or waive the checkpoint. Record the
checkpoint revision and any required approval in the tracker.

The contract must say: for each hill/day, divide sum(area * depth) by sum(area).
For ET use Ep+Es+Er, also preserving each component's weighted depth. Then
aggregate daily results over time. Do not sum area across days as a denominator
for annual totals. Preserve single-OFE identity, labels, units, and unrelated
numeric fields. If multiple native IDs translate to one reported hillslope,
combine their volumes and areas consistently before producing that feature's
depth. Specify how the advertised export ET field is derived from Ep/Es/Er,
without changing the raw WAT schema.

Separate input combinations from runtime states. Cover unequal/equal area,
single/multiple OFEs and hillslopes, dates and water years, merged translator
IDs, baseline/Roads and applicable AgFields data, current/legacy columns,
duplicates, missing/null/nonfinite/nonpositive area, and absent/empty/populated
source plus cold/warm/stale/historical cache states. Resolve each error/absence
policy against existing contracts before implementation; do not invent silent
zero or unweighted fallbacks.

Use the independent fixture: one day, areas 250/750 m²; Ep 1/4, Es .5/1,
Er .5/1, Dp 4/8 mm. Expected Ep 3.25, Es .875, Er .875, ET 5, Dp 7 mm.
Repeat on a second day: annual contributions ET 10 and Dp 14 mm. Add a second
hill with a different total area/depth to prove watershed weighting and subset
selection. Preserve reference results from TotalWatSed and the daily loader.
Add regression tests at the actual consumer boundaries; current parity
expectations must not replace this mathematical oracle.

### M2: native report and compatible cache generation


In native `hillslope_watbal.rs::produce`, replace only ET-component and Dp
spatial summation with volume/area accounting consistent with M1. Preserve the
bounded native implementation, mapping API, output names, unrelated metrics,
and existing time conventions. Update native and Python report tests that
currently assert erroneous sums.

In WEPPpy `hillslope_watbal.py`, verify downstream watershed weighting uses the
corrected hill depths and each hill's area exactly once. Version cache semantics
through existing report freshness mechanisms; explicitly cover old cache with
source present and source absent. Do not serve a historical wrong cache as a
verified corrected result or remove unrelated caches. Record recovery policy.
Read fresh native Parquet and HTML/CSV report output from the normal consumer.

### M3: dashboard event ET, including comparison baseline


Change ET expressions in both named functions in `wepp-data.js` to weight
Ep/Es/Er by wat.Area and divide by the selected hill/day's summed area, using
the M1 absent/invalid-area contract. Retain date/scope filters, joins, comparison
direction, units, and non-ET event modes. Test actual generated SQL against
heterogeneous OFE rows, not just mocked already-aggregated JSON. Confirm selected
and baseline event values and their displayed difference through the browser.

### M4: field-specific Features Export reduction


Replace terminal-only treatment of Ep/Es/Er/Dp with per-day, per-feature weighted
reduction before yearly sums or annual averages. Keep terminal routing
semantics for measures/layers that require them; do not globally remove
`_collapse_terminal_ofe_rows`. Trace selected-column resolution so Area and
OFE/date identifiers are available to aggregation even when not exported.
Implement the ratified ET derivation/catalog contract.

Update temporal materializer, service/catalog tests, and existing cache identity
as necessary. Exercise event, yearly, annual-average, wide and long tabular
layouts and at least one geospatial output. All exporter backends share a
corrected materialized table; verify schema/units and unchanged identity/geometry
with fresh serialized output. Record where broader format coverage is supplied
by existing tests rather than claiming every format was manually exercised.

### M5: release, generated artifacts, and reviewed handoff


Follow wepppyo3 build/release guidance to build the candidate and verify the
exact module loaded by the WEPPpy development stack. Record source revisions,
module path/hash and release provenance; a host-only source fix is not a wired
application fix. Do not introduce a deployment mechanism.

Use an actual MOFE project under `/wc1/runs/` through an isolated development
copy, preserving its source/interchange evidence. Record normal report/export
requests, fresh output readbacks, dashboard current/baseline values, and cold,
warm, and stale cache results. Compare against an independent daily volume/area
oracle and unchanged TotalWatSed/daily-loader controls.

Run required quality gates, update current user/operator/developer docs, and
obtain an independent correctness review using
`docs/prompt_templates/correctness_review_template.md`. Record artifact
observability/archive coverage or explicit applicable exclusions per current
standards. Close medium/high findings. Finish with a coordinated native/Python
release and narrowly scoped cache regeneration handoff. Mark deployment,
historical-project repair, and incident resolution separately; they require
their own authorization and evidence.

## Concrete Steps


For the scaffold, run from `/workdir/wepppy`:

    wctl doc-lint --path docs/work-packages/20261020_mofe_et_dp_area_weighting
    wctl doc-lint --path PROJECT_TRACKER.md
    git diff --check
    git diff -- weppcloudR/templates/scripts/users/chinmay/new_report.Rmd

Preview `uk2us` changes for the new Markdown files and check local links.
Verify that the R diff contains only inactive comments/chunks and that
`calc_watbal`, `Hwatbal_spdf`, and `gethillwatfiles` no longer occur in that
template. No simulation, R rendering, or broad suite is needed for this
inactive-only deletion.

For implementation, read the wepppy-tester skill and subsystem guidance first.
From `/workdir/wepppyo3`, use:

    cargo test -p wepp_interchange
    python3 -m pytest tests/wepp_interchange/test_hillslope_watbal.py tests/wepp_interchange/test_totalwatsed3.py

Use the repository's explicit native test-binary override when validating a
fresh candidate and record it; also verify the release import consumed by
WEPPpy. From `/workdir/wepppy`, use:

    wctl run-pytest tests/wepp/reports/test_hillslope_watbal.py
    wctl run-pytest tests/nodb/mods/test_features_export_service.py
    wctl run-pytest tests/wepp/interchange
    wctl run-npm test
    wctl run-npm lint
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master

Add the actual new focused test paths and browser/project commands as milestones
land. Passing existing tests alone is insufficient: the heterogeneous fixture
must fail against the baseline and pass through the real changed boundary.
Record environment blockers separately rather than treating a skipped gate
as success.

## Validation and Acceptance


The one-day fixture must yield ET 5 and Dp 7 mm through native report, daily
dashboard query, and all three export temporal modes. The dashboard only
exposes ET; do not add a Dp overlay. Exported components must sum to 5.
Two days must contribute 10/14 mm before the existing annual averaging policy.
Single-OFE controls and unrelated routed fields remain unchanged. Partitioning
an OFE into equal-state subareas must not change ET/Dp results.

Read the report's generated summary and HTML/CSV, executed query responses,
and serialized feature exports, with supported legacy and stale-cache cases.
Check that TotalWatSed component volumes remain m³ and derived depths remain
mm. Validate the runtime state matrix without mocks replacing the failing
writer/query/materialization boundary. Document actual-project evidence and
all limits of validation.

## Idempotence and Recovery


Scaffold creation and inactive R removal are reversible source edits. Preserve
unrelated dirty files and the current branch. For implementation evidence, use
isolated fixture/project outputs; never regenerate an original project in place
just to compare before/after values. Reuse existing atomic publication and
cache mechanisms. On failure retain prior published artifacts and visible
failure evidence according to the current contract. Rollback pairs compatible
native/Python code and cache semantics; never relabel old numerical results as
corrected.

## Artifacts and Notes


`notes/consumer-audit.md` records the prior observations and affected consumers.
Create dated contract/review artifacts and a compact fixture/real-project
evidence manifest during implementation. Retain semantic expected/actual
values, candidate hashes, commands, and exact consumed/generated paths.
Do not retain secrets or claim that transient session output is a permanent
validation artifact.

## Interfaces and Dependencies


Keep `hillslope_watbal_to_parquet`, `hillslope_watbal_wepp_ids`,
`HillslopeWatbalReport`, `load_hill_wat_dataframe`, and `run_totalwatsed3`
signatures stable. Keep existing SQL query transport and Features Export
selection/format APIs. Use owned Rust, DuckDB, pandas/PyArrow, existing report
caches, and existing frontend tooling. No new dependency or infrastructure
is permitted by this plan.

Revision note: initial scaffold on 2026-10-20 18:45 UTC; separates completed
inactive R cleanup from planned, contract-gated aggregation remediation.
Validated scaffold and recorded inactive-only R readback at 18:50 UTC.
