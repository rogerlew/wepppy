# Scale continuous watershed timeout

Maintain under docs/prompt_templates/codex_exec_plans.md.

## Purpose and context

Prevent legitimate large/long watershed jobs being killed by the fixed 12-hour
RQ allowance. RQ pipeline functions in wepppy/rq/wepp_rq_pipeline.py enqueue
all stages with a shared timeout; only continuous watershed leaf jobs change.
No-prep executes checked-out native inputs, so saved controller counts may differ.

## Progress

- [x] Operator approved empirical years × hillslopes budget.
- [x] Commit independently reviewed contract ancestor (`728965382`).
- [x] Implement policy, metadata and four enqueue paths; add regression tests.
- [ ] Verify real serialized RQ jobs/job tree, focused/broad tests and reviews.
- [ ] Update tracker, close plan and commit; deployment separate.

## Surprises & Discoveries

Production assessment found current NoDb sizes differing from consumed input
in two runs. No-prep must use the native run file, without regenerating it.
Correctness review exposed truncated-file acceptance; bounded hillslope-block
and final-record checks close it without building a general native parser.

## Decision Log

2026-09-28: use exact integer ceiling of years×hills/72000 hours, minimum 12,
with caller timeout preserved if larger. Record inputs as additive child metadata.
Read prepared workload only for no-prep; validate before any child enqueue.
Do not bundle the separately identified subprocess cleanup issue.
2026-09-28: validation targets real RQ graphs and immutable native inputs rather
than rerunning the unchanged model; these are the artifacts WRT-01 changes.

## Plan of Work

First amend contract/ADR and collect two independent reviews before committing.
Then add a small policy module for bounded integral workload validation and
legacy/modern prepared-run parsing. Call it once at applicable pipeline entry;
pass timeout/metadata only to watershed leaf enqueue, merging fork lineage.
Extend graph tests for all four entry points and exact integer rounding, and
exercise real RQ serialization against disposable Redis/job trees.

## Validation and acceptance

From repository root use wctl run-pytest tests/rq/test_wepp_rq_pipeline.py and
new targeted policy tests; check-rq-graph/catalog and stub checks as applicable.
Run wctl run-pytest tests --maxfail=1 before handoff. Expected output includes
97,200 seconds for 1,000 years × 1,908 hillslopes, immutable no-prep input hashes and
unchanged unrelated-stage timeouts/dependencies. Inspect real saved job metadata,
job_info tree and unchanged native input bytes. The observable change is the
serialized RQ allowance; no model code or input writer changed, so a new native
simulation adds no timeout-policy evidence and is not required. No production reruns.

## Compatibility and recovery

No new libraries or services. Tests use temporary paths and disposable development
run/queue data. Preserve existing RQ errors and absent optional state. Reverting
code affects new enqueue only; do not modify already stored job timeouts.

## Outcomes & Retrospective

Implemented and wired. Focused tests: 98 passed. Four real Redis graphs saved
27-hour budgets with unchanged source hashes, fork callbacks and child trees;
41 disposable job records removed. Final reviews approved. Full suite pending.
