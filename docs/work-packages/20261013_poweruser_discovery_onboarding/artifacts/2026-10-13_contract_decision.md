# PUUX-01 contract decision — prepared, not ratified

Recorded: 2026-10-13 17:42 UTC. Base: `a8de37a0db1e678e76eefb36a991514036fb9a9c`.
Authority: operator requested a scaffold to carry out the static-review improvements and specifically proposed a Runs notice only for non-PowerUsers. No implementation/deployment approval or completed independent review is inferred from this document.

## Current contracts and proposed delta

Amend `docs/schemas/feature-access-governance-contract.md` in its UI/onboarding sections with the Runs notice audience, immediate-activation wording, complete post-success navigation, legacy explanation and secondary internal-statement presentation. Preserve current POST fields, authorization, acceptance version semantics and atomic role assignment. If the statement itself changes, require an explicit versioning decision; explanatory text around it is the preferred scope.

Amend the applicable presentation contract under `docs/ui-docs/contracts/` (create a dedicated PowerUser presentation contract there if none applies) for placement, focus, feedback, conditional report trigger and panel task groups. `docs/ui-docs/controller-contract.md` remains the shared runtime authority. Inspect `wepppy/weppcloud/feature_registry/specification.md` and YAML for conflicts; feature-menu role, maturity and prerequisite policies are unchanged. Add a cross-reference only if needed; do not silently broaden discoverability semantics.

Classification: intended presentation amendment plus correction of the report trigger to existing panel eligibility. Rationale: make capability acquisition understandable while preserving actual permissions. No account/run schema or migration. Security impact high for review purposes: role-sensitive entry points and successful grant presentation. M0 requires independent correctness and security contract reviews and a standalone committed checkpoint before code changes.

## Valid-state matrix

| State | Required outcome |
| --- | --- |
| Anonymous | Existing authentication behavior; no grant or privileged panel |
| Ordinary account, zero runs/no acceptance/no memberships | Runs notice visible; onboarding usable; no internal acceptance required |
| Ordinary account, populated runs | Same notice across table/map; filters/selection unchanged |
| PowerUser with current acknowledgment | No notice; active Profile status and destinations |
| Legacy PowerUser with no recorded current acceptance | No notice; existing access preserved; no action required |
| Admin/Root without literal PowerUser role | No notice; existing panel access preserved |
| Dev without PowerUser/Admin/Root | Notice shown; do not confuse existing Builder/token access with panel access |
| Membership absent or empty | Secondary internal explanation; voluntary acknowledgment remains reachable |
| Active membership awaiting acknowledgment | Internal action remains gated; acknowledgment prominently available |
| Expired/inactive membership | No implication of restored authority from PowerUser activation |
| Access store unavailable | Explicit unavailable state; never report activation or hide failure as success |

## Input and interaction matrix

| Input/interaction | Expected result |
| --- | --- |
| Both answers true, current statement, valid session/CSRF | One committed grant/acceptance; refreshed active state and valid destinations |
| Missing/false answer | No grant; clear form validation |
| Repeated submission or retry after lost response | Idempotent server behavior; active role accurately displayed |
| Stale statement version | Preserve existing rejection; reload current statement without claiming activation |
| Expired session/invalid CSRF | No grant; recoverable authentication/refresh instruction |
| Malformed success response/network failure | Error feedback, retry available, no fabricated active state |
| Other-user/role injection | Existing server-owned identity/role contract retained |
| Keyboard/small viewport | Notice, form and completion links usable; status announced and focus not lost |
| Direct unauthorized action request | Existing denial; discovery does not become execution authorization |

## Source evidence

`templates/user/runs2.html` is rendered by `routes/user.py:runs`; there is no active `user/runs.html` target. Under `wepppy/weppcloud/`, `templates/header/_run_header_fixed.htm:197` and `templates/controls/poweruser_panel.htm:39` share the three-role guard. `templates/reports/_base_report.htm:120` has an unconditional trigger and includes the guarded panel at line 203. `templates/user/profile.html:113` includes both access sections. `static/js/feature_access.js:85` exposes manual refresh and re-enables submit after approval. `routes/usersum/weppcloud/clearing-locks.md:25` tells unprivileged users to contact an administrator instead of explaining self-service.

## Review disposition

Pending. This prepared decision does not constitute the required contract checkpoint. Record amended canonical paths, reviewer findings, operator scope reconciliation and the ancestor SHA here before implementation.
