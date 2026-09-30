# Security review — run catalog projection

## Metadata and triage

Reviewer: unassigned. Date: 2026-09-30 UTC. Base:
`c8497e2cbf210ebc74ef51e2c73cb5351373da2f`.
Scope: authenticated catalog/query changes, source extraction, worker adapter,
registration lifecycle, and operator controls. Impact: **high**; dedicated
review required. Gate: **pending / hold**, not a completed review.

Related: [correctness review](2026-09-30_correctness_review.md),
[contract decision](2026-09-30_contract_decision.md), and
[specification](../../../schemas/run-catalog-projection-contract.md).

## Threat model and noninterference

Users may control project names and source payloads; identities, paths, and
serialized data must not expand access or execute reconstruction hooks.
Notifications are internal hints, not registration or authorization commands.
Workers may be on another host sharing a queue but not the host's local DB.
Valid standalone, empty, legacy, grouped, and missing-optional-state workflows
must survive every protection, alongside rejection of hostile inputs.

## Required surface checks

- [ ] Existing normal/shared/admin alias authorization and CSRF remain intact.
- [ ] Scoped counts/freshness metadata cannot disclose unauthorized registrations.
- [ ] Cached readonly and TTL cannot authorize writes/deletion.
- [ ] Extractor uses data-only decoding and canonical source containment without
  rejecting valid legacy/grouped paths or following untrusted injected paths.
- [ ] No database credentials, arbitrary source locators, raw exceptions, or
  payloads enter public responses/log evidence.
- [ ] Notifications cannot create owners/ACLs/registrations or resurrect deletion.
- [ ] SQL parameterization, transaction fencing, pool/fork safety, and timeouts
  are validated with actual failures and concurrent processes.
- [ ] Scheduler coalescing/recovery cannot create unbounded work or drop durable
  dirty state; existing queue/task behavior is preserved.
- [ ] Startup validates enabled integration and job-origin database identity;
  standalone-disabled mode performs no dependency or network discovery.
- [ ] Existing secret files, runtime users/groups/mounts/umask, and canonical
  deployment are preserved and exercised end-to-end.
- [ ] RQ response, graph, and live job-tree evidence match actual wiring.
- [ ] Project artifacts remain browsable/archivable/restorable; projection data
  is deliberately deployment-owned and rebuilt rather than hidden in projects.
- [ ] Fault tests preserve valid user outcomes as well as reject hostile cases.

## Findings, evidence, and sign-off

No independent findings or acceptance evidence collected yet. Record each
finding's severity, surface, evidence, remedy, and disposition. Close medium/high
findings before release; any accepted residual risk needs security reviewer
recommendation and explicit owner acknowledgment. A passing unit suite does
not replace real file/SQL and production-equivalent workflow evidence.

Security reviewer sign-off: pending. Package owner acknowledgment: pending.
Release recommendation: hold until required review/evidence exists.
