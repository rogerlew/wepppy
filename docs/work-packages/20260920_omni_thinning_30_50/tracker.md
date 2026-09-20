# Tracker: Omni thinning 30/50

Started: 2026-09-20 19:32 UTC. Phase: closed, locally validated code delivery.

## Progress

- [x] Scope and compatibility plan recorded; user authorized execution.
- [x] Independent contract reviews and ancestor commit `e56d610e1`.
- [x] Eight assets, five catalogs, UI and documentation.
- [x] Generated-input evidence, tests, correctness review and closeout.

## Decisions

Retain frozen legacy assets and add eight files; template refactoring is unnecessary
for two new canopy values. Preserve 40% default explicitly. No deployment requested.

## Evidence

Starting revision: `b72fd53f635c7a03b3b66fcf891f796e02fe33e5`.
Contract ancestor: `e56d610e1`. Both contract reviews approved.
Focused management/MOFE/archive tests: 188 passed. Frontend: 112 suites, 911 tests
passed; lint passed. Browse/download: 38 passed. Full Python suite running.
Host bundle build lacked jinja2; canonical container build used instead.
CSV export regenerated with canonical script; only eight new rows retained to
avoid unrelated historical export drift. Legacy CSV uses CRLF; retain it.

## Implementation milestone

2026-09-20 19:45 UTC: implementation committed as `2eefbec19`; independent
correctness review approved with zero findings. All focused/frontend/docs gates
pass. Full suite has passed the existing slow disturbed simulation matrix and
is progressing. New management files intentionally preserve source whitespace;
CSV additions preserve its existing CRLF convention. No unrelated dirty files
were included in either commit.

## Broad-suite continuation

2026-09-20 20:01 UTC: full suite stopped at the existing disturbed-class snapshot
after 6,677 passed and 92 skipped (19m20s). Its expected list omitted exactly the
eight newly approved variants. Updated only that snapshot and count (39 to 47);
independent reviewer confirmed correctness. Collected the full 9,267-node order
and resumed from the failed file: 2,499 tests across 223 files. Initial and
continuation logs are separate; already-passed tests were not repeated because
only the failed test expectation changed.

Continuation selection discovery: explicit filenames opt the WBT integration
module into native-binary execution; that exploratory run failed its existing
diagnostics sidecar check after 457 passes. This is unrelated to thinning and
would be skipped in the original broad invocation. Replaced remaining subdirectory
filenames with directory arguments to preserve broad-suite opt-in semantics.
No WBT code, skip policy or environment flags changed. Retained both selection
manifests and the exploratory failure summary.

## Closeout — 2026-09-20 20:06 UTC

Continuation passed: 2,492 tests, 7 skipped. Combined unique coverage with the
initial run: 9,169 passed, 99 skipped (including one collection skip). This is
not a claim of one uninterrupted green full-suite invocation. The initial
snapshot failure was corrected; no production changes followed focused review.
All 9,267 collected tests were covered, with the original broad opt-in behavior.
Frontend: 112 suites / 911 tests passed; lint passed. Focused artifacts: 188
passed; browse/download: 38 passed. Documentation lint and broad-exception gate
pass. Quality observability completed (radon unavailable; nonblocking telemetry).

Independent reviews: two contract approvals, final correctness approval and
snapshot follow-up approval, no open findings. Contract ancestor `e56d610e1`,
implementation `2eefbec19`; final snapshot/closeout commit follows.

Highest supported claim: implemented and locally validated. No deployment or
project repair performed. Operator retains live browser/download acceptance and
production-equivalent scenario execution before deployment. Fresh model results
were not generated. Durable decision: canonical thinning contract, Choice and
parameter contract / Compatibility, states and errors; ADR-0071.

Concrete tooling friction: explicit-file pytest continuation activates opt-in
native WBT tests unlike the original directory invocation. Preserve directory
selection when resuming a broad run; a canonical resume helper could avoid this.
