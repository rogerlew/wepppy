# MRS-01 independent contract reviews

Date: 2026-10-30. Baseline: `e35d7a3e69497ddfd9709736af50107f56963584`.
Reviewed surface: new `docs/schemas/request-payload-contract.md`, six schema integration
amendments plus the hillslope-clipping contract reconciliation, package/decision/consumer matrix and active ExecPlan. No implementation
was edited. The author (root Codex) dispositions findings; reviewers are separate
read-only agents and do not approve their own amendments.

## Flask / security review

Reviewer: `/root/flask_contract_review`, security_reviewer.
Initial verdict: hold for two medium ambiguities. Follow-up verdict after fixes:
**checkpoint-only approval**, no remaining medium/high contract findings.

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| F-01 | Medium | Null/blank table left different Flask state setters ambiguous, omitted bootstrap disabled | Split project/WEPP, soils, climate/WATAR and bootstrap rows; preserve explicit legacy sentinels; reviewer confirmed closed |
| F-02 | Medium | Recorder described with top-level list exceptions | Require object envelope with nested events array; reviewer confirmed closed |
| F-03 | Low | Generic tokens could obscure Geneva native-only config flags | Cite current Geneva specification/native-only constraint; reviewer confirmed closed |

The reviewer confirms revised webhook ordering preserves replay and cleanup.
Security approval is limited to checkpoint design; actual repair, direct tests,
final security review and commit authority/ancestry remain outstanding.

## RQ correctness review

Reviewer: `/root/rq_contract_review`, reviewer.
Initial source audit identified webhook-only body guards, undeclared deletion flag,
early Omni recovery/upload promotion and malformed numeric fallback. These are
registered implementation obligations, not resolved by documentation alone.

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| R-01 | Medium | Pre-reservation validation language could force state-dependent checks before replay | Limit prerequisite to transport/raw flags/structure and state-independent values; reserve/replay remains before state-dependent checks; later rejection uses existing cleanup |
| R-02 | Medium | Numeric malformed-value rule omitted null/blank/collection/conversion policy | Added bounded numeric acceptance table, preserving sentinels and existing conversion semantics; reject malformed nonempty/nonfinite values without new scientific range/integrality |

| R-03 | High | Existing hillslope-clipping contract explicitly retained malformed no-update/infinity exceptions | Amended User Controls and Validation and Failure Behavior; preserved numeric alias/sentinel/finite conversion/runtime policies; both independent reviewers confirmed resolved |

Post-fix RQ confirmation: **checkpoint approved**, no remaining medium/high contract
findings, 2026-10-30 23:37:25 UTC. Flask/security reviewer independently rechecked
the clipping reconciliation and reaffirmed checkpoint-only approval. Commit
authority remains absent; accepted documentation alone does not permit implementation.

## Review limits

These are pre-implementation contract reviews. The source matrix labels candidates
unresolved rather than inferring conformance. Final correctness, QA and security
reviews must inspect exact ancestry, source changes, real-route exception mapping,
NoDb persistence/cache evidence, actual multipart cleanup and WAM-01 compatibility.
No production deployment or full failure-class closure follows from checkpoint approval.
