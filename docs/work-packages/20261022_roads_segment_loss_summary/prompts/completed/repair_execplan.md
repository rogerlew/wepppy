# Correct Roads segment loss attribution

This completed ExecPlan follows `docs/prompt_templates/codex_exec_plans.md` and is
executed with its tracker. It is independent of other active packages.

## Purpose / Big Picture

Roads users need one accurate source-profile loss row per completed simulation.
UM1 currently repeats 14 receiving-hillslope vectors across 34 road rows. Correct
this without changing model inputs, water accounting, downloads or baseline.

## Progress

- [x] (2026-10-22) Diagnose table and raw segment PASS differences.
- [x] (2026-10-22) Scaffold package, compatibility plan, contract and ADR.
- [x] (2026-10-22) Two independent contract approvals; checkpoint `bac3042b1`.
- [x] (2026-10-22) Source-qualified producer, README and 76 passing focused tests.
- [x] (2026-10-22) All 34 UM1 rows, live Chromium/downloads and canonical archive/restore pass.
- [x] (2026-10-22) Full suite 11,085 passed/126 skipped; both final reviews pass; implementation `a8380cbbd`, package closed.

## Surprises & Discoveries

The bad target-first join is explicitly specified and covered by old tests.
This requires a reviewed normative correction, not merely swapping join order.
Independent review caught eager facade climate access for empty manifests;
a lazy calendar provider and real empty-facade regressions resolve it.
H.loss.parquet contains particle classes, not profile mass totals. Native H.pass
already contains all source segment IDs in addition to canonical routing targets.

## Decision Log

2026-10-22 / Roger: authorize scaffolding and execution after source-attribution
assessment; existing task-scoped commit permission persists.
2026-10-22 / Codex: retain complete source-profile diagnostics and distinguish
unsupported road-only/buffer-only aliases rather than mislabel MOFE totals.
Use native interchange and existing DuckDB aggregation, no model rerun.

## Outcomes & Retrospective

Implementation and independent correctness review pass. All 34 isolated UM1
rows match original PASS/WAT; aggregate and original artifacts are unchanged.
Live consumer and archive/restore evidence pass. Full regression: 11,085 passed,
126 skipped. All local acceptance gates are complete. Contract checkpoint
`bac3042b1` precedes implementation `a8380cbbd`. Original UM1 and native repo
remain unchanged; no deployment claim.

The real facade empty-state probe caught a dependency helper-only tests missed.
Future artifact work should keep that boundary in acceptance tests. The long
broad gate completed without exclusions; a per-process Chromium path correction
avoided the previously documented unrelated environment failure.

## Context and Orientation

Controller: `wepppy/nodb/mods/roads/roads.py`, method
`_build_roads_segment_loss_summary_parquet`. Input manifest under segments/;
PASS/WAT under output/interchange/. Current SQL repeats receiving hillslope loss.
Canonical decision: `docs/schemas/roads-segment-loss-summary-contract.md` and
ADR-0103. Use existing native geometry and DuckDB, optionally a bounded collaborator
under Roads, preserving facade API. Tests: tests/nodb/mods/test_roads_controller.py
and a dedicated source-summary test module. Native repo is read-only for this task.

## Plan of Work

Milestone 1 obtains two independent read-only contract reviews, dispositions all
high/medium findings and commits canonical amendments plus checkpoint as ancestor.
Milestone 2 replaces attribution, validates required source/calendar/area states,
publishes atomically and retains readable provenance. Add unmocked writer tests
before replacing wrong legacy join assertions. Missing data is never zero-filled.
Milestone 3 uses the previously restored isolated UM1 project (canonical archive
workflow) to regenerate through the actual controller; verify every row against
independent PASS sums, native WAT areas and untouched aggregate/source hashes.
Exercise existing browser/download CSV and canonical archive/restore with actual
filesystem behavior and local runtime identity. Keep source original UM1 unchanged.
Milestone 4 completes focused wctl tests, broad `wctl run-pytest tests --maxfail=1`,
stub/doc gates as applicable and independent correctness/security review. Record
exact environmental failures rather than hiding them. Commit task files only,
update tracker/PROJECT_TRACKER and close/move plan using canonical tooling.

## Concrete Steps

Use `/workdir/wepppy`, existing branch, existing local Docker stack. Read root,
NoDb and tests instructions. Run focused source-summary and Roads controller tests
through wctl. For known local browser-path environment use existing installed
Chromium under `/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers`.
Do not alter unrelated environment defaults. Lint changed docs with wctl doc-lint.

## Validation and Acceptance

Two roads sharing a target retain different own-source exports. Complete no-event
years lower annual averages correctly. Full OFE area normalizes MOFE; remainder
is labeled and unsupported aliases NULL. Existing columns/types remain readable
through Parquet and on-demand CSV; empty manifests produce a typed empty table.
Duplicate/missing/invalid source or alias destinations fail without replacing old
summary or certifying ready resources. Source drift is explicit. UM1 34 rows sum
to roughly 4,810.818 kg/year and dominant source roughly 4,071.013 kg/year.
No changes to totalwatsed, canonical PASS or baseline hashes. Archive/restore
preserves generated summary bytes/modes and source lineage. No deployment claim.

## Idempotence and Recovery

Rebuild from original native outputs, never target-loss or old summary. Atomic
replacement preserves old complete summary on failure; existing log retains error.
Rollback code and regenerate only with explicit operator scope. No source deletion.

## Artifacts and Notes

Retain checkpoint/reviews, test summaries, UM1 source/download/archive hashes and
parsed comparisons in artifacts/. Do not edit prior closed water-repair package.

## Interfaces and Dependencies

Keep controller method and summary path stable. Reuse DuckDB/PyArrow and native
geometry API; no added dependency, native release, queue edge or endpoint.
