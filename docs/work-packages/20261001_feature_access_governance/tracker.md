# Feature access governance tracker

Timezone: UTC. Started: 2026-10-01 20:47 UTC.

Current phase: milestone zero complete; accepted documentation checkpoint committed. Runtime work has not started.

## Progress

- [x] Assessed baseline `45a39a8337d37c7f7d30087ff4d23c03610072b3`; 275 existing tests passed during the original assessment, not rerun as implementation evidence.
- [x] Prepared amendment/plan committed as `4cd85e2d5`; independent review fixes committed as `36f35b6f0`.
- [x] Operator clarified feature-only read-only behavior; ordinary anonymous creation/functionality unchanged. Broader writer/creator proposals withdrawn.
- [x] Verified designated `rogerlew@gmail.com`: local active ID 1, wepp1 active ID 12; resolve separately in every deployment before seeding.
- [x] Verified wepp2 Culvert client configuration/source and operation-token metadata; actual wepp1 signature matches, normal validation rejects expired token.
- [x] Froze bounded 516-declaration/79-file route snapshot, protected data/resource matrix, principal adapters and new web transport.
- [x] Completed final narrowed-checkpoint security/correctness reviews and findings disposition; zero unresolved High/Medium findings.
- [x] Committed standalone accepted checkpoint `d3639f970669411e9c0f5bf8e80898645c947559`.
- [ ] Implement milestones one through five only under subsequent runtime authority.

## Decision log

2026-10-01: One maintainer records group membership person/scope/reason/actor/time. Separate OpenET/Batch groups initially contain only the designated account. No broad technical-role bypass. PowerUser sanctions remain deferred.

2026-10-01: Operator explicitly preserved ordinary anonymous creation and functionality. Read-only applies only to limited features for callers lacking entitlement. No creator grant, general owner gate, legacy recovery or incidental collaborator-management changes are authorized.

2026-10-01: Culvert client on wepp2 uses a submit-only operation credential, open polling and separate batch-bound browse token. Configured token expired September 1. Preserve validation and existing client semantics; no rotation/expiry bypass. Renewal and positive live acceptance are later operational dependencies.

## Evidence and checkpoint

[M0 evidence](artifacts/2026-10-01_milestone_zero.md), [credential matrix](artifacts/2026-10-01_credential_matrix.md), [route inventory](artifacts/2026-10-01_route_inventory.tsv), [contract decision](artifacts/2026-10-01_contract_decision.md), and [earlier reviews](artifacts/2026-10-01_contract_reviews.md).

Accepted checkpoint revision: `d3639f970669411e9c0f5bf8e80898645c947559`. Final review record: [independent M0 disposition](artifacts/2026-10-01_m0_reviews.md). No runtime, account, membership, token or deployment mutation occurred. Read-only operations used local account DB, wepp1 account DB/rq-engine validator, and wepp2 Culvert worker/configuration; secret values were not retained.

## Next milestone and operational dependency

After the accepted ancestor is recorded, milestone one is additive account records/shared decisions. The current authorization ends at milestone zero. The expired configured Culvert credential must be renewed under separate operator authority before claiming successful live integration acceptance or rollout; implementation tests cannot substitute for that evidence.

## Validation

Validation passed: 23 changed/new Markdown files linted with zero errors/warnings; relative file targets resolved; 516 inventory declarations across 79 existing files have valid line bounds and admission rules; whitespace and root AGENTS size checks passed. Spelling previews inspected; unrelated existing tracker wording retained. No runtime suite is required for this documentation-only work; existing baseline tests are not implementation acceptance.
