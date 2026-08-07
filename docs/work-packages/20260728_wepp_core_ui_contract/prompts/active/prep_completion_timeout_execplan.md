# Harden the WEPP prep-completion timeout from production timing evidence

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`. The work amends the registered
DOM-14A contract for one production failure: the prep-only terminal job must
have enough time to commit generated inputs on NFS without losing its Git lock.

## Purpose / Big Picture

After this change, a prep-only WEPP pipeline whose bootstrap commit takes as
long as the measured `door-to-door-salad` recovery will not fail at RQ's
180-second default. Operators can verify the leaf job is enqueued with a
3,703-second timeout and a 4,003-second run-scoped Git lock lifetime.

## Progress

- [x] (2026-08-07 04:56 UTC) Measured the complete production bootstrap commit
  at 1,234.117 seconds and recovered commit `1e7fb6b`.
- [x] (2026-08-07 04:58 UTC) Began the DOM-14A contract checkpoint and ADR.
- [x] (2026-08-07 05:09:55 UTC) Operator approved the exact timeout, lock
  lifetime, and two-phase consumer-first rollout.
- [x] (2026-08-07 05:15 UTC) Obtained governance and operations/security
  checkpoint reviews, dispositioned all findings, and received post-fix PASS.
- [ ] Commit the accepted checkpoint as a standalone ancestor.
- [x] (2026-08-07 05:16 UTC) Committed accepted checkpoint as standalone
  ancestor `cdc51d421`.
- [x] (2026-08-07 05:25 UTC) Implemented phase-1 consumer-compatible lock TTL
  derivation with old-job, prep-only, success, failure, and sibling coverage;
  focused suite passed 21 tests.
- [ ] Deploy and verify phase-1 compatibility on every default-worker host.
- [ ] Activate the 3,703-second prep-only producer timeout.
- [ ] Run focused, RQ graph, stub, broad-exception, docs, and full test gates.
- [ ] Obtain final correctness and security confirmation and record outcomes.

## Surprises & Discoveries

- Observation: The first 743-second measurement covered only `git status`.
  Evidence: the full locked bootstrap recovery took 1,234.117 seconds; `git add`
  remained in NFS wait for several minutes and `git commit` also ran materially.
- Observation: The existing bootstrap Git lock lasts only 900 seconds.
  Evidence: `BOOTSTRAP_GIT_LOCK_TTL_SECONDS` defaults to 900, shorter than both
  the measured recovery and proposed RQ timeout.

## Decision Log

- Decision: Use `ceil(3 * 1234.1167397499084) = 3703` seconds for the RQ timeout.
  Rationale: RQ uses an integer-second timeout; rounding up preserves at least
  the operator-requested three-times margin.
  Date/Author: 2026-08-07 / WEPPcloud operator and Codex.
- Decision: Hold the operation-scoped Git lock for 4,003 seconds and roll out
  consumer compatibility before activating the enqueue timeout.
  Rationale: a five-minute bounded cleanup margin reduces expiry risk, while
  consumer-first rollout prevents mixed-version jobs from using a 900-second
  lock under the longer timeout.
  Date/Author: 2026-08-07 / WEPPcloud operator and Codex.

## Outcomes & Retrospective

Pending implementation and validation.

## Context and Orientation

`wepppy/rq/wepp_rq_pipeline.py` constructs the prep-only job tree. Its terminal
leaf calls `_log_prep_complete_rq` with no explicit timeout, so RQ applies 180
seconds. `wepppy/rq/wepp_rq_stage_finalize.py` acquires the run-scoped bootstrap
Git lock and calls `Wepp.bootstrap_commit_inputs`. The lock helper defaults to
900 seconds. DOM-14A is the registered contract owner for WEPP run/prep RQ.

## Plan of Work

First amend DOM-14A and ADR-0039, obtain two independent reviews, and commit
those documents alone. Phase 1 changes the prep finalizer to derive its lock
lifetime from the current job timeout plus 300 seconds with the existing default
as a floor. Deploy phase 1 to every default worker before phase 2 sets the prep
leaf enqueue timeout. Preserve every queue edge, payload, status event, and
non-prep completion timeout; do not add a serialized job keyword.

## Milestones

Milestone 1 produces the reviewed standalone contract ancestor. Acceptance is
a documentation-only commit containing DOM-14A, ADR-0039, both independent
reviews, their disposition, the root plan pointer, and PROJECT_TRACKER, with no
production Python or unrelated report files.

Milestone 2 produces and deploys consumer compatibility. The finalizer derives
the lock lifetime from `get_current_job().timeout`; tests prove a long job maps
to timeout plus 300 seconds and short/default jobs retain at least 900 seconds.
All default workers on wepp1 and wepp2 must run the compatible revision before
milestone 3.

Milestone 3 activates the prep-only leaf timeout at 3,703 seconds, validates the
generated job tree and repository gates, and records rollout/rollback evidence.

## Concrete Steps

From `/home/workdir/wepppy`, validate and commit the checkpoint:

    wctl doc-lint --path docs/work-packages/20260728_wepp_core_ui_contract
    wctl doc-lint --path docs/adrs/ADR-0039-wepp-prep-completion-timeout.md
    git diff --check

Expected: zero documentation errors and no diff-check output. Stage only the
checkpoint documents, verify with `git diff --cached --name-only`, and commit.

After that ancestor exists, implement and test consumer compatibility first:

    wctl run-pytest tests/rq/test_bootstrap_autocommit_rq.py --maxfail=1
    wctl run-stubtest wepppy.rq.wepp_rq_stage_finalize

Expected: all focused tests pass and stubtest reports success. Deploy phase 1
through the production runbook only after the queue gate is clear and verify
wepp1/wepp2 source revisions and worker start times.

Then activate the enqueue timeout and validate:

    wctl run-pytest tests/rq/test_wepp_rq_pipeline.py --maxfail=1
    python tools/check_rq_dependency_graph.py --write
    wctl check-rq-graph
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl run-pytest tests --maxfail=1

Expected: focused and full tests pass, the graph is current, and broad-exception
delta is zero. Direct source/job-tree readback must show timeout 3,703 and
derived lock lifetime 4,003.

After phase-2 production activation, capture the first natural representative
prep-only finalizer as canary evidence. Record job id, configured 3,703-second
timeout, start/end/duration, derived 4,003-second lock lifetime, commit or no-op
result, terminal prep-completion trigger, token-owned lock release, and default
queue wait/occupancy impact. A missing terminal trigger, surviving lock, Git
error, or breached guardrail fails acceptance and invokes containment/rollback.

## Validation and Acceptance

Focused tests must prove timeout-to-lock derivation, old-job compatibility,
success/exception lock release, and prep-only scoping. Exact literal values are
validated by source and live job-tree readback rather than a literal-only test.
`wctl check-rq-graph`, stubtest, broad-exception enforcement, documentation
lint, and `wctl run-pytest tests --maxfail=1` must pass. No queue edge changes.

## Idempotence and Recovery

The production timing recovery already completed and released its lock; do not
repeat it. Code generation and tests are repeatable. Rollback first restores
old producer behavior, inventories and drains longer-timeout queued, deferred,
and started leaves, and only then removes consumer compatibility.

If interruption occurs during `status`, `add`, `commit`, or `rev-parse`, do not
blindly requeue or delete a lock. The WEPPcloud operator first checks for a
surviving Git process, `.git/index.lock`, HEAD, staged index, and worktree. A
completed commit is accepted after verification; staged-only state is retained
for inspected retry; a live process or NFS wait remains contained until it exits
or the host is safely fenced.

## Artifacts and Notes

Production evidence: host `wepp1`, run `door-to-door-salad`, failed job
`9636f1fd-3475-4b32-9216-65a7324c9d80`, measured recovery commit `1e7fb6b`,
elapsed 1,234.117 seconds, and clean lock release.

## Interfaces and Dependencies

The public route and response contracts do not change. The internal prep-only
enqueue helper gains timeout propagation. `_log_prep_complete_rq` derives its
lock lifetime from the current RQ job; no new serialized argument is introduced.
Redis remains the lock substrate; no new dependency or queue is introduced.

Revision note (2026-08-07): Created from the completed production measurement
and corrected the earlier status-only timing assumption.
