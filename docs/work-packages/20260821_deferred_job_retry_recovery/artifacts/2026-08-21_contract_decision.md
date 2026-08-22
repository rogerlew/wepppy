# SURF-20A deferred-job retry contract decision

**Governance milestone**: GOV-00A-M1J
**Starting implementation revision**: `80e621164`
**Operator approval**: Explicitly granted 2026-08-21 after the exact broad
requirement was restated: fix every controller without added user friction or
regressions, and create the required standalone contract commit.
**Implementation conformance**: Pending

## Discrepancy and Rationale

This is an intended behavior amendment, not conformance to the existing text.
The current RQ contract and WEPP tests intentionally treat a dependency-viable
deferred descendant as active. Shared browser controls also treat every
nonterminal status, including deferred, as button-disabling. Production users
experience a failed child followed by a permanently deferred parent/finalizer;
they cannot submit the same action and generally do not know how to cancel it.

The accepted recovery interaction is the ordinary submission button. Deferred
means the job has not begun execution, so the server can supersede it before
accepting replacement work. Ignoring the job without canceling it is rejected
because its dependency might later release it and race the replacement.

## Normative Delta

For every user-facing WEPPcloud controller and corresponding mutable submission
endpoint:

1. `queued`, `started`, and `scheduled` remain active states and retain existing
   duplicate-submission protection.
2. `deferred` is replaceable and must not disable or reject submission.
3. Under the endpoint's existing submission lock, or the bounded submission lock
   added by this package where none exists, the server reconciles the complete
   associated workflow. Any queued, started, or scheduled node blocks. Every
   associated deferred node is conditionally canceled, removed from
   `DeferredJobRegistry`, removed from each prerequisite's dependent set,
   detached from deferred dependents, and cleared of dependency membership
   before replacement enqueue begins.
   Every run-scoped admission also participates in a canonical run lifecycle
   fence. Family locks still serialize same-operation receipts, while the
   lifecycle fence prevents destructive destination recovery from racing any
   other mutable controller submission for that run. Batch and culvert work
   retain batch-scoped lifecycle fences.
4. Cleanup is idempotent and conditional. It uses Redis optimistic locking over
   the job status/hash and affected registry/dependency keys, and commits only
   while every target remains exactly deferred. Concurrent promotion aborts and
   retries reconciliation; queued, started, or scheduled state becomes the
   existing conflict and is never canceled.
5. A deferred descendant does not block a WEPP tree retry even if its dependency
   chain appears viable. Any queued, started, or scheduled descendant still
   blocks, including when another branch failed or remains deferred.
6. Polling may display deferred status and its job link, but it must enable the
   command and stop indefinite polling. A successful replacement response
   replaces the displayed/tracked job ID through the existing lifecycle API.
7. Before any cleanup, the server verifies trusted association: canonical
   run/batch identity, expected operation family and queue origin, and root/
   descendant workflow lineage. A copied, cross-run, cross-operation,
   mismatched-origin, or ambiguous legacy ID is never mutated. It is treated as
   an invalid/stale hint according to the endpoint's existing explicit error or
   missing-hint behavior.
8. Operation verification does not permit a conflicting deferred operation to
   be ignored. The surface matrix defines resource-conflict families. A retry
   supersedes every safely associated deferred operation in that family (for
   example Batch run/delete and archive create/restore/delete) before starting
   replacement work. A job outside the authorized family or with ambiguous
   association is not mutated and remains an explicit conflict when it could
   affect the same resource; replacement must not race it.

## Finite Surface and Ownership Matrix

`artifacts/deferred_retry_surface_matrix.md` is the exhaustive normative source,
owner, association, conflict-family, serialization, and frontend-state matrix.
It covers every persisted user-facing controller hint writer, every dependent
controller workflow, every registry-scanning admission guard, and every shared
or specialized deferred poller/latch found in the repository-wide inventory.
The diagnostic RQ dashboard and read-only orchestration/schema descriptors
retain raw nonterminal classification and are explicitly excluded.

## Valid-State Matrix

- Absent/never-used hint: enqueue normally; cleanup is a no-op.
- Present-empty hint: normalize as absent and enqueue normally.
- Deferred root/tree: verify every node's association; if no associated node is
  queued/started/scheduled, conditionally cancel and detach every associated
  deferred node before enqueueing replacement.
- Populated queued, started, or scheduled job: preserve existing conflict or
  disabled-button behavior.
- Finished, failed, stopped, canceled, or not-found job: enqueue normally.
- Legacy status enum/bytes dependency keys: normalize without changing meaning.
- Malformed or hostile hint: do not mutate an unrelated job; preserve run access
  and job ownership/association validation, then use the endpoint's canonical
  explicit error or missing-hint recovery behavior.
- Concurrent status change: Redis watch aborts cleanup. Reconcile again; queued,
  started, or scheduled becomes conflict, while terminal/missing permits retry.
- Registry scan: collect the complete safely associated candidate set without
  the UI summary cap; never use the human-readable summary helper as a cleanup
  selector.

## Compatibility and Security

No request/response schema, endpoint, authorization, CSRF, queue, worker,
parameter, artifact, or persisted project-data schema changes. Existing clients
continue to submit the same request and receive the same successful job payload.
The behavioral compatibility change is intentional: deferred conflicts become
accepted replacements. Run-scoped authorization remains before lookup/mutation.
The helper may mutate only a fully associated deferred graph after conditional
status reconciliation; queued/started/scheduled work cannot be canceled through
this path. Cleanup failure enqueues nothing and returns canonical 5xx with an
`error_id`. Admission preallocates and durably saves the replacement ID before
enqueueing with that exact ID. Hint-save failure therefore enqueues nothing.
Enqueue failure leaves a missing planned ID, returns canonical 5xx, and ordinary
retry treats that hint as missing; it leaves the old graph safely canceled.
There is no post-enqueue hint write or emergency persistence path.

Security impact is high because authenticated submission now performs registry
cleanup. Required evidence includes an unmocked RQ test proving exact registry
and dependency-set changes, hostile/mismatched ID containment at applicable
ownership boundaries, and independent final security review.

## Applicable Canonical Contracts

- `docs/schemas/rq-response-contract.md`: admission, lifecycle, and cancellation.
- `docs/ui-docs/controller-contract.md`: shared command-button and polling UX.
- `docs/schemas/rq-controller-state-contract.md`: raw async status and client
  polling behavior; deferred remains raw nonterminal RQ state but becomes an
  explicit retry boundary for interactive controllers.
- Domain contracts remain unchanged because request fields, domain mutations,
  execution algorithms, and outputs do not change.

## Regression Evidence Required

- Direct Redis/RQ lifecycle test for a multi-level deferred graph before and
  after cleanup, proving no registry or dependency residue can later execute.
- Direct deferred-to-queued and deferred-to-started race tests proving cleanup
  aborts without cancellation.
- Cross-run, cross-operation, copied-hint, mismatched-origin, and hostile-linked
  ID containment tests.
- Unit tests for shared cleanup status normalization and idempotence.
- WEPP tree tests proving deferred never blocks while queued/started/scheduled
  descendants still block.
- Focused guard/route tests for every row in the finite surface matrix, including
  uncapped Batch registry selection and partial cleanup/enqueue/hint failures.
- Shared `controlBase` Jest tests for enabled command and stopped polling on
  deferred, plus normal replacement job tracking.
- Generated controller bundle, frontend lint/tests, RQ graph, documentation
  lint, broad exception enforcement, and substantive broad pytest gate.

## Alternatives Rejected

Keeping dependency-viability analysis was rejected because it perpetuates the
observed user lockout. Adding a Cancel button or retry confirmation was rejected
because it creates the user friction the operator explicitly prohibited.
Automatically releasing deferred jobs was rejected because the user requested
new work and obsolete work must not race it. Clearing only the persisted job ID
was rejected because the deferred job would remain live in RQ.

## Reviews

Two independent read-only checkpoint reviews and their disposition must be
stored beside this decision before the standalone ancestor is committed.
