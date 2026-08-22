# SURF-20A checkpoint security assessment

**Stage**: Pre-implementation checkpoint
**Security impact**: High
**Status**: Checkpoint approved; no unresolved High or Medium findings

## Boundary

The change does not alter authentication, authorization, CSRF, tokens, request
payloads, queues, or worker commands. It adds authenticated mutation of RQ
deferred registry and dependency state for the exact finite source matrix in
the contract decision.

## Threats and Required Controls

- Cross-run or cross-operation cancellation is contained by verifying canonical
  run/batch identity, expected operation family/origin, and workflow lineage for
  every root and descendant before mutation. Ambiguity fails closed for cleanup
  but remains frictionless as a stale/missing hint where the endpoint already
  permits that behavior.
- Deferred-to-queued/started promotion is contained by watching the RQ job hash,
  status, registry, and dependency keys. Transaction conflict retries
  reconciliation; active work is never canceled.
- Partial graph cleanup is contained by collecting the complete associated graph
  without presentation caps, blocking on any executable node, and canceling all
  associated deferred nodes in one conditional transaction or retrying without
  mutation.
- Competing submissions are contained by existing domain locks and new bounded
  locks only for Batch and other matrix paths that lack one. Lock keys use
  validated canonical run/batch identity.
- Partial failure cannot create undiscoverable work: cleanup failure enqueues
  nothing; the replacement ID is durably saved before enqueue; hint-save failure
  enqueues nothing; and enqueue failure leaves a visible missing planned ID that
  ordinary retry replaces.

## Mandatory Evidence

Direct Redis/RQ tests must cover successful graph cleanup, idempotence,
transition races, cross-run/cross-operation/origin/lineage rejection, registry
scan isolation, and all partial failures. Route tests must prove authorization
precedes cleanup. Final security review must inspect the implementation and
close all high/medium findings before package completion.

## Independent Checkpoint Verdict

The independent security reviewer approved the corrected documentation-only
checkpoint on 2026-08-21 with zero unresolved High and zero unresolved Medium
findings. Residual risk is implementation error in the broad call-site cutover;
the finite per-row tests and final independent security review are mandatory
before package completion.
