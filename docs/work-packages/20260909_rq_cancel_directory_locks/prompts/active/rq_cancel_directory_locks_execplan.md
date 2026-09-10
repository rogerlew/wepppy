# Clear canceled RQ execution directory locks safely

Maintain this living ExecPlan under docs/prompt_templates/codex_exec_plans.md.

## Purpose / Big Picture

After canceling a build and stopping its writers, its directory locks should no
longer block the next build. Preserve other executions' exclusion locks.

## Progress

- [x] (2026-09-10 UTC) Inspect incident, cancellation, locks, and RQ supervisor.
- [x] (2026-09-10 UTC) Prepare contract amendment and state matrix.
- [x] (2026-09-10 UTC) Complete two independent checkpoint reviews; findings closed.
- [ ] Obtain authority and create standalone checkpoint ancestor commit.
- [ ] Implement ownership and cleanup with regression tests.
- [ ] Verify real process/Redis lifecycle, broad tests, and final reviews.

## Surprises & Discoveries

cancel_job.py sends send_stop_job_command for started jobs; no directory cleanup
exists. RQ kill_horse signals the process group, and monitor_work_horse waits
for the workhorse before handling user-stop failure. Waiting for the leader
alone does not prove every descendant writer has terminated.
The incident lock had a six-hour TTL and named a removed container.
Independent reviews identified CLIGEN's start_new_session=True launch at
wepppy/climates/cligen/cligen.py:2554: its writer can escape the workhorse's
process group. The real regression must include detached/reparented writers.

## Decision Log

2026-09-10 UTC, Codex: attach execution identity and use token-checked release
after verified termination. Reject run-wide clear because concurrent jobs can
hold unrelated locks. Keep legacy ambiguous locks for explicit recovery.
The operator authorized cleanup and granted checkpoint commit/implementation authority
with "yes" on 2026-09-10 UTC.

## Outcomes & Retrospective

Checkpoint preparation only. No implementation or rollout is complete.

## Context and Orientation

wepppy/rq/cancel_job.py recursively requests RQ cancellation.
wepppy/rq/rq_worker.py defines WepppyRqWorker, the surviving supervisor around
the workhorse (the process executing a job).
wepppy/runtime_paths/thaw_freeze.py stores directory maintenance locks in Redis
with owner, token, scope and expiry. Its token check prevents stale cleanup from
deleting a replacement owner's lock. Controller .nodb locks are a separate scope.

## Plan of Work

Milestone 1: review artifacts/20260910_contract_decision.md and the two canonical
amendments. Obtain two independent reviews, resolve findings, request commit
authority if absent, and commit only checkpoint documentation on the existing
branch. Record the ancestor revision in tracker.md before production code edits.

Milestone 2: establish a unique server-owned execution identity before locks
can be acquired, include it in maintenance lock payloads, and implement
ownership/token-scoped cleanup in the surviving worker after verified writer
termination. Keep ordinary context-manager release and existing cancellation
authorization. Confirm how process-pool descendants terminate; do not equate
stop-command acknowledgment with completed cleanup.

Milestone 3: add real Redis/worker cancellation regression and ownership-race
tests, run required checks, update user/operator/developer README guidance, and
obtain independent correctness, QA and dedicated security review. Record any
blockers truthfully; no production rollout without process-boundary parity.

## Concrete Steps

Work in /home/workdir/wepppy on the existing branch. Read tests/AGENTS.md before
test edits. Use wctl run-pytest for focused runtime-path, cancellation and worker
tests; then wctl run-pytest tests --maxfail=1. Lint changed Markdown with
wctl doc-lint --path <file>. Run stub checks if worker/public signatures change.
No queue wiring change is intended; if discovered necessary, amend scope first.

## Validation and Acceptance

Use a unique disposable run in development Compose with the real worker class,
Redis, mounts and execution identity. Start a job that acquires a directory lock
and launches a descendant writer. Cancel through the shared cancellation path.
Observe termination of all writers before lock removal and then successfully
acquire that root immediately. Assert unrelated and replacement locks survive.
Include a real detached-session writer as used by CLIGEN. Unknown or denied
termination evidence must retain locks and expose a cleanup reason. Verify
process identity against PID reuse; group-leader exit is insufficient evidence.
Capture writer identities before stopping or demonstrate equivalent containment;
post-stop PPID scanning alone is insufficient. Preserve unrelated process groups.
Test delayed execution-A cleanup against a retry B with the same RQ job ID.
Repeat with no locks, queued cancellation, legacy/malformed ownership and Redis
failure. Tests must exercise actual locking and process shutdown without mocks
at those boundaries. Record execution identity, mounts and commands as evidence.

## Idempotence and Recovery

Cancellation and cleanup must be repeatable. Release only matching execution
ownership and current token. Remove disposable validation artifacts only after
all test processes stop. Failed cleanup must retain locks and diagnostic state
for existing explicit operator recovery.

## Artifacts and Notes

Incident: wepp1 job 2964a4f7-6b07-4d3b-a70d-d78dabcb8c67,
2026-09-10 03:56:20 UTC, NODIR_LOCKED for climate.
No proof yet that user cancellation caused the original owner to disappear.

## Interfaces and Dependencies

Reuse installed RQ, Redis, WepppyRqWorker and maintenance-lock token operations.
Add no dependencies or lease/retry defaults. Public cancellation payloads stay
compatible. Execution identity must distinguish retries of the same RQ job.

Revision note: initial plan records requested cleanup and mandatory sequencing.
