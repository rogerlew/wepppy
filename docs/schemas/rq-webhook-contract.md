# RQ operation webhook contract

Status: Accepted 2026-10-28 19:56 UTC; implementation/activation pending.
Operator approved the exact RQ-WH-01 decision matrix and authority grants.
Native RQ webhooks stay disabled. The requirements below govern implementation.

## Scope and rationale

Initial admission surface (direct service paths): POST `/api/culverts-wepp-batch/`,
POST `/api/runs/{runid}/{config}/run-wepp`, `/run-wepp-watershed`, and
`/prep-wepp-watershed` (the latter two share the same run/config prefix).
The culvert field is a multipart text field beside the existing ZIP upload;
WEPP uses its existing JSON/form parser. Operation names are respectively
`culverts-wepp-batch`, `run-wepp`, `run-wepp-watershed`, `prep-wepp-watershed`.
The mechanism is generic; this finite admission scope permits instrumentation
verification. Other submission routes reject a supplied callback as unsupported;
adding an admission route requires coverage evidence, not a new completion detector.

Preserve existing authentication, scope, feature-group, resource access and CSRF
checks. Passing those checks authorizes one callback for that submission. Do not
store or forward bearer credentials, recheck expiry during dispatch, or grant the
receiver access to project data. Cancellation does not revoke accepted intent.
An explicit operator dispatch pause is separate from ordinary token expiration.
No registration, destination challenge, history/replay API or signing-key service.

## Admission and recovery matrix

`webhook_url` absent preserves the existing route response and behavior, including
synchronous batch/base-project input updates. Present means exactly one nonempty
string; null, blank, duplicate form keys, arrays and objects are invalid. Do not
coerce or silently discard malformed callback values. Validate before input mutation,
ZIP extraction or computation enqueue. Synchronous input-only WEPP mode rejects a
callback before applying inputs because it starts no operation.

Callback-bearing requests also require `Idempotency-Key`, an opaque ASCII token of
16–128 characters from `[A-Za-z0-9._-]`. This additional requirement is proposed to
make initial culvert submission recoverable after a lost response; resource locks
alone cannot deduplicate creation of a new batch UUID. Bind it to the verified
principal, operation, resource and canonical request digest, including the URL and
actual upload digest. Neither key nor digest is an authorization credential.
Do not persist arbitrary request bodies in this receipt. Retries authenticate anew.

Receipt/quota principal identity is typed and issuer-scoped: verified canonical
account ID for human user/delegated-human credentials, verified session ID for
anonymous sessions, and registered integration subject for independent service/MCP
credentials. Include token class/origin where needed to prevent cross-class aliasing;
never use bare numeric sub, jti, mutable group membership or an anonymous fallback.
Resolve human delegation through existing verified identity adapters. The identity
must remain stable across renewal of the same credential family. If a credential
accepted by the underlying route lacks a verified stable principal mapping, reject
only its callback request with 400 `webhook_principal_unsupported`; ordinary requests
remain unchanged. Different issuers/classes cannot retrieve each other's receipts.

| Condition | HTTP / canonical error code | Effect and recovery |
| --- | --- | --- |
| No callback | Existing contract | No notification record; no new header required |
| Valid URL and key, supported async mode | Existing success status and body plus `webhook: {status: accepted}` | Intent and root publication committed together; existing `job_id` is correlation ID |
| Missing/invalid key or malformed URL/type | 400 `invalid_webhook` | Expected validation error; no enqueue or input mutation |
| Unsupported route or synchronous input-only mode | 400 `webhook_not_supported` | Expected capability error before mutation |
| Same principal/key and identical request | Same accepted receipt with refreshed credentials as below, or 202 `webhook: {status: admission_pending}` with planned `job_id` | Resume/read the same admission; never create a second operation |
| Same key has expired unavailable admission tombstone | 410 `webhook_admission_unavailable`, `error.details: {job_id, publication: not_published or unknown}` | No enqueue; new-key resubmission is safe only when absence of publication was proved; unknown may duplicate work and requires operator reconciliation |
| Callback principal cannot be mapped stably | 400 `webhook_principal_unsupported` | No enqueue or mutation; use ordinary submission or a supported identity |
| Same principal/key with different request | 409 `webhook_idempotency_conflict` | No mutation; choose a new key for new work |
| Per-principal capacity exhausted | 429 `webhook_capacity_exceeded` | No enqueue; Retry-After 60 seconds |
| Global capacity, disabled/incomplete instrumentation, store unavailable before publication | 503 `webhook_unavailable` | No enqueue; Retry-After 60 seconds |
| Publication acknowledgment lost, exact root/intent recovered | Original success | Never report failed submission for committed computation |
| Publication outcome cannot be read | 503 `webhook_admission_unknown` with `error.details.job_id` and instruction to retry the same key | Exceptional uncertainty, not a claim of nonacceptance; do not retry with a new key |

Pre-publication reservations survive API crashes. Recovery under the existing
submission lock must verify the planned root, exact request binding and publication
receipt before completing an admission. Unknown records are never blindly enqueued.
An accepted duplicate must not rerun input mutation or extraction. An in-progress
reservation with no proof of publication remains pending until verified or expires;
expiry resolves it as admission unavailable, not permission to enqueue again with
that key. Keep the deduplication tombstone through the retention period below.
A request with a new key is new work, subject to existing single-flight rules.
After deduplication retention expires, clients must not retry old keys.

Store only allowlisted credential-free response fields: job_id, batch UUID,
status_url and webhook receipt. For culvert success/replay mint a fresh browse token
through the existing helper under fresh normal route authorization and the original
batch/principal binding; preserve its existing audience, scope and expiry policy.
Never store/replay browse_token or browse_token_expires_at. If issuance fails after
publication, return HTTP 202 with those committed identifiers,
`webhook: {status: accepted}`, and
`warnings: [{code: browse_credential_unavailable, message: "Retry the same submission key to obtain browse credentials; computation is already accepted."}]`.
Omit browse credential fields on that response. Do not remove staged inputs, report
computation failure, or enqueue again. Same-key retry reattempts issuance only after
authorization; no new token-renewal API is introduced.

## Event envelope

Send an unsigned HTTPS POST with `Content-Type: application/json`,
`Webhook-Id: <event_id>` and stable UTF-8 JSON body, bounded by the ADR. No API token,
cookie, signature or arbitrary client headers. First-release unsigned delivery
avoids an unrequested key lifecycle. Receivers treat it as a hint and confirm any
sensitive action through existing authenticated result APIs.

```json
{
  "schema_version": 1,
  "event_id": "server-generated-uuid",
  "event": "operation.completed",
  "job_id": "original-root-job-id",
  "operation": "run-wepp",
  "resource": {"type": "run", "id": "authorized-run-id"},
  "execution_status": "finished",
  "settled_at": "2026-10-28T20:00:00Z",
  "observed_at": "2026-10-28T20:00:01Z"
}
```

Resource type is `run` or `culvert_batch`; the latter ID is the accepted batch UUID.
No child list, filesystem path, results, arguments, tracebacks or domain summary.
`settled_at` is the time closure evidence became complete, not parent ended_at;
`observed_at` is evaluator observation time. Both are UTC RFC3339 timestamps.
Persist the exact bytes once. Retries reuse bytes and event ID. A lost acknowledgment
can cause duplicate delivery; there is no exactly-once or guaranteed-receipt promise.

After settlement, aggregate precedence is `failed` > `stopped` > `canceled` >
`finished`. A terminal failed member or a proven dependency block rooted in failed
execution contributes failed; stopped/canceled blockers contribute their respective
status, including verified external blockers without disclosing their identities.
Failures that are still eligible for automatic retry do not settle. A prior failed
attempt superseded by a successful retry is not a final failed member.
`finished` asserts settled execution without RQ failure, never domain success.
Caught culvert errors may coexist with finished execution and failed domain results.
Manual requeue after a committed event requires a new API submission/key; direct
operator requeue of an already-notified hierarchy is outside supported callback
semantics and cannot revise or generate a second event for that submission.

## Membership, settlement and event commit

Membership is server-owned root/parent identity, distinct from dependency edges.
Descendants inherit an opaque root reference, never the destination. Reject client
attempts to set reserved root/parent/notification metadata. External prerequisites
are observed dependencies, not owned payload members. Detached maintenance must
use an explicitly audited server-only detached context; arbitrary child code cannot
choose a new destination or silently detach required postprocessing.

Settled requires complete publication and producer closure, and every member to be
terminal or provably blocked by the actual dependency rules. Traverse beneath failed
parents. Queued, started, scheduled, pending-retry and active-producer states keep it
open. Missing records, incomplete publications, cycles, unverified external edges,
unknown execution exit and unsupported instrumentation mean unknown, never success.

A strict deferred member with a permanently unsuccessful prerequisite is blocked.
Blocking propagates through a still-deferred prerequisite even when its descendant
allows failure: logical blocking is not RQ FAILED. Direct failure-tolerant edges
accept actual FAILED and must be awaited. CANCELED is not accepted. STOPPED uses
only the existing explicit stopped-observer release contract. Until that release
handler closes, the evaluator cannot classify its observer as blocked. Never release,
cancel, retry or alter jobs to make notification possible.

Use minimal retained member receipts for terminal state, final-attempt identity,
dependency policy and producer exit; do not extend existing job/result TTLs. A missing
job without a trustworthy receipt remains unknown. Parent return or canceled status
alone cannot close a producer: enqueue-capable callbacks, outstanding pipelines,
workhorse/supervisor lifecycle and process-exit evidence must be included. Detached
untracked processes cannot establish complete closure. Abandonment recovery may close
only with verified execution exit; uncertainty ages out without fabricating failure.

The implementation additionally requires the actual RQ job hash when committing an
event. Its dedicated attempt-generation field is written atomically with ordinary
pre-fork metadata, independent of optional receipt success. The predecessor must
match the last tracked attempt; a gap permanently invalidates closure proof, including
overlapping retries. Older job metadata saves cannot overwrite these dedicated fields.
Only the first publication seeds the never-started generation; recreation cannot
reset it. Committed root publication without that initial member/generation proof
permanently marks notification tracking incomplete while preserving computation.
Missing hashes, including zero-TTL deletion, remain unknown: an old closure receipt
cannot exclude an entirely missed rerun that also deleted its job. This conservative
loss boundary preserves existing RQ retention rather than extending it for callbacks.

Publication registers child identity and reservation before visibility, and commits
publication evidence with RQ publication in the same Redis transaction. Bulk,
deferred, direct and caller-owned pipeline paths need explicit coverage. A canceled
or discarded pipeline leaves a reservation unresolved until its producer proves
abort; an API return is not commit evidence. Instrumentation failures must not alter
computation: the producer cannot issue a complete closure receipt after a missed
registration. Missing closure is recovered or ages out as unavailable.

Evaluate outside computation workers. Use a paginated snapshot and per-root revision
covering membership, publication, retry/state generation and producer closure. Every
supported writer participates. Conditional event creation validates that same revision
and closure atomically and inserts one immutable event; conflicts reevaluate. A unique
insert after an unchecked snapshot is insufficient. State transitions or manual requeue
outside instrumentation invalidate proof; activation requires writer coverage, not
merely an enqueue wrapper. No registry reads with implicit cleanup, KEYS/all-job
scans, computation locks, graph mutation or RQ TTL extension.

## Storage, independent execution and loss boundary

Use a notification namespace in the existing RQ Redis database, with bounded
intent, membership, due-work and sanitized audit indexes. This permits atomic root
publication and event transitions without a cross-database transaction or new broker.
A dedicated dispatcher process performs evaluation and delivery; it consumes no
computation RQ queue. A bounded killable attempt subprocess makes the total deadline
include DNS. No additional third-party dependency is selected. Concrete service
configuration requires scoped stack approval and measured isolation before activation.

No webhook guarantee exceeds the existing Redis persistence policy. Process crashes
with Redis state intact recover from receipts/due indexes and expiring fenced claims.
Redis loss can lose accepted callbacks and audits; no zero-loss durability or bounded
host-loss window is promised. Do not change shared AOF policy. Expose this limitation
in API docs; keep operator backups under existing secret-access restrictions.

Bounded worker hooks record local lifecycle evidence and signal due work; they do
not traverse roots or wait for HTTP. Their target incremental deadline and measurements
are in the ADR. If bookkeeping fails, suppress complete closure and continue existing
computation behavior. Independent reconciliation of subscribed roots recovers missed
signals; it never scans unrelated jobs. Unknown tracking expires to operator-visible
`outcome_unavailable`; no operation.completed event is invented.

## Egress and audit

HTTPS only, port 443 (explicit or default), no userinfo, fragment, control characters,
backslashes, IP-literal targets or ambiguous host syntax. DNS hostnames must be valid
ASCII or normalized IDNA and fit URL bounds. Resolve at every attempt; reject any
answer outside public global unicast, including loopback, private, link-local,
multicast, reserved, IPv4-mapped unsafe IPv6 and transition-address bypasses. Pin the
validated address for connection; preserve original hostname SNI and certificate
verification and verify peer address. No environment proxies, redirects, downgrade,
credential forwarding or second implicit DNS resolution. DNS changes are allowed
only after full revalidation; public destinations do not need registration.

Raw URLs (paths and queries can be capabilities) exist only in restricted intent,
never RQ arguments/descriptions/meta, profiles, playback, public polling, ordinary
logs or project archives. Audit uses sanitized hostname plus opaque random destination
ID, principal ID, root/event ID, attempt number/time, HTTP status or bounded error
category and final state. Never record response bodies, arbitrary exception text or
receiver headers. Remove callback fields from captures and default playback; an
explicit test URL override must pass normal admission. Do not replay captured keys.
Notification records are operator infrastructure, outside scientific project artifacts;
existing project browse/archive content remains unchanged. This exclusion was approved in RQ-WH-01; sanitized status is inspectable by operators.

## Retry and operator controls

Numeric policies and rationale: [ADR-0109](../adrs/ADR-0109-rq-webhook-bounds.md).
Only HTTP 2xx acknowledges. Retry connection failures, DNS temporary failures,
timeouts, 408, 429, 500, 502, 503, 504. TLS validation, unsafe resolution, permanent
DNS failure, redirects and all other status codes are terminal delivery errors.
Read only bounded headers; never consume or retain receiver bodies. Retry-After
accepts delta-seconds or HTTP-date, clamped to the remaining age and configured cap;
malformed values use the normal schedule. No computation-worker sleeps.

Separate controls: admission disable rejects new callback requests while preserving
old records; dispatch pause prevents new attempts but permits evaluation; component
stop pauses both. Deadlines/retention continue on wall time during pause. Resume
records expired work as exhausted/unavailable rather than extending authority forever.
Claims use owner tokens and fencing; crash recovery cannot overwrite newer attempts.
Persist attempt-start before HTTP; an interrupted attempt counts toward the limit.
Bind notification records to an operator-configured environment identity. A copied,
restored or rolled-back store starts with admission and dispatch disabled, including
when the backup contains an enabled flag; an external startup control must enforce
this. Evaluation may inspect records but must not send. Production disaster recovery
requires explicit operator review of lost acknowledgment/attempt history and possible
duplicates before rearming that environment. Test/copy environments must never send
to restored destinations: discard callback intents or explicitly replace them with
controlled test destinations and new test event identities. Ordinary process restart
against the unchanged live store may recover fenced claims without reauthorization.
Validate copied-store, stale-backup and ordinary-restart cases separately.
Admission disable and rollback must retain instrumented execution until accepted
producers drain, or explicitly mark affected roots unavailable; never silently
reclassify incomplete tracking as complete. No shared Redis flush or RQ downgrade.
