# Implement operation-completion webhooks for RQ API clients

Completed locally 2026-10-28. Approved checkpoint `6ba2d8d9d`; runtime `62b272a6c`.
Final evidence: [validation summary](../../artifacts/validation_summary.md).
No production deployment occurred. Earlier pending entries are execution history.

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep
Progress, Surprises & Discoveries, Decision Log and Outcomes & Retrospective
current. Revised 2026-10-28 to reflect explicit operator direction; no runtime
implementation or activation is authorized by this planning revision.

## Purpose / Big Picture

Clients supply an optional HTTPS webhook URL with an operation submission and
receive its outcome when the requested work completes. Culvert clients receive
batch outcomes; WEPP clients receive complete selected workflow outcomes, not
submission acknowledgment or parent-task return. Accepted callbacks remain valid
after the submission token expires. Delivery is independently executed, auditable,
short and bounded, with limited transient retries documented for API consumers.
Callbacks report execution completion/outcome only (Option A); domain result
details remain in existing APIs. Start via `implementation_kickoff.md` and retain
row-level evidence in `../../artifacts/acceptance_matrix.md`.

## Progress

- [x] (2026-10-27 22:09 UTC) Scaffolded package and retained prior draft reviews.
- [x] (2026-10-28 17:53 UTC) Recorded operator direction superseding registration,
  continuing authorization checks, mandatory key infrastructure and observer-first
  recommendations; inspected existing culvert/WEPP finalization boundaries.
- [x] (2026-10-28 18:00 UTC) Recorded requirement for generic hierarchical
  terminal detection; withdrew per-workflow completion adapters.
- [x] (2026-10-28 18:20 UTC) Operator selected Option A: execution completion
  and execution_status only; domain results remain in existing APIs (HC-03).
- [x] (2026-10-28 18:47 UTC) Refreshed implementation scaffold with fresh-agent
  kickoff and concrete acceptance matrix; no runtime implementation performed.
- [x] Specified and ratified execution precedence and callback admission behavior.
- [x] Evaluated independent dispatcher placement and capture/recovery tradeoffs.
- [x] Ratified wire contract, unsigned delivery, audit and ADR-0109 bounds.
- [x] Ratified contracts/ADR after two independent reviews; committed ancestor `6ba2d8d9d`.
- [x] Implement accepted mechanism and complete independent source reviews.
- [x] Validate actual WEPP API/worker/receiver bytes, token expiry and artifact parity.
- [x] Validate mixed-result culvert: 38 finished nodes, one success, 35 caught failures, exact callback.
- [x] Meet approved backlog performance limits: canonical-pool p95 +0.849% / +0.637 ms.
- [x] Complete regression gates, final reviews, documentation and local closure; unrelated full-suite roads baseline failure isolated.

- [x] (2026-10-28 kickoff execution) Recorded HEAD and preexisting working tree;
  audited shared publication/lifecycle/cancellation/recording boundaries.
- [x] (2026-10-28 kickoff execution) Retained disposable real Redis/RQ probes for
  publication gaps, strict/failure-tolerant dependencies and conditional commit.
- [x] (2026-10-28 kickoff execution) Prepared exact D01–D10 recommendations,
  proposed canonical contract/amendments, ADR-0109 and dated checkpoint matrix.
- [x] (2026-10-28 kickoff execution) Two independent contract reviews and post-fix
  confirmation complete; no unresolved high/medium drafting findings.
- [x] Operator approved exact matrix and authority; checkpoint committed before implementation.
- [x] Complete generic closure/concurrency and independent HTTP/performance proof
  with final real Redis, API/model/receiver and canonical-pool evidence.
## Surprises & Discoveries

`enqueue_culvert_batch_jobs` returns a failure-tolerant finalizer that writes
succeeded/failed/skipped summary counts. Finalizer success is not all-runs success.
`enqueue_wepp_pipeline` returns a completion job after selected final dependencies;
failed strict prerequisites can leave it deferred forever. Therefore a callback
attached only to parent success or final-job success misses real operation outcomes.
Existing `job_info.py` aggregation is a possible reuse point, not yet proof of
complete cancellation/partial-graph coverage.

Prior review established that RQ registry reads can trigger cleanup. Any recovery
observation must read committed state without mutation. The old design introduced
registration, ongoing grants and key storage before establishing client needs;
these are no longer prerequisites. Historical reviews do not approve this revision.

Kickoff probes on local RQ 2.12.0/Redis 7.0.15 demonstrate enqueue_many and
enqueue_job bypass the current actor hook, caller-owned pipeline return precedes
publication, and culvert-style parent recording has a visible-child gap. A failed
strict prerequisite keeps the downstream failure-tolerant grandchild deferred;
direct failure-tolerant child finishes. Retained source/output:
`artifacts/20261028_source_and_probe_evidence.md`. These are discovery assertions,
not implementation acceptance or a complete publication protocol.
## Decision Log

2026-10-28 17:53 UTC, operator: notify operation completion; accept URL at submission;
honor accepted callbacks despite token expiry; freely supplied HTTPS URLs with
auditing; independently execute short attempts (10 seconds suggested) with limited
retries. Prefer a general shared mechanism with minimal regression risk. Codex
removed the observer-first prescription and mandatory registration/grant/key-store
infrastructure from the plan. Exact failure semantics, placement and numeric values
remain pending in `artifacts/decision_register.md`.

2026-10-28 kickoff execution, Codex recommendation (operator approval pending):
prepare `docs/schemas/rq-webhook-contract.md` and ADR-0109 with exact admission,
unsigned payload, precedence, bounded Redis ledger and independent dispatcher.
Callback-only idempotency keys address ambiguous initial culvert creation. Reject
wrapper-only terminal inference based on retained probe evidence. No runtime edits
before the standalone approved checkpoint. Proposed module boundaries are recorded
in `artifacts/20261028_source_and_probe_evidence.md`.
## Review disposition (2026-10-28)

See `artifacts/20261028_hierarchy_review.md`. Nine findings received independent
confirmation of drafting remedies. HC-03's semantic choice was subsequently resolved
by the operator selecting Option A at 2026-10-28 18:20 UTC. Emit operation.completed
with explicit execution_status, not domain success. Existing APIs remain the source
for domain results. This is decision closure, not implementation acceptance or a
new independent review of the exact final canonical contract.

## Outcomes & Retrospective

The approved checkpoint is committed and the opt-in implementation is wired.
Independent source reviews have closed the generation/continuity and publication
findings. Actual WEPP and mixed-domain culvert output/callback readbacks passed;
final source verification and the corrected hung-receiver performance measurement
passed. The local implementation package is complete; production deployment remains excluded.

The main discovery is that current RQ status cannot certify an earlier producer's
exit. Ordinary attempt-generation continuity, one-time publication evidence, actual
job fences and positive process exit must agree. Missing job hashes remain unknown
rather than extending RQ TTLs. Early-return evaluation of active receipts avoids
unnecessary Redis WATCH pressure without weakening terminal-candidate fences.

Historical scaffold and pending-approval entries below/above are provenance. The
operator ratification and later implementation updates supersede them.

## Context and Orientation

Work in `/home/workdir/wepppy`. Runtime is RQ 2.12.0; current response/runtime
contract is `docs/schemas/rq-response-contract.md`. Keep the closed upgrade package
immutable. Read root and nearest AGENTS before editing. Preserve unrelated changes.

`wepppy/microservices/rq_engine` owns submissions/authentication/responses.
`wepppy/rq/culvert_rq_pipeline.py` builds batch jobs and the finalizer;
`wepppy/rq/culvert_rq.py:_final_culvert_batch_complete_rq` writes batch summaries.
`wepppy/rq/wepp_rq_pipeline.py` returns final completion jobs for pipeline variants;
`wepppy/rq/wepp_rq.py` contains the orchestration entry points. `rq_worker.py`
provides central terminal hooks, `job_dependencies.py` preserves graph semantics,
`cancel_job.py` handles cancellation and `job_info.py` aggregates child state.

An operation is the work requested by the API submission. A hierarchy record
identifies the submission root, owned descendants and actual dependency edges.
An event is its immutable notification payload; an attempt is one HTTP request.
A lease is a bounded claim allowing another dispatcher to recover after a crash.
These are candidate interfaces to specify, not permission for a new workflow engine.

## Plan of Work

### Milestone 1: Specify generic hierarchical terminal states

Audit shared enqueue paths, recursive `jobs:*` child tracking and dependency
records, using culvert and WEPP variants as representative graphs. Separate owned
descendants from external dependencies and deliberately detached work. Define a
shared settled predicate requiring complete stable membership, no active work or
retries, and every remaining deferred member provably blocked under its actual
dependency rules. Unknown/missing state is not terminal. Distinguish outcome
precedence from settlement and wait for independent branches/finalizers. Name
required versus optional execution work using current contracts. Domain partial
success and skipped-run classification stay in existing result APIs. Specify
upstream failure, canceled/stopped work, retrying attempts and orchestration failure
before final-job creation. Detect failure internally as soon as known, but emit
the terminal webhook only after relevant work settles. A separate early-failure
event is outside this scope. Avoid early completion and indefinite waits on descendants blocked by a failed prerequisite. Preserve the
computation graph; webhook needs do not authorize changing dependencies.

Define the uniform optional `webhook_url` field, validation errors before enqueue,
response compatibility and ambiguous callback/submission persistence. Do not report
submission failure after accepting computation solely due to webhook bookkeeping.
Keep intent available before fast workers can finish. Define scope of accepted
callback authority without rechecking token expiry during delivery.

### Milestone 2: Evaluate minimal shared implementation

Prototype generic membership tracking and a shared terminal evaluator, reusing
existing enqueue interception and tree traversal where sound. Do not copy the
current polling status-priority list as a completion predicate: it can omit missing
children and classify failure ahead of unexplained deferred work. Preserve public
polling behavior unless explicitly amended. Prove child registration before or
atomically with visibility and snapshot/revision checks around parent completion.
Pending enqueue or failed notification bookkeeping means uncertain membership,
never false completion and never a change to computation results. Test normal finalizers, failures before registration,
partial graph construction, deferred finalizers, cancellation, crash and abandonment.
Use isolated synthetic Redis and controlled HTTP; no live data, external client
endpoints, shared-state mutation or stack restart before checkpoint/authorization.

Compare independent delivery options. A dedicated small RQ worker on existing
Redis is one candidate; an independently executed bounded dispatcher is another.
Record complexity and recovery cost before selecting new queue/service topology.
Using ordinary computation workers is not isolated merely because requests time
out quickly. Retain evidence for any escalation beyond existing mechanisms.

If a handoff can be lost, specify its recovery/loss window. A bounded read-only
reconciliation pass can supplement completion signals if justified; it is not the
prescribed main design. No Redis KEYS, whole-job scans, implicit registry cleanup,
TTL extension or computation mutation. State persistence loss bounds honestly.

Add graph cases for late/nested children, child completion racing parent return,
concurrent final children, bulk/pipeline enqueue, partial publication crashes,
strict versus failure-tolerant edges, external dependencies, scheduled retries,
blocked chains, missing records, malformed cycles and detached work. Generic
completion must not require knowledge of task function names. Measure complexity
and bounded read/load behavior for representative large batches.

### Milestone 3: Ratify canonical contract

Resolve D01-D10 in the decision register with operator provenance. Signing is a
separate choice; do not assume a mandatory encrypted-key subsystem. If signatures
are selected, specify exact bytes/envelope and secret lifecycle. Never forward or
reuse API bearer credentials. Specify sanitized destination/attempt audits, access,
retention, total HTTP deadline, transient retry cases/count/backoff and resource
bounds. Record numeric choices in the required ADR.

Promote accepted rules to `docs/schemas/rq-webhook-contract.md`; amend current
response/runtime/auth contracts without reopening the upgrade package. Record
starting revision, exact delta, rationale, compatibility/security impacts and
regression matrix in the dated checkpoint. Obtain two independent contract reviews
and dispositions. With explicit contract approval and commit authority, create a
standalone ancestor before implementation. Earlier design reviews are not a
substitute for reviewing this materially revised contract.

### Milestone 4: Implement the approved narrow mechanism

Finalize exact module paths, schemas and function signatures in this plan at the
checkpoint. Separate callback admission, generic lineage/terminal-state evaluation,
event recording and attempt execution. Use existing API/auth/config helpers and
preserve no-webhook behavior. Do not add per-workflow completion detectors or HTTP handlers in model tasks.
Central worker transitions may trigger root reevaluation; cancellation/abandonment
and missed triggers require coverage. The hierarchy evaluator and delivery sender
are distinct, and delivery jobs must not become computation descendants.

Catch notification boundary failures without altering task state or dependency
release; bound persistence work too. Independently deliver HTTPS with the selected
total deadline, TLS/SSRF/redirect policy, transient retry scheduler and audit record.
Retries reuse the immutable event ID; clients must tolerate duplicates. Use due
schedules rather than sleeps in computation workers. Bound pending/history growth
and fairness. No endpoint management, manual replay or history API is required
unless separately selected. Do not change public job polling auth or output shape.

### Milestone 5: Acceptance, review and handoff

Obtain scoped runtime authority; identify forest Docker context/Compose/wctl before
rebuild/recreate. Preserve unrelated active work and use disposable projects and
controlled receivers. No remote/production deployment follows from this plan.
Verify code and runtime versions in affected containers.

Run actual authenticated submissions with callback URLs and let the issuing token
expire before completion. Verify whole-operation payloads, HTTP attempts/audit and
unchanged generated artifacts under receiver failure. Exercise total deadline,
transient-only retry policy and restart/rollback with pending attempts. Run final
correctness/security reviews using canonical templates and close medium/high
findings before claiming completion. Publish consumer examples and clear delivery
limits; document operator audit, pause and recovery procedures.

## Concrete Steps

From `/home/workdir/wepppy`, run `git status --short` and `git rev-parse HEAD`.
Read applicable instructions and docs-maintainer/wepppy-tester skills. Retain exact
commands and fixture/runtime provenance for each probe. No broad tests for this
planning-only revision. Implementation gates include:

    wctl run-pytest tests/rq tests/microservices --maxfail=1
    wctl run-pytest tests --maxfail=1
    wctl check-rq-graph
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20261027_rq_webhooks

Add exact new targeted suites once paths are selected. Stub checks apply to changed
stub/API surfaces; frontend checks only to frontend changes. Update the dependency
catalog and inspect live job trees when wiring changes. Record actual pass/skip
counts and unrelated baseline failures without claiming unexecuted evidence.

## Validation and Acceptance

Carry the 2026-10-28 independent review requirements into executable acceptance.
Producer closure must cover enqueue-capable lifecycle callbacks and canceled but
still-running producers. Test delayed callback enqueue and descendants created
while cancellation state is already visible. Event commit must atomically validate
the evaluated membership revision, closure evidence and relevant state generation;
a barrier-controlled membership/retry/requeue change before commit must invalidate
completion. Uniqueness alone is insufficient.

Pair A failed -> B strict/deferred -> C allow_failure (C remains blocked) with
A failed -> C allow_failure (wait for C). Cover canceled/stopped prerequisites and
existing explicit stopped-observer release exceptions without evaluator mutation.
Apply accepted Option A: actual culvert code can return "failed" without failing
its RQ job. Test a complete hierarchy with such a caught failure: callback uses
operation.completed and execution_status: finished; existing batch results still
report the failed run. Assert no domain-success field/summary in the callback.
Pair with an uncaught RQ failure yielding settled execution failure. Do not change
task exceptions or introduce domain detectors/task outcome conventions.

Verify server-controlled root/parent/destination bindings against spoofed metadata,
foreign references and interleaved clients. Redact complete raw callback URLs from
profile recording, dry-run output, task descriptions, errors and artifacts. Captured
playback must omit callbacks or require an explicit test URL override; verify that
executing a recording cannot send to its original destination unintentionally.

Test simultaneous large-batch completions, root-lock contention, tracking-storage
failure and evaluator crash, measuring computation completion and next-job latency.
Only bounded signaling/bookkeeping may run on computation workers; full traversal
runs independently or has demonstrated bounded incremental cost, without holding
computation/dependency locks. Exercise published unknown-state expiry/audit and
minimal tracking retention without extending existing task TTLs.

Before admission activation, verify instrumentation across supported producers and
workers. Test mixed instrumented/uninstrumented enqueue paths and rollback during
child creation. Reject unsupported callback admission before enqueue or retain
explicit incomplete tracking; preserve accepted callback intent across disable and
rollback. Do not manufacture completion by treating unregistered children as absent.

Explicitly test a continuing batch where a failed parent/child coexists with
queued/running independent descendants: failure is known, but no terminal event
is emitted until remaining work and runnable finalizers settle. Pair this with a
strict chain whose failed prerequisite leaves deferred descendants provably
blocked: emit settled failure without waiting forever or mutating those jobs.
Traverse beneath failed ancestors and inspect actual dependency rules; ancestor
failure alone does not mean every descendant is blocked. Keep failure detection
separate from hierarchy settlement, including pending retries and graph producers.

Test missing/empty/valid/hostile webhook inputs and unchanged existing responses.
Test retained submission intent through token expiry, fast workflows, ambiguous
submission acknowledgment and dispatcher outages. Verify complete selected WEPP postprocessing and distinguish graph execution
outcome from domain-level partial/skipped results a task returns without raising.
Do not infer domain errors invisible to RQ; specify any generic outcome extension
separately. Cover retrying versus final
failure, final jobs left deferred, parent failure, partial graph construction,
cancellation, timeout, workhorse death and abandonment.

With actual persistence and controlled receivers, test refusal, hangs, slow/oversize
responses, TLS/DNS errors, redirect/rebinding and forbidden IPv4/IPv6 destinations,
429/5xx, retry exhaustion, duplicate attempt claims and acknowledgment loss. Check
exact event bytes, any selected signature and audit redaction. No expired token
may suppress an already accepted callback. Unknown state is not fabricated success.

Measure normal task throughput and dependency/cancellation behavior against a
webhook-disabled baseline under receiver failure and backlog. Compare prepared
inputs, fresh model outputs and reports semantically. Retain runtime identities,
groups/mounts/umask and code/image provenance. RQ success alone is insufficient.

## Idempotence and Recovery

Specify durable callback acceptance and recovery before enqueue races can occur.
One operation event remains immutable across attempts, allowing receiver dedup.
Describe admission disable, dispatch pause and component stop separately, including
lease expiry, retry-age progression and recovery of acknowledged-but-unrecorded
attempts. Preserve existing task data and schema compatibility. Never flush shared
Redis, downgrade RQ or alter global persistence to manufacture webhook durability.
Clean up only owned fixtures and retain sanitized audit/acceptance evidence.

## Artifacts and Notes

Retain source boundary map, candidate comparisons, exact decision/checkpoint
revisions, targeted tests, integrated artifact evidence, reviews/dispositions and
operator recovery evidence. Update tracker and living plan at every milestone.
Promote durable contracts outside the package before closure and archive completed
prompts. Historical 2026-10-27 review recommendations are superseded where the
2026-10-28 operator direction conflicts; do not claim they approve this revision.

## Interfaces and Dependencies

Reuse RQ 2.12.0, existing Redis settings, API auth and canonical response helpers.
Select storage and execution placement from evidence, not speculative new services.
Require dependency-evaluation gates for additions. Keep completion resolution,
persistence and HTTP delivery separate and minimal. Precise interfaces depend on
accepted failure/admission semantics and must be written before implementation.

Revision note (2026-10-28 17:53 UTC): replaced job-subscription/registration and
observer-first plan with client-requested workflow callbacks and bounded independent
delivery. Kept noninterference, audit, safe egress and crash-recovery acceptance.

Revision note (2026-10-28 18:00 UTC): operator requires generic hierarchical
terminal detection. Replaced workflow adapters with shared lineage and dependency
analysis; added race, missing-state and blocked-descendant acceptance requirements.

Revision note (2026-10-28): independent hierarchy review adds producer-closure and
atomic event-commit gates, mixed-edge semantics, bounded evaluator execution,
unknown-state resolution, instrumentation rollout and URL/lineage controls. Culvert
execution/domain outcome was initially left open and later resolved by Option A.

Revision note (2026-10-28 18:20 UTC): operator accepted Option A. HC-03 decision
closed; generic callbacks report execution completion/outcome only. Domain result
retrieval stays with existing APIs; caught-domain-failure acceptance is explicit.

## Kickoff handoff evidence

`artifacts/20261028_checkpoint_reviews.md` retains independent correctness/security
reviews and confirmed dispositions. `artifacts/20261028_contract_decision.md`
contains the exact unratified matrix. Source/probe evidence and ADR-0109 provide
rationale and proposed bounds. Scoped doc lint and isolated substrate probes pass;
no production implementation or runtime acceptance is claimed. Next action requires
operator approval of that matrix and authority to commit its standalone ancestor.

## Operator ratification (2026-10-28 19:56 UTC)

Operator: "decision matrix is approved. authority grants are authorized".
RQ-WH-01 exact matrix and ADR-0109 are accepted. Package commit and scoped local
implementation/integration/restart authority are granted; production deployment
remains excluded. Earlier pending-approval entries above are historical and
superseded. Create the standalone checkpoint ancestor before implementation edits.

## Active implementation sequence

Accepted ancestor `6ba2d8d9d` precedes all runtime edits. Build and test
`webhook_policy.py`, `webhook_http.py`, `webhook_settlement.py`,
`webhook_tracking.py`, `webhook_hooks.py`, `webhook_dispatcher.py`, and
`rq_engine/webhooks.py`; wire the four admitted routes and worker lifecycle,
then capture/playback protections. Keep admission disabled until writer coverage,
real Redis/process/HTTP security, bounded scheduling/performance, and actual
API/model-artifact acceptance pass. The initial substrate tests are not closure.
Intermediate correctness/security findings require attempt-fenced closure, atomic
terminal delivery, exact envelope/principal cleanup, IPv6 special-address rejection
and bounded evaluator scheduling. Record fixes and post-fix review before closure.

## Implementation validation update

Admission/receipt recovery, server-owned lineage, per-execution closure, incremental
settlement, conditional event creation, fenced independent delivery and capture/
playback protections are implemented but not activated. Existing route/recorder
regression suite: 137 passed. Disposable Redis API/tracking suite: 25 passed.
The full repository gate is running. These counts precede later hierarchy tests.

Intermediate reviews found and drove fixes for bounded-upload parser consumption,
prepublication retry ownership/expiry, raw preview leakage and reserve-to-enqueue
restore races. RQ 2.12 prepares explicit MULTI before enqueue returns; publication
now transfers buffered commands into a fresh WATCH transaction to retain existing
auth-actor hooks while fencing the exact intent. Callback staging cleanup precedes
making known nonpublication retryable. Final review is still required.

Development Compose includes an opt-in dispatcher profile with disabled defaults.
Client/operator guidance: `docs/dev-notes/rq-webhook-operations.md`. No production
deployment, local admission activation, model artifact parity or full acceptance
is claimed. Outstanding work includes controlled TLS/process fault evidence,
performance/fairness, actual workflows, remaining gates and final review closure.

### Bounded closure handoff decision

Retained 1,000-transition probes exceeded the approved 5% p95 overhead: initial
23.6%, cached connection 35.3%, and coalesced receipt 12.0%. Each was under the
absolute 50 ms delta, which does not satisfy the conjunction. Do not activate.
Diagnostic timings identify extra lifecycle Redis calls as avoidable overhead.
The next smallest implementation is a nonblocking close-on-exec pipe carrying one
completion byte from workhorse to supervisor, followed by one atomic durable
returned/exited receipt only after waitpid and existing containment checks.
No queue, daemon or datastore is added. Operational cost: two transient descriptors
per subscribed execution; missing signal or supervisor death remains unknown.
The pipe is execution-specific, never an alternative source of RQ outcome. State
receipts and conditional actual-job WATCH checks remain required. Source/process
regression and renewed performance evidence must confirm this change.

Broad targeted gate: 3,018 passed, 188 skipped. Full gate attempts exposed parser
ordering regressions subsequently fixed and covered in that targeted run. Full
suite must be repeated after source stabilization. Scoped worker stubtest and
check-test-stubs passed. Exception enforcement needs exact existing allowlist line
relocation plus the two documented new credential/sender boundaries.

### Actual workflow and final review progress

Disposable API/worker runs on path-rebased continuous-model copies completed all
18 RQ nodes and regenerated 388 artifacts each (disabled, healthy-destination and
failing-destination submissions). Artifact semantic comparison and actual delivery
remain separate gates. Copied catalog identity requires configured managed roots
and canonical incarnation invalidation; raw directory copying was insufficient.
The first culvert attempt exposed a missing fixture base mount and an unavailable
receiver; retained evidence records failed execution and three bounded DNS retries,
not successful domain or receiver acceptance.

Final correctness review found omitted helper-thread producers, fork-local failure
state, missing verified external prerequisites, unaudited catalog detachment and
large dependency serialization exceeding the hook budget. Fixes add process-wide
ownership, live-thread closure suppression, inherited pipe poison, watched foreign
receipts, explicit catalog-only detached context and deadline-checked serialization.
Actual model process helpers require bounded positive pidfd exit observation (ADR
allocation above); no inference from status or elapsed time replaces closure.
These changes require fresh process regressions, performance and workflow evidence.

### Final review and acceptance update

Both independent source reviewers report no remaining high/medium findings.
Late review fixes preserve exact 410 publication evidence, postcommit culvert Redis
recovery, retryable-admission replay and monotonic generic scheduling. Eight focused
boundary regressions pass. Six thread/fork lifetime regressions and 39 real catalog
queue regressions pass. Real Redis RDB restart rejects old reservation publication
and stale dispatch arming with zero attempts while paused.

`workflow_readback_v3.json` proves 388 fresh files per actual WEPP run, zero semantic
mismatches, exact persisted callback bytes, token-expiry independence, HTTP 204 and
three-attempt HTTP 503 exhaustion. All-failed culvert submissions correctly report
failed execution because their existing finalizer raises, even though children
catch domain validation failures. A mixed-result case remains under acceptance.

Full suite: 6,826 passed, 64 skipped before an unchanged roads publication-provenance
failure; isolated reproduction confirms the preexisting blocker. Initial and
reconciled backlog probes failed the relative limit (40.0%, 27.6%); root state
signals now preserve reconciliation deadlines and full delivery slots no longer
hot-poll waiting roots. A new measurement remains required. Admission stays disabled
outside the explicitly authorized disposable fixture.

### Latest source validation and actual mixed outcome

Actual mixed culvert evidence (`artifacts/culvert_mixed_egress_probe.json`) now
proves the required execution/domain distinction: 38 finished RQ jobs, one model
success, 35 caught domain validation failures and exact `finished` callback bytes
after token expiry. Fresh parquet content and actual job-tree state were read back.
The disposable fixture used one batch slot to isolate a preexisting parent/finalizer
lock race and normal model-data egress for USDA. No production defaults changed.

Immediate WATCH without MULTI cannot carry a buffered atomic receipt: tracking
now marks uncertainty while preserving ordinary RQ errors and repeated saves.
Profiling identified duplicate containment scans; reuse the existing positive
retirement observation, retaining scheduler verification and uncertain-child checks.
Attempt registration shares the existing pre-fork metadata transaction with exactly
RQ's serializer and meta field; tagged notification errors alone are isolated.
These are measured reductions of existing work, not a topology change. Ten real
process-boundary tests passed; both independent reviewers passed the final deltas.
The 100-transition diagnostic remains insufficient for the 1,000-transition gate.

The batched-start backlog run still failed: p95 77.7 ms disabled versus 98.9 ms
tracked, a 27.3% increase. Retained as `backlog_performance_batched_start.json`.
The scheduler previously multiplied its 100 ms budget by four evaluators; now all
active roots share one budget and rotate every bounded generator step. Three real
Redis scheduler regressions passed and both independent source reviews passed.
A fresh full-size backlog measurement follows; no threshold was relaxed.

### Final generation and benchmark review disposition

Both independent reviewers closed the lost-bookkeeping findings after adding an
ordinary pre-fork atomic metadata/current/predecessor write, a one-time unstarted
publication seed, sticky generation-gap detection and root publication proof checks.
A known older overlapping producer's state is ignored without discarding its exit
obligation. A completely missed attempt cannot disappear behind a successful retry.
Zero-TTL/missing hashes remain unknown, including later hash recreation; no RQ TTL
is extended. API computation acceptance survives missing initial notification proof.
Canonical rationale: `docs/schemas/rq-webhook-contract.md`, Membership, settlement and event commit.

The former late-WATCH optimization was rejected for an ABA race. The retained fix
returns immediately on an active page and keeps early WATCH/current-generation
checks for every page that could contribute to an event. Real process/regression
runs progressed from 47 to 49 to 51 passing tests; final combined gates follow.

Review also found the older backlog probes had zero actual sender attempts. Four
stale terminal due entries starved later roots for the same principals; terminal
recovery now repairs their retention deadline. Historical JSON explicitly records
its evaluator-only scope. The corrected probe requires four initial active senders
and actual hung-receiver traffic during the measured 1,000 transitions. A passing
old idle/evaluator-only sample cannot satisfy this gate.

### Closure (2026-10-28)

Canonical six-default/four-batch orchestration passed: v6 WEPP runs each have 18
finished jobs and 388 fresh artifacts with exact/semantic parity; parallel culvert
has 38 finished jobs, one model success and 35 caught failures. Healthy and exhausted
callback bytes match persisted events after token expiry. Final 1,000-transition
p95 is 75.064 → 75.701 ms (+0.849% / +0.637 ms), with 11 receiver observations
during timing and 15 audited attempts. Both independent reviewers verified these
artifacts. Final tests: 109 real boundaries and 3,020 targeted passes/223 skips.

The full-suite run stopped after 6,826 passes on unchanged Roads source-provenance
evidence; isolated reproduction and matching source hashes are retained. This is
a separate repository issue, not a webhook change or a reason to rewrite scientific
evidence. No production activation is authorized. Disposable Compose containers,
networks, copied data and private credentials were removed after readback; originals
remain untouched. See `artifacts/fixture_cleanup.json`.
