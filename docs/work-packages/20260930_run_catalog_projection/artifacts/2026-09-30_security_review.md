# Security review — run catalog projection

## Metadata and triage

Reviewer: Ohm, independent read-only `security_reviewer` agent
`01a0f460-864f-7eb3-87aa-d9e763b175f5`. Date: 2026-09-30 UTC.
Reviewed specification: `62d4273d9006156745649b12f3bb96225cb5042f`
plus the author's section 8 startup/readiness amendment. Runtime baseline:
`c8497e2cbf210ebc74ef51e2c73cb5351373da2f`.
Scope: authenticated catalog/query changes, source extraction, worker adapter,
registration lifecycle, and operator controls. Impact: **high**; dedicated
review required. Initial contract-only verdict: **HOLD**, one high and three
medium findings. Final independent contract-only verdict: **PASS** after two
amendment rounds; runtime checks below remain
future implementation obligations, not evidence claimed by contract review.

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

| ID | Severity | Finding | Author disposition |
| --- | --- | --- | --- |
| SEC-01 | High | Source links/event identity could bind another project's metadata to an authorized row | Explicit registration/configuration/fixed-source binding, descriptor containment, and supported same-project/grouped/legacy cases |
| SEC-02 | Medium | Existing grouped path resolution repairs files | Pure resolver, no repair calls, full directory/link inventory comparison |
| SEC-03 | Medium | Old shared batch consumers and rollback can encounter an unknown callable | All-consumer activation gate; catalog-only queued/started drain protocol before incompatible rollback |
| SEC-04 | Medium | Public job-info exposes multi-user sweep details | Reserved opaque namespace and narrowly scoped single/batch/recursive/failure redaction; matching RQ response amendment |
| SEC-05 | Medium | Reserved prefix conflicts with canonical identifier generation | Explicit catalog-only prefixed UUID exception and exact-string handling; duplicate of COR-05 |

Ohm independently confirmed OPS-01's static-startup/dynamic-readiness correction.
First re-review closed SEC-01/02/03 but held SEC-04 for jobstatus and outer
polling errors; both contracts now explicitly cover those pre-deserialization
and aggregation paths. All five security findings were accepted for correction;
none is risk-accepted. COR-04 separately requires redaction-compatible public
serializers throughout terminal job retention, even after application rollback.
See the [disposition record](2026-09-30_contract_review_disposition.md) for source
evidence, detailed scenarios, and validation cases. Failed post-replace mirror
work remains distinct from existing explicit monotonic-signature errors.

Ohm confirmed SEC-01 through SEC-05, OPS-01, and COR-04 closed at contract level;
no unresolved security/operations contract blockers were identified.
Independent post-fix contract verdict: **PASS**. Runtime security validation,
operator policy ratification, and deployment release recommendation remain
separate gates; no runtime or environment proof is claimed.
