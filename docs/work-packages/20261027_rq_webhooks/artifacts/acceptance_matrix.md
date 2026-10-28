# RQ webhook implementation acceptance matrix

Status: planned, 2026-10-28 18:47 UTC. No tests in this matrix have been executed
for the webhook feature. Record exact test/probe and evidence links as implemented.
This matrix carries accepted Option A and hierarchy review obligations into testing;
it does not select remaining numeric policies or authorize runtime changes.

| ID | Constructed state / action | Required observation | Evidence |
| --- | --- | --- | --- |
| A01 | Existing API submission without callback | Existing response, computation and artifacts unchanged | Pending |
| A02 | Valid URL; token expires before workflow settles | Accepted callback attempted independently of token expiry | Pending |
| A03 | Malformed/unsupported URL; ambiguous submission commit | Ratified admission response, no unreported accepted job or duplicate operation on retry | Pending |
| H01 | Parent finished; nested child running | No completion event until whole owned hierarchy settles | Pending |
| H02 | Failed batch parent/child with independent runnable siblings | Failure-known but unsettled; wait for siblings and runnable finalizers | Pending |
| H03 | Strict failed prerequisite and deferred descendants | Settled execution failure once all remaining work is terminal or provably blocked; no RQ mutation | Pending |
| H04 | A failed -> B strict/deferred -> C allow_failure | C logically blocked because B is not actually failed; no indefinite wait or invented release | Pending |
| H05 | A failed -> C allow_failure | Await C; also test actual stopped/canceled rules and approved stopped-observer exception | Pending |
| H06 | Automatic retry queued/scheduled; independent external dependency | Not settled while execution can advance; external prerequisite not an owned payload member | Pending |
| H07 | Delayed callback creates children; canceled producer still executes | Producer closure remains unresolved; no early terminal event | Pending |
| H08 | Child publication races parent completion; bulk/pipeline enqueue; producer crash | Complete membership or explicit uncertainty, never silently omitted children | Pending |
| H09 | Membership/retry/requeue changes between snapshot and event commit | Conditional commit rejects stale result and reevaluates | Pending |
| H10 | Concurrent last-child completions | One immutable logical event; duplicate delivery remains possible | Pending |
| H11 | Missing/expired child, zero retention, orphan registration, cycle | No invented success/failure; bounded audited outcome_unavailable per published tracking policy | Pending |
| H12 | Workhorse death, abandonment, timeout and cancellation | Generic evaluator handles actual terminal/recovery states without registry cleanup side effects | Pending |
| H13 | Spoofed lineage, foreign root, detached maintenance, interleaved clients | Server-owned binding preserved; foreign jobs excluded, callback cannot be redirected by descendants | Pending |
| O01 | Culvert catches domain failure and RQ members all finish | operation.completed with execution_status finished; no domain-success claim; existing results expose failure | Pending |
| O02 | Uncaught RQ failure within settled hierarchy | Execution failure reported under ratified precedence; distinct from O01 | Pending |
| D01 | Healthy receiver | Exact payload bytes conform; acknowledgment and sanitized audit recorded | Pending |
| D02 | Hung DNS/connect/TLS/read or slow/oversize response | Entire attempt bounded by ratified total deadline; computation capacity unaffected | Pending |
| D03 | Network error, 408/429/selected 5xx versus ordinary 4xx/redirect | Only documented limited transient retries, bounded Retry-After; final exhaustion audited | Pending |
| D04 | Receiver acknowledges; sender dies before recording receipt | Stable event ID/body on redelivery; receiver can deduplicate | Pending |
| D05 | Simultaneous delivery claims; lease expiry; evaluator/dispatcher outage | Ratified recovery/loss bounds honored, no event mutation or silent permanent lease | Pending |
| S01 | Rebinding, mixed IPv4/IPv6, internal target, redirect, invalid TLS | Selected connection-time egress controls hold without registration/challenge requirement | Pending |
| S02 | Raw URL with path/query capability passes through recorder, logs, archives and jobinfo | Raw URL stays only in restricted intent; audit uses safe host/fingerprint | Pending |
| S03 | Capture-enabled request followed by dry-run/executed playback | No raw URL disclosure or unsolicited send to recorded destination; omit intent or explicit test override | Pending |
| N01 | Large concurrent batch completions with tracking-store latency/root contention | Bounded computation-side work; measured completion/next-job latency within ratified baseline limits | Pending |
| N02 | Receiver backlog, quota-abusing client, storage pressure | Fair bounded notification load; no computation cancellation/throttling to free notification capacity | Pending |
| R01 | Mixed instrumented/uninstrumented producers; rollback while parent enqueues | Unsupported callback admission rejected or explicitly incomplete; accepted callbacks retained/recovered | Pending |
| R02 | Disable admission, pause dispatch, restart and restore pending records | Distinct controls, published age/lease semantics, no shared Redis flush or RQ downgrade | Pending |
| R03 | Copy environment or restore stale backup with pending deliveries | Dispatch defaults disabled outside ordinary live-store restart; explicit recovery accounts for duplicate risk; test copies never send to original URLs | Pending |
| A04 | Same-key replay after browse credential expiry or mint failure | Credential-free persisted receipt; fresh authorization/mint, accepted computation preserved, no second enqueue | Pending |
| A05 | Expired unavailable admission tombstone | Exact 410 response distinguishes proven nonpublication from unknown; no unsafe new-key retry instruction | Pending |
| S04 | Same sub across credential classes/issuers; same identity after jti rotation | Distinct typed principal bindings across identities; stable receipt/quota binding across renewal; no anonymous fallback | Pending |
| E01 | Actual culvert batch and selected WEPP pipeline under healthy/failing receivers | API-to-receiver behavior and execution/domain distinction proven on authorized environment | Pending |
| E02 | Webhook-disabled versus backlog/failure project execution | Prepared inputs, fresh model outputs and reports semantically match; exact runtime provenance retained | Pending |

## Evidence requirements

Test absent, present-empty, populated, supported legacy and malformed/hostile
optional state separately from request combinations. Use synthetic graphs to prove
generic behavior without task-name-specific logic. Use real persistence, worker
processes and HTTP boundaries for races and recovery. Never substitute a successful
job, file existence or broad-suite pass for exact payload/artifact readback.

The canonical checkpoint must specify expected responses, execution status
precedence, numeric bounds and allowed loss windows before the associated rows can
be judged. Link targeted regression tests and retained integrated artifacts here;
record justified exclusions as explicit scope decisions rather than passing them.

## Kickoff substrate evidence (2026-10-28)

[Real Redis/RQ discovery probes](20261028_source_and_probe_evidence.md) exercise
parts of H04/H05/H08/H09, but do not implement the webhook evaluator. All feature
acceptance rows remain Pending. Exact proposed policies now live in the
[checkpoint contract](../../../schemas/rq-webhook-contract.md) and ADR-0109;
operator ratification and implementation acceptance have not occurred.
