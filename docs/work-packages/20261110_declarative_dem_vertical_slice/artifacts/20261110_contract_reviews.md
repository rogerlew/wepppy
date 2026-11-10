# DEM v1 independent contract reviews

Date: 2026-11-10. Source baseline: `3a113ac28df9c5b2cdf453a4223e1c42e83b81bb`.
Scope: `docs/schemas/declarative-dem-v1-contract.md`, contract decision and
linked parent/NoDb/RQ/UI/catalog/Bootstrap amendments, before implementation.

## Correctness and UX

Reviewer: `/root/dem_contract_correctness` (`reviewer`), independent read-only.
Initial verdict: changes required. Post-fix verdict: approved for checkpoint;
no remaining medium/high contract findings.

- COR-C1, high: interrupted restore could remove the only declarative fence.
  Resolved: prevalidate same identity/records/protected bytes and preserve
  `provenance/` plus `READONLY` through cleanup/extraction.
- COR-C2, medium: finalization authority and command flow were underspecified.
  Resolved: distinct operational RQ finalizer, settled-writer proof, observational
  status, explicit engine verification/completion and machine-readable results.

Retained obligations: direct interrupted restore, normal RQ failure bookkeeping,
canceled-writer settlement, public HTTP viewer and ordinary compatibility tests.

## Security

Reviewer: `/root/dem_contract_security` (`security_reviewer`), independent read-only.
Initial verdict: HOLD. Post-fix verdict: approved for contract checkpoint;
no remaining medium/high contract findings.

- SEC-C1, high: local publication lock could survive tree replacement and publish
  stale state. Resolved: stable catalog lifecycle guard precedes local lock;
  revalidate admission/incarnation and reject active/uncertain archive/restore.
- SEC-C2, medium: incoming archive identity was ambiguous. Resolved: prevalidate
  same build/submission/run/owner and protected records/hashes before deletion.

Public-only fixture, operator-observed exact image binding, no worker API token,
Bootstrap exclusion, redaction and additive ordinary-state behavior are adequate
at contract level. Direct implementation and actual runtime evidence remain gates.

## Primary disposition

All four findings accepted and amended before post-fix independent confirmation.
Approval is for the contract ancestor only. Final correctness/QA/security reviews,
local artifact evidence and deployment acceptance remain pending. No implementation
files were edited during these reviews; no live cluster changes occurred.
