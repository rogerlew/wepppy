# Independent correctness contract review

Reviewer: `/root/contract_correctness` (reviewer agent), read-only. Initial review: 2026-10-23 20:15 UTC. Base: `fc3234efc6da58ff1da896dfab5b2dd5875988c2`. Reviewed canonical contract, package, caller matrix and ExecPlan, plus targeted consumer/native source. Initial verdict: changes required.

## Findings

- C1 / high: Existing synchronous context/report helpers are not freshness barriers for already-cataloged assets. They reuse readable catalogs or repair only missing entries. Require internal receipt/source-aware barriers and cache reload before producer migration, including changed schema/fs_path/alias tests. Public pending UX may remain later.
- C2 / high: Artifact rename followed by receipt creation leaves a process-death gap with no durable request. Receipt-only rediscovery cannot guarantee convergence. Require prepublication intent or recurring source reconciliation, plus a kill-point test with no later user action.
- C3 / medium: Native scans catalog JSON under the new refresh journal, creating stale/self-referential datasets. Exclude the exact refresh subtree from query indexing while preserving browse/download/archive visibility.
- C4 / medium: New strict unreadable-asset failure requirements conflict with retained synchronous best-effort schema behavior. Scope strictness to new async acknowledgment/barriers and preserve compatibility APIs unless separately changed.

## Positive and residual assessment

Broad caller inventory and explicit synchronous API retention are appropriate. Atomic publication, exact receipt acknowledgment, child scope identity and batch deadlock avoidance are recognized. This review does not prove NFS locks, lifecycle exclusion, capacity or live workflow behavior; those remain implementation gates.

## Post-fix confirmation

2026-10-23 20:19 UTC: C1–C4 closed at contract level. New C5 (medium): standalone/temp synchronous directories lack production namespace/mount access; specify a local guard mode without allowing managed roots to bypass shared coordination. Primary author added the policy and requested final confirmation. Disposition is in `2026-10-23_review_disposition.md`.

Final confirmation: 2026-10-23 20:20 UTC — reviewer approves contract checkpoint preparation. C1–C5 closed; no remaining high/medium correctness findings. Design only; runtime evidence remains pending.
