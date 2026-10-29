# RQ-WH-01 accepted contract checkpoint

Date: 2026-10-28. Starting implementation revision:
`dd4e5381ba4e3fd66e82c0e14e8d82faa174ff47`.
Classification: intended additive behavior, not conformance repair.
Status: independently reviewed and operator-approved 2026-10-28 19:56 UTC.
Standalone ancestor commit: `6ba2d8d9d`. Runtime implementation: `62b272a6c`.
These execution references were appended after the approved checkpoint; the matrix is unchanged.

## Exact authority and change matrix

| Contract | Intended delta / preserved obligation |
| --- | --- |
| [RQ webhook contract](../../../schemas/rq-webhook-contract.md) | New finite admission surface, request/response/error matrix, Option A payload, generic settlement, independent delivery, retention/egress/controls |
| [RQ response contract](../../../schemas/rq-response-contract.md) | Cross-link additive callback receipt/errors; preserve absent-field and polling behavior; native RQ webhooks stay disabled |
| [Agent API contract](../../../schemas/rq-engine-agent-api-contract.md) | Accepted callback authority survives token expiry; no new scopes, resource access or polling authority |
| [Auth token specification](../../../dev-notes/auth-token.spec.md) | Same bounded callback authority distinction; no bearer persistence/forwarding |
| [Upload contract](../../../schemas/upload-endpoint-contract.md) | Culvert multipart callback plus recovery header; preserve ZIP validation and bounds |
| [ADR-0109](../../../adrs/ADR-0109-rq-webhook-bounds.md) | Proposed exact deadlines, retries, limits, retention, quotas and latency acceptance |
| Feature access governance, CSRF, NoDb persistence/concurrency, output scope, culvert JWT renewal | Applicable unchanged invariants: route authorization, locks, scientific outputs and result-access token behavior remain in force |

Owners: rq-engine API/auth, RQ worker operations, culvert upload and WEPP workflow
maintainers. This bounded composition does not advance or close any other owner's
work package. The operator explicitly approved this exact matrix, including all numeric values,
finite cross-owner composition and operator-only notification archive exclusion.

## Recommendations D01–D10

| ID | Approved decision |
| --- | --- |
| D01 | Settled hierarchy only; Option A; precedence failed > stopped > canceled > finished; external proven blockers contribute status but no identity |
| D02 | Existing Redis atomic admission/publication and conditional event ledger; process-crash recovery, explicit possible Redis-loss callback loss; duplicate-tolerant delivery |
| D03 | Four named initial routes; nonempty webhook_url; callback-only Idempotency-Key; additive receipt, exact errors and same-key ambiguous recovery |
| D04 | Submission authorization binds callback permanently for tracking window; token expiry no dispatch gate; emergency pause remains available |
| D05 | Freely supplied public HTTPS DNS hosts on port 443; connection pinning/TLS/SSRF checks, no proxies/redirects, sanitized audit |
| D06 | Unsigned first release; receiver confirms sensitive decisions via existing API; no signing infrastructure |
| D07 | Existing Redis namespace plus one independent bounded dispatcher, no computation delivery queue; shared publication/producer receipts; activation awaits coverage/performance |
| D08 | ADR-0109 exact numeric table, including 10-second attempts, 3 attempts, one-hour delivery age and 30-day tracking |
| D09 | Restricted raw intent; sanitized operator audit, fenced claims, fair scheduling, admission disable versus dispatch pause; project-archive exclusion explicitly proposed |
| D10 | Two independent read-only reviews and disposition, operator approval of this matrix and commit authority, then standalone ancestor; stack authority separately required |

Rationale: existing wrapper/polling misses publication and closure evidence; retained
[real Redis probes](20261028_source_and_probe_evidence.md) establish specific gaps.
New idempotency header is proposed because a lost first culvert response otherwise
creates a second batch on retry. Independent dispatcher avoids normal computation
capacity and a second RQ delivery lifecycle. No new datastore/dependency is selected.
Alternative topology remains a contingency if the smallest candidate fails measured
acceptance; do not silently escalate or change shared Redis persistence.

## Valid state and request matrices

| Stored/runtime state | Validity and required behavior | Evidence obligation |
| --- | --- | --- |
| Feature never used / absent intent | Valid; normal computation, no callback | A01, existing route regressions |
| Empty namespace | Valid; first callback creates bounded records | A02/A03 real Redis |
| Populated pending/terminal intent | Valid; recover same receipt/event, enforce age and fencing | H09/H10, D04/D05, R02 |
| Legacy jobs without tracking | Valid legacy; do not infer a subscription or backfill authority | A01, R01 |
| Missing member/partial publication/expired job | Incomplete; recover or outcome_unavailable, no fabricated event | H08/H11/H12 |
| Malformed/spoofed/foreign records | Invalid; quarantine tracking, sanitized audit; computation unaffected | H13, S01–S03 |
| Live producer after cancel or callback still enqueues | Valid unsettled execution; wait for exit/closure | H07/H12 |
| Delivery exhausted or paused past age | Valid terminal tracking; existing results remain usable | D03/R02 |

Request combinations are separately enumerated in the canonical admission table:
absent, empty, populated, malformed, unsupported mode, quota/store failure,
identical/different idempotent replay and ambiguous commit. All new user-reachable
errors are expected validation/capacity/capability errors except exceptional
publication uncertainty. Their codes, status and safe recovery instructions are
specified there. Existing authorization errors keep their current precedence.

## Compatibility, security and data plan

Additive notification namespace and callback-only field/header; no changes to
run CSV/parquet/NoDb schemas, scientific parameters, public polling, model exception
behavior, queue dependencies or existing no-callback response. Callback intent is
not a scientific project artifact; operator-only visibility/archive exclusion needs
explicit approval. No production code changed in checkpoint preparation.

Security impact HIGH: outbound user-directed HTTP, retained sensitive URL,
server-controlled lineage and quota abuse. Test valid public TLS as well as unsafe
addresses, rebinding, redirects, hostile metadata, capture/playback and audit leakage.
No signing capability is promised. Restore/backup procedures must treat raw intent
as sensitive and never restart dispatch automatically in a copied environment.

## Regression and artifact evidence

Use the existing [acceptance matrix](acceptance_matrix.md), all feature rows still
pending. Current substrate probes are discovery only. Required suites: proposed
`tests/rq/test_webhook_*`, `tests/microservices/test_rq_engine_webhooks.py`, targeted
RQ/microservices then full pytest, graph gate if wiring changes, exception inventory,
doc lint and conditional stub/frontend gates. Independent correctness/security final
review and actual authorized API/worker/receiver acceptance remain mandatory.

Validate admitted request -> reloaded intent -> immutable exact event bytes -> actual
receiver request/audit. Compare prepared model inputs, fresh executable outputs and
reports to disabled baseline under backlog/receiver failure. RQ success alone is
insufficient. Verify no raw URL in project browse/download/archive or profiles.
No environment acceptance, HTTP sender test, throughput proof or deployment claimed.

## Approval and review record

Operator approval recorded 2026-10-28 19:56 UTC: "decision matrix is approved.
authority grants are authorized". This grants exact contract approval, package
commit authority and scoped local implementation/stack integration/restart authority
identified in the matrix. Production deployment remains excluded. No repeat
approval is needed for those authorized steps. The standalone ancestor is created
before implementation source changes; its revision is recorded in the tracker.

Independent [reviews and disposition](20261028_checkpoint_reviews.md) now pass
proposal readiness. COR-01/COR-02 and SEC-01/SEC-02/SEC-03 were corrected and
independently confirmed. No unresolved high/medium drafting findings remain.
Operator approval and commit authority are now granted; runtime acceptance remains pending.
