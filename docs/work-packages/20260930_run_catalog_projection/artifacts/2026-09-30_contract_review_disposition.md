# Run catalog contract review and findings disposition

## Review identity and scope

Review requested by the operator on 2026-09-30 UTC after specification commit
`62d4273d9006156745649b12f3bb96225cb5042f`. Runtime baseline remains
`c8497e2cbf210ebc74ef51e2c73cb5351373da2f`. This is pre-implementation review;
runtime/deployment validation remains a future gate.

Independent reviewers (read-only; neither authored the specification):

- Dirac, `reviewer`, agent `01a0f460-85ce-7b71-9137-0ceea20a52e8`:
  correctness, synchronization, compatibility, and testability.
- Ohm, `security_reviewer`, agent `01a0f460-864f-7eb3-87aa-d9e763b175f5`:
  security, source identity, standalone noninterference, and operational safety.

Codex remains the specification author and disposition editor, not an
independent approver. Read-only review findings and subsequent confirmation
are recorded here and in the dedicated review artifacts. No runtime source changes
or live host actions are part of this task.

## Original reviewed contract snapshot

All four original files are recoverable from `62d4273d9`:

| File | SHA-256 |
| --- | --- |
| `docs/schemas/run-catalog-projection-contract.md` | `ac40dd0f91f9d8c0c5a9e6b41f41cdcdbf5460085dc71a429763b10fd5d36357` |
| `docs/adrs/ADR-0078-run-catalog-projection.md` | `890eb6ac7f6c7353e731e2b1375f6b5f0d8ca78e3fc06bfb9ecc87e50e9396a6` |
| `docs/schemas/nodb-persistence-concurrency-contract.md` | `e10ee02958bec1cebccffea860682a27d47305ab34d072c34ef95d89a7021a74` |
| `docs/ui-docs/contracts/runs-catalog-ttl-deletion-contract.md` | `2e1602d687aface652cd3b59c75613c3d6d57c9d7c08c8dbabb44d5616fd00cc` |

## Author's supplemental operational check

OPS-01 (medium, amended; independently confirmed): original section 8 combined static
configuration validity with live sweep health. If implemented as startup
validation, a full canonical redeploy could refuse web startup while workers
and the scheduler are being recreated; a transient outage could prevent the
very process startup needed for recovery. Separate static startup checks from
dynamic promotion/readiness checks; existing database-mode request errors and
explicit rollback must remain available without an automatic NFS fallback.
Section 8 now separates those gates and requires restart/outage readiness tests.
This is an author finding, not an
independent review verdict.

## Independent initial findings

Both independent initial verdicts were HOLD. Neither reviewer changed files,
ran live host operations, or treated absent runtime implementation evidence as
a pre-implementation contract blocker. Findings below refer to the specification
at `62d4273d9`; section references under remedies refer to the amended contract.

| ID | Severity | Concrete failure | Disposition / amended authority |
| --- | --- | --- | --- |
| COR-01 | Medium | Ready TTL with a stored expiry becomes unreadable; retaining expiry violates the proposed ready-only CHECK and rolls back good Ron updates | Accepted. Sections 3.1/7.2 clear stored expiry on TTL failure, retain its observation time, publish other successful sources, and keep the row dirty |
| COR-02 | Medium | Fork registers before enqueue; snapshot readiness can precede finalization, while waiting for a lost final notification cannot be repaired from the specified state | Accepted. Sections 5/7.2 define metadata readiness, never job completion; finalization is an acceleration hint. Registration/partial/failed/lost-final/restart transitions and optional TTL first-read failure are explicit |
| COR-03 | Low | SQL NULL policy makes the original CHECK evaluate NULL, admitting non-null expiration | Accepted. Section 3.1 uses `IS TRUE` and specifies null/unknown/non-ready truth-table cases |
| SEC-01 | High | Project A's imported source/ancestor link redirects into project B; SQL authorization for A then exposes B's metadata | Accepted. Section 6.5 binds registration to trusted configuration and fixed sources with descriptor-bound containment, lexical event identity checks, and supported same-project/legacy/grouped cases |
| SEC-02 | Medium | Existing grouped `get_wd` repairs shared links during a supposedly read-only comparison/reconciliation | Accepted. Section 6.5 requires a pure resolution seam and complete directory/link inventory equality, leaving ordinary workflow repair unchanged |
| SEC-03 | Medium | Older remote batch consumers cannot import the new sweep; rollback leaves queued jobs eligible for incompatible workers | Accepted. Sections 11.1/11.4/11.5 gate all eligible consumers, scope old-writer tolerance to nonconsumers, and drain/remove only catalog work before incompatible rollback |
| SEC-04 | Medium | Open RQ polling exposes maintenance result/description/traceback across users | Accepted. Section 9.1 and the shared RQ response amendment specify reserved opaque identity and bounded public-safe serialization even for import/fetch/abandonment failures |
| OPS-01 | Medium | Requiring live sweep health during startup prevents canonical restart/outage recovery | Accepted. Section 8 separates static process construction from dynamic readiness/promotion; Ohm confirmed initial closure |

No finding was dismissed as speculative or risk-accepted. Changes are bounded
contract corrections, not runtime patches or permission/ACL changes.

## Evidence and validation obligations

COR-02 was grounded in registration before enqueue in
`wepppy/microservices/rq_engine/fork_archive_routes.py`. SEC-01/02 were grounded
in ordinary-open snapshot reads, cache existence checks, and
`helpers._ensure_omni_shared_inputs`, with existing path-helper tests showing
repair behavior. SEC-03 was grounded in shared batch consumption in
`docker/docker-compose.prod.worker.yml`. SEC-04 was grounded in default-open
poll authorization, `recursive_get_job_details` result/description/traceback
exposure, and the existing shared contract's unrelated-error behavior.

The reviewers require future real tests for the corrected TTL transitions and
constraint truth table; pre-enqueue/partial/lost/failed lifecycle cases; source
link containment and pure inventories; mixed consumers/wrong-database setup;
rollback with queued/started sweeps; and anonymous single/batch job-info error
paths. Revision/UUID races, lost coordinator connection, recovery/coalescing,
and registration before schema installation remain implementation obligations.

Additional grounded clarification: `wepppy/tools/scheduler.py` has a 30-second
loop sleep. Section 6.4 now requires wakeup bounded by this task's next due time,
not merely zero initial delay/jitter. Other tasks retain their declared timing
semantics. Initial usable Ron/READONLY with unreadable optional TTL is explicitly
visible/stale even while aggregate indexed revision remains zero.

## Post-fix confirmation

First re-review closed COR-01/02/03, SEC-01/02/03, and OPS-01. Both reviewers
retained HOLD while identifying the following additional gaps:

| ID | Severity | Finding and disposition |
| --- | --- | --- |
| COR-04 | High | Rolling back public serializers could expose retained terminal sweep diagnostics. Accepted: section 11.5 requires compatible redaction throughout retained job lifetime, including rollback; a previous unprotected revision is not an eligible polling rollback candidate |
| COR-05 / SEC-05 | Medium | Reserved prefix conflicted with canonical job-ID generation. Accepted as one duplicate finding: both contracts define the exact prefixed UUID form, canonical suffix generator, and complete exact-string handling |
| SEC-04 follow-up | Medium | Jobstatus and outer polling failures could still expose tracebacks before deserialization. Expanded the original disposition to cover these paths explicitly in both contracts |

Future validation also includes retained failed jobs after application rollback,
jobstatus aggregation/fetch failures, and exact-string identifier generation,
enqueue, lookup, cancellation, and classification before deserialization.

Both original independent reviewers returned final **contract-only PASS** on
2026-09-30 after read-only re-review of the amended working tree over `62d4273d9`.
Dirac closed COR-01 through COR-05 and supported SEC-04 closure; Ohm closed
SEC-01 through SEC-05, OPS-01, and COR-04 from security/operations review.
No unresolved contract blockers remain. Ten distinct findings are closed:
nine independent findings plus OPS-01, counting COR-05/SEC-05 only once and the
SEC-04 follow-up as part of its original finding. None is risk-accepted.

Operator ratification, accepted checkpoint ancestry, and runtime/deployment proof
remain distinct and cannot be supplied by the author or by a technical review.

## Final authoritative snapshot

SHA-256 values identify the amended contract set. ADR status records the final
verdict; the authoritative technical rules were unchanged after reviewer PASS.

| File | SHA-256 |
| --- | --- |
| `docs/schemas/run-catalog-projection-contract.md` | `2d018a2255502aef735f756675e0fd5b7f6cea2fed38c06e39877fc799f7a2d8` |
| `docs/schemas/rq-response-contract.md` | `072fa557c76de105694fcf8057bbb206b79bd49fc9f7fb6604c87bc5532ef072` |
| `docs/adrs/ADR-0078-run-catalog-projection.md` | `3f3f8f26db2d304a6e7849af6a3392be75ab585ced97ba9ccaaa1f26fceae585` |
| `docs/schemas/nodb-persistence-concurrency-contract.md` | `e10ee02958bec1cebccffea860682a27d47305ab34d072c34ef95d89a7021a74` |
| `docs/ui-docs/contracts/runs-catalog-ttl-deletion-contract.md` | `2e1602d687aface652cd3b59c75613c3d6d57c9d7c08c8dbabb44d5616fd00cc` |
