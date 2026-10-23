# Independent security and operations contract review

Reviewer: `/root/contract_security` (security_reviewer agent), read-only. Initial review: 2026-10-23 20:15 UTC. Base: `fc3234efc6da58ff1da896dfab5b2dd5875988c2`. Security triage: high for future queue/filesystem/public polling boundary. Initial verdict: changes required.

## Findings

- S1 / high: `_query_engine/refresh/publication.lock` is replaced during restore. An old process can retain the unlinked inode while a new publisher takes a new lock. Name a stable shared lifecycle guard, lock order and incarnation/descriptor checks; test old-holder/new-inode and restore/delete races directly.
- S2 / medium: “Run-authorized or sanitized” leaves privacy policy unresolved. Ordinary UUID jobs expose descriptions/results/exceptions through current polling. Specify classification before deserialization and deterministic safe shape for single/batch/recursive/missing/import-failed/abandoned/rollback-retained records; cross-link RQ contract.
- S3 / medium: Blanket READONLY no-write wording conflicts with explicit combined-viewer offline staged/manifest-owned preparation. Preserve that positive valid workflow and exclude generic workers from inheriting its exception.
- S4 / medium: Shared batch consumers include companion/off-host workers. Require compatible protocol, storage namespace/root mapping and coordination at admission/startup/execution; unavailable compatibility leaves durable pending work, without changing worker identity/mounts/privileges/topology.

## Positive and residual assessment

Explicit async interface, durable acknowledgment, atomic publication, barriers, Redis-loss recovery and index-only work are sound. High-impact triage is appropriate. Approval is limited to the contract phase; real queue, polling, NFS and lifecycle evidence remains required before deployment.

## Post-fix confirmation

2026-10-23 20:19 UTC: reviewer approves contract design; S1–S4 closed and no new medium/high findings. Low wording recommendation S5 distinguishes full sanitized job-info shape from existing successful jobstatus shape; incorporated. Runtime NFS/lifecycle/privacy/READONLY evidence remains pending. Final standalone-mode addition sent for confirmation. Disposition is in `2026-10-23_review_disposition.md`.

Final confirmation: 2026-10-23 20:20 UTC — reviewer approves contract design. S1–S5 closed; standalone policy does not reopen lifecycle fencing. No unresolved security findings; execution evidence remains pending.
