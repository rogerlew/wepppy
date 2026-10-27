# RQ webhook contract and implementation planning draft

Status: discussion draft, 2026-10-27. Not an accepted contract or authorization
to implement. RQ 2.12.0 remains the runtime target; native RQ webhooks remain
disabled. The completed upgrade package is historical evidence, not an amendment
target. This draft will be promoted into `docs/schemas/` after scope agreement.

## Confirmed requirement

API clients can request webhook notifications. Delivery success, failure,
timeouts, retries, and dispatcher outages must not alter computation job status,
release or block dependencies, change computation retries, or occupy computation
workers with HTTP requests. Shared datastore resource use must be bounded and
measured; absolute isolation from shared infrastructure outages is not promised.

## Product choices awaiting agreement

| Choice | Proposed starting point | Alternative |
| --- | --- | --- |
| Event scope | Explicit individual jobs | Domain workflow completion, or both |
| Reliability | Persisted events, bounded retries, history and manual replay | Best effort with polling recovery |
| Destination | Register an owned endpoint, reference its ID | URL on every submission |

These are recommendations, not decisions already made by the operator. API
shape, storage, delivery capacity and numeric policies remain provisional.

## Proposed event semantics

Start with terminal job outcomes: `job.finished`, `job.failed`, `job.stopped`,
and `job.canceled`. A failed attempt scheduled for retry is not final failure.
Cancellation describes RQ state; it must not claim that every descendant process
has exited or that directory locks have been released. Unknown, expired or
unreadable state is an observation problem, never fabricated success or failure.

Job success is not proof of artifact validity or completion of dynamically
enqueued children. Workflow events require named domain completion boundaries,
expected child membership and artifact acceptance; do not infer them from the
parent task returning or an empty instantaneous child list.

For an initial job subscription, propose one terminal event. Close observation
atomically with creation of that immutable event, not with HTTP acknowledgment.
Enforce one event per subscription; competing observers recover the same event
ID. Pending delivery cannot replace its outcome when the job is requeued.
Requeueing after event capture requires a new subscription; retries
before terminal completion stay within the existing subscription. Concurrent or
repeating executions need an explicit execution-level contract before support.
Polling can miss a transient terminal state followed by requeue; this is a
specific acceptance risk to test, not an exactly-once promise.

Use immutable event bodies with `schema_version`, `event_id`, `event_type`,
`subscription_id`, exact `job_id`, authorized run identity when applicable,
`status`, `subject_type: rq_job`, and `observed_at`. This status describes the
individual persisted RQ job. Existing jobstatus can aggregate descendants: a
parent's `job.finished` event and an aggregate running or failed polling response
can both be correct. Include an occurrence timestamp only when reliably
available; do not invent it from observation time. Do not include arbitrary
results, arguments, stack traces, filesystem paths, bearer credentials, or auth
actor metadata. Clients fetch permitted details through existing APIs.

Duplicate delivery is possible, including after an acknowledgment is lost.
Receivers deduplicate by event ID. Attempts and manual replay retain the same
event ID and body, with a new delivery attempt identity and signing timestamp.
No global ordering guarantee is proposed.

Observation lifetime and delivery age are separate clocks. The proposed retry
window starts at durable event creation, not subscription creation; long queue
waits must not consume it. Specify supported observation deadlines, job retention
and observer outage bounds before promising outcome capture. Durable retries
after capture do not guarantee capture of every transition. Expose terminal
`observation_expired` or `observation_unavailable` in subscription history when
the outcome cannot be established, without emitting an invented job event.

For the separate-subscription candidate, propose immediate capture of a retained
terminal job after authorization. Reject missing or unsupported jobs explicitly.
An idempotency key scoped to principal and operation recovers the same
subscription/event after an ambiguous commit; the same key with different input
is a conflict. A fresh key permits a deliberate new subscription after requeue.
Do not deduplicate subscriptions by job ID alone. These admission semantics must
be ratified with the selected API shape.

## Ownership and endpoint lifecycle

Every webhook operation requires authenticated authorization independent of the
existing optional/open job polling mode. Use a stable verified client principal,
not token `jti`, and retain ownership across token renewal. Endpoint ownership
alone is insufficient: subscriptions also require permission for the target
job/run and applicable feature. Public run visibility must not implicitly grant
permission to create outbound subscriptions. Map supported token classes and
revocation semantics explicitly before implementation.

Stable identity is not durable dispatch authority. Require a bounded subscription
grant covering the exact job/resource, endpoint version, event types, lifetime
and revocation authority. Reuse verified identity adapters without treating them
as scope/resource authorization. Ratify token-expiry versus renewal/revocation,
narrower replacement credentials, removed run access and account/session changes.
Unknown or unavailable authorization pauses delivery; it never changes RQ work.
Reject token classes without a supported durable grant model in the first release.

Proposed API resources under `/rq-engine/api`: endpoint registration and disable,
job subscriptions, delivery history, and replay. Exact routes and scopes are
pending. Registration creates no subscription to all of a client's future work.
Subscriptions and replay are idempotent; authorization precedes lookup disclosure.
Use the canonical RQ error envelope. Endpoint secrets and delivery records must
never enter public jobinfo responses or downloadable run archives.

Prefer an immutable URL per endpoint version. A URL replacement requires a new
version and must not silently redirect pending events. Disabling an endpoint
prevents new sends; an already transmitted request cannot be recalled. Secret
rotation, pending attempts, disabled records, and deletion retention require
explicit lifecycle rules. Recheck dispatch authorization/revocation without
requiring the original short-lived bearer token to remain valid forever.

Endpoint-record ownership does not establish control of the destination. Before
activation, select a bounded exact-URL challenge under the same outbound security
policy or operator-approved registration. No event data may leave before
activation; a changed URL version requires revalidation. Any policy allowing
unverified public destinations needs explicit operator risk acceptance and abuse
limits, rather than describing those destinations as controlled by the client.

Set per-principal quotas for endpoints, pending subscriptions and deliveries,
registration/subscription/replay rates, stored payload sizes, and fair scheduling.
Define canonical quota-exhaustion responses and numeric limits before activation.
Quota rejection must not fail or cancel an already accepted computation job.
Bound subscription lifetime, pending-event bytes/count and attempt-history growth
both per principal and globally, including indefinitely deferred jobs. On overload,
reject new webhook admission explicitly and preserve accepted records within their
published retention policy. Do not throttle computation to free webhook capacity.

## Delivery and destination security

Use HTTPS POST, verified TLS, bounded DNS/connect/read/total attempt time, bounded
response handling, and no redirects. Reject credentials in URLs and destinations
that resolve to prohibited internal, loopback, link-local, metadata or other
nonpublic addresses, including IPv6 and mixed-address answers. Validate the
address actually connected to while retaining hostname TLS verification; a
registration-only DNS check does not prevent rebinding. Define explicit policy
for ports, proxies, and any operator-approved private destinations. Do not allow
arbitrary caller-supplied headers in the initial API.

Sign the exact transmitted body together with event ID and per-attempt timestamp
using a versioned HMAC-SHA256 envelope. Generate per-endpoint secrets and provide
rotation and receiver examples. Inventory the existing secret facilities before
selecting encryption: deployment secret-file lookup is not a dynamic encrypted
credential store. Ratify separate webhook encryption keys, key versions, one-time
secret disclosure or another explicit retrieval policy, rotation overlap, access
boundaries and backup/restore recovery. Do not reuse JWT/session signing keys.
Missing decryption material explicitly stops notification operations while
computation stays available. Do not invent an unreviewed key store.

Any 2xx acknowledges receipt. Retry transient network failures, 408, 429 and
appropriate 5xx responses with bounded backoff and jitter; honor Retry-After
within the maximum delivery age. Other 4xx and redirects end automatic delivery.
Persist final exhaustion and permit authorized, rate-limited replay. Numeric
limits, retry policy, retention and latency objectives need explicit decisions
and the required parameterization ADR before implementation.

## Smallest implementation candidates

First evaluate an indexed observer of explicitly subscribed job IDs. It reads
terminal RQ state and records an immutable event independently of computation
workers. This can avoid changes to all enqueue routes and cover terminal state
written by cancellation or abandoned-job cleanup. A separate subscription call
after enqueue is a possible minimal API, provided retained fast-completing jobs
remain observable. No whole-Redis scans or Redis KEYS commands are acceptable.

Observation must use side-effect-free reads of committed exact-job state, not
callback-local `job._status`. Do not invoke registry cleanup, enqueue dependents,
retry jobs, or alter retention. RQ registry enumeration defaults can run cleanup;
any necessary enumeration must explicitly disable it and have a bounded index.
The observer reports state established by RQ; it does not repair tasking.

Before selecting this design, test fast completion, result_ttl=0, short retention,
job deletion, manual requeue, dispatcher outage and required notification latency.
The current worker's default result retention is one week; it is not a guarantee
for every job. Subscription admission must establish supported retention and
execution semantics without silently changing task retention defaults.

If evidence shows observation cannot meet the agreed contract, evaluate bounded
post-commit terminal receipts in WepppyRqWorker plus reconciliation. Hooks must
never perform HTTP. Existing success/failure hooks alone do not cover queued
cancellation, every abandonment path, or the crash between job commit and receipt.
No catch-and-log handoff can honestly guarantee no event loss by itself.

Separate durable event creation from delivery attempts. Claim due deliveries
with expiring leases, conditional updates and idempotency; tolerate worker death
before/after HTTP acknowledgment. Schedule retries without sleeping inside
computation workers. Record attempts separately from original RQ job state.

Choose existing PostgreSQL or Redis only after evaluating persistence, eviction,
retention, access patterns, backups and recovery. Do not label Redis persistence
as lossless without verifying deployment settings. A PostgreSQL record and an
RQ enqueue are not one transaction; if subscriptions are attached at submission,
specify admission and ambiguous-commit recovery rather than reporting a failed
submission after a computation job was actually accepted.

Define separate acknowledgment boundaries for subscription acceptance, durable
event capture and receiver acknowledgment. Publish the selected datastore recovery
point and possible loss window. Current Redis startup defaults include AOF
`everysec` and snapshots; verify effective settings. An acknowledged write is not
a zero-loss recovery guarantee. Do not change shared persistence globally to
manufacture a webhook guarantee without separately authorized evidence.

Independent delivery execution needs a bounded deployment owner, resource budget,
restart behavior and backlog controls. Evaluate reuse of existing scheduling and
storage before adding a queue or service. Record evidence and operational cost
for any escalation. Native RQ webhooks and inline callbacks fail the required
worker-isolation condition because they perform blocking delivery.

Rollback must distinguish admission disabled, dispatch paused and component
stopped. Define in-flight attempt completion, lease drain/expiry, whether retry age
continues during pause, retained keys/records, backward-compatible schema access
and resumption after restore. Preserve pending and acknowledged-but-unrecorded
deliveries, allowing deduplicated redelivery. Never flush shared Redis or downgrade
RQ as a webhook rollback. Values and pause semantics remain ratification gates.

## Implementation milestones after ratification

1. Inventory pilot clients/routes, identity and retention contracts. Agree event
   scope, delivery guarantee, subscription API, revocation and numeric limits.
   Test the minimal observer candidate and record uncovered cases. Pre-checkpoint
   probes are disposable synthetic experiments with isolated Redis and HTTP test
   servers; they may not modify production paths, shared job state or forest
   runtime, read live job data, call external client endpoints or restart stacks.
   Scaffold the work package before sustained experimental execution. Integrated
   activation requires the accepted checkpoint and scoped environment authority.
2. Scaffold a work package and active ExecPlan. Promote the agreed normative
   contract to `docs/schemas/rq-webhook-contract.md`; amend affected auth/API and
   runtime contracts without reopening the upgrade package. Complete the
   contract-first decision checkpoint, two independent reviews and standalone
   ancestor commit before implementation.
3. Implement registration/subscription authorization and durable records with
   migrations, idempotency, secret handling and canonical errors. Preserve all
   webhook-absent requests and existing submission responses.
4. Implement observation or evidenced receipt/reconciliation design, then bounded
   signed delivery, retry scheduling, history, disable and replay. Add metrics for
   observation lag, pending age, attempts, exhausted delivery and authorization
   rejection. Redact URLs, query credentials, secrets and response bodies.
5. Run targeted security and lifecycle regression tests plus local integrated
   acceptance. Keep activation opt-in. Publish client and operator documentation,
   rollback and outstanding-event handling. Production rollout is separate.

## Acceptance matrix

Test endpoint absence, empty state, valid registration, token renewal, cross-client
access, revoked access, disabled endpoint, secret rotation and repeated requests.
Test bounded grants across token expiry, narrower renewal, credential/session
revocation, removed run access and authorization outages. Test endpoint activation,
cross-client fairness under quota abuse, and missing/rotated encryption keys.
Exercise success, failure with retries, queued cancellation, running stop, timeout,
workhorse death, abandonment, parent-before-child completion and post-terminal
requeue. Missing/expired state must produce explicit observation failure.
Test retained already-terminal jobs, ambiguous subscription commits, idempotency
conflicts, simultaneous observers and delayed delivery across requeue. Assert the
raw-parent-finished/aggregate-child-failed distinction. Prove observation performs
no RQ writes or registry cleanup and reads only committed outcomes.
Include an expired started-registry entry whose job and dependency graph remain
unchanged by observation. Ordinary RQ maintenance remains responsible for it.

Inject hung receivers, connection refusal, TLS/DNS errors, redirect chains,
rebinding, prohibited IPv4/IPv6 destinations, oversize/slow responses, 429 and
5xx. Verify signatures, deduplication, retry exhaustion, crash recovery, duplicate
dispatch claims and acknowledgment loss with actual persistence and HTTP servers.

Under receiver failure and delivery backlog, verify unchanged task outcomes,
strict dependency release, approved failure finalizers, cancellation containment,
worker capacity and representative generated artifacts. Measure shared datastore
load against a webhook-disabled baseline and enforce agreed resource/latency
bounds. Validate with actual forest identities, mounts and orchestration when
execution is authorized. Unit tests alone cannot close these boundaries.
Exercise sustained backlog and datastore pressure, disable/pause/restart with
outstanding leases, and restore after receiver acknowledgment but before local
receipt persistence. Verify retention and the published recovery loss boundary.

## Review status

Independent correctness, security and operations findings and their drafting-stage
dispositions are retained in the [review record](rq-webhooks-draft-review-20261027.md).
Resolving wording and decision gates is not runtime validation, operator
ratification, or the formal contract-first checkpoint review.

## References

- [RQ response and runtime contract](../schemas/rq-response-contract.md)
- [RQ migration and recovery](rq-2-12-migration.md)
- [Earlier integration proposal](webhook_integration_strategy.md)
- [Earlier implementation guide](webhook_implementation_guide.md)
- [RQ native webhook documentation](https://python-rq.org/docs/#webhooks)
- [OWASP webhook security guidance](https://cheatsheetseries.owasp.org/cheatsheets/Webhook_Security_Cheat_Sheet.html)

The earlier proposal and guide contain illustrative, unimplemented callback-based
designs. They are historical design context, not instructions to enable inline
HTTP delivery or evidence that their listed routes already support webhooks.
