# Runs deletion-date sorting and bulk protection

Status: contract checkpoint preparation; implementation pending.

## Scope

Implement the operator-requested sortable Automatic deletion column and adjacent
**Disable Automated Deletion for Selected** button on `/runs/`. Compose only
Runs catalog presentation/sorting and the existing authenticated TTL setter.
Do not advance or close the separate catalog projection initiative. No scheduler,
expiration calculation, schema, queue, authorization, or deployment changes.

Security impact: high by public route-handler classification; sort allowlist
only, with bulk requests reusing the existing authorization and CSRF boundary.
Independent contract reviews and final correctness/security evidence are required.

Execution: [ExecPlan](prompts/active/implementation_execplan.md).
Decision: [checkpoint](artifacts/2026-11-05_contract_decision.md).
