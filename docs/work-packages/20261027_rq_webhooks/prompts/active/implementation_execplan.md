# Implement isolated client webhook delivery for RQ

This is a living ExecPlan maintained under
`docs/prompt_templates/codex_exec_plans.md`. Keep Progress, Surprises & Discoveries,
Decision Log, and Outcomes & Retrospective current. This package was scaffolded
at the user's request; execution after scaffolding is gated as described below.

## Purpose / Big Picture

An authorized API client should receive the selected job/workflow notifications
without a slow or failing receiver changing computation outcomes or occupying
computation workers. Acceptance requires real signed requests and recoverable
delivery records alongside unchanged model outputs and dependency behavior.
Native RQ webhook delivery is excluded because it performs blocking HTTP.

This is an implementation package, but scaffolding is not implementation
completion. The product choices are not settled. Resolve them before promoting a
canonical contract or implementing runtime behavior; do not silently substitute
the draft's recommendations for operator decisions.

## Progress

- [x] (2026-10-27 22:09 UTC) Read reviewed design and independently confirmed
  correctness/security/operations dispositions; scaffold package and register plan.
- [ ] Resolve decision register D01-D10 and capture approval/provenance.
- [ ] Inventory actual identity, retention, storage and runtime boundaries.
- [ ] Evaluate isolated observer candidate and retain sufficiency evidence.
- [ ] Ratify canonical contracts/ADR, obtain two independent contract reviews,
  and commit standalone checkpoint before runtime implementation.
- [ ] Implement admitted API/persistence, capture and independent delivery.
- [ ] Pass targeted and integrated acceptance, artifact parity and rollback.
- [ ] Complete broad checks, final reviews, documentation and package closure.

## Surprises & Discoveries

Prior review established that RQ registry enumeration defaults can run cleanup,
changing failures/retries/dependencies. Observation must use committed exact-job
reads without cleanup or mutation. Stable identity adapters do not enforce durable
resource grants. The current secret resolver is not proof of an encrypted dynamic
credential store. Durable event delivery does not guarantee capture of transient
terminal state. Evidence and full dispositions are in
`docs/dev-notes/rq-webhooks-draft-review-20261027.md`.

## Decision Log

2026-10-27 22:09 UTC, operator request and Codex scaffold: preserve unresolved
product options and make ratification a first milestone. This avoids converting
reviewed recommendations into approved API behavior. Evaluate observation before
worker receipts because it may avoid production-worker changes; escalate only on
retained acceptance evidence. Scaffolding does not authorize stack changes or
commit the future contract checkpoint.

## Outcomes & Retrospective

Current outcome is a discoverable package, plan and pending-decision register.
No runtime implementation, probe, deployment or webhook activation has occurred.
All acceptance remains outstanding. Update this section after every milestone.

## Context and Orientation

Work from `/home/workdir/wepppy`. RQ 2.12.0 is the intended runtime, pinned in
`docker/requirements-uv.txt`; the prior upgrade package is immutable history.
`docs/schemas/rq-response-contract.md` remains authoritative for responses,
identifiers and the native-webhook exclusion. Amend living contracts when the
new scope is approved, never the closed upgrade records.

`wepppy/rq/rq_worker.py` centralizes execution, completion and failure behavior.
`wepppy/rq/job_dependencies.py` handles deferred graphs; `cancel_job.py` handles
cancellation. `job_info.py` and `job_summary.py` expose state, sometimes aggregated
over children. `wepppy/microservices/rq_engine/__init__.py` registers API routers;
`auth.py`, `feature_access.py` and `wepppy/rq/auth_actor.py` supply identity/access
and enqueue metadata. Inspect nearest AGENTS before editing any of these.

A subscription is a client's explicit request to observe one authorized subject.
An event is an immutable captured outcome. An attempt is one HTTP delivery of
that event. A grant is bounded persisted authority for subsequent delivery. A
lease is a time-bounded exclusive claim on pending work, allowing recovery after
dispatcher death. Job terminal state is not workflow completion or artifact
validity. Existing aggregate polling can disagree legitimately with a raw parent
job event; name the event subject explicitly.

## Plan of Work

### Milestone 1: Resolve scope and inventory boundaries

Use `artifacts/decision_register.md` to resolve event scope, pilot clients/routes,
delivery guarantees and endpoint API shape. Obtain exact choices for grants,
destination activation, encryption, storage, execution placement, numeric policies
and rollback. Inventory jobs with zero/short result retention, requeue/repetition,
orchestration roots and supported token classes. Write a compatibility matrix
covering webhook-absent, empty, populated, legacy and hostile states separately
from request combinations. Explain every new user-reachable error.

Do not assume the earlier RQ migration's local-stack authority grants authority
to deploy new webhook infrastructure. Record scoped runtime authority before
integrated work. Preserve all unrelated changes and do not create/switch branches.

### Milestone 2: Evaluate the smallest design

Evaluate an indexed exact-job observer in disposable synthetic Redis/HTTP
environments. No live job data, external client endpoints, shared Redis mutation,
production-path changes or stack restarts before the checkpoint. Record fixtures,
versions, commands and observations in `artifacts/observer_evaluation.md`.

Exercise fast completion, already-terminal admission, result_ttl=0, deletion,
requeue, observer outage, stuck deferred jobs and expected latency/load. Reads must
not extend TTL, run registry cleanup, retry jobs or release dependents. Distinguish
accepted subscriptions, captured events and acknowledged HTTP in the recovery
promise. Verify actual persistence loss bounds rather than equating an acknowledged
Redis write with zero-loss recovery.

If observation fails the selected acceptance condition, retain the failure and
propose bounded post-commit receipts with reconciliation, including cancellation,
abandonment and crash windows. Do not assume hooks cover all outcomes. Any new
queue/service/store/dependency/topology needs evidence, cost and explicit scope
disposition before implementation. No architecture is preselected by this plan.

### Milestone 3: Canonical contract checkpoint

Promote accepted rules to `docs/schemas/rq-webhook-contract.md` and amend applicable
auth, response and runtime contracts. Record the exact normative delta, compatibility,
security, rationale, regression matrix and operator approval in a dated contract
decision artifact. Select numeric defaults in the required ADR. Obtain two
independent read-only contract reviews and disposition all findings. With commit
authority established, create the standalone ancestor checkpoint and record its
revision in tracker.md. No runtime source edits precede this checkpoint.

### Milestone 4: Implement the selected contract

Add a narrowly scoped rq_engine router and webhook domain modules with explicit
interfaces for endpoint admission, subscription admission, committed-state
observation, immutable-event creation, attempt claim, send and attempt completion.
Finalize exact paths/signatures in this plan at the checkpoint; they depend on
storage and API choices and are intentionally not fabricated by the scaffold.

Require endpoint and job/resource authorization independently from open polling.
Persist bounded grants without storing bearer tokens. Apply quotas/idempotency
before side effects; ambiguous commits recover the same subscription/event.
An individual subscription closes observation atomically with its unique event,
not HTTP success. Implement retained terminal-job semantics from the contract.

Deliver independently of computation with connection-time SSRF protection,
hostname TLS verification, no redirects, exact-body HMAC signatures and bounded
attempt duration/response handling. Secret encryption, versioning and rotation
follow the selected reviewed key mechanism. Unknown authorization or missing keys
stop notification activity only. Retry scheduling uses due times, not sleeps in
computation workers. History/replay and disable behavior obey ownership, quotas,
retention and the immutable event identity. Never expose raw exceptions, task
arguments, secrets or paths in payloads or public job metadata.

### Milestone 5: Integrated validation and review

After scoped authorization, identify the actual forest Docker context, Compose
project and installed wctl workflow before rebuilding/recreating affected services.
Preserve unrelated jobs; test with disposable projects and controlled receivers.
Read back candidate code/runtime identity inside every affected container. No
production, forest1 or remote-host action is authorized by this scaffold.

Run the acceptance matrix below, then repository gates and independent final
correctness/security reviews using canonical templates. Record defects, fixes and
re-review. Update affected client/operator/developer documentation, including pause,
rollback, replay, key rotation and recovery limits. Do not close with untested
runtime boundaries or open medium/high findings.

## Concrete Steps

From `/home/workdir/wepppy`, begin with `git status --short` and `git rev-parse HEAD`.
Read root/nested AGENTS, docs-maintainer/wepppy-tester skills, work-package guidance,
contract-first, generated-artifact, dependency-evaluation and parameterization-ADR
standards. Preserve unrelated Roads files and ignore generated usersum index drift.

Record targeted test commands once implementation paths exist. Canonical gates:

    wctl run-pytest tests/rq tests/microservices --maxfail=1
    wctl run-pytest tests --maxfail=1
    wctl check-rq-graph
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20261027_rq_webhooks

Run stub checks for changed API/stub surfaces and frontend lint/tests only if
frontend code changes. Update `wepppy/rq/job-dependencies-catalog.md` and validate
live job trees when wiring changes. Expected results are passing targeted/broad
checks and no unexplained graph drift; record actual counts/skips, never planned
counts as evidence. Unrelated baseline failures require reproduction and explicit
disposition rather than concealment. No code gates are necessary for scaffolding.

## Validation and Acceptance

Prove supported absent/empty/populated/legacy requests remain usable. Exercise
cross-client access, token expiry/renewal/narrower replacement/revocation, run access
removal, authorization outage, endpoint activation/change/disable and encryption
key loss/rotation. Test fairness with an abusive client and quota exhaustion.

Exercise success, failure/retries, queued cancel, running stop, timeout, workhorse
death, abandonment, parent-before-child completion and requeue. An expired started
entry must remain unchanged by observation. Test retrospective subscription,
ambiguous commit, duplicate idempotency key with conflicting input, simultaneous
observers, delayed delivery across requeue and unsupported retention.

Use actual persistence and controlled HTTP servers for refusal, hung/slow/oversize
responses, TLS/DNS errors, redirect/rebinding and prohibited IPv4/IPv6 destinations,
429/5xx, retry exhaustion, lease recovery and acknowledgment loss. Verify signatures
over captured bytes and receiver deduplication by immutable event ID. Missing
observation must be explicit, never fabricated task failure or success.

Compare webhook-disabled and receiver-failing/backlogged workloads against the
ratified resource/latency bounds. Prove unchanged task results, strict prerequisites,
approved finalizers, cancellation containment and worker capacity. Inspect prepared
model inputs, fresh outputs and user-facing reports, not just status/NoDb state.
Record identities/groups/mounts/umask and code/image provenance. Verify pause/restart
and restore with outstanding and acknowledged-but-unrecorded deliveries.

## Idempotence and Recovery

Admission retries recover the same operation under principal-scoped idempotency;
new intentional subscriptions use new identities. At-least-once delivery permits
duplicates but never changes the event body. Distinguish disable admission, pause
dispatch and stop component. Validate lease expiry, pause-age policy, retained
schemas/keys and resumed dispatch. Never flush shared Redis, delete existing jobs,
change shared persistence to manufacture durability, or downgrade RQ for rollback.
Clean up only owned disposable fixtures; retain sanitized evidence.

## Artifacts and Notes

Retain the starting revision, decision register, exact contract/checkpoint revisions,
candidate evaluation, tests and integration reports, artifact manifests, final
review/disposition and operator recovery evidence beneath this package. Link the
prior dev-note review as provenance without reopening the closed migration package.
Promote durable rules outside the package before closure and archive completed
prompts with outcomes. Update root plan index and project tracker at closure.

## Interfaces and Dependencies

Reuse RQ 2.12.0 and canonical Redis configuration, verified identity and response
helpers. Existing PostgreSQL/Redis are candidates, not an approved storage choice.
Dependency or encryption additions require the repository evaluation gates.
Finalize versioned endpoint/subscription/event/attempt schemas and errors before
implementation; numerical limits and wire signing format belong in the canonical
contract/ADR. Preserve all existing response keys and auth boundaries unless an
exact amendment is approved. Production deployment and native RQ webhooks remain
outside this package's scaffold authority.

Revision note (2026-10-27 22:09 UTC): initial scaffold integrates all 13 reviewed
drafting findings while preserving operator choices and implementation gates.
