# Checkpoint Review Disposition

**Date**: 2026-08-04
**Status**: accepted; both independent post-fix confirmations passed with no
unresolved High or Medium findings

## Governance Findings

- **Exact approval (High) — resolved**: the operator explicitly approved the
  final matrix, then explicitly approved the superseding queue-specific
  cancellation rule and directed execution. The checkpoint, register, owners,
  tracker, and ExecPlan now record that chronology without relying on the
  earlier scaffold instruction.
- **Source boundary (Low) — resolved**: GOV-00A-M1G incorporates the package's
  exact `In Scope` source-path boundary by reference.

## Operations and Security Findings

- **Rollback concurrency (High) — resolved**: rollback now uses an ordinary
  maintenance admission fence, drains all executable `fork-archive` state
  before route reversion, and retains fencing until a D-state wepp3 host is
  fenced or its old process is proven dead. Validation is an operational
  interleaving drill; no artificial D-state simulation is required.
- **Restore exclusion fence (High) — accepted residual risk**: the operator
  rejected removing restore or introducing a broad cross-mutator fence. The
  hazard exists on the current multi-worker default queue and is a primary
  reason for this package. Moving restore to the single queue materially
  reduces concurrent NAS load; the immediate pre-deletion lock recheck is a
  bounded additional guard. The package does not claim transactional restore
  isolation. Project state may require deletion or retry after interruption,
  and D-state remains an operational NFS incident.
- **Wepp3 privilege boundary (Medium) — resolved in contract**: the dedicated
  worker may mount `/wc1` plus only inputs proven necessary by focused startup
  and task-import evidence. Docker socket and unrelated application/provider
  credentials are prohibited. Compose tests will enforce the result.
- **Sole consumer (Medium) — resolved in contract**: a wepp3-specific compose
  file contains the production service; wepp1 and wepp2 compose files do not.
- **Host-local inspection (Medium) — resolved in contract**: `wctl rq-info`
  gains a dedicated service selector, while the runbook retains local
  container/process/D-state inspection independent of Redis.
- **Cancellation scope clarification — resolved in contract**: the new rule is
  limited to jobs with RQ origin `fork-archive`. Existing buttons remain;
  authorized project users may cancel queued jobs; started cancellation
  requires Admin or Root. The non-Admin mutation path fails closed if dispatch
  has handed the job to an intermediate or started state and cannot issue a
  stop command. Every other queue, including Culvert compatibility, retains
  existing behavior.

## Scope-Control Rationale

The operator explicitly directed the package not to over-engineer rare D-state
events or add fragile simulation. This disposition therefore distinguishes the
bounded serialization improvement from a comprehensive NFS or transactional
restore redesign. No distributed lock framework, host-role framework,
automatic failover, or synthetic D-state test is introduced.
