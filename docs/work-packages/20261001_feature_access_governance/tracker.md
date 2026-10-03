# Feature access governance tracker

Timezone: UTC. Started: 2026-10-01 20:47 UTC.

Current phase: M5 is complete in the forest development environment. The final candidate has staged consumer-before-web deployment, real generated-output and public-sharing acceptance, archive/restore integrity, disposable database restore, and independent review. Production is unchanged.

The operator clarified that internal/embargo status restricts feature operation, while permitted users may share results more broadly. [FA-02 checkpoint](artifacts/2026-10-02_fa02_sharing_checkpoint.md) amends canonical authority and defines removal of the checkpoint's feature-derived read gates. Fork lineage/refusal and a DuckDB upgrade solely to enforce a result embargo are no longer decisions needed for M3. SQL/D-Tale findings must be reassessed for actual private-resource/containment violations. Existing private grouped-resource and action controls remain. FA-02 independent correctness/security contract reviews passed with all findings closed; ancestor commit is `102c81066` and runtime sharing reconciliation is implemented.

FA-02 review confirmed S04/S08 private Batch/Culvert escape paths independently of contrast sharing. The retained canary now shows S04 external reads blocked and S08 anonymous private-table reads denied with HTTP 403. Public D-Tale and declared query data remain readable. Independent bounded and final correctness/security reviews pass with zero unresolved findings. Exact-candidate service/browser acceptance is complete.

The [interim security review](artifacts/2026-10-02_m3_security_review.md) assessed FA-01 and was **NOT PASSED**. Its historical findings were remediated and independently closed under FA-02. The [final reviews](artifacts/2026-10-02_m3_final_reviews.md) report zero unresolved High, Medium or Low findings for candidate `23c2f27fe`. Frontend lint passed and **112 suites / 919 tests passed**. Test-stub, syntax, whitespace and scoped documentation checks passed. The exact-candidate [service/browser acceptance](artifacts/2026-10-02_m3_service_browser_acceptance.md) passed through the real local Caddy and service boundaries.

The final full Python regression passed **10,246 tests with 126 skipped and 12
subtests passed in 2,668.41 seconds (44:28)**. A deterministic collection-order
failure was traced to the signed-token test patching `redis.Redis` after
`rq_engine.auth` had captured the original constructor. Patching that captured
test boundary closed the isolation defect; production code was unchanged.

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
- [x] Implement milestone-two group administration/acknowledgment and complete focused/browser acceptance and independent reviews.
- [x] Back up/test-restore, migrate and initialize the local development database; retain sole-maintainer audit readback.
- [x] Complete broad Python regression: 10,198 passed, 126 skipped; finalize milestone-two handoff.
- [x] Reconcile FA-02 shared-result visibility and close S04/S08 private-resource containment with independent reviews.
- [x] Complete stable affected microservice/query/WEPPcloud regression: 3,468 passed, 2 skipped.
- [x] Execute milestone three: protected action/data admission, trusted credential provenance and public inspection.
- [x] Implement milestone four conservative maturity and PowerUser onboarding with real PostgreSQL/browser/token acceptance.
- [x] Complete milestone-four full regression: 10,267 passed, 126 skipped; frontend 112 suites / 919 tests passed.
- [x] Complete milestone five forest rollout, real workflow/artifact acceptance, backup restore/readback and final independent review.

## Decision log

2026-10-02: The live human-token subject is the positive numeric account ID used
by account/group adapters. Browse, D-Tale and Query Engine receive the existing
Postgres secret and retain Redis startup ordering; Query Engine separately
receives the existing WEPP verification secret for browser tokens. Private
D-Tale launch redirects are constructed only for the verified dataset using
D-Tale's double-quoting convention. No credential or trust class was added.

2026-10-01: One maintainer records group membership person/scope/reason/actor/time. Separate OpenET/Batch groups initially contain only the designated account. No broad technical-role bypass. PowerUser sanctions remain deferred.

2026-10-01: Operator explicitly preserved ordinary anonymous creation and functionality. Read-only applies only to limited features for callers lacking entitlement. No creator grant, general owner gate, legacy recovery or incidental collaborator-management changes are authorized.

2026-10-01: Culvert client on wepp2 uses a submit-only operation credential, open polling and separate batch-bound browse token. Configured token expired September 1. Preserve validation and existing client semantics; no rotation/expiry bypass. Renewal and positive live acceptance are later operational dependencies.

## Evidence and checkpoint

[M0 evidence](artifacts/2026-10-01_milestone_zero.md), [credential matrix](artifacts/2026-10-01_credential_matrix.md), [route inventory](artifacts/2026-10-01_route_inventory.tsv), [contract decision](artifacts/2026-10-01_contract_decision.md), and [earlier reviews](artifacts/2026-10-01_contract_reviews.md).

Accepted checkpoint revision: `d3639f970669411e9c0f5bf8e80898645c947559`. Final review record: [independent M0 disposition](artifacts/2026-10-01_m0_reviews.md). Milestone zero made no runtime, account, membership, token or deployment mutation. Read-only operations used local account DB, wepp1 account DB/rq-engine validator, and wepp2 Culvert worker/configuration; secret values were not retained.

## Rollout boundary and operational dependency

Forest is deployed and environment validated. OpenET/Batch groups contain only the verified designated account, with retained events and no fabricated acknowledgment. Production migration/initialization and service activation remain separately authorized rollout work. The expired Culvert credential still needs separately authorized renewal before positive live compatibility acceptance; it was not modified.

## Milestone zero validation

Validation passed: 23 changed/new Markdown files linted with zero errors/warnings; relative file targets resolved; 516 inventory declarations across 79 existing files have valid line bounds and admission rules; whitespace and root AGENTS size checks passed. Spelling previews inspected; unrelated existing tracker wording retained. No runtime suite was required for milestone zero; existing baseline tests are not implementation acceptance.

## Milestone one implementation and validation

Four account models and migration `e7a1c9d204bf` follow existing head `d30c91a7b802`. The migration seeds only group definitions; tested schema/model parity and real Flask model registration pass. Shared decisions enforce current group membership, acknowledgment, resource/backend/prerequisite limits and contrast dependencies. Both metadata fields are required for the six governed features, including direct/dependency specs.

Validation completed: initial focused registry/route run **293 passed**; post-review PostgreSQL suite **26 passed**; final account/registry run including missing/null metadata cases **180 passed**. All three new modules pass stubtest; test-stub, documentation/link and whitespace checks pass. Broad-exception enforcement passed for tracked changes, and direct AST inspection found no broad catches in new modules. Observe-only quality report ran without radon; generated root reports were restored after retaining output in `/tmp`.

[Correctness review](artifacts/2026-10-01_m1_correctness_review.md) and [security review](artifacts/2026-10-01_m1_security_review.md) passed with zero unresolved High/Medium findings. Three Medium issues were corrected and independently confirmed. The broad `wctl run-pytest tests --maxfail=1` run passed: **10,149 passed, 126 skipped, 4,011 warnings in 2,477.03 seconds**. It started before the final metadata guard; the final source of that guard is covered by the 180-case rerun. At milestone-one handoff, no shared account schema or memberships had been changed; PostgreSQL test schemas were isolated and cleaned up.

The operator authorized committing the completed milestone-one implementation and validation records. The package stays open for milestones two through five; no PowerUser self-service, route enforcement or live Culvert compatibility pass is implied.


## Milestone two implementation and validation

[Acceptance and local initialization](artifacts/2026-10-01_m2_acceptance.md) retains the full-app browser observations/screenshots, real database evidence and backup/restore details. Focused PostgreSQL tests: **75 passed**. Final route/usermod/Profile regression: **73 passed**. Browser workflow: **1 passed**, zero axe violations. Frontend: **112 suites / 919 tests passed**, standard and explicit new-script lint pass. Store/web stubtest and test-stub guard pass. Broad Python suite: **10,198 passed, 126 skipped, 4,010 warnings in 2,535.69 seconds (42:15)**. The final qualified-import/export cleanup is also covered by the 73-case route rerun and web stubtest. Documentation/link/whitespace checks and exact statement/policy readback pass.

[Correctness review](artifacts/2026-10-01_m2_correctness_review.md) and [security review](artifacts/2026-10-01_m2_security_review.md) confirmed all findings closed. Fixes cover initial Profile rendering, contrast dependency guidance, inactive-account effective status, stale-session token fallback and authentication-error correlation. No unresolved High/Medium/Low findings remain in this bounded milestone.

Local development is now at `e7a1c9d204bf`, with sole maintainer ID 1 in OpenET and Batch; [readback](artifacts/2026-10-01_m2_local_readback.json) confirms two audit events, no acceptances and unchanged account/role/run counts. Backup restore was tested before migration; production was not touched, no service was restarted, and runtime feature enforcement remains M3. User acknowledgment must be completed by the user; the initializer does not accept it on anyone's behalf.

## FA-02 runtime reconciliation, 2026-10-02

[Runtime validation](artifacts/2026-10-02_fa02_runtime_validation.md) records the
sharing implementation, regression results and disposable private-resource
reproductions. [Correctness review](artifacts/2026-10-02_fa02_runtime_correctness_review.md)
closed three findings; [security review](artifacts/2026-10-02_fa02_runtime_security_review.md)
closed the grouped cancellation-context regression. No new concrete sharing
reconciliation findings remain. S04/S08 containment is now implemented and the
retained synthetic canaries are denied. The [private-resource correctness review](artifacts/2026-10-02_private_resource_correctness_review.md)
closed PRC01–PRC10, and the [private-resource security review](artifacts/2026-10-02_private_resource_security_review.md)
closed all bounded findings; each reports zero unresolved findings. The exact
candidate [service/browser acceptance](artifacts/2026-10-02_m3_service_browser_acceptance.md)
and [final reviews](artifacts/2026-10-02_m3_final_reviews.md) close the remaining
M3 runtime gates. The stable affected microservice/query/WEPPcloud regression
passed **3,468 cases with 2 skipped**. The full repository passed **10,246 tests
with 126 skipped and 12 subtests passed**.

## Milestone four implementation and validation

[M4 acceptance](artifacts/2026-10-02_m4_acceptance.md) records the conservative
multi-OFE ceiling and atomic current-user PowerUser workflow. The final focused
registry/Profile/account run passed **275 tests**. The isolated full-app browser
passed **1 test**, with real role assignment, profile-token minting, private
Batch denial and zero axe violations; retained screenshots contain no token.
Frontend lint passed and **112 suites / 919 tests** passed. The final full
repository regression passed **10,267 tests, 126 skipped, 4,013 warnings in
2,794.19 seconds (46:34)**. A transient unrelated NoDb lock failure from the
first attempt passed in isolation and did not recur in the complete rerun.

No schema migration, shared membership, token scope/lifetime, queue topology,
service credential or production state changed. PowerUser suspension,
reinstatement and permanent revocation remain outside scope.

## Milestone five implementation and validation

[Forest acceptance](artifacts/2026-10-03_m5_forest_acceptance.md) records the
staged consumer-before-web deployment, a real Omni execution, generated reports,
public read-only browser access, denied anonymous mutation, archive/restore byte
integrity, and disposable PostgreSQL restore/readback. The fork path rebases
nested Omni controllers through root-anchored, no-follow descriptors with
identity-bound publication and rollback. The focused fork suite passed 107
tests; frontend lint and **113 suites / 922 tests** passed. The final review and
broad Python result are retained in the M5 artifacts. The first broad attempt
encountered one unrelated stale test-only NoDb lock; the exact case passed alone,
the two dead-owner lock keys were removed, and the clean complete rerun exited
zero. Its PTY summary was truncated, so no numerical pass total is inferred.
