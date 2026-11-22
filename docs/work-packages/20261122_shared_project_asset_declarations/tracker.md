# Shared project asset declarations tracker

Opened 2026-11-22 UTC. Owner group: project asset producers, Feature Export, query engine and WEPPcloud operations.

| Milestone | Status and evidence |
| --- | --- |
| Scaffold and design review | Complete for the scaffold. Three independent reviewers returned findings, which were addressed. See [contract decision](artifacts/20261122_contract_decision.md), [correctness review](artifacts/20261122_correctness_review.md) and [security review](artifacts/20261122_security_review.md). |
| Contract checkpoint | Complete. Reviewed contract `1b51ac142` is an ancestor of implementation baseline `a957440ab`. |
| Scoped tests and implementation | Passed on `f17ec6ca3`. The combined suite passed 461 cases with no skips, including disposable-Redis RQ tests. The separate Roads inspection passed 6. Additional query/report regression coverage passed 261 cases, with overlap. [Scoped evidence](artifacts/20261122_scoped_validation.md). |
| Actual production projects and isolated replay | Fourteen production views, 56 matched observations; private normal-project writer and fresh export replay passed. All 21 scenarios inspected used the parent watershed, matching the clone contract and the operator’s expectation. Two primary scenario loss tables had values distinct from the parent. [Observed cohorts and gaps](artifacts/20261122_live_project_comparison.md) · [Private replay](artifacts/20261122_private_replay.md). |
| First-slice disposition | Complete on 2026-11-22 UTC. [Implementation review](artifacts/20261122_implementation_correctness_review.md) accepted all six production case classes. [Security review](artifacts/20261122_implementation_security_review.md) records the authorization outcomes. |
| Adoption/rollout | Consider a separate shadow study before expanding discovery or changing defaults. This revision preserves full traversal; throughput was outside this experiment. |

2026-11-22 UTC decision: keep consumer-specific policy and layer semantics with their owners. Actual production-project readback is mandatory even when every fixture and scoped unit test passes. The production comparison used isolated readers on the original NFS projects. Worker deployment remains a separate release decision.
