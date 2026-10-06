# Apply WRT-01 budgets to Omni scenario and contrast leaves

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`. The sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must
remain current.

## Purpose / Big Picture

Large continuous Omni scenario and contrast jobs currently receive a fixed
12-hour RQ allowance even though their watershed workload has an accepted
years-by-hillslopes budget. After this change, a newly enqueued Omni scenario or
contrast leaf will carry the same finite WRT-01 timeout and metadata as an
ordinary continuous watershed leaf. Operators can verify this directly from the
serialized RQ job. The package does not deploy or retry production work.

## Progress

- [x] (2026-10-06 16:42 UTC) Diagnose production failure and current source gap.
- [x] (2026-10-06 16:42 UTC) Draft package, WRT-02 contract checkpoint, and ADR
  scope amendment.
- [ ] Create the standalone checkpoint ancestor commit. Two independent reviews
  returned five medium findings in total; all were dispositioned and both
  reviewers approved the amended checkpoint at 2026-10-06 16:54 UTC.
- [ ] Implement the smallest leaf-enqueue change and focused regressions.
- [ ] Refresh/check RQ catalog and run focused and full validation.
- [ ] Obtain independent final correctness and security review.
- [ ] Close package and archive this plan with exact evidence and residual work.

## Surprises & Discoveries

- The September WRT-01 implementation changes only ordinary WEPP pipeline
  watershed children. Omni calls `wepp.run_watershed()` inside a scenario or
  contrast leaf, so the production failure was outside that enqueue surface.
- Production job `8f8d9f2a-9dd2-4fbe-970b-6898bfccd51a` ran from 2026-10-01
  16:13:10 UTC until 2026-10-02 04:13:10 UTC and then raised the exact
  43,200-second RQ timeout.
- The failed prepared workload used 500 years and 1,908 hillslopes. WRT-01 would
  provide 50,400 seconds (14 hours), but total scenario overhead is an acceptance
  risk because WRT-01 was fitted to watershed runtime.

## Decision Log

- **2026-10-06 16:42 UTC**: Reuse WRT-01 unchanged and apply it only to
  `run_omni_scenario_rq` and `run_omni_contrast_rq` child enqueue calls. This
  exactly addresses the reported fixed-timeout leaf while avoiding an
  unevidenced Omni-specific coefficient or a global timeout increase.
- **2026-10-06 16:42 UTC**: Compute the options once after the coordinator has
  established that leaves will be enqueued and before the first leaf enqueue.
  Empty and fully skipped workflows therefore retain their current behavior,
  while malformed required continuous workload cannot leave a partial leaf
  graph.

## Outcomes & Retrospective

Implementation and validation are pending.

## Context and Orientation

`wepppy/rq/watershed_timeout.py` owns WRT-01 arithmetic and returns an RQ option
dictionary containing `timeout` and, for continuous mode, `meta`. Ordinary WEPP
pipelines consume this dictionary in `wepppy/rq/wepp_rq_pipeline.py`.
`wepppy/rq/omni_rq.py` coordinates scenario and contrast workflows on the batch
queue. `run_omni_scenarios_rq` enqueues `run_omni_scenario_rq` children;
`run_omni_contrasts_rq` enqueues `run_omni_contrast_rq` children. The children
perform watershed execution internally, but both enqueue sites currently pass
the fixed module `TIMEOUT`.

WRT-02 does not change dependency relationships. Scenario compile/finalize and
contrast finalize children retain `TIMEOUT`. Coordinator jobs submitted by
rq-engine routes retain their existing timeout. Existing queued or failed jobs
are immutable; only new child serialization changes.

## Plan of Work

First, complete the contract-first checkpoint. Amend
`docs/schemas/wepp-run-input-contract.md` and ADR-0076 to name Omni scenario and
contrast leaves, record exact valid/invalid state behavior in the checkpoint,
obtain two independent reviews, and commit only these governance/package files.

Second, add a small helper in `wepppy/rq/omni_rq.py` that obtains the base
project's `Wepp` and `Climate` controllers and delegates to
`watershed_timeout_options(..., TIMEOUT)`. Call it once in each coordinator only
when at least one corresponding leaf will be submitted. Calculate before an
affected child id is allocated or written/saved in parent metadata, before the
RQ Redis connection, and before any affected enqueue. For contrasts, calculate
immediately after the `not run_ids` return and before
`_rerun_hillslopes_for_contrast_scenarios`. Earlier existing NoDb
freshness/cleanup updates remain outside this admission boundary. Expand the
returned dictionary into every scenario or contrast leaf enqueue. Do not apply
it to compile/finalize jobs and do not change dependency arguments.

Third, extend `tests/rq/test_omni_rq.py`. Prove a continuous workload above the
floor serializes the calculated timeout and exact metadata on every applicable
leaf. Prove single-storm leaves retain only `TIMEOUT`. Prove empty/skipped paths
do not read workload. Prove invalid required workload fails before any affected
leaf enqueue. Retain existing assertions for dependency ordering and fixed
compile/finalizer timeouts.

Fourth, update the RQ README and regenerate/check the dependency catalog because
an enqueue site changed. Run focused tests, graph validation, changed-file broad
exception enforcement, the full Python suite, doc lint, and diff checks. Capture
results in the plan/tracker and independent final review artifacts.

Fifth, create a package-local validation harness that uses a uniquely named real
Redis queue, serializes disposable scenario and contrast graphs without allowing
workers to consume them, fetches every job back, and inspects timeout, metadata,
dependencies, and the `get_wepppy_rq_job_info` tree. The harness must delete only
its own jobs and queue in a `finally` block, verify cleanup, and retain sanitized
JSON evidence without credentials or production session metadata.

Finally, close the package as implemented and locally validated only. Move this
plan to `prompts/completed/`, update `PROJECT_TRACKER.md`, and state that wepp1
deployment and production rerun remain separate operator work.

## Concrete Steps

All commands run from `/home/workdir/wepppy`.

1. Review and commit the checkpoint:

       wctl doc-lint --path docs/work-packages/20261006_omni_dynamic_timeout
       git diff --check
       git commit <checkpoint files> -m "Approve Omni dynamic timeout contract"

2. Implement and run focused validation:

       wctl run-pytest tests/rq/test_watershed_timeout.py tests/rq/test_omni_rq.py
       wctl check-rq-graph
       python tools/check_broad_exceptions.py --enforce-changed --base-ref HEAD^
       wctl run-python docs/work-packages/20261006_omni_dynamic_timeout/artifacts/verify_live_rq.py

3. Run broad validation:

       wctl run-pytest tests --maxfail=1
       wctl doc-lint --path docs/work-packages/20261006_omni_dynamic_timeout
       wctl doc-lint --path docs/schemas/wepp-run-input-contract.md
       wctl doc-lint --path docs/adrs/ADR-0076-watershed-runtime-budget.md
       git diff --check

## Validation and Acceptance

Acceptance requires queued-and-fetched scenario and contrast jobs in disposable
real Redis plus `job_info` tree inspection; captured enqueue arguments remain
supporting state-matrix evidence and cannot replace serialization. For continuous workload where
`years * hillslopes` exceeds 864,000, both leaf types must have
`timeout = 3600 * ceil(years * hillslopes / 72000)` and the existing metadata
fields. Single-storm leaves must retain `TIMEOUT` without workload metadata.
Compile/finalizer jobs must remain fixed at `TIMEOUT`, and the dependency graph
must be byte-equivalent apart from source line numbers regenerated by the
canonical tool.

Malformed positive-integer workload must raise before an affected child id or
parent metadata/save mutation, RQ Redis connection, leaf enqueue, and, for
contrasts, hillslope rerun. Tests must assert zero affected queue calls and zero
affected parent metadata/save mutation. Empty and fully skipped workflow states
must return through their existing paths without consulting workload. Existing
contrast batch size, fan-out, and dependency chaining must remain unchanged. No
test may claim deployment, production recovery, or scientific-output validation.

## Idempotence and Recovery

The change is additive for new jobs and safe to re-run. Existing Redis jobs are
not edited. If validation fails, revert only the implementation commit; the
accepted contract remains current and records pending conformance. If the
formula proves insufficient in environment validation, do not raise it in this
package: retain the failed job evidence and open a separately authorized
parameterization amendment.

Deployment is separately gated: confirm no started `default` or `batch` jobs,
record exact current/candidate revisions and container identities, retain the
rollback revision, and review worker/queue state after the retry. Existing
timeout subprocess-cleanup behavior is not repaired by WRT-02 and must not be
described as resolved.

## Artifacts and Notes

Retain the contract decision, two checkpoint reviews, final correctness review,
final security review, and concise validation output under this package's
`artifacts/` directory. Do not retain secrets, session identifiers, or full
production Redis payloads.

## Interfaces and Dependencies

No external dependency is added. The implementation uses:

- `wepppy.nodb.core.Climate.getInstance(wd)`;
- `wepppy.nodb.core.Wepp.getInstance(wd)`;
- `wepppy.rq.watershed_timeout.watershed_timeout_options`;
- the existing `Queue.enqueue_call` `timeout` and `meta` keyword arguments.

Revision note (2026-10-06): initial WRT-02 scaffold and contract-first execution
plan created from production diagnosis.
