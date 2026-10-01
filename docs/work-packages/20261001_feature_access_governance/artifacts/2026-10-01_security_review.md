# FA-01 security review preparation

Scope update, 2026-10-01: the operator clarified that only limited features become read-only for callers lacking access; ordinary anonymous creation/functionality is unchanged. Earlier general writer/creator-proof requirements in this historical review are superseded. Current scope and deployed evidence are in [the M0 record](2026-10-01_milestone_zero.md). Final narrowed-checkpoint reviews are separate from the earlier review confirmations.


Status: Prepared-plan security review passed after documented fixes; M0 design review also passed after fixes; implementation review pending.

Package: `docs/work-packages/20261001_feature_access_governance/`

Prepared by: Codex, amendment author, 2026-10-01 20:47 UTC. Prepared-plan independent reviewer: `/root/contract_security`; implementation reviewer remains unassigned.

## Triage

Security impact: high. This package changes privilege assignment, current group admission, public data inspection, restricted internal operations and human/service authorization composition. The current turn changes documentation only. No authority, credential, database or deployment mutation has occurred.

## Review surfaces and required evidence

| Surface | Evidence needed before passing |
| --- | --- |
| PowerUser self-service | Current-user binding, two affirmative answers, atomic acceptance/role record, duplicate handling, CSRF/origin enforcement; no extra role choice |
| Group administration | Root-only mutation, reason/actor/time, no unauthorized group scope invention, durable non-cascading history, direct transaction rollback/concurrency tests |
| Group-only features | Root/Admin/Dev without membership cannot execute OpenET/Batch; verified sole-member initialization; later membership decisions auditable |
| Public inspection | Unentitled limited-feature views are observational; restricted actions denied; ordinary anonymous behavior unchanged; no protected credentials/audit PII exposed |
| Embargo and derived data | Exact report/file/query/archive/fork representation coverage, valid non-embargoed reads preserved, no path-guessing-only protection |
| Culvert service | Verified identity/scope/consumer inventory; submit/retry/finalize/poll/cancel/browse/download compatibility; cross-batch denial; no secret logging |
| Tokens and membership freshness | Signature/audience/scope/expiry/revocation remain enforced; stale group claim cannot retain membership; service principal not treated as user ID |
| Migration and rollback | Additive upgrade/readback; no broad automatic membership; history retained; rollout orders consumers before self-service; rollback cannot restore broad admission |

## Valid-state noninterference

The reviewer must use the separate state/principal matrix in `2026-10-01_surface_inventory.md`. Absent optional state, empty output, legacy users and legitimate anonymous creator sessions must reach their accepted outcomes. Denial of valid workflows is a correctness failure, not a security success.

## Findings and verdict

[Independent prepared-plan findings and disposition](2026-10-01_contract_reviews.md) record the High private-credential admission issue and Medium identity-provenance issue, both independently confirmed closed in documentation. Prepared-plan verdict: ready for milestone zero, no unresolved High/Medium findings from that review. Runtime gate: hold. The narrowed M0 review separately checks exact artifacts, verified identities, provenance and preserved anonymous behavior; no runtime or implementation review pass is claimed.

Use `docs/prompt_templates/security_review_template.md` for the completed review, including actual checks of authentication/session/CSRF, secrets, input/path, queues, cross-service access, data concurrency, logging and rollback. The single-maintainer operational approval model does not waive engineering review.

Final narrowed M0 verdict: [security review passed](2026-10-01_m0_reviews.md) with zero unresolved High/Medium findings; implementation/runtime gate remains open.
