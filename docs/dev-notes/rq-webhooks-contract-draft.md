# RQ webhook contract and implementation planning draft

Status: revised discussion draft, 2026-10-28. Operator direction below supersedes
conflicting 2026-10-27 recommendations. Not yet a ratified canonical contract or
permission to implement. RQ native webhooks remain disabled.

## Client-facing contract

A client supplies an optional `webhook_url` with an authenticated operation
submission. Accepting that submission authorizes notification for that operation;
later token expiry must not prevent delivery. No endpoint-registration
API, separate subscription request, destination challenge or ongoing token
validation is required for the initial design.

The notification describes the outcome of the operation the client requested.
For culverts this means the batch; for running WEPP it means the complete selected
workflow, including its required postprocessing. Submission acknowledgment and
orchestrator-job completion are not useful completion notifications. Simple
single-job operations can use their own terminal outcome.

URLs are freely supplied HTTPS destinations. Audit submission, destination,
delivery attempts and outcome so operators can investigate abuse and tighten
policy if needed. This removes destination-control challenges and operator
allowlists, not baseline HTTPS/SSRF handling: the proposed sender still rejects
credentials in URLs, unsafe internal destinations and redirects, and validates
the connected address while preserving hostname TLS verification. Any requirement
for private destinations must be explicit rather than accidentally bypassing these
checks. Sanitize audit records and restrict access; never log bearer tokens or
secret URL query values. Treat the entire raw URL as sensitive outside the
restricted delivery-intent record, since paths can contain capabilities too. Audit
with sanitized host plus opaque destination fingerprint. Inventory request capture,
profile-recorder playback, dry-run printing, task descriptions, public jobinfo,
archives and exception logs. Recorded playback must omit callback intent or require
an explicit test-destination override; it must not resend a captured production URL.

Delivery must not block normal computational tasks, change their outcomes,
release dependencies or cause computation retries. Use a short total attempt
budget (operator example: 10 seconds) and limited retries in documented transient
cases. Total includes DNS/connect/TLS/read work, not merely a socket read timeout.
Exact retry count/backoff and whether 10 seconds is the final value remain open.

"Honor the webhook" means retain and attempt the accepted callback independently
of token expiry. It cannot mean guaranteed receipt from an unreachable receiver;
exhaustion is recorded and computation remains unaffected. Ordinary token expiry
must not be confused with an explicit operator emergency dispatch stop.

## Consumer payload and identity proposal

Operator decision (2026-10-28 18:20 UTC): Option A. Notify execution completion
and execution outcome; clients obtain domain results from existing APIs. Do not
introduce a generic task-reported domain outcome convention in this release.

Use `event: operation.completed` once the hierarchy settles, with an explicit
`execution_status` and immutable event ID, schema version, original submission/root
job ID, operation name, completion/observation timestamps and authorized resource
identifier. `execution_status: finished` means the hierarchy settled without an
RQ-level failure; it does not mean every requested domain item succeeded. Failed
execution also settles the operation; completion is not a success assertion.
Exact stopped/canceled precedence remains to ratify.

Do not embed domain success/partial-success classification or a batch outcome
summary in this release's generic callback. Do not include arbitrary arguments,
raw results, tracebacks, paths or credentials. Clients retrieve batch summaries,
reports and other detailed outputs through the existing APIs. Preserve those APIs.

An event ID is stable across retries; receivers must tolerate duplicates. A
successful HTTP acknowledgment can be lost before local persistence. Do not promise
exactly-once delivery. The root job ID is a correlation ID, not a claim that its
individual RQ status equals the hierarchy's execution status.

Required HC-03 acceptance: run a culvert task that catches a domain failure and
returns "failed" normally. Once its full hierarchy settles with no RQ-level
failure, the callback reports `operation.completed` / `execution_status: finished`;
the existing batch-results API still exposes the failed run. Assert no callback
field claims all-runs success. Pair with an uncaught RQ failure, where settled
execution reports failure. Do not change task exception behavior to fit callbacks.
Do not report completion while required work or final artifact preparation remains,
or imply cancellation proves every descendant process has exited.

## Signing is a separate capability decision

A shared signing secret lets a receiver distinguish WEPPcloud callbacks from
forged requests. It is useful, but it is not required to isolate delivery from RQ
or to accept a client-supplied HTTPS URL. The prior design prematurely made a
registered encrypted-secret facility mandatory. Remove that prerequisite.

Whether the first release offers optional signatures, requires signatures or
ships unsigned minimal notifications remains an explicit decision. Do not add a
key-management subsystem by assumption. An unsigned callback is a notification,
not authenticated evidence on which the receiver should perform sensitive actions;
a receiver can confirm the outcome through the authenticated API. Do not put the
submission's bearer token into the callback or treat it as a signing key.

## Generalizable implementation proposal

Use three narrow responsibilities: capture the optional callback with the accepted
submission; resolve that submission's workflow outcome; independently attempt
HTTP delivery and record results. Keep consumer configuration the same across
supported endpoints. No per-task HTTP handlers and no changes to model code.

The terminal-state mechanism must be generic for hierarchical jobs, not selected
by operation name or handwritten culvert/WEPP finalizer adapters. Treat one accepted
submission as a root with owned descendants. Finalizer tasks are ordinary members
of that hierarchy, so their work is naturally included without special completion
hooks for each pipeline.

Existing substrate: `job_info.py:recursive_get_job_details` follows `jobs:*` child
references; `get_wepppy_rq_job_status` aggregates their states.
`auth_actor.py:install_rq_auth_actor_hook` intercepts enqueue calls and already has
access to the executing parent through `get_current_job()`. Existing pipeline
helpers record children. Audit these before adding mechanisms. The existing poll
formatter is not yet a reliable terminal predicate: missing children can be omitted
and failure outranks deferred state without dependency analysis. Do not change its
public response contract incidentally while extracting a minimal shared evaluator.

Proposed generic predicate: a hierarchy is settled only when membership is complete
and stable and every member is terminal or provably unable to execute in this
submission attempt. Queued/running/scheduled jobs and pending retries keep it open.
A deferred member is blocked only when its actual dependency rules establish that
it cannot run because a prerequisite ended unsuccessfully; honor failure-tolerant
edges. A missing record, incomplete enqueue registration, unknown dependency or
unresolved external prerequisite means unknown/waiting, never completion. Propagate
proven blocking transitively without modifying RQ states or dependencies. For
A failed -> B strict/deferred -> C allow_failure, C remains blocked because B is
still deferred; logical blocking is not an actual RQ failed status. Conversely,
A failed -> C allow_failure can run and must be awaited. Include stopped/canceled
semantics and explicitly supported stopped-observer release behavior from the
current dependency helper, without inventing releases in the evaluator.

Derive aggregate outcome separately from the settled predicate: failures take
precedence over success, with explicit stopped/canceled precedence still to ratify.
Wait for independent branches and runnable failure-tolerant finalizers before the
single terminal event. Manual requeue after final notification belongs to a new
submission/attempt policy; an unresolved automatic retry is not terminal.

Operator clarification (2026-10-28): batch hierarchies can expose a failed parent
while intentionally continuing their children; other hierarchies stop downstream
execution on child failure. Neither parent failure nor first descendant failure
is a terminal-notification trigger by itself. Continue traversal beneath failed
parents and distinguish `has_failure` from `settled`. Evaluate actual dependency
rules rather than selecting continuation behavior by task name.

Required paired acceptance: a continuing batch with one failed child and other
queued/running children is failure-known but unsettled; notification waits for
those children and runnable finalizers. A strict chain with a failed prerequisite
and provably blocked deferred descendants becomes settled failure when no other
branch, retry or producer can advance. Failed ancestry alone does not prove an
independent descendant is blocked. Evaluation must not change RQ task states.

Callback binding, accepted submission identity and root/parent membership are
server-controlled. Clients may provide their own callback URL, not nominate an
existing root/parent. Bind the destination once at admission; descendants inherit
an opaque reference and cannot replace it. Verify every owned member's root
binding. Foreign/external prerequisites are dependencies, not payload members.
Test spoofed metadata, conflicting roots and interleaved cross-client submissions.

Membership and dependency edges are different. Jobs created by a member inherit
the root/parent identity through the common enqueue path; an external prerequisite
is not automatically an owned descendant. Audit bulk enqueue, explicit pipelines,
callbacks, alternate producers and intentionally detached maintenance work before
claiming universal coverage. Route/job-type-specific completion detectors are not
the desired solution; shared metadata or explicit generic membership is acceptable.

The race to prove is child publication versus parent completion. Register membership
before or atomically with job visibility, account for pending enqueue operations,
and evaluate a consistent/version-checked snapshot after producers have settled.
Producer closure includes pending enqueue operations, lifecycle callbacks capable
of enqueueing, and execution-exit evidence when cancellation leaves a producer
potentially alive. Task return, ended_at or canceled status alone is insufficient.
A quiet moment or a parent returning is insufficient. Preserve fail-open notification
behavior: bookkeeping uncertainty must not change computation outcomes, but must
mark notification completeness uncertain rather than permit false completion.
Document persistence/crash gaps and recovery instead of claiming atomic guarantees
that the selected storage/enqueue integration cannot provide.

Computation-side hooks may perform only bounded bookkeeping/signaling. Full graph
traversal must run independently, or use an incrementally maintained implementation
whose bounded cost is demonstrated. Never hold computation/dependency locks during
evaluation or delivery. Measure simultaneous large-batch completion, slow/unavailable
tracking storage, root-lock contention and evaluator crashes against disabled
completion/next-job latency; HTTP isolation alone does not prove noninterference.

Use worker terminal transitions as candidate triggers for reevaluating the root;
they do not themselves prove the hierarchy is terminal. Cancellation and abandonment
also need coverage, potentially via a bounded reconciliation pass. Terminal event
creation must be idempotent under simultaneous child completions. Event commit
must conditionally validate the same membership revision, producer-closure evidence
and relevant state generation used to establish settlement; a conflict forces
reevaluation. A checked snapshot followed by an unconditional unique insert is
insufficient. Test membership/retry/requeue changes between evaluation and commit.
Callback delivery is outside the tracked computation hierarchy to avoid recursive notifications.

This generic mechanism reports persisted execution outcomes, not scientific validity
of arbitrary returned results. If a task catches a domain failure and returns
normally, no job graph can infer that hidden failure. Under accepted Option A,
clients retrieve domain results separately. Do not add task-reported domain
outcomes or domain-specific detectors to this release.

Delivery runs outside computation capacity. A small dedicated RQ delivery worker
using existing Redis is a candidate, not yet a selected topology. A separately
executed bounded dispatcher is another candidate. Short HTTP timeouts alone do
not make delivery on a normal computation worker nonblocking. Compare the smallest
options and record resource, recovery and operating costs before selection.

The earlier indexed-observer proposal meant periodically reading only explicitly
subscribed job IDs. It is no longer the prescribed first architecture. A bounded
read-only reconciliation pass may be useful to recover a missed handoff, but must
be justified by failure evidence. Never use registry APIs that implicitly run
cleanup, mutate task state or extend job retention.

## Reliability and audit proposal

Retain callback intent before a worker can race ahead of submission completion.
Specify atomicity and ambiguous-submission recovery using the existing enqueue
patterns. Do not report "submission failed" after creating a computation job merely
because webhook bookkeeping failed. Define whether malformed webhook admission
rejects submission before enqueue and how webhook-store unavailability is reported.

Distinguish accepted callback intent, captured operation outcome and receiver
acknowledgment. Storage/retention and crash recovery must make their loss windows
explicit; neither log-only handoff nor Redis AOF everysec implies zero loss.
Bound attempt history, pending count/bytes and per-client/global resource use.
Retain a sanitized audit record including event/job ID, destination identity,
attempt timestamps, HTTP status/error category and final delivered/exhausted state.
Unknown membership/outcome must have a published bounded evaluation/retention
window and an audited `outcome_unavailable` terminal notification-tracking state,
not a fabricated computation failure. Specify which minimal membership/outcome
records survive that window without silently extending task TTLs. Test deleted or
expired children, result_ttl=0, orphan registrations and evaluator outages. No new
consumer history API is required for this operator-visible resolution.

No delivery-history API, manual replay API or endpoint management API is required
by the current request; evaluate those separately if needed.

Proposed retry classes: transient connection failures, 408, 429 and selected 5xx;
no ordinary 4xx or redirect retries. Honor Retry-After only inside the documented
budget. Define explicit pause/resume and outstanding-attempt recovery. Do not alter
shared Redis persistence or flush task data to satisfy notification durability.

## Implementation plan and acceptance

The [implementation package](../work-packages/20261027_rq_webhooks/package.md)
tracks this revised direction. First map existing hierarchy registration and dependency
semantics across culvert and WEPP as representative cases. Define the generic
settled predicate, root membership and minimal independent delivery placement, then settle wire payload, retry/timeout,
retention, audit and optional-signing decisions. Retain a scoped synthetic prototype
with no live stack changes before the canonical checkpoint.

Promote the accepted contract to `docs/schemas/rq-webhook-contract.md`, amend current
response/runtime/auth contracts as needed, record numeric decisions in an ADR, and
obtain two independent contract reviews before the standalone ancestor commit.
Earlier reviews concern the superseded design and do not approve this revision.
The [2026-10-28 hierarchy review](../work-packages/20261027_rq_webhooks/artifacts/20261028_hierarchy_review.md)
records current findings and their dispositions.

Activate callback admission only after verifying instrumentation across all
supported producers/workers, including bulk/pipeline paths. Mixed/uninstrumented
paths must reject unsupported callback admission before computation enqueue or
explicitly retain incomplete tracking; never claim a complete hierarchy. Admission
disable/rollback must drain or preserve tracking for accepted callbacks. Test a
mixed deployment and rollback while parents still create children.

Implement only after that checkpoint and scoped execution authorization. Validate
actual API submissions with per-request URLs, token expiry during a long workflow,
culvert partial outcomes, full WEPP postprocessing and failing prerequisites that
leave final jobs deferred. Test missing callback state, fast completion, retries,
duplicate delivery, ambiguous enqueue, receiver hang/timeout/429/5xx, dispatcher
crashes and audit loss/recovery. Test SSRF/TLS/redirect controls and quota fairness.

Compare computational throughput and model input/output/report artifacts with a
webhook-disabled baseline under hung receivers and backlog. Use real storage and
HTTP boundaries, then authorized forest identities/mounts/orchestration. Native
RQ webhooks remain excluded. Do not close on unit tests or job success alone.

## References and review status

- [RQ response/runtime contract](../schemas/rq-response-contract.md)
- [Historical draft review](rq-webhooks-draft-review-20261027.md)
- [Current decision register](../work-packages/20261027_rq_webhooks/artifacts/decision_register.md)

The 2026-10-27 review findings retain useful correctness/noninterference tests.
Registered endpoints, mandatory durable grant/revalidation infrastructure,
destination challenges and mandatory secret encryption are no longer selected
requirements. The operator's 2026-10-28 client-facing direction supersedes them. Later clarification
requires generic hierarchical terminal detection, not per-workflow completion adapters.
