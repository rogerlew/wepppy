# Shared project asset declarations tracker

Opened 2026-11-22 UTC. Owner group: project asset producers, Feature Export, query engine and WEPPcloud operations.

| Milestone | Status and evidence |
| --- | --- |
| Scaffold and design review | Complete for the scaffold. Three independent reviewers returned findings, which were addressed. See [contract decision](artifacts/20261122_contract_decision.md), [correctness review](artifacts/20261122_correctness_review.md) and [security review](artifacts/20261122_security_review.md). |
| Contract checkpoint | Verify independent dispositions and ancestor revision before implementation. |
| Scoped tests and implementation | Pending. Record exact node IDs, revision and results. |
| Actual production projects and isolated replay | Pending. Record coverage and mismatches against the [production protocol](artifacts/production_validation.md). |
| Adoption/rollout | Open for later decision. |

2026-11-22 UTC decision: keep consumer-specific policy and layer semantics with their owners. Actual production-project readback is mandatory even when every fixture and scoped unit test passes. No production experiment or deployment was performed for this scaffold.
