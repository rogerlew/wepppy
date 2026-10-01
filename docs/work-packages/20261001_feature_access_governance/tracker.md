# Feature access governance tracker

Timezone: UTC

Started: 2026-10-01 20:47 UTC

Current phase: amendment and implementation planning

Security impact: high; independent contract, correctness and security reviews pending.

## Progress

- [x] Source assessment and baseline evidence retained: 275 existing tests passed in the assessment; not rerun as implementation evidence.
- [x] Operator directions recorded: public read-only views; single-maintainer auditable groups; OpenET/Batch group-only initial one-person membership; internal Batch/Culvert; conservative maturity; deferred PowerUser sanctions.
- [x] FA-01 canonical amendment, ADR and linked shared contracts prepared.
- [x] Self-contained active ExecPlan, migration/compatibility plan and acceptance matrices prepared.
- [ ] Freeze exact endpoint/artifact inventory and public-write/anonymous-creator authority.
- [ ] Resolve designated account and redacted Culvert service identity/scope inventory.
- [ ] Obtain two independent contract reviews, close findings, and record accepted ancestor commit.
- [ ] Implement database/evaluator, group management, read/action enforcement and PowerUser onboarding in plan order.
- [ ] Complete independent correctness/security reviews and real workflow acceptance before rollout.

## Decision log

2026-10-01 20:47 UTC: FA-01 uses separate inspection/action decisions because public feature visibility must not grant API/compute actions. Existing publication-embargo data protection is retained while the public-release question remains unanswered; no release is inferred.

2026-10-01 20:47 UTC: Single maintainer records group membership reason, actor and timestamps. The former dual-role workflow is removed for staffing reasons. Engineering contract/security reviews do not become operational access approvals.

2026-10-01 20:47 UTC: OpenET/Batch restrictions are enforced by separate groups with only the designated maintainer initially enrolled. No hard-coded account authorization and no broad-role bypass. Culvert service compatibility is independent of human groups.

2026-10-01 20:47 UTC: PowerUser suspension, reapplication and permanent revocation are excluded. Group membership removal and existing token revocation remain distinct. Grouped data admission is corrected before general self-service opens.

## Checkpoint and evidence

Starting revision: `45a39a8337d37c7f7d30087ff4d23c03610072b3`.

Contract ancestor revision: not created. Independent reviews: not performed. Runtime edits: none. Account/token mutations: none. Deployment: none.

Prepared records: [decision](artifacts/2026-10-01_contract_decision.md), [surface inventory](artifacts/2026-10-01_surface_inventory.md), [review gates](artifacts/2026-10-01_review_gates.md). Documentation checks passed: all 20 changed/new Markdown files linted with zero errors/warnings; relative link targets resolved; `git diff --check` clean; root AGENTS size 160/160. Spelling previews inspected without rewriting unrelated tracker prose.

## Next steps

Milestone zero of the [ExecPlan](prompts/active/feature_access_governance_execplan.md) closes concrete identity, writer-authority and surface questions, then gets the exact technical matrix reviewed. Runtime work is not authorized by an uncommitted, unreviewed plan. Preserve the current branch and unrelated working-tree changes.
