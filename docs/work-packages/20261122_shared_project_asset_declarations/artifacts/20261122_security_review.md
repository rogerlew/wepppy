# Security and operational review

High impact. The independent production/security reviewer reviewed the proposed contract, decision, ExecPlan and actual-project protocol on 2026-11-22 UTC. No remaining scaffold blocker after disposition. Baseline `94ad6360266a`; implementation and operational sign-off remain open.

| Surface and finding | Disposition |
| --- | --- |
| Child/parent containment, symlinks, stale absolute roots and scope replacement | Preserve each consumer's authorization. Pin incarnation and physical identity, and cover both authorized and denied cases. |
| NoDb hydration, catalog freshness repair and export publication can turn a nominal read into a write. | Enforce a read-only production mount, use vetted detached reads, isolate queue/cache access and private output. Exercise the normal writer/export path on a matching private writable replay. |
| Sensitive project paths or contents could escape through evidence. | Keep raw bindings and row evidence private; publish sanitized counts, digests and dispositions. |
| NFS pressure, moving inputs or partial cohort | Predefine observation bounds, run serially, monitor ordinary workers, stop on impact and retain inconclusive cases. |
| Network, permissions, deployment and CI | Proposed scope adds no production service, dependency, privilege, queue or external transfer. Reassess the actual candidate and review any escalation before rollout. |

Before release, review the implemented resolver, both consumer boundaries, actual artifacts and residual risks. No production candidate ran during this scaffold review.
