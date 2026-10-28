# RQ client webhook delivery

**Status**: Open; kickoff executed to independently reviewed checkpoint proposal; operator ratification pending (2026-10-28)
**Timezone**: UTC
**Started**: 2026-10-27 22:09 UTC

## Overview

Provide API clients with per-submission operation callbacks while keeping HTTP
delivery, receiver outages and notification recovery independent of computation
outcomes and dependency execution. This package carries the reviewed design
through contract ratification, implementation and integrated acceptance.

The operator selected workflow completion, per-submission HTTPS URLs, delivery
authority independent of subsequent token expiry, auditability and bounded
nonblocking delivery on 2026-10-28. Exact wire/runtime decisions remain open; this
direction does not satisfy the contract-first implementation checkpoint. This
package is not complete merely because its documents exist.

## Objectives and scope

Deliver the ratified per-submission callback option, operation-outcome capture,
bounded independent delivery, auditable attempts and operator recovery. Preserve
webhook-absent behavior, existing RQ response contracts, model artifacts and
task/dependency semantics. Persist durable rules outside this work package.

Initial workflow targets are culvert batches and complete selected WEPP pipelines.
Option A is accepted: callbacks describe execution completion/outcome only; clients
retrieve domain success/partial-failure details through existing APIs. No generic
task-reported domain outcome convention is required for this release.
The [decision register](artifacts/decision_register.md) distinguishes accepted
client direction from pending wire, failure/recovery and execution decisions.
The [current draft](../../dev-notes/rq-webhooks-contract-draft.md) is revised design
input, not yet canonical authority. Endpoint registration, destination challenges,
ongoing token-validity checks and mandatory signing-key storage are not prerequisites.

Excluded: native RQ webhook activation, inline HTTP callbacks, unrelated RQ or
dependency upgrades, changes to model parameterization, public polling auth
defaults, production deployment, new infrastructure without evidence/approval,
and changes to the closed RQ migration package. Do not touch unrelated Roads work.

## Complexity budget

Reuse RQ 2.12.0, existing verified identity adapters, canonical errors and existing
storage/deployment mechanisms where proven suitable. The first candidate is a
generic hierarchical terminal-state mechanism using shared membership and
dependency semantics, plus independent delivery. Culvert and WEPP are acceptance
cases, not per-workflow completion adapters. Observation is an optional recovery
technique, not the prescribed architecture. No all-job scans, implicit registry
cleanup or task-state mutation by notification code.

No new queue, service, datastore, daemon, dependency, privilege or topology is
currently approved. Delivery requires independent execution capacity; its concrete
placement remains a decision gate. Retain latency, backlog, retention and recovery
evidence from the smallest candidate before proposing an escalation, including its
operational cost. Do not silently add a broker or redesign computation graphs.

## Security impact and review gate

Security impact is **high**: authenticated API operations, bounded persistent
submission-to-callback authority, outbound HTTP, SSRF protection, audit data and
shared-resource admission. Signing is an open capability decision. Dedicated
security and correctness reviews are required
using repository templates, with no unresolved medium/high findings at closure.

The three prior independent reviews closed 13 drafting findings; the
[review disposition](../../dev-notes/rq-webhooks-draft-review-20261027.md) is retained
as provenance for the earlier design. The 2026-10-28 direction supersedes its
registration/grant/challenge/key-management recommendations. It is not review
approval of this revision or a formal canonical-contract checkpoint.
Create final dated correctness and security artifacts after there is a concrete
implementation to review; do not manufacture passing placeholder reviews.

## Parameterization ADR gate

New observation deadlines, retry schedules, timeout bounds, quotas, retention and
pause-age policies will require a parameterization ADR before implementation/merge
under the applicable standard. Values, ADR number and decision provenance remain
pending. No numeric defaults are selected by this scaffold.

## Generated artifact validation gate

Applicable: yes, as noninterference evidence for RQ-driven model workflows and as
direct validation of webhook payload bytes (and signatures if selected). Capture the accepted request and callback intent,
reload persisted event/attempt state, inspect exact receiver bytes and any selected
signature, then compare a representative model run's prepared inputs, fresh
outputs and user-facing report with a webhook-disabled baseline. Preserve job
trees, content manifests, semantic comparisons and candidate runtime identities.

Use actual Redis/storage and HTTP boundaries plus a disposable project on an
authorized forest runtime with representative identities, groups, mounts and
umask. A successful job or HTTP status alone does not prove acceptance. Current
evidence supports reviewed planning only; nothing is implemented or wired.

## Success criteria

- The operator approves the exact decision matrix; affected canonical contracts,
  two independent contract reviews and disposition are committed as a standalone
  ancestor before implementation.
- The selected design meets its published acceptance, capture, delivery and loss
  boundaries with duplicate tolerance, auditability, resource bounds and recoverable
  disable behavior. Expired submission tokens must not suppress callbacks.
- Receiver failure/backlog cannot change computation results, dependency release,
  retries or cancellation containment; shared-resource bounds pass measurement.
- Direct security/lifecycle tests and actual API/worker/receiver acceptance pass,
  including artifact parity and rollback with outstanding events.
- Required regression gates, correctness/security reviews and user/operator docs
  are complete, with no open medium/high findings.

## Dependencies and stakeholders

The [RQ 2.12 upgrade](../20261027_rq_2_12_upgrade/package.md) is complete on forest;
production rollout is independent. Runtime authority remains
[rq-response-contract.md](../../schemas/rq-response-contract.md). Feature identity
and resource access owners must review the bounded submission-to-callback authority. API clients,
RQ operators and maintainers are primary stakeholders; the operator owns product
and scope decisions.

## Deliverables and execution

Start with the [fresh-agent kickoff](prompts/active/implementation_kickoff.md),
[active ExecPlan](prompts/active/implementation_execplan.md),
[acceptance matrix](artifacts/acceptance_matrix.md) and [tracker](tracker.md).
The updated scaffold carries the accepted generic hierarchy/Option A direction;
the matrix is planned evidence, not executed validation.
Required retained artifacts are the decision/checkpoint
record, compatibility/retention inventory, isolated candidate evidence, canonical
contract reviews, targeted tests, integrated acceptance, independent final
reviews, and rollback/operator evidence. Production rollout remains separate.

## Kickoff execution checkpoint

The [exact proposal](artifacts/20261028_contract_decision.md), proposed canonical
contract, amendments and ADR-0109 are prepared. [Independent reviews](artifacts/20261028_checkpoint_reviews.md)
pass drafting readiness after confirmed corrections. [Real Redis substrate probes](artifacts/20261028_source_and_probe_evidence.md)
retain discovery evidence; implementation/HTTP/environment acceptance is pending.
Exact operator approval and package commit authority remain required before runtime
implementation. No production deployment authority is requested by this checkpoint.

## Operator ratification (2026-10-28 19:56 UTC)

Operator: "decision matrix is approved. authority grants are authorized".
RQ-WH-01 exact matrix and ADR-0109 are accepted. Package commit and scoped local
implementation/integration/restart authority are granted; production deployment
remains excluded. Earlier pending-approval entries above are historical and
superseded. Create the standalone checkpoint ancestor before implementation edits.
