# Add observed streamflow to flow-duration plots

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

A project with uploaded daily streamflow can enable Show observed streamflow on
both hillslope and channel-outlet flow-duration plots. The curve uses the full
observed record and appears once alongside all simulated scenarios.

## Progress

- [x] (2026-10-14 UTC) Inspect upload normalization and current daily graph pipeline.
- [x] (2026-10-14 UTC) Scaffold package, canonical amendment and ADR.
- [ ] Obtain two independent contract reviews and commit checkpoint.
- [ ] Add tests, bootstrap adapter, observed series and checkbox.
- [ ] Run focused/full gates, browser artifact verification and final review.
- [ ] Record outcomes and update tracker/board.

## Surprises & Discoveries

Observed normalizes Julian to zero-based, while the graph uses one-based Julian.
Observed input flow is Streamflow (mm); model-fit output is unnecessary. Observed
model-fit uses maximum Area from totalwatsed3 for depth/discharge conversion.

## Decision Log

2026-10-14, Codex implementing user request: use raw normalized Observed CSV,
not comparison outputs, so upload alone is sufficient. Include narrow string-valued
rows in authorized bootstrap to avoid new routes, catalog activation or CSV parser
dependencies. Resolve canonical Omni children to their parent project's observation
and area; never substitute a parent simulation for child model outputs.

2026-10-14: use the full measured record without simulated warm-up; measurements
have no model initialization period. Keep independent distributions instead of
silently intersecting dates. Default overlay off preserves existing graph behavior.

## Outcomes & Retrospective

Pending implementation and validation. No production deployment is requested.

## Context and Orientation

`wepppy/weppcloud/routes/gl_dashboard_flow_duration.py` builds authorized dashboard
metadata. `wepppy/nodb/mods/observed/observed.py::parse_textdata` writes
observed/observed.csv with Year, Month, Day, Julian and Streamflow (mm).
`wepppy/weppcloud/static/js/gl-dashboard/graphs/flow-duration-data.js` validates
and ranks daily rows. Controls live beside it; graphs/controller.js wires them.
`wepppy/weppcloud/static/js/gl-dashboard.js` passes bootstrap to graph loaders.

## Plan of Work

Milestone 1: amend the canonical flow-duration contract and ADR, record starting
revision and authority, obtain independent read-only reviews, disposition findings
and commit the documentation checkpoint before editing implementation.

Milestone 2: write regression tests first. Add a read-only observed metadata
adapter using csv.DictReader and DuckDB over owned totalwatsed3.parquet. Keep flow
strings (including NaN/Infinity), normalize empty flow to null and Julian +1.
Enforce 16 MiB read and 100,000-row bounds without truncation. Expose absent/available/unavailable states and narrow rows only. Add optional
includeObserved state and a labeled native checkbox when observations are present;
show unavailable explanation when present but unusable. Append one stable Observed
series using existing hillslope unit conversion and excludedYears=0. Preserve
simulated source/year settings and independent errors. Document full-record policy.

Milestone 3: run direct filesystem, data/controls/renderer tests and a local browser
harness with actual modules. Assert [4,2,2,0] mm at 86,400,000 m² gives [4,2,2,0]
m³/s at [20,40,60,80] percent. Run repository broad gates, record limitations, obtain
final independent correctness and dedicated security reviews and update documentation and tracker.

## Concrete Steps

From /home/workdir/wepppy run wctl run-pytest
 tests/weppcloud/routes/test_gl_dashboard_flow_duration.py, wctl run-npm test --
 --runInBand flow-duration, wctl run-npm lint, wctl run-npm test -- --runInBand,
 and wctl run-pytest tests --maxfail=1. Use wctl doc-lint --path for changed docs.
Retain concise command results and browser evidence in artifacts/validation.md.

## Validation and Acceptance

Absent uploads preserve normal simulated graphs. Empty uploads, no streamflow
column, unavailable area, malformed dates/flows and symlinks have explicit statuses.
Valid values including ties/zero render with original dates and correct coverage.
One observed curve survives both source choices and simulation warm-up selection;
unchecked means no observed curve. Roads does not offer observed data. A canonical
Omni child uses parent observations, while model curves retain exact ownership.
A browser must show checkbox operation, legend and plotted values for both sources.

## Idempotence and Recovery

All artifact reads are read-only. Re-running tests uses temporary files. Rollback
is removal of additive code and docs; no migration or run repair is necessary.
Reload the dashboard after changing uploads or model outputs.

## Artifacts and Notes

Contract checkpoint and review evidence are under artifacts/. Starting revision:
ebaed5a23cc9132424db90a38241f1e9f090fafc.

## Interfaces and Dependencies

Bootstrap flowDuration.observed adds present, available, reason, and records.
Records contain year/month/day/julian, flow string/null and area string. Existing
rankDailyFlows performs validation and converts depth to m³/s. State gains
includeObserved=false; native checkbox delegates updates to existing setValue.
No external dependency, schema migration, or transport is introduced.
