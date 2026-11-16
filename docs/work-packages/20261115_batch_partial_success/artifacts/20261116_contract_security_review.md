# Independent security contract review

Reviewer: `/root/contract_security` (security_reviewer agent), read-only.
Final rereview: 2026-11-16 06:28:07 UTC.
Base: df8b5249c70a3d98fd27f2b3b3b16ac1d96deb52.
Reviewed contract: docs/schemas/batch-outcome-contract.md.
SHA-256: 42d00a1931ea77e862412349ff91414bfae47d3dc33dd57faf0eb6ac7f8fed92.
Related: 20261116_contract_correctness_review.md and 20261116_inventory.md.

## Triage and scope

High security impact; dedicated review required. Public polling is not a private
manifest channel. Download credentials authorize a resource, not arbitrary ZIP
members or arbitrary URL destinations. Scope includes workers, job serialization,
browse access/containment, skeleton retention and external client consumption.
Valid partial/legacy/prep-only states must remain usable under existing policy.

## Findings and author disposition

| ID | Severity | Finding | Resolution |
| --- | --- | --- | --- |
| SEC-01 | Medium | Skeleton retention allows logs/NoDb/recorder content and symlink targets that a bundle may disclose beyond direct browse policy | Exact derivative file allowlist; raw member and resolved target containment/secret/Root-only/recorder checks; diagnostics retained on project surfaces |
| SEC-02 | Medium | Returned download URL may forward credentials off-origin | Pin configured WEPP origin and exact batch/attempt path; reject unsafe redirects before forwarding credentials |
| DI-01 | Medium | Fast successful leaf evidence expires before slow sibling timeout | Non-expiring required leaf/Omni evidence through explicit cleanup |
| SEC-03 | Medium | Omni reconciliation could mutate foreign graphs or cancel the batch finalizer | Explicit worker/polling triggers, verified same-attempt graph, resource lease and atomic state recheck, preserve independent work and batch finalizer; prohibit broad helper reuse |

Primary author accepted all findings. Independent final rereview confirmed all
closed at contract level; zero unresolved medium/high security findings. No risk
acceptance or implementation approval is inferred.

## Verdict and remaining gates

Technical contract pass at the recorded hash. Canonical cross-links are present
in RQ response, webhook and batch task-boundary contracts. Operator ratification
and standalone checkpoint remain pending.

Implementation acceptance must directly prove authorized/foreign downloads,
member and symlink exclusions, stale-finalizer fencing, failed publication,
archive/restore, credential-safe redirects and real timeout settlement. Polling
must not mutate foreign/superseded graphs; automatic retries stay eligible;
concurrent promotion must cause no partial cancellation. Review performed no
runtime tests, deployment or artifact validation.
