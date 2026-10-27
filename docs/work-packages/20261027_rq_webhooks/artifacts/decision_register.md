# Webhook decision register

Status: pending, 2026-10-27 22:09 UTC. This is an execution register, not canonical
authority. Operator approval of scaffolding does not choose the proposed values.

| ID | Decision required | Candidate / constraint | Status |
| --- | --- | --- | --- |
| D01 | Event scope and pilot clients/routes | Individual terminal jobs first; workflow scope needs named domain completion/artifact rules | Operator choice pending |
| D02 | Reliability and clocks | Distinct subscription acceptance, event capture and receiver acknowledgment; observation deadline separate from delivery age | Guarantee and loss window pending |
| D03 | API shape and retrospective subscriptions | Registered endpoint ID plus explicit job subscription; retained terminal capture and principal-scoped idempotency proposed | Operator choice pending |
| D04 | Durable authorization | Exact resource, endpoint version, events, lifetime and revocation grant; token classes/renewal/access-change semantics explicit | Identity owner and operator review pending |
| D05 | Destination activation and egress | Challenge or operator approval, connection-time SSRF checks, HTTPS/no redirects, ports/proxies/private-target policy | Policy pending |
| D06 | Key management | Separate webhook key material, encryption versions, disclosure/rotation/recovery; never reuse JWT/session keys | Inventory/design pending |
| D07 | Capture/storage/execution placement | Indexed read-only observer first; existing storage evaluated for persistence and recovery; independent delivery capacity bounded | Evidence and topology decision pending |
| D08 | Numeric policy | Observation/retry lifetimes, timeout bounds, quotas, fair scheduling, retention, latency/resource acceptance thresholds | ADR and values pending |
| D09 | Pause/disable/rollback | Separate admission/dispatch/component controls; outstanding leases, retry age and compatible retained state | Semantics pending |
| D10 | Execution and checkpoint authority | Exact contract matrix approval, commit authority, scoped local integration/restart authority; production excluded | Not established by scaffold request |

## Requirements carried forward

No notification HTTP or sleeps in computation workers. No notification-caused
computation status, dependency or retry changes. Unknown observation is not a job
outcome. Unknown authorization pauses dispatch. Preserve webhook-absent behavior.
Existing polling can aggregate descendants; individual event status must be named
explicitly. One immutable event atomically closes an individual subscription's
observation independently of delivery; competing observers recover the same ID.
Delivery is duplicate-tolerant, not exactly once.

The [reviewed draft](../../../dev-notes/rq-webhooks-contract-draft.md) and
[13-finding disposition](../../../dev-notes/rq-webhooks-draft-review-20261027.md)
contain the detailed proposed obligations and acceptance matrix. All 13 drafting
findings were independently re-reviewed; none represents implementation approval.

## Checkpoint preparation

For each decision, record the chosen value, exact operator statement/date,
rationale, rejected alternative, applicable canonical sections and regression
evidence. Produce a separate dated contract-decision artifact from these accepted
choices. Record starting revision, compatibility/security impacts and the final
standalone ancestor revision. Do not mark a decision accepted from silence.
