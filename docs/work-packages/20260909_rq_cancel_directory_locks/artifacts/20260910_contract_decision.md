# Contract decision: RQ-CANCEL-LOCKS-01

## Authority and classification

Starting implementation: 028413e5ce2e33a6bceb6785f8f365db8410a223.
Operator authorization: "canceling rq-jobs needs to clear directory locks."
This approves the intended behavior; checkpoint commit and implementation authority were subsequently granted with
"yes" on 2026-09-10 UTC. Production deployment remains separate. Classification: intended behavior amendment.

Applicable contracts: docs/schemas/rq-engine-agent-api-contract.md (cancellation),
docs/schemas/directory-maintenance-lock-contract.md (maintenance lock ownership), and
docs/schemas/nodb-persistence-concurrency-contract.md (unchanged controller-lock
ownership constraint). RQ response/error and CSRF contracts remain unchanged.

## Normative delta and rationale

Cancellation must release the canceled execution's directory locks after its
writers have terminated. Preserve asynchronous stop acknowledgment. Record a
server-generated execution identity on new directory locks and release only
matching ownership and token. Never clear every lock for the run. A worker-side
supervisor owns post-stop cleanup; request handlers cannot infer termination
from sending a stop command or from job.cancel(). Cleanup failures are logged
with job/root context and remain inspectable, never reported as cleanup success.

The safe legacy case is no-op when there are no owned locks. Legacy payloads
without verifiable execution ownership retain explicit operator recovery.
Previously failed jobs cannot be used to clear the lock belonging to an older,
different build. Whole-container crash reconciliation remains separate.

## Source boundary

wepppy/runtime_paths/thaw_freeze.py: additive execution ownership and exact
token cleanup. wepppy/rq/rq_worker.py: execution lifecycle and verified post-stop
cleanup, including termination evidence for descendant writers.
wepppy/rq/cancel_job.py only if needed to preserve cancellation/cleanup state;
no new enqueue edges. Tests cover runtime paths, worker cancellation, and API
compatibility. User/operator/developer guidance belongs in wepppy/rq/README.md.

## State and regression matrix

Absent or empty lock state: cancellation succeeds with no cleanup work.
Populated owned state: retain while active, release after termination.
Other-job or replacement state: never release.
Supported legacy state: cancellation still works; ambiguous locks remain for
explicit recovery.
Malformed identity/token: never broaden deletion; expose contextual cleanup error.
Redis failure: preserve stop handling, log cleanup failure and make it inspectable.
Repeated cancellation: idempotent.
Queued job: no release of active jobs' locks.
Child RQ jobs: each execution follows the same termination/ownership rule.
Process-pool writers: prove stopped before directory lock release.
Detached/reparented writers: include a real start_new_session=True child,
matching CLIGEN's current launch behavior. Prove no writes after cleanup.
Unknown/permission-denied termination evidence: preserve locks and an
inspectable cleanup reason; PID reuse cannot authorize termination or cleanup.
Same-job retry: delayed cleanup from execution A must preserve execution B's
locks even when both executions share the same RQ job ID.
Containment: capture writer identities before stopping or prove an equivalent
containment mechanism; post-stop PPID scanning alone misses reparented writers.
Real cancellation regression must preserve unrelated process groups.
Terminal jobs and queued-to-started/started-to-finished races: job status alone
must never authorize cleanup; require execution ownership and termination proof.

## Compatibility and review

Additive internal lock metadata; no key, TTL, UI, auth, public response, NoDb
schema, or model parameter changes. Security impact high (write exclusion).
Implementation conformance pending. Two independent read-only contract reviews
and a standalone checkpoint ancestor are required before code edits.
