# Make every deferred RQ job safely replaceable

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

A failed child can leave its parent or finalizer deferred forever. Today that
state disables controller buttons or triggers backend conflicts, forcing users
to discover cancellation tooling or abandon a project. After this work, every
controller permits a normal resubmission when the recorded job is deferred; the
server cancels and detaches the obsolete deferred job before recording the new
job. Actually runnable queued, started, and scheduled jobs continue to prevent
unsafe duplicates.

## Progress

- [x] (2026-08-21 UTC) Confirmed the prior WEPP-only viability fix and inventoried other deferred-as-active guards.
- [x] (2026-08-21 UTC) Received explicit operator approval for the broad no-friction behavior and standalone contract commit.
- [x] (2026-08-21 UTC) Completed two independent checkpoint reviews, dispositions, and post-fix confirmations with no remaining High/Medium findings.
- [x] (2026-08-21 UTC) Committed the approved documentation-only ancestor as `cfcb8aa33`.
- [x] (2026-08-22 UTC) Implemented shared deferred cleanup and adopted it across generic and specialized backend guards, including cross-surface lock families.
- [x] (2026-08-21 UTC) Implemented shared controller retry behavior, added focused Jest evidence, and rebuilt generated assets in the WEPPcloud container.
- [x] (2026-08-22 UTC) Completed the repository-wide pytest gate and independent implementation reviews with no remaining High/Medium findings.
- [x] (2026-08-23 UTC) Correct the discovered dependency regression: strict
  executable stages must stop after required-parent failure while ordinary
  submission remains the no-friction deferred-graph recovery action.
- [x] (2026-08-23 UTC) Ratify the narrow WBT addendum discovered by focused
  real-RQ evidence: prior request tails serialize mutation ownership and remain
  tolerant; each build-to-abstraction edge is strict.

## Surprises & Discoveries

- Observation: Live WEPP job `5af82b08-f1af-4180-8613-9917d53ac3f0`
  disproved the global failure-tolerant dependency design. Missing soils failed
  stage 0, but `allow_failure=True` released transitive executable stages that
  waited for or consumed nonexistent outputs.
  Evidence: the live job tree and commit `9022acba6`.
- Observation: The existing real-RQ same-run WBT test failed when prior request
  serialization was made strict: an earlier controlled failure prevented a later
  independently valid request from acquiring mutation ownership.
  Evidence: `test_same_run_policy_trees_serialize_through_abstraction`.

- Observation: The prior fix was behaving as designed, but its design conflicts
  with the newly required invariant because it intentionally blocks a deferred
  descendant whose dependency chain appears viable.
  Evidence: `docs/schemas/rq-response-contract.md` and
  `tests/rq/test_wepp_singleflight_tracking.py` explicitly require that block.
- Observation: The defect is not confined to WEPP. Multiple Python guards and
  `controlBase.should_disable_command_button` classify deferred as active.
  Evidence: repository searches on 2026-08-21 found guards in WEPP, Roads,
  AgFields, Path CE, migrations, archives/rendering, and shared controller UI.
- Observation: Batch Runner scans the queue registry instead of one saved hint,
  and its route lacks a submission lock. A generic hint-only helper would miss
  the reported parent/child failure shape and would race another submitter.
  Evidence: `wepppy/rq/batch_rq.py::_active_batch_job_summaries` and
  `wepppy/microservices/rq_engine/batch_routes.py`.
- Observation: A normal Redis pipeline is atomic but cannot prevent RQ from
  promoting a deferred job after the status read and before cancellation.
  Evidence: both independent checkpoint reviewers required a watched
  compare-and-mutate transaction and direct transition-race evidence.
- Observation: Existing route tests frequently used queue doubles without a
  Redis connection and asserted post-enqueue hint writes. Pre-enqueue durable
  receipts and admission locks deliberately expose those stale test doubles.
  Evidence: the first broad microservice run reached 482 passing tests before
  stopping on 20 focused failures, primarily missing `Queue.connection`/lock
  behavior and old deferred-as-active expectations.
- Observation: Fork, Batch+Omni, Watershed, and SWAT roots create descendants
  outside their root function. Exact association therefore requires finite
  cross-function lineage allowlists rather than run ID or module matching.
  Evidence: post-implementation correctness review and the regenerated static
  RQ dependency graph on 2026-08-22.
- Observation: SWAT parsed and persisted request inputs before single-flight
  admission, so a request rejected as active could still mutate the running
  workflow's inputs.
  Evidence: final security review traced `swat_routes.run_swat`; parsing now
  occurs only after reconciliation and active-job rejection under the lock.
- Observation: Bootstrap's ambiguous-enqueue recovery originally retained a
  random lock token that could not be reconstructed when the planned RQ job was
  confirmed missing.
  Evidence: `tests/weppcloud/bootstrap/test_enable_jobs.py` now covers both the
  planned-ID token scheme and legacy terminal-job tokens without deleting a
  successor owner's lock.

## Decision Log

- Decision: Restore strict dependencies for every required-output stage; retain
  failure tolerance only for explicitly reviewed terminal observers/finalizers
  and the enumerated AgFields and Omni-contrast serialization edges.
  Rationale: Dependency correctness and deferred retry recovery are independent.
  The established replacement transaction solves user lockout without running
  invalid downstream work.
  Date/Author: 2026-08-23, operator and Codex.

- Decision: Retain failure tolerance from a prior WBT request tail to the next
  request's build, while making each request's build-to-abstraction edge strict.
  Rationale: Focused real-RQ validation proved the prior-tail edge serializes
  same-run mutation ownership between independent requests; making it strict
  stranded a valid later request after an earlier controlled failure. The later
  request reconstructs state under the admission and directory-root locks.
  Date/Author: 2026-08-23, Codex; approved by fresh independent correctness and
  security review in `artifacts/2026-08-23_wbt_serialization_addendum_review_disposition.md`.

- Decision: Deferred is retryable everywhere; queued, started, and scheduled
  remain active.
  Rationale: A deferred job has not started and can otherwise remain stranded
  forever. Retrying must be the recovery action users already understand.
  Date/Author: 2026-08-21, operator and Codex.
- Decision: Cancel and detach the old deferred job before persisting the
  replacement ID.
  Rationale: Merely ignoring deferred state risks obsolete work being released
  later and racing the replacement.
  Date/Author: 2026-08-21, Codex.
- Decision: Cleanup uses an RQ-state compare-and-set and verifies run, operation,
  origin, and workflow lineage before mutating any root or descendant.
  Rationale: Submission locks do not serialize worker/RQ promotion, and stale or
  copied hints must never authorize cross-run cancellation.
  Date/Author: 2026-08-21, Codex after independent reviews.
- Decision: The replacement job ID is preallocated and durably recorded before
  enqueue; persistence failure aborts submission.
  Rationale: This removes the enqueue-to-hint orphan window that made recovery
  unreliable and ensures every accepted receipt is the exact enqueued ID.
  Date/Author: 2026-08-21, Codex.
- Decision: Bootstrap enable uses its preallocated job ID as its opaque git-lock
  token while retaining compatibility with tokens fetched from legacy jobs.
  Rationale: A confirmed-missing ambiguous enqueue can then clear only its own
  correlated stale lock, while compare-and-delete preserves a newer owner.
  Date/Author: 2026-08-22, Codex after final correctness/security review.
- Decision: Do not delete an uncorrelated legacy Bootstrap lock when its RQ job
  record is missing.
  Rationale: Legacy lock and receipt TTLs are identical, the lock is created
  first, supported enqueue failures release it, and terminal/canceled records
  retain the token. A receipt outliving a random-token lock is therefore the
  supported expiry order; the inverse requires out-of-band deletion or corrupt
  state, where guessing ownership would risk deleting a successor's lock.
  Date/Author: 2026-08-22, Codex during compatibility review.
- Decision: Validate identical tracked-job controllers through one exhaustive
  shared-admission suite plus a production-policy manifest, reserving full
  producer adapters for specialized state owners and destructive ordering.
  Rationale: Repeating the same mocked endpoint transaction for every thin
  wrapper does not exercise additional production logic; extracting every call
  site's real policy keeps coverage finite and explicit while focused adapters
  cover genuinely distinct behavior.
  Date/Author: 2026-08-22, Codex during final validation.

## Outcomes & Retrospective

The original deferred-retry implementation and validation completed, but this
package reopened on 2026-08-23 after a live run exposed the global failure-
tolerant dependency regression. The shared admission path renews an
owner-safe lease while traversing watched dependency graphs, pre-saves the exact
replacement receipt, and treats only queued, started, and scheduled work as
active. Deferred graphs are canceled and detached before an exact-ID replacement
is enqueued. Specialized Batch, Culvert, Roads, WEPP/SWAT, AgFields, Bootstrap,
fork/archive, Geneva, migration/run-sync, Path CE, and DEVAL paths retain their
resource-specific containment and ordering. The final unified Python gate
passed 6,636 tests with 62 skips and 12 passing subtests; frontend, graph, stub,
documentation, and broad-exception gates also passed for the original scope.
Those reviews do not approve the reopened corrective dependency work.

The corrective implementation restores ordinary strict dependencies for every
required-output edge while retaining only the matrix's named tolerant
finalizers and serialization edges. After a same-revision local stack restart,
missing-soils WEPP job `18cd9c41-039f-482e-904f-e5edb0182a80` failed in
`_prep_managements_rq`; all 13 downstream jobs remained deferred and
never-started. Ordinary resubmission canceled all 13 deferred jobs from prior
tree `06c141e3-ef3f-4dfb-98fd-9d650135a732` and returned a distinct replacement
without manual cancellation. Focused validation covers strict owners, real-RQ
WBT serialization/retry, Batch-to-Omni cleanup, atomic tolerant-finalizer
release, and status precedence; the graph contains 143 edges. The final-tree
repository suite passed 6,663 tests with 63 skips in 894.99 seconds. Stub,
graph, broad-exception, and diff checks also passed.

## Context and Orientation

RQ stores dependency-blocked jobs in a deferred registry. WEPPcloud also saves
the last job ID in `RedisPrep` or controller-specific state and hydrates it into
browser controllers. The backend uses those IDs for single-flight admission;
the browser uses polling status to disable command buttons. Both layers must
agree that `deferred` is replaceable. `wepppy/rq/job_dependencies.py` will own
the shared cancellation primitive. Admission guards in `wepppy/rq/`,
`wepppy/microservices/rq_engine/`, and relevant `wepppy/weppcloud/routes/`
modules will invoke it. `wepppy/weppcloud/controllers_js/control_base.js` will
own the shared browser rule.

## Plan of Work

For the corrective milestone, first ratify
`artifacts/dependency_edge_matrix.md`, aggregate status precedence, and the
mixed-version cutover in a standalone reviewed documentation ancestor. Then add
failing direct RQ tests for strict dependencies, each retained tolerant
finalizer, WEPP/Omni transitive stopping, and failed-over-blocked-deferred
aggregation. Change only the classified enqueue sites and aggregation priority.
Regenerate the RQ graph, execute each family's production admission retry test,
restart the local producers/workers at one revision, run live strict-failure and
ordinary-retry smokes, and complete correctness/security review before commit.

First ratify the cross-cutting contract and review it in a documentation-only
ancestor. Then add a helper that uses Redis optimistic locking to cancel only a
job whose current RQ status remains exactly deferred. It verifies server-side
run/batch identity, expected operation family/origin, and workflow lineage,
then removes all safely associated deferred nodes from their registries and
dependency/dependent sets. A status transition aborts and reconciles instead of
canceling. Refactor the finite guard matrix to use that primitive inside an
existing domain submit lock or a new bounded batch/route serialization lock.
Preserve all queued, started, and scheduled checks. Change shared controller
button and polling behavior so deferred is displayed but does not disable
resubmission or continue indefinite polling. Add direct RQ integration and race
evidence plus one focused test for every matrix row. Rebuild `controllers-gl.js`
and validate the queue graph.

## Concrete Steps

Work from `/home/workdir/wepppy`.

1. Amend the canonical RQ and shared controller contracts, create the package
   checkpoint, obtain two read-only reviews, disposition findings, and commit
   only documentation.
2. Add focused failing tests for direct deferred cleanup and every backend and
   frontend row in `artifacts/deferred_retry_surface_matrix.md`. Independent
   single-job producers may share parameterized route/service evidence only
   when every listed call site is named in the parameter set.
3. Implement the smallest shared helper and guard changes that pass those tests.
4. Run `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`,
   `wctl run-npm lint`, `wctl run-npm test`, targeted `wctl run-pytest`,
   `wctl check-rq-graph`, documentation lint, and the substantive-code broad
   pytest gate.
5. Commit the reviewed dependency/aggregate/cutover checkpoint alone. Implement
   the edge matrix and aggregate precedence, regenerate graph artifacts, restart
   the local stack at one revision, execute the two live smokes, run focused and
   broad gates, obtain independent implementation reviews, update this plan and
   the tracker, then commit and push.

## Validation and Acceptance

Corrective acceptance additionally requires every row in
`artifacts/dependency_edge_matrix.md` to execute its classification. No
required-output dependent starts after failure. Only named direct finalizers and
the three named independent serialization families may tolerate `failed`;
  present stopped/canceled prerequisites are not releasable, and manual eager
  release fails closed on missing/malformed records. Native RQ observer fan-out
  retains its result-TTL behavior. With no queued/started/scheduled member, failed outranks blocked
deferred descendants; viable deferred-only trees remain deferred and retryable.
Mixed-version evidence must show all local producers/workers restarted from the
correction revision.

An RQ graph constructed with unfinished dependencies must initially contain
deferred nodes. Shared cleanup must leave every associated deferred node
canceled, absent from `DeferredJobRegistry`, absent from parent/dependent sets,
and unable to execute. Deferred-to-queued/started races must abort cleanup.
Validation is layered: the shared admission primitive proves exact replacement,
queued/started/scheduled protection, four-way containment, and cleanup/hint/
enqueue failure behavior; a production-bound manifest names every ordinary
controller call site and extracts its actual policy; specialized state owners
execute their production reconciler or admission boundary with focused spanning
tests. Custom inventory or destructive paths additionally require producer-level
ordering evidence. Each frontend matrix row must display deferred without
indefinite polling or disabled submission and must track the new response ID
after retry. No backend or frontend row may be unnamed or inferred from an
unlisted representative.

## Idempotence and Recovery

The cleanup helper is safe to call repeatedly: missing or no-longer-deferred
jobs are a no-op. Existing submission locks plus a new bounded lock on paths
that lack one serialize competing submitters; watched Redis state serializes
cleanup against RQ promotion. Cleanup failure returns the endpoint's canonical
5xx and enqueues nothing. Enqueue failure after successful cleanup leaves the
obsolete graph canceled and returns canonical 5xx so ordinary retry is safe.
Replacement IDs are preallocated and durably saved before enqueue. If that save
fails, nothing is enqueued. If enqueue fails, the saved planned ID resolves as
missing and ordinary retry replaces it. Production jobs are not mutated by
development or test commands.

## Artifacts and Notes

The original starting implementation revision is `80e621164`; the corrective
milestone starts at `4197be09d`. Live evidence is job
`5af82b08-f1af-4180-8613-9917d53ac3f0`. Preserve unrelated user changes.

## Interfaces and Dependencies

`wepppy.rq.job_dependencies` will export a narrow helper accepting an RQ `Job`
plus a required association predicate and returning a structured reconciliation
result (`canceled`, `active`, `terminal`, `missing`, or `mismatch`). It uses RQ
1.16.2's job hash/status, `DeferredJobRegistry`, dependency/dependent Redis keys,
and Redis `WATCH`/transaction retries. Callers hold a route/domain submission
lock while reconciling the full associated graph and enqueueing replacement
work. Batch routes add one bounded lock keyed by validated batch name.

The corrective milestone limits failure-tolerant dependency construction and
eager release to the named finalizers and three named serialization families in
`artifacts/dependency_edge_matrix.md`. AgFields and Omni use the shared eager-
release helper; transactional WBT admission handles its prior-tail race inside
the existing watched registration/reconciliation boundary.
Required-output edges pass ordinary
`depends_on`. `wepppy.rq.job_info.get_wepppy_rq_job_status` applies active
executable work, then terminal failure, then viable deferred precedence.

## Corrective command runbook (revision 2026-08-23)

Write and run focused evidence with:

    wctl run-pytest tests/rq/test_job_dependencies.py tests/rq/test_wepp_rq_pipeline.py tests/rq/test_culvert_rq_pipeline.py
    wctl run-pytest tests/rq/test_project_rq_fork.py tests/rq/test_project_rq_mutation_guards.py tests/rq/test_bootstrap_autocommit_rq.py
    wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_ag_fields_rq.py tests/rq/test_batch_rq_retry_selection.py
    wctl run-pytest tests/microservices/test_rq_engine_geneva_routes.py tests/microservices/test_rq_engine_run_sync_routes.py
    wctl run-pytest tests/rq/test_job_info.py tests/rq/test_submission_recovery.py
    wctl check-rq-graph

Before the local cutover, stop HTTP producers while leaving workers available to
drain already accepted work:

    wctl docker stop weppcloud rq-engine scheduler
    wctl rq-info

Do not continue until `wctl rq-info` reports zero queued and started jobs on
`default`, `batch`, and `fork-archive`. Run this separate read-only scheduled-
registry check and require `0` for all three queues:

    wctl docker run --rm --no-deps weppcloud python - <<'PY'
    import redis
    from rq.registry import ScheduledJobRegistry
    from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
        for queue_name in ('default', 'batch', 'fork-archive'):
            print(queue_name, ScheduledJobRegistry(queue_name, connection=connection).count)
    PY

Deferred legacy trees may remain;
they are never promoted or rewritten by deployment and are recoverable only by
an authenticated ordinary resubmission after restart. Immediately before worker
stop, rerun both `wctl rq-info` and the scheduled-registry command; any nonzero
queued, started, or scheduled count aborts cutover. Then stop workers and restart
every producer/worker from the same working-tree revision:

    wctl docker stop rq-worker rq-worker-batch rq-worker-fork-archive
    wctl docker up -d --force-recreate weppcloud rq-engine scheduler rq-worker rq-worker-batch rq-worker-fork-archive
    wctl rq-info

Use the local operator-created missing-soils fixture `soft-boiled-copying` with
config `disturbed9002_wbt` for the exact developer cutover smoke. This is not an
autonomous API-operator runbook: it uses the trusted local `wctl` service-token
issuer and does not amend API-only bootstrap obligations.

    export RQ_DEP_SMOKE_TOKEN="$(wctl issue-auth-token dependency-smoke -s rq:enqueue -s rq:status --runs soft-boiled-copying --audience rq-engine --expires-in 900 --claim token_class=service --json | jq -r .token)"
    curl -fsS -o /tmp/dependency-smoke-submit.json -w '%{http_code}\n' -H "Authorization: Bearer $RQ_DEP_SMOKE_TOKEN" -H 'Content-Type: application/json' -d '{}' http://localhost/rq-engine/api/runs/soft-boiled-copying/disturbed9002_wbt/run-wepp | tee /tmp/dependency-smoke-submit.status
    test "$(cat /tmp/dependency-smoke-submit.status)" = 200
    export RQ_DEP_SMOKE_JOB_ID="$(jq -r .job_id /tmp/dependency-smoke-submit.json)"
    curl -fsS -H "Authorization: Bearer $RQ_DEP_SMOKE_TOKEN" "http://localhost/rq-engine/api/jobinfo/$RQ_DEP_SMOKE_JOB_ID" | tee /tmp/dependency-smoke-tree.json
    curl -fsS -H "Authorization: Bearer $RQ_DEP_SMOKE_TOKEN" "http://localhost/rq-engine/api/jobstatus/$RQ_DEP_SMOKE_JOB_ID" | tee /tmp/dependency-smoke-status.json
    jq -e '.status == "failed"' /tmp/dependency-smoke-status.json
    jq -e '((.children["0"] | map(select(.description | contains("_prep_remaining_rq")))) + [.children | to_entries[] | select(.key != "0") | .value[]]) as $jobs | (($jobs | length) > 0 and all($jobs[]; .status == "deferred" and .started_at == null))' /tmp/dependency-smoke-tree.json

Poll both GET commands until the first missing-soils prep failure appears. The
strict smoke passes only when every stage after stage 0, plus stage-0
`_prep_remaining_rq`, remains deferred with `started_at=null`, aggregate status
is failed, and no missing-artifact cascade appears. Execute the retry:

    curl -fsS -o /tmp/dependency-smoke-retry.json -w '%{http_code}\n' -H "Authorization: Bearer $RQ_DEP_SMOKE_TOKEN" -H 'Content-Type: application/json' -d '{}' http://localhost/rq-engine/api/runs/soft-boiled-copying/disturbed9002_wbt/run-wepp | tee /tmp/dependency-smoke-retry.status
    test "$(cat /tmp/dependency-smoke-retry.status)" = 200
    export RQ_DEP_SMOKE_RETRY_JOB_ID="$(jq -r .job_id /tmp/dependency-smoke-retry.json)"
    test -n "$RQ_DEP_SMOKE_RETRY_JOB_ID" && test "$RQ_DEP_SMOKE_RETRY_JOB_ID" != "$RQ_DEP_SMOKE_JOB_ID"
    curl -fsS -H "Authorization: Bearer $RQ_DEP_SMOKE_TOKEN" "http://localhost/rq-engine/api/jobstatus/$RQ_DEP_SMOKE_RETRY_JOB_ID" | tee /tmp/dependency-smoke-retry-status.json
    jq -e '.status == "queued" or .status == "started"' /tmp/dependency-smoke-retry-status.json

Direct RQ tests, rather than the endpoint projection, prove registry/dependency
detachment. Record UTC timestamp, method, path, HTTP status, both job IDs, and
redacted tree summaries in the tracker; never record the token. Then unset both
token and job-ID variables.

Rollback validation first runs `wctl docker config --quiet`. An actual
rollback, if needed, repeats the producer stop, zero-active-work drain, worker
stop, and same-revision recreation sequence at the chosen prior revision. Never
switch revisions or recreate only part of the producer/worker set while work is
active.
