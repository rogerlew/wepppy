# FA-01 security review preparation

Status: Not reviewed; hold for independent checkpoint and implementation review.

Package: `docs/work-packages/20261001_feature_access_governance/`

Prepared by: Codex, amendment author, 2026-10-01 20:47 UTC. Independent reviewer: unassigned.

## Triage

Security impact: high. This package changes privilege assignment, current group admission, public data inspection, restricted internal operations and human/service authorization composition. The current turn changes documentation only. No authority, credential, database or deployment mutation has occurred.

## Review surfaces and required evidence

| Surface | Evidence needed before passing |
| --- | --- |
| PowerUser self-service | Current-user binding, two affirmative answers, atomic acceptance/role record, duplicate handling, CSRF/origin enforcement; no extra role choice |
| Group administration | Root-only mutation, reason/actor/time, no unauthorized group scope invention, durable non-cascading history, direct transaction rollback/concurrency tests |
| Group-only features | Root/Admin/Dev without membership cannot execute OpenET/Batch; verified sole-member initialization; later membership decisions auditable |
| Public inspection | Valid public reads work without writer authority or side effects; direct actions denied; no protected credentials/audit PII exposed |
| Embargo and derived data | Exact report/file/query/archive/fork representation coverage, valid non-embargoed reads preserved, no path-guessing-only protection |
| Culvert service | Verified identity/scope/consumer inventory; submit/retry/finalize/poll/cancel/browse/download compatibility; cross-batch denial; no secret logging |
| Tokens and membership freshness | Signature/audience/scope/expiry/revocation remain enforced; stale group claim cannot retain membership; service principal not treated as user ID |
| Migration and rollback | Additive upgrade/readback; no broad automatic membership; history retained; rollout orders consumers before self-service; rollback cannot restore broad admission |

## Valid-state noninterference

The reviewer must use the separate state/principal matrix in `2026-10-01_surface_inventory.md`. Absent optional state, empty output, legacy users and legitimate anonymous creator sessions must reach their accepted outcomes. Denial of valid workflows is a correctness failure, not a security success.

## Findings and verdict

No independent findings inventory or sign-off exists yet. Do not interpret this as zero findings. Gate: hold. The author has identified milestone-zero gaps (writer authority, exact artifacts and verified identities) that must be resolved before the technical review can pass.

Use `docs/prompt_templates/security_review_template.md` for the completed review, including actual checks of authentication/session/CSRF, secrets, input/path, queues, cross-service access, data concurrency, logging and rollback. The single-maintainer operational approval model does not waive engineering review.
