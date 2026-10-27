# Security review — streaming inventory contract checkpoint

## Findings

| ID | Severity | Surface | Evidence and required action | Status |
| --- | --- | --- | --- | --- |
| INV-SEC-01 | Low | Public maintenance classification | The new refresh contract assigns configuration-wide discovery jobs the existing reserved prefix, while `rq-response-contract.md` describes that prefix in terms of the per-project task. Explicitly include inventory maintenance under the same sanitized fields/error envelope, with detailed inventory records restricted to operator diagnostics. No new public shape is needed. | Resolved: canonical RQ section now explicitly covers inventory tasks and operator-only detail. |

No unresolved contract findings at any severity. The owner amended the canonical
RQ disclosure section; independent readback confirmed closure of INV-SEC-01. This is a design review, not
approval of unimplemented queue/filesystem behavior or production enablement.

## Metadata and scope

- Reviewer: `/root/inventory_security_review`, independent security reviewer.
- Date: 2026-10-27 UTC.
- Starting revision: `8593a299596b289dea8ffac548d889be74e5efe6`.
- Reviewed: [checkpoint decision](20261027_inventory_contract_decision.md),
  [refresh contract — Recovery and liveness](../../../schemas/query-engine-catalog-refresh-contract.md#recovery-and-liveness),
  [ADR-0104 clarification](../../../adrs/ADR-0104-query-catalog-refresh-operational-bounds.md#october-27-inventory-execution-clarification),
  and the existing RQ maintenance-prefix/admission behavior.
- Related correctness review: `20261027_inventory_contract_correctness_review.md`.
- Excluded: HTTP/MCP implementation, inventory implementation, deployment and
  production operations. No canonical contract or production code was edited.

## Triage and authority

Security impact is **high**: the added worker task consumes Redis-derived paths
and coordinates filesystem discovery across processes. A dedicated final
implementation review remains required. The operator's instruction to proceed
with the four recommended remediation steps supports this bounded internal
change. Prior measured listing timeouts justify moving discovery to the existing
batch queue; there is no new queue, service, dependency, mount or privilege.

Assumptions: Redis and worker registration are internal trusted infrastructure,
not user-controlled authorization sources. Configuration defines root authority;
a queued locator or cursor cannot extend it. Discovery only writes derived Redis
state. Existing authorized refresh paths alone write project metadata. Filesystem
roots and durable receipts reconstruct discovery after Redis loss.

## Surface checks and implementation obligations

| Surface | Contract disposition and required implementation evidence |
| --- | --- |
| Auth/session/CSRF | No new public endpoint or authorization rule. Reject user-selected roots/functions/queues. Preserve current project access and model-job responses. |
| Worker capability and mixed rollout | The added inventory capability must participate in exact configuration comparison at admission and execution. Every eligible consumer must match; one compatible worker does not permit mixed admission. Validate the executing worker registration before filesystem access. Do not bump filesystem receipt/incarnation protocol merely to advertise this worker capability. |
| Paths and filesystem | Traverse configured roots only. Validate cursor structure, root indexes and relative components; reject traversal/absolute locators and symlink escape at traversal and consumption. Revalidate directory replacement and project incarnation before downstream writes. Include a real filesystem valid/hostile boundary test, not only mocked orchestration. |
| Readonly and legacy roles | Include active legacy projects; do not make missing or read-only namespaces disappear. Discovery needs read/search access only. Validate the existing wepp3 fork/archive role independently; this contract does not authorize writable remounts, chmod or a new queue membership. |
| Job ownership and concurrency | Current job identity plus cycle fences every checkpoint, failure/completion publication and ownership-sensitive cleanup. A replaced job may finish blocked I/O but must fail publication. Test stale job A after job B admission and after cycle replacement. |
| Atomic retained progress | Mark a child seen atomically with its frontier/scope publication. Commit directory exhaustion only after preceding entries. Scheduler batch acknowledgment and pending-cursor incorporation are one fenced transaction; post-commit trim must target only acknowledged sequence/cycle records. Test death on both sides of each boundary and replay after uncertain transaction results. |
| Completion and recovery | Required traversal failures remain incomplete and retryable. Empty valid roots may complete; missing/error roots may not. Full discovery completion and full reconciliation completion remain distinct. Restart may replay the current directory prefix; it must retain prior discoveries. Redis loss reconstructs, rather than silently treating absent derived state as completed. |
| Resource use and denial of service | Existing timeout/retry limits and one active inventory job constrain worker occupancy; they are not measured capacity. Measure retained frontier/dedup/batch storage and queued discoveries. Generation cleanup must preserve active/unacknowledged work and avoid indefinite abandoned-state accumulation. No untested first-page extrapolation or capacity claim. |
| Public polling and logs | Existing prefix classification occurs before deserialization for single/batch/recursive polling, including failed, malformed, expired and retained jobs. Inventory paths, root lists, results and raw errors remain absent from open responses. Detailed discovery diagnostics belong to authorized operator surfaces. |
| Secrets, subprocesses, egress and supply chain | No new secret flow, shell execution, egress destination or external dependency is proposed. Do not expose configuration secrets through diagnostics. |
| Rollback and artifacts | Retain receipts and incomplete progress, fence obsolete jobs, and keep the privacy classifier through job retention. Project artifact visibility/archive obligations remain unchanged; Redis inventory state is derived coordination, not a replacement scientific record. |

Valid states considered separately: absent derived state, empty configured roots,
populated and nested projects, readonly projects, active legacy namespaces,
ordinary directory mutation, directory replacement, missing/unreadable roots,
malformed cursor, symlink/traversal attempts, mixed consumers, worker death,
replaced job generation, stalled I/O and Redis loss. Security constraints must
preserve each valid outcome; this review does not replace the correctness gate.

## Verdict and validation

**Contract gate: pass. Implementation and production gates: pending.** No medium/high risk acceptance is requested.
A completed contract checkpoint must remain an ancestor of inventory code edits.

Read-only review checked the proposed contracts against existing worker admission,
capability comparison, job-ID generation and canonical polling policy. No runtime
security tests were run because inventory implementation does not yet exist.
Before release, require real Redis race/recovery tests, a real containment test,
normal-worker execution, public polling privacy, complete legacy enumeration,
forced worker restart and production identity/mount parity. Queue graph and live
job-tree checks remain required when wiring changes.

Residual risks are explicit rollout gates: prefix replay cost, NFS blocking beyond
an application deadline, batch occupancy and Redis checkpoint growth. They are
not accepted production limitations merely because the contract is approved.

Security reviewer sign-off: `/root/inventory_security_review`, 2026-10-27 UTC.
Package-owner disposition and runtime release sign-off remain separate.
