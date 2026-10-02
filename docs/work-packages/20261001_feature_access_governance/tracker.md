# Feature access governance tracker

Timezone: UTC. Started: 2026-10-01 20:47 UTC.

Current phase: FA-02 result-sharing amendment and M3 reconciliation. M3 is checkpointed at `458557219` but incomplete; M2 is `c19fefcc6`. Production rollout remains later work.

The operator clarified that internal/embargo status restricts feature operation, while permitted users may share results more broadly. [FA-02 checkpoint](artifacts/2026-10-02_fa02_sharing_checkpoint.md) amends canonical authority and defines removal of the checkpoint's feature-derived read gates. Fork lineage/refusal and a DuckDB upgrade solely to enforce a result embargo are no longer decisions needed for M3. SQL/D-Tale findings must be reassessed for actual private-resource/containment violations. Existing private grouped-resource and action controls remain. FA-02 independent correctness/security contract reviews passed with all findings closed; ancestor commit is `102c81066` and runtime sharing reconciliation is implemented.

FA-02 review confirms that S04/S08 also have source-supported private Batch/Culvert escape paths, independently of contrast sharing. Retain those as High implementation findings pending bounded reproduction/remediation; accepting the sharing policy does not close them. Public contrast-only denial/filtering findings are superseded as detailed in the checkpoint.

The [interim security review](artifacts/2026-10-02_m3_security_review.md) assessed FA-01 and was **NOT PASSED**. Its historical two open High findings and eight applied fixes are reassessed in the FA-02 checkpoint; this policy change is not a claim of technical closure or a passing final review. The reconciled affected microservice/WEPPcloud scope passed **3,325 of 3,326** tests; the sole pre-existing run-catalog latency threshold failure passed both parameterizations in isolation. Independent focused correctness ran **84 passed**. Frontend lint passed and **112 suites / 919 tests passed**. Test-stub, syntax, whitespace and scoped documentation checks passed. Full repository regression, private-resource remediation and production-equivalent browser/service acceptance remain pending.

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
- [ ] Execute milestone three: protected action/data admission, trusted credential provenance and public inspection.
- [ ] Milestones four and five remain future work.

## Decision log

2026-10-01: One maintainer records group membership person/scope/reason/actor/time. Separate OpenET/Batch groups initially contain only the designated account. No broad technical-role bypass. PowerUser sanctions remain deferred.

2026-10-01: Operator explicitly preserved ordinary anonymous creation and functionality. Read-only applies only to limited features for callers lacking entitlement. No creator grant, general owner gate, legacy recovery or incidental collaborator-management changes are authorized.

2026-10-01: Culvert client on wepp2 uses a submit-only operation credential, open polling and separate batch-bound browse token. Configured token expired September 1. Preserve validation and existing client semantics; no rotation/expiry bypass. Renewal and positive live acceptance are later operational dependencies.

## Evidence and checkpoint

[M0 evidence](artifacts/2026-10-01_milestone_zero.md), [credential matrix](artifacts/2026-10-01_credential_matrix.md), [route inventory](artifacts/2026-10-01_route_inventory.tsv), [contract decision](artifacts/2026-10-01_contract_decision.md), and [earlier reviews](artifacts/2026-10-01_contract_reviews.md).

Accepted checkpoint revision: `d3639f970669411e9c0f5bf8e80898645c947559`. Final review record: [independent M0 disposition](artifacts/2026-10-01_m0_reviews.md). Milestone zero made no runtime, account, membership, token or deployment mutation. Read-only operations used local account DB, wepp1 account DB/rq-engine validator, and wepp2 Culvert worker/configuration; secret values were not retained.

## Next milestone and operational dependency

Next is milestone three: wire restricted feature action/data admission and public read-only views across the frozen matrix. Milestone-two implementation and validation are complete; the operator authorized committing this milestone. Local OpenET/Batch groups contain only the verified designated account, with retained events and no fabricated acknowledgment. Production migration/initialization and service activation remain rollout work. The expired Culvert credential still needs separately authorized renewal before positive live compatibility acceptance; it was not modified.

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
reconciliation findings remain. M3 remains incomplete: S04/S08 are reproduced
private-resource defects, not contrast-sharing policy questions. Full regression
and service acceptance remain separately tracked in the validation record.
