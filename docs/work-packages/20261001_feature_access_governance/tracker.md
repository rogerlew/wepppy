# Feature access governance tracker

Timezone: UTC. Started: 2026-10-01 20:47 UTC.

Current phase: milestone one complete; account substrate/shared decisions implemented and validated, not wired to routes or deployed.

## Progress

- [x] Assessed baseline `45a39a8337d37c7f7d30087ff4d23c03610072b3`; 275 existing tests passed during the original assessment, not rerun as implementation evidence.
- [x] Prepared amendment/plan committed as `4cd85e2d5`; independent review fixes committed as `36f35b6f0`.
- [x] Operator clarified feature-only read-only behavior; ordinary anonymous creation/functionality unchanged. Broader writer/creator proposals withdrawn.
- [x] Verified designated `rogerlew@gmail.com`: local active ID 1, wepp1 active ID 12; resolve separately in every deployment before seeding.
- [x] Verified wepp2 Culvert client configuration/source and operation-token metadata; actual wepp1 signature matches, normal validation rejects expired token.
- [x] Froze bounded 516-declaration/79-file route snapshot, protected data/resource matrix, principal adapters and new web transport.
- [x] Completed final narrowed-checkpoint security/correctness reviews and findings disposition; zero unresolved High/Medium findings.
- [x] Committed standalone accepted checkpoint `d3639f970669411e9c0f5bf8e80898645c947559`.
- [x] Completed authorized milestone one implementation, validation and independent reviews.
- [ ] Milestones two through five remain future work.

## Decision log

2026-10-01: One maintainer records group membership person/scope/reason/actor/time. Separate OpenET/Batch groups initially contain only the designated account. No broad technical-role bypass. PowerUser sanctions remain deferred.

2026-10-01: Operator explicitly preserved ordinary anonymous creation and functionality. Read-only applies only to limited features for callers lacking entitlement. No creator grant, general owner gate, legacy recovery or incidental collaborator-management changes are authorized.

2026-10-01: Culvert client on wepp2 uses a submit-only operation credential, open polling and separate batch-bound browse token. Configured token expired September 1. Preserve validation and existing client semantics; no rotation/expiry bypass. Renewal and positive live acceptance are later operational dependencies.

## Evidence and checkpoint

[M0 evidence](artifacts/2026-10-01_milestone_zero.md), [credential matrix](artifacts/2026-10-01_credential_matrix.md), [route inventory](artifacts/2026-10-01_route_inventory.tsv), [contract decision](artifacts/2026-10-01_contract_decision.md), and [earlier reviews](artifacts/2026-10-01_contract_reviews.md).

Accepted checkpoint revision: `d3639f970669411e9c0f5bf8e80898645c947559`. Final review record: [independent M0 disposition](artifacts/2026-10-01_m0_reviews.md). Milestone zero made no runtime, account, membership, token or deployment mutation. Read-only operations used local account DB, wepp1 account DB/rq-engine validator, and wepp2 Culvert worker/configuration; secret values were not retained.

## Next milestone and operational dependency

Milestone one is complete. Next is milestone two: simple group administration and internal acknowledgment. Initial maintainer memberships still require per-deployment identity verification and an audited, explicitly authorized operation; no shared database migration or membership initialization was performed in milestone one. The expired configured Culvert credential must be renewed under separate operator authority before claiming successful live integration acceptance or rollout; implementation tests cannot substitute for that evidence.

## Milestone zero validation

Validation passed: 23 changed/new Markdown files linted with zero errors/warnings; relative file targets resolved; 516 inventory declarations across 79 existing files have valid line bounds and admission rules; whitespace and root AGENTS size checks passed. Spelling previews inspected; unrelated existing tracker wording retained. No runtime suite was required for milestone zero; existing baseline tests are not implementation acceptance.

## Milestone one implementation and validation

Four account models and migration `e7a1c9d204bf` follow existing head `d30c91a7b802`. The migration seeds only group definitions; tested schema/model parity and real Flask model registration pass. Shared decisions enforce current group membership, acknowledgment, resource/backend/prerequisite limits and contrast dependencies. Both metadata fields are required for the six governed features, including direct/dependency specs.

Validation completed: initial focused registry/route run **293 passed**; post-review PostgreSQL suite **26 passed**; final account/registry run including missing/null metadata cases **180 passed**. All three new modules pass stubtest; test-stub, documentation/link and whitespace checks pass. Broad-exception enforcement passed for tracked changes, and direct AST inspection found no broad catches in new modules. Observe-only quality report ran without radon; generated root reports were restored after retaining output in `/tmp`.

[Correctness review](artifacts/2026-10-01_m1_correctness_review.md) and [security review](artifacts/2026-10-01_m1_security_review.md) passed with zero unresolved High/Medium findings. Three Medium issues were corrected and independently confirmed. The broad `wctl run-pytest tests --maxfail=1` run passed: **10,149 passed, 126 skipped, 4,011 warnings in 2,477.03 seconds**. It started before the final metadata guard; the final source of that guard is covered by the 180-case rerun. No shared account schema or memberships have been changed; PostgreSQL test schemas were isolated and cleaned up.

The operator authorized committing the completed milestone-one implementation and validation records. The package stays open for milestones two through five; no PowerUser self-service, route enforcement or live Culvert compatibility pass is implied.
