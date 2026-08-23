# Dependency correction security assessment

## Scope

This assessment covers only `artifacts/dependency_edge_matrix.md`, registered-
tree aggregate precedence, and the same-revision producer/worker cutover. The
existing 2026-08-21 assessment remains authoritative for authenticated deferred-
graph cancellation, association, locking, and replacement receipt persistence.

## Boundary and threats

- Strictification changes only whether never-started jobs become executable; it
  grants no new request, filesystem, queue, or worker authority.
- Retained tolerant edges are finite. Fork, Culvert, AgFields, Batch, and Omni
  finalizers may observe direct outcomes but must not read missing model output.
  AgFields and Omni contrast serialization edges connect independent work and
  must not transfer untrusted output from the failed predecessor.
- Aggregate failure precedence must derive only from the already-authorized job
  tree traversal. It must not traverse arbitrary Redis IDs or expose additional
  traceback, identity, metadata, or cross-run information.
- Ordinary retry remains authorization-gated and may cancel only a fully
  associated deferred graph under the existing Redis WATCH transaction. Strict
  dependency changes must not weaken run, operation, origin, or lineage checks.
- Mixed producer revisions are unsafe because RQ persists dependency-failure
  permission in each job hash. Cutover therefore stops producers, drains active
  legacy work, and restarts every producer/worker at one revision. Active legacy
  work is never rewritten or canceled by deployment tooling.
- Rollback uses the same stop/drain boundary. It must not rewrite persisted jobs
  or run old and new dependency constructors concurrently.

## Required evidence

- The exhaustive static graph and source audit contain no tolerant edge absent
  from `dependency_edge_matrix.md`.
- Each retained tolerant finalizer test proves it consumes no failed required
  output; Fork additionally proves profile-claim release on failed WEPP.
- AgFields and Omni contrast serialization tests prove predecessor output is not
  passed to or loaded by the independent dependent.
- WBT prior-request serialization protects shared mutation ownership rather than
  transferring outputs. A failed predecessor may leave partial run state, so the
  later request must reacquire the existing admission/directory-root locks,
  reconstruct and validate required state, and never assume predecessor success.
  Focused real-RQ evidence covers failure-first ordering, lock-serialized later
  execution, and the strict build-to-abstraction child remaining never-started.
- Each strict family proves a failed prerequisite cannot execute its dependent,
  followed by a production admission retry that clears only its associated
  deferred graph.
- Batch early-Omni failure proves the job-wide tolerant finalizer remains blocked
  on a deferred Omni receipt, reports failed aggregate, and supports authenticated
  retry cleanup.
- Aggregate polling tests prove active-work precedence, failed-over-blocked-
  deferred precedence, viable deferred-only behavior, and unchanged sanitized
  error projection.
- Local cutover records pre-stop queue inventory, zero queued/started/scheduled
  legacy executable trees before restart, one-revision container images/code,
  strict failure smoke, retry smoke, and rollback command validation.

## Review status

Independent security review and post-fix confirmation are required before the
documentation ancestor and again after implementation. Implementation
conformance is pending.
