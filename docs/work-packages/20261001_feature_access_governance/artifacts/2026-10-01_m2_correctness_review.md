# Milestone two correctness and user-experience review

## Metadata

- Package: `docs/work-packages/20261001_feature_access_governance/`.
- Reviewer: `/root/contract_correctness`, independent review, 2026-10-01.
- Base revision: `62ce1af3f`; reviewed the uncommitted M2 working tree after fixes.
- Scope: `utils/feature_access_web.py`, account store changes, admin/Profile routes, Pure templates, `static/js/feature_access.js`, and `tests/weppcloud/routes/test_feature_access_routes.py`.
- Canonical authority: [FA-01](../../../schemas/feature-access-governance-contract.md), especially Account records and atomicity, UI and backend obligations, and the web transport checkpoint; active ExecPlan milestone two; existing CSRF/response contracts.
- Related independent review: [M2 security review](2026-10-01_m2_security_review.md).

The reviewer inspected source and regression tests, read the completed database/browser logs and semantic readback, visually inspected both rendered screenshots, and ran documentation/whitespace checks. The reviewer did not independently rerun the database suite or browser workflow. The full Python suite and local initialization evidence remain parent-owned closeout checks.

## User outcome

An active Root user can record a named person's feature membership with a reason and optional dates, inspect retained history, and remove membership. The person sees only their own membership status and can acknowledge the current internal statement. Membership and acknowledgment affect the shared evaluator; M2 does not wire restricted feature endpoints or enable PowerUser self-service.

Successful mutations report an explicit change/no-op result. Effective membership is distinguished from a stored pre-grant to an inactive account. Validation/authentication failures commit nothing. Database failures return a sanitized unavailable response with a correlated error ID; mutation status is read within the transaction so a failed read cannot follow a successful commit and falsely report failure.

## Valid-state matrix

| State | Valid? | Required behavior and reviewed evidence |
| --- | --- | --- |
| No memberships or history | Yes | Admin/Profile templates render empty states; unacknowledged Profile presents the statement form with its own macro import |
| Membership before acknowledgment | Yes | Profile explains that actions await acknowledgment; `test_grant_ack_remove_real_transport_and_admission` traverses the real HTTP/store/evaluator boundary |
| Current acknowledged membership | Yes | Evaluator allows the bounded operation subject to existing requirements; duplicate grant/acknowledgment is a no-op |
| Removed membership | Yes | New evaluator admission is denied, while audit history and acknowledgment remain |
| Expired membership or review date without expiry | Yes | Expiry is distinct from review; Profile shows expired status, and conflicting active dates produce an explicit conflict |
| Inactive account with a pre-grant | Yes | Stored decision remains auditable, effective `member` is false, and admin status says Inactive account; dedicated route/readback regression |
| Existing Dev/Root operational access | Yes | Internal acknowledgment is not presented as a new gate for preserved legacy access; group-only features still require membership |
| PATH-CE membership without contrast entitlement | Yes | Admin and Profile explain the separate contrast dependency; grants remain explicit and separately audited |
| Empty initialization groups | Yes | Explicit designated-account initializer grants only OpenET/Batch in one transaction, with retained events and no fabricated acknowledgment |
| Unchanged sole maintainer / conflicting initialization state | Yes | Repeat initialization is a no-op; conflicting grants/dates are preserved and initialization fails without a partial grant |
| Hostile body, forged CSRF, other-account acknowledgment, or token-only identity | No | Strict request fields and real session/CSRF boundaries reject the request without writes |
| Required persistence unavailable | Exceptional | Mutation failure is correlated and sanitized; Profile has an explicit unavailable subsection |

This is a bounded state review, not exhaustive coverage of every request/state combination. M3 credential adapters and protected feature routes are outside this milestone.

## User-reachable error policy

| Condition | Classification | Expected result |
| --- | --- | --- |
| Missing active browser identity / non-Root management | Expected | Mutation 401/403; no state change |
| Invalid JSON fields, IDs, reason, dates, or answer | Expected | 400 validation response; unchanged records |
| Statement version changed | Expected | 409 with reload/read guidance |
| Active membership has different dates | Expected | 409 explaining explicit remove/add |
| Same grant, absent removal, repeated acknowledgment | Expected valid state | 200 with `changed: false`; no duplicated history |
| Event insertion or required lookup fails | Exceptional | Transaction rollback and correlated 503; no database details disclosed |

The final GET route wraps its existing authentication/role decorators with the narrow dependency-error handler. SQL/registry failures become correlated unavailable responses while normal authentication/authorization behavior is preserved. This does not change application-wide error handling.

## Findings and disposition

| ID | Severity | Finding | Fix and independent readback |
| --- | --- | --- | --- |
| M2-C01 | Medium | Unacknowledged Profile used `ui.checkbox_field` without importing `ui`, breaking the initial form and ordinary Profile render | Fragment now imports the Pure macros explicitly; real Profile route regression covers the initial state. Closed |
| M2-C02 | Medium | Group administration omitted the required explanation of PATH-CE's separate contrast entitlement | Admin form and affected Profile membership now explain the dependency and separately recorded grants. Closed |
| M2-C03 | Medium | Add-to-inactive returned effective `member: true`, and the admin table labeled the record current although admission denied | Transactional status read includes active account/group and expiry; UI marks inactive accounts, with a dedicated real route/readback case. Closed |

The security review separately confirmed the session-provenance correction. The correctness reviewer read back its compatibility with current-user acknowledgment and the absence of new token scopes or credential issuance.

## Persistence and artifact evidence

| Stage | Reviewed evidence | Supported claim |
| --- | --- | --- |
| Request intent | Exact JSON fields, Root/session checks and server-owned acknowledgment version | Bounded transport implemented |
| Persisted state | Completed real PostgreSQL route/store suite reloads memberships, events and acceptances, then calls the evaluator | Locally validated; 75 focused tests passed |
| Partial failure | Passing real event constraint cases test mutation rollback and failure on the initializer's second event | No partial grant/event state in covered failures |
| User-facing result | Passing full-app Playwright round trip, retained semantic JSON and two visually reviewed screenshots | Browser grant/acknowledgment/removal and history validated for the covered desktop workflow |
| Generated intermediate, executable input, model output | N/A: M2 launches no jobs and produces no run artifacts | No scientific or feature execution claim |

The initializer locks the account and both groups, validates sole-maintainer preconditions, and records both grants in one transaction. Existing M1 concurrency/expiry behavior is retained. History uses a descending event-ID cursor and retains older events rather than truncating storage.

## Executed validation and visual readback

- `/tmp/m2-focused-current.log`: **75 passed**, comprising 36 real PostgreSQL route cases and 39 store/evaluator cases. The reviewer read the completed summary; execution was performed by the parent.
- `/tmp/m2-playwright.log`: **1 passed** against the full Flask application with native Flask-Security/Redis sessions, standard CSRF and an isolated PostgreSQL schema.
- [Semantic browser readback](m2-browser/roundtrip.json) records evaluator transitions **false → false → true → false** across absent membership, grant awaiting acknowledgment, acknowledgment and removal; retained add/remove audit history; keyboard submission; and focused validation-error feedback. The reviewer also read the Playwright assertions producing this record.
- The reviewer visually inspected [admin grant](m2-browser/admin-granted.png) and [Profile awaiting acknowledgment](m2-browser/profile-pending.png). The admin view has labeled Pure controls, separate dependency guidance, readable membership/status tables and retained reasons/times. Profile retains its existing account hierarchy and clearly explains pending acknowledgment. Final scope labels use user-facing language rather than raw access-mode identifiers.
- [Admin axe result](m2-browser/admin-granted-axe.json) and [Profile axe result](m2-browser/profile-pending-axe.json) each contain **zero violations** for the exercised WCAG-tagged axe scan. This is bounded desktop/default-theme evidence, not comprehensive accessibility certification.
- The parent reported frontend lint and **112 suites / 919 tests** passing. The full Python suite was still running at this evidence update; its final result belongs in the tracker.

The retained browser bundle under `artifacts/m2-browser/` matches the inspected files byte for byte. Local development migration/initialization is being recorded separately following verified backup/restore and account-count/head checks. Production is unchanged; the reviewer performed no account, schema or deployment operation.

## Review checks and observability

- Canonical intent, valid stored states, strict input handling, retries/no-ops and failure recovery are named separately.
- Tests use real PostgreSQL, Flask-Security sessions, CSRF middleware, route bodies and templates; mocks do not replace the changed writer or evaluator.
- Root can inspect account decision history; Profile exposes own status without another person's reasons or history.
- Existing User Management, Preferences Pure form macros and inline status patterns are the comparable UI surfaces.
- Account records remain in the canonical account database. This creates no project artifact, hidden run file, archive exclusion or filesystem permission change; project browse/download/archive/restore checks are N/A for M2.
- Actual-project model execution is N/A. The covered browser/evaluator acceptance passed; full-suite completion and deployment-specific backup/migration/initialization records remain distinct from this review. Production rollout is outside this verdict.

## Verdict

- Gate status: **pass for bounded M2 correctness and local browser acceptance**.
- Unresolved findings: High **0**; Medium **0**; Low **0**.
- Release recommendation: **ship with conditions** for the M2 implementation checkpoint after the parent records final full-suite and local initialization outcomes. Focused persistence/browser gates have passed. No production deployment or M3 enforcement approval is implied.
- Reviewer sign-off: `/root/contract_correctness`, 2026-10-01; all three findings independently confirmed closed in the working tree.


## Parent closeout record, 2026-10-02 UTC

After the independent review above, the parent recorded the completed full
Python suite: **10,198 passed, 126 skipped, 4,010 warnings in 2,535.69 seconds**.
Final route regression passed 73 cases; local migration/initialization passed
backup restore and audit readback. See [M2 acceptance](2026-10-01_m2_acceptance.md).
This is a parent execution record, not a claim that the reviewer reran those
checks or approved production rollout.
