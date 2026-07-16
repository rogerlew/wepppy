# Execute AgFields Run All as one canonical RQ job tree

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` current while executing it.

## Purpose / Big Picture

After this change, a user choosing Run All sees one top-level RQ job whose three
children run Concept 1, Concept 2, and hybrid serially. The existing recursive job
dashboard, status polling, and cancellation tools can then operate on the whole
comparison suite, while each child continues to own its existing state and fixed
output tree.

The result is observable by submitting `scheme=all`, polling the returned parent,
opening its job info, and verifying exactly three ordered child jobs plus all
three generated output roots.

## Progress

- [x] (2026-07-15 23:07 UTC) Read governing instructions and canonical RQ/API
  contracts.
- [x] (2026-07-15 23:07 UTC) Trace the current AgFields enqueue flow and existing
  parent metadata convention.
- [x] (2026-07-15 23:07 UTC) Scaffold package, tracker, security review, and
  compatibility plan.
- [x] (2026-07-15 23:40 UTC) Implement the suite parent, additive state key, tree lifecycle fixes, and
  frontend tracking.
- [x] (2026-07-15 23:40 UTC) Add route, worker, job status, cancellation, and frontend regressions.
- [x] (2026-07-15 23:40 UTC) Update API/RQ/AgFields documentation and regenerate the dependency graph.
- [x] (2026-07-16 00:03 UTC) Pass focused, stub, frontend, docs,
  broad-exception, and full Python gates.
- [x] (2026-07-16 04:23 UTC) Restart the local forest stack and complete authenticated acceptance on
  `sacral-self-discipline`.
- [x] (2026-07-16 04:25 UTC) Complete dual review, remediate findings, close the security gate, archive
  this plan, and close the package.

## Surprises & Discoveries

- The existing generic recursive status prioritizes a failed child over another
  active child. That makes an allow-failure suite look terminal before its later
  comparison jobs finish; the parent cutover requires a focused lifecycle fix.
- Recursive cancellation currently returns immediately when the dispatch parent
  is already terminal, so it never reaches active descendants. A dispatch-parent
  topology makes that existing behavior directly user-visible.
- RQ 1.16 can leave an allow-failure dependent deferred when its prerequisite
  failed before dependent registration. The Batch Runner release safeguard is
  required after Concept 2, hybrid, and finalizer enqueue, not only finalization.
- Complete planned metadata alone does not close the in-flight cancellation
  race because a planned job may not exist yet. Dispatch and cancellation now
  share a Redis lock and cancellation marker.
- The generic run endpoint-discovery response did not list the live AgFields
  operations. The authenticated route and state endpoint were healthy, so
  acceptance used the locally documented OpenAPI route. The discovery omission
  is recorded as separate operator-usability follow-up.

## Decision Log

- **2026-07-15 23:07 UTC** - Use a new additive
  `agfields_run_watershed_suite` parent key. Keep
  `agfields_run_watershed` as the historical Concept 2 alias.
- **2026-07-15 23:07 UTC** - Preserve preallocated scheme IDs in `job_ids`, while
  changing only the Run All `job_id` to the parent.
- **2026-07-15 23:07 UTC** - Treat active descendants as non-terminal even when
  an earlier child failed; surface failure only after the tree has no active
  descendants.
- **2026-07-15 23:07 UTC** - Preserve serial allow-failure dependencies and all
  fixed output paths.
- **2026-07-15 23:20 UTC** - Follow `run_batch_rq` finalization: enqueue a fourth
  child that depends on all three scheme IDs with `allow_failure=True`, ensuring
  it waits for every terminal child and is released despite child failure.
- **2026-07-15 23:40 UTC** - Apply the ready-deferred release guard to every
  failure-tolerant dependent and make the finalizer the suite terminal trigger's
  only publisher.
- **2026-07-15 23:40 UTC** - Atomically register the complete planned tree on
  the parent and synchronize dispatch/cancellation with a lock and marker.
- **2026-07-15 23:40 UTC** - Preserve AgFields' already-shipped named-child
  `job_ids` object and document it as a narrow compatibility form: `job_id` is
  the registered root and the mapping contains domain children.

## Outcomes & Retrospective

Run All now returns one canonical parent with ordered Concept 1, Concept 2,
hybrid, and finalizer children. Serial failure-tolerant dependency release,
recursive lifecycle, cancellation, state/UI hydration, and run authorization
are regression-covered. Both independent reviews and the high-impact security
gate passed with no unresolved findings.

The full Python suite passed with 4,914 tests and 58 skips; all 635 frontend
tests plus lint, stub, graph, route-contract, broad-exception, diff, and docs
gates passed. Authenticated local-forest acceptance ran from 00:01 to 04:22 UTC
on `sacral-self-discipline`: all three schemes completed serially, the finalizer
started after hybrid, the parent reached 5/5 terminal success, and every fixed
tree reported 3,543 parent/PASS outputs with all required resources present.

The principal implementation lesson is that an RQ dispatch parent must register
its complete planned tree atomically and share a lock with cancellation; job
dependencies alone do not close dispatch/cancel or already-terminal dependency
races. The Batch Runner ready-deferred release guard remains the canonical
failure-tolerant pattern.

## Context and Orientation

`wepppy/microservices/rq_engine/ag_fields_routes.py` authenticates and validates
the Run All request. Its current `_enqueue_watershed_jobs` helper creates three
top-level scheme jobs. `wepppy/rq/ag_fields_rq.py` contains the single-scheme
worker and will own the new dispatch parent.

WEPPpy's canonical tree convention is described in `wepppy/rq/README.md`:
parent workers enqueue children and persist each ID under an ordered `jobs:*`
metadata key. `wepppy/rq/job_info.py` recursively reads those keys;
`wepppy/rq/cancel_job.py` recursively cancels them. The AgFields browser
controller is `wepppy/weppcloud/controllers_js/ag_fields.js`.

The authoritative behavior is recorded in this package's `package.md`,
especially `Behavior and Compatibility Contract` and `Project Data
Compatibility and Regression Plan`.

## Plan of Work

First, add the suite worker and public stub. The worker must validate the three
planned identifiers, get its current parent job, persist every per-scheme job ID
before the first child enqueue, enqueue the children on the default queue with
stable allow-failure dependencies, and save each child under an ordered `jobs:*`
parent metadata key. It then enqueues a registered finalizer with one
`allow_failure=True` dependency over all scheme jobs. The dispatch parent must
not publish the suite terminal trigger merely because dispatch finished; the
finalizer owns that terminal signal.

Second, change the route helper so one scheme keeps the current direct enqueue,
while three schemes preallocate child IDs and enqueue only the suite parent. Add
the suite parent key to state/hydration and active-job checks. The response must
contain parent `job_id` and child `job_ids`.

Third, make recursive status non-terminal while any descendant is active and let
cancellation traverse descendants after a benign terminal-parent cancellation
error. Freeze both failure modes in focused unit tests.

Fourth, make the browser explicitly track the suite parent for Run All and retain
the scheme-child mapping for independent status rows. Update its Jest coverage
and generated asset only through the repository's normal build/test tooling if a
generated copy is tracked.

Fifth, update the AgFields module/UI docs, RQ dependency catalog and generated
graph, and the agent API contract. Run all required gates.

Finally, restart the local forest stack, discover the live endpoint contract,
submit Run All for `sacral-self-discipline`, poll the parent, inspect its child
tree, and verify the three fixed outputs. Record redacted UTC evidence. Dispatch
two independent reviews, remediate all actionable findings, close security, and
archive this plan.

## Concrete Steps

Run from `/home/workdir/wepppy` unless noted otherwise.

1. Implement with `apply_patch` in the files named above and add focused tests in
   `tests/rq/`, `tests/microservices/`, and the AgFields Jest suite.
2. Run focused gates:

       wctl run-pytest tests/rq/test_ag_fields_rq.py tests/rq/test_job_info.py tests/rq/test_cancel_job.py tests/microservices/test_rq_engine_ag_fields_routes.py --maxfail=1
       wctl run-npm lint
       wctl run-npm test -- --runInBand wepppy/weppcloud/controllers_js/__tests__/ag_fields.test.js
       wctl run-stubtest wepppy.rq.ag_fields_rq
       wctl check-rq-graph

   Adapt exact test filenames to the repository's existing modules discovered
   during implementation; do not create duplicate suites solely to match these
   provisional names.
3. Run broad gates:

       wctl run-npm test
       wctl check-test-stubs
       python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
       wctl run-pytest tests --maxfail=1

4. Restart the necessary local forest services with `wctl`, then use the
   rq-engine HTTP contract to discover, submit, and poll the Run All operation.
   Never print or retain bearer tokens in evidence.
5. Run doc lint for each changed Markdown file and preview `uk2us` changes.

## Validation and Acceptance

Automated acceptance requires all focused and broad gates to exit zero. The RQ
graph guard must match the updated catalog/artifact, and the AgFields public stub
must match runtime exports.

Live acceptance requires:

- the submission response has one parent `job_id` and three distinct child IDs;
- parent `jobinfo.children` has scheme groups `0`, `1`, and `2` plus finalizer
  group `3`;
- parent `jobstatus` stays non-terminal while any child is active and finishes
  only after all children are terminal;
- the state endpoint exposes the suite parent and three scheme IDs;
- `concept-1`, `concept-2`, and `hybrid` fixed output roots exist with terminal
  manifests/results;
- no unexpected 4xx/5xx response, worker crash, or OOM event occurs.

## Idempotence and Recovery

Code and test steps are repeatable. The route's existing submission lock and
active-job checks prevent a second concurrent AgFields submission. If live
acceptance fails, inspect the parent and child job info plus worker logs before
retrying. Use the authenticated clear-watershed operation only if regenerable
scheme artifacts must be reset; do not remove protected baseline or independent
AgFields artifacts manually.

Stack restarts are limited to the local forest development stack. No forest1 or
production deployment is authorized or required.

## Artifacts and Notes

- Compatibility plan:
  `artifacts/2026-07-15_job_tree_compatibility_plan.md`
- Security review: `artifacts/2026-07-15_security_review.md`
- Live verification evidence: `artifacts/2026-07-15_forest_acceptance.md`
- Independent reviews will be recorded as separate artifacts.

## Interfaces and Dependencies

The suite worker should have a stable interface equivalent to:

    run_ag_fields_watershed_suite_rq(
        runid: str,
        max_workers: int | None,
        planned_job_ids: dict[str, str],
        finalizer_job_id: str,
    ) -> dict[str, Any]

It depends only on existing Redis/RQ, `RedisPrep`, `AgFields`, routing-scheme
validation, and the existing single-scheme worker. No new external dependency is
allowed.
