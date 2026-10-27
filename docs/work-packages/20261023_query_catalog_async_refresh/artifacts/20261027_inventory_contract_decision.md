# Inventory rollout remediation checkpoint

Status: accepted checkpoint; both independent reviews PASS; no inventory implementation edits.
Starting implementation: `8593a299596b289dea8ffac548d889be74e5efe6`.
Operator authority: “proceed as recommended” following the recommendation to fix
resumable inventory, preserve four namespaces/permissions, isolate HTTP blocking
work, and rerun complete capacity gates. Existing package commit authority applies.

## Normative delta and rationale

Amend [refresh recovery/liveness](../../../schemas/query-engine-catalog-refresh-contract.md#recovery-and-liveness)
, [maintenance disclosure](../../../schemas/rq-response-contract.md#query-engine-catalog-maintenance-specified-implementation-pending)
and [ADR-0104](../../../adrs/ADR-0104-query-catalog-refresh-operational-bounds.md)
to specify streaming inventory on the existing batch queue, fenced per-job
checkpoint batches and scheduler acknowledgment. Production eager enumeration
failed >137 s; listdir failed65 s; full scandir failed60 s. No per-directory
count or unmeasured lease increase resolves the demonstrated failure.

This changes internal queue wiring/capability, not user model job responses,
scientific artifacts or authorization. Existing prefix privacy classification
applies to inventory jobs. Add an inventory capability to worker configuration;
old consumers must block admission. Do not change filesystem protocol/version.
Preserve all four active namespaces and existing mounts/permissions.

## Compatibility, security and regression

High security: new queue execution crosses Redis/filesystem boundaries. Inputs
are configured roots and private derived cursor state, never user-selected
paths/functions. Fence every checkpoint against current job/cycle ownership.
Validate containment/nofollow and replacement identity repeatedly. No inventory
project writes: discovery records only Redis-derived state. Existing authorized
refresh jobs alone create receipts/catalogs. Readonly and legacy role behavior
remain unchanged. Public polling must not disclose inventory paths/errors.

Valid states: empty roots, uninitialized and existing projects, nested scopes,
readonly scopes, supported legacy roots, directory mutation/replacement, missing
roots, malformed cursor, symlink/traversal attempts, failed or replaced workers,
Redis loss, mixed consumers and stalled storage. Empty valid roots complete;
missing/error roots remain degraded; no state may silently omit required scopes.

Tests: actual Redis transaction/recovery, slow iterator across checkpoints,
kill/restart replay deduplication, stale-worker fencing, atomic batch ack,
receipt-free nested convergence, incompatible worker refusal, public maintenance
privacy. Production-equivalent scratch acceptance plus read-only complete legacy
root scan and full fleet counts/capacity remain required. Normal process restart
may replay a directory prefix; no durable OS cursor or fixed outage deadline is
promised. HTTP offload is a separately recorded conformance fix, not part of this
inventory checkpoint.

## Review disposition

- Correctness C1: clarified that unresolved required-root/directory failures block
  completion and retain retry frontier. Verified closed by independent reviewer.
- Correctness C2: clarified entry/scope-record units for checkpoint/drain limits.
  Verified closed by independent reviewer.
- Security INV-SEC-01: amended RQ disclosure contract to explicitly cover inventory
  jobs and operator-only detail. Verified closed by independent security reviewer.

Reviews: [correctness](20261027_inventory_contract_correctness_review.md) and
[security](20261027_inventory_contract_security_review.md). Both approve only the
contract; implementation, production role parity and capacity remain pending.
