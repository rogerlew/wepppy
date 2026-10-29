# RQ webhook implementation acceptance matrix

Status: local implementation acceptance passed. Contract ratified at `6ba2d8d9d`;
runtime implementation `62b272a6c`.
Evidence below distinguishes component tests and actual environment/performance
acceptance; production activation remains outside scope.

| ID | Constructed state / action | Required observation | Evidence |
| --- | --- | --- | --- |
| A01 | Existing API submission without callback | Existing response, computation and artifacts unchanged | Existing route regressions; [actual WEPP readback](workflow_readback_v6.json) |
| A02 | Valid URL; token expires before workflow settles | Accepted callback attempted independently of token expiry | [Actual WEPP delivery after expiry](workflow_readback_v6.json); [culvert delivery](culvert_domain_probe.json) |
| A03 | Malformed/unsupported URL; ambiguous submission commit | Ratified admission response, no unreported accepted job or duplicate operation on retry | API replay/publication/read-failure tests; [real restart barrier](restart_restore_probe.json) |
| H01 | Parent finished; nested child running | No completion event until whole owned hierarchy settles | Settlement tests; real worker hierarchy/callback tests |
| H02 | Failed batch parent/child with independent runnable siblings | Failure-known but unsettled; wait for siblings and runnable finalizers | Real worker hierarchy execution/domain regression; settlement tests |
| H03 | Strict failed prerequisite and deferred descendants | Settled execution failure once all remaining work is terminal or provably blocked; no RQ mutation | Settlement strict-blocking tests; no RQ mutation |
| H04 | A failed -> B strict/deferred -> C allow_failure | C logically blocked because B is not actually failed; no indefinite wait or invented release | Settlement mixed dependency-chain regression |
| H05 | A failed -> C allow_failure | Await C; also test actual stopped/canceled rules and approved stopped-observer exception | Settlement allow-failure tests; real stopped-worker regression |
| H06 | Automatic retry queued/scheduled; independent external dependency | Not settled while execution can advance; external prerequisite not an owned payload member | Real retry and watched foreign-prerequisite mutation regressions |
| H07 | Delayed callback creates children; canceled producer still executes | Producer closure remains unresolved; no early terminal event | Real timeout/stop/SIGKILL and late-thread/fork producer regressions |
| H08 | Child publication races parent completion; bulk/pipeline enqueue; producer crash | Complete membership or explicit uncertainty, never silently omitted children | Real bulk/discarded pipeline, late helper publication and poison tests |
| H09 | Membership/retry/requeue changes between snapshot and event commit | Conditional commit rejects stale result and reevaluates | Actual RQ mutation and foreign prerequisite WATCH race tests |
| H10 | Concurrent last-child completions | One immutable logical event; duplicate delivery remains possible | Conditional event tests and concurrent claim fencing |
| H11 | Missing/expired child, zero retention, orphan registration, cycle | No invented success/failure; bounded audited outcome_unavailable per published tracking policy | Unknown expiry/cycle tests; real zero-TTL worker regression |
| H12 | Workhorse death, abandonment, timeout and cancellation | Generic evaluator handles actual terminal/recovery states without registry cleanup side effects | Real timeout/stop/SIGKILL tests remain unknown without exit proof |
| H13 | Spoofed lineage, foreign root, detached maintenance, interleaved clients | Server-owned binding preserved; foreign jobs excluded, callback cannot be redirected by descendants | Explicit detached-context/spoofed-metadata test; 39 catalog regressions |
| O01 | Culvert catches domain failure and RQ members all finish | operation.completed with execution_status finished; no domain-success claim; existing results expose failure | [Actual mixed culvert readback](culvert_mixed_parallel_probe.json): 38 finished nodes, one success and 35 caught failures, exact finished callback |
| O02 | Uncaught RQ failure within settled hierarchy | Execution failure reported under ratified precedence; distinct from O01 | Real worker uncaught hierarchy test; [actual all-failed culvert finalizer](culvert_domain_probe.json) |
| D01 | Healthy receiver | Exact payload bytes conform; acknowledgment and sanitized audit recorded | [Exact persisted event bytes and HTTP 204](workflow_readback_v6.json) |
| D02 | Hung DNS/connect/TLS/read or slow/oversize response | Entire attempt bounded by ratified total deadline; computation capacity unaffected | [Controlled TLS total-deadline probes](https_probe.json); verified-sender backlog noninterference passed |
| D03 | Network error, 408/429/selected 5xx versus ordinary 4xx/redirect | Only documented limited transient retries, bounded Retry-After; final exhaustion audited | [TLS status/header probes](https_probe.json); [actual three-attempt HTTP 503 exhaustion](workflow_readback_v6.json) |
| D04 | Receiver acknowledges; sender dies before recording receipt | Stable event ID/body on redelivery; receiver can deduplicate | Interrupted concurrent claim/recovery test preserves exact event bytes and fences late receipt |
| D05 | Simultaneous delivery claims; lease expiry; evaluator/dispatcher outage | Ratified recovery/loss bounds honored, no event mutation or silent permanent lease | Real Redis concurrent claim, expired lease and stale scheduler tests |
| S01 | Rebinding, mixed IPv4/IPv6, internal target, redirect, invalid TLS | Selected connection-time egress controls hold without registration/challenge requirement | [Production sender TLS/network probes](https_probe.json); hostile URL/IP tests |
| S02 | Raw URL with path/query capability passes through recorder, logs, archives and jobinfo | Raw URL stays only in restricted intent; audit uses safe host/fingerprint | Recorder/body-preview redaction tests and independent security review |
| S03 | Capture-enabled request followed by dry-run/executed playback | No raw URL disclosure or unsolicited send to recorded destination; omit intent or explicit test override | Dry-run/executed playback stripping regressions |
| N01 | Large concurrent batch completions with tracking-store latency/root contention | Bounded computation-side work; measured completion/next-job latency within ratified baseline limits | [Final verified-sender backlog](backlog_performance.json): 1,000 transitions each, +0.849% / +0.637 ms p95; 500000-edge construction deadline passed |
| N02 | Receiver backlog, quota-abusing client, storage pressure | Fair bounded notification load; no computation cancellation/throttling to free notification capacity | Principal quota/release and page-fairness tests passed; [Verified sender backlog passed](backlog_performance.json) |
| R01 | Mixed instrumented/uninstrumented producers; rollback while parent enqueues | Unsupported callback admission rejected or explicitly incomplete; accepted callbacks retained/recovered | Mixed-worker admission and incomplete producer tests |
| R02 | Disable admission, pause dispatch, restart and restore pending records | Distinct controls, published age/lease semantics, no shared Redis flush or RQ downgrade | [Real persisted Redis restart](restart_restore_probe.json); paused dispatch tests |
| R03 | Copy environment or restore stale backup with pending deliveries | Dispatch defaults disabled outside ordinary live-store restart; explicit recovery accounts for duplicate risk; test copies never send to original URLs | [Stale process arm rejected and zero restored attempts](restart_restore_probe.json) |
| A04 | Same-key replay after browse credential expiry or mint failure | Credential-free persisted receipt; fresh authorization/mint, accepted computation preserved, no second enqueue | Actual culvert API test with real Redis, mint failure and same-job fresh credential replay |
| A05 | Expired unavailable admission tombstone | Exact 410 response distinguishes proven nonpublication from unknown; no unsafe new-key retry instruction | Exact HTTP 410 tests distinguish not_published and unknown |
| S04 | Same sub across credential classes/issuers; same identity after jti rotation | Distinct typed principal bindings across identities; stable receipt/quota binding across renewal; no anonymous fallback | Typed principal binding and renewal tests |
| E01 | Actual culvert batch and selected WEPP pipeline under healthy/failing receivers | API-to-receiver behavior and execution/domain distinction proven on authorized environment | [WEPP readback](workflow_readback_v6.json) and [mixed culvert readback](culvert_mixed_parallel_probe.json) passed; canonical six-default/four-batch worker configuration verified |
| E02 | Webhook-disabled versus backlog/failure project execution | Prepared inputs, fresh model outputs and reports semantically match; exact runtime provenance retained | [WEPP fresh input/output/report semantic parity passed](workflow_readback_v6.json); [Final backlog gate passed](backlog_performance.json) |

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
parts of H04/H05/H08/H09, but do not implement the webhook evaluator. At that historical discovery checkpoint all feature
acceptance rows remained pending. Ratified policies now live in the
[checkpoint contract](../../../schemas/rq-webhook-contract.md) and ADR-0109;
operator ratification has occurred; current acceptance status is in the matrix above.

## Test sources

- [Generic settlement](../../../../tests/rq/test_webhook_settlement.py)
- [Redis and actual worker lifecycle](../../../../tests/rq/test_webhook_tracking.py)
- [HTTP security/deadline](../../../../tests/rq/test_webhook_http.py)
- [Admission/receipt recovery](../../../../tests/microservices/test_rq_engine_webhooks.py)
- [Independent implementation review](20261028_implementation_reviews.md)
