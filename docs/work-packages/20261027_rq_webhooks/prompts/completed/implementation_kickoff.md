# RQ webhook implementation kickoff

Completed locally 2026-10-28: approved checkpoint `6ba2d8d9d`, implementation
`62b272a6c`, canonical-pool model/callback/performance acceptance and independent
reviews passed. [Outcome and limits](../../artifacts/validation_summary.md).
Production deployment remained excluded. The prompt below is retained as history.

Use the existing work package `docs/work-packages/20261027_rq_webhooks/`; do not
create a duplicate. Follow its active `implementation_execplan.md`, updating the
plan and tracker as execution progresses. This prompt is a handoff scaffold;
invoking it does not waive the checkpoint or grant unspecified deployment rights.

## Accepted requirements

Clients supply an optional HTTPS `webhook_url` with an authenticated operation
submission. Its accepted callback remains authorized after token expiry. URLs are
freely supplied with auditable attempts; mandatory registration, challenges and
ongoing token validation are not part of this feature. Do not add mandatory signing
or encrypted-key infrastructure by inference; signing remains a separate choice.

Detect completion generically across hierarchical RQ jobs. No culvert/WEPP-specific
completion detectors. Parent failure is not hierarchy settlement: continuing batch
children and runnable finalizers must finish; strict deferred descendants may be
classified as blocked only from actual dependency rules. Pending retries, active
producers and uncertain membership keep evaluation nonterminal. Do not modify task
status or dependencies to make notification possible.

Option A is accepted: emit `operation.completed` with explicit `execution_status`.
`finished` describes settled execution without RQ failure, not domain success.
Clients retrieve domain results through existing APIs. A culvert task that catches
an error and returns normally may legitimately yield finished execution while its
batch summary contains failures. Do not introduce domain outcome inference or a
new task-reporting convention for this release.

Independent delivery must not occupy normal computation capacity. Computation-side
notification bookkeeping/signaling is bounded; recursive evaluation is independent
or demonstrably bounded incremental work. Use short total HTTP deadlines (operator
example: 10 seconds), limited transient retries and sanitized audit records. No
native blocking RQ webhooks or HTTP sleeps inside computation workers.

## Start here

Read root and nearest AGENTS, the package brief/tracker, current webhook draft,
decision register, 20261028 hierarchy review, and active ExecPlan. Apply relevant
docs-maintainer/wepppy-tester skills. Record working tree and HEAD; preserve all
unrelated work and do not create/switch branches.

Inventory shared enqueue, lineage, callback and dependency paths. Existing
`auth_actor.py` enqueue interception and `job_info.py` traversal are candidates,
not complete terminal-detection implementations. Audit bulk/pipeline publication,
failure/cancellation/abandonment and callback-created children. Use isolated
synthetic experiments before changing production paths; retain evidence for the
smallest approach and any necessary topology escalation.

Complete the remaining decision register with concrete recommendations: exact
execution failure/cancel precedence, admission errors and ambiguous commit recovery,
storage/independent execution placement, total deadline/retry policy, tracking/audit
retention and resource limits, safe egress and signing scope. Do not reopen accepted
Option A or generic-settlement choices. Numeric policies require an ADR.

Prepare the current canonical contract, affected contract amendments and dated
contract-decision artifact. Obtain explicit operator approval of the exact matrix,
two independent contract reviews and disposition; with commit authority create the
standalone ancestor checkpoint before implementation. If approvals are missing,
finish the concrete reviewable checkpoint materials and report the exact missing
authority. Do not treat this scaffold as checkpoint approval.

## Implementation and acceptance

After the checkpoint, implement in bounded stages: admission/intent persistence;
server-controlled lineage; generic settlement/outcome evaluation; conditional unique
event creation; independent delivery/audit; recovery and operator controls. Verify
each stage against `artifacts/acceptance_matrix.md`. Precise module/interfaces are
selected in the checkpoint, not imposed by this scaffold.

Use real Redis/persistence and controlled HTTP receivers for concurrency, failure
and security tests. Test caught domain failure versus uncaught RQ failure explicitly.
Do not call fixture-only success environment acceptance. Obtain scoped local stack
authority before integration/restarts, inspect canonical wctl/Compose procedures,
and validate actual API/worker/receiver workflows and generated-artifact parity.
Do not deploy to production or reuse the closed RQ upgrade's deployment authority.

Run the ExecPlan's targeted/full/conditional checks and independent final correctness
and security reviews. Close all medium/high findings. Publish API examples showing
execution/domain distinction and delivery limits, plus operator audit/recovery docs.
Close only after wiring, environment acceptance and review evidence exist. Report
exact remaining blockers without overstating completion.
