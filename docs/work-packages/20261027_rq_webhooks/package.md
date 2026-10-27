# RQ client webhook delivery

**Status**: Open; scaffolded, contract decisions pending (2026-10-27)
**Timezone**: UTC
**Started**: 2026-10-27 22:09 UTC

## Overview

Provide API clients with explicit webhook subscriptions while keeping HTTP
delivery, receiver outages and notification recovery independent of computation
outcomes and dependency execution. This package carries the reviewed design
through contract ratification, implementation and integrated acceptance.

The current request authorizes scaffolding. It does not select the unresolved
product options, authorize runtime changes, or satisfy the contract-first
implementation checkpoint. This package is not complete merely because its
documents exist.

## Objectives and scope

Deliver the ratified subscription/endpoint API, authorized event capture, signed
bounded delivery, observable delivery state and operator recovery. Preserve
webhook-absent behavior, existing RQ response contracts, model artifacts and
task/dependency semantics. Persist durable rules outside this work package.

Pilot clients/routes, event scope, reliability level and endpoint API shape are
pending in the [decision register](artifacts/decision_register.md). The reviewed
[draft](../../dev-notes/rq-webhooks-contract-draft.md) is design input, not current
canonical authority. Workflow events are conditional on explicit selection and
domain completion rules; they are not inferred from parent-job success.

Excluded: native RQ webhook activation, inline HTTP callbacks, unrelated RQ or
dependency upgrades, changes to model parameterization, public polling auth
defaults, production deployment, new infrastructure without evidence/approval,
and changes to the closed RQ migration package. Do not touch unrelated Roads work.

## Complexity budget

Reuse RQ 2.12.0, existing verified identity adapters, canonical errors and existing
storage/deployment mechanisms where proven suitable. The first candidate is a
bounded indexed observer of explicitly subscribed jobs, using committed,
side-effect-free reads. No all-job scans, registry cleanup or task-state mutation.

No new queue, service, datastore, daemon, dependency, privilege or topology is
currently approved. Delivery requires independent execution capacity; its concrete
placement remains a decision gate. Retain latency, backlog, retention and recovery
evidence from the smallest candidate before proposing an escalation, including its
operational cost. Do not silently replace observation with receipts or add a broker.

## Security impact and review gate

Security impact is **high**: authenticated API operations, bounded persistent
authorization grants, outbound HTTP, SSRF protection, signing secrets, replay and
shared-resource admission. Dedicated security and correctness reviews are required
using repository templates, with no unresolved medium/high findings at closure.

The three prior independent reviews closed 13 drafting findings; the
[review disposition](../../dev-notes/rq-webhooks-draft-review-20261027.md) is retained
as provenance. It is not formal canonical-contract or implementation approval.
Create final dated correctness and security artifacts after there is a concrete
implementation to review; do not manufacture passing placeholder reviews.

## Parameterization ADR gate

New observation deadlines, retry schedules, timeout bounds, quotas, retention and
pause-age policies will require a parameterization ADR before implementation/merge
under the applicable standard. Values, ADR number and decision provenance remain
pending. No numeric defaults are selected by this scaffold.

## Generated artifact validation gate

Applicable: yes, as noninterference evidence for RQ-driven model workflows and as
direct validation of signed webhook bytes. Capture the request and subscription,
reload persisted event/attempt state, inspect exact receiver bytes and verify the
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
  boundaries with idempotency, revocation, quotas and recoverable disable behavior.
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
and resource access owners must review persistent grant semantics. API clients,
RQ operators and maintainers are primary stakeholders; the operator owns product
and scope decisions.

## Deliverables and execution

Use the [active ExecPlan](prompts/active/implementation_execplan.md) and
[tracker](tracker.md). Required retained artifacts are the decision/checkpoint
record, compatibility/retention inventory, isolated candidate evidence, canonical
contract reviews, targeted tests, integrated acceptance, independent final
reviews, and rollback/operator evidence. Production rollout remains separate.
