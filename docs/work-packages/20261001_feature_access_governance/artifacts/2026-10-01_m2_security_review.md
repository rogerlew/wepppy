# Milestone two security review

## Metadata

- Package: `docs/work-packages/20261001_feature_access_governance/`.
- Reviewer: `/root/contract_security`, 2026-10-01; independent code review.
- Base: `62ce1af3f`; reviewed the uncommitted M2 changes after findings fixes.
- Scope: `utils/feature_access_web.py`, store readers and maintainer initializer,
  admin/Profile routes, Pure templates, `static/js/feature_access.js`, and
  `tests/weppcloud/routes/test_feature_access_routes.py`.
- Authority: [FA-01](../../../schemas/feature-access-governance-contract.md),
  [CSRF contract](../../../schemas/weppcloud-csrf-contract.md), and
  [package tracker](../tracker.md). The separate
  [correctness review](2026-10-01_m2_correctness_review.md) owns valid-state/UX
  findings; browser acceptance evidence is described below.

## Security Triage Decision

Security impact: **high**; dedicated review required. M2 exposes account
membership administration and current-user acknowledgment through browser routes.
It does not wire the restricted feature endpoints, mint credentials, or assign
PowerUser. Deployment and shared-account initialization are separate operator
actions, not authorized by this review.

Threat assumptions: Flask-Security resolves the current identity; the session
store and account database are trusted infrastructure. A token and an unrelated
or stale session marker do not establish browser authentication. Only active
Root accounts administer membership. The CLI is an explicit deployment operation
whose email lookup must resolve the designated active Root in that deployment.

Valid states include empty groups/history, existing and expired memberships,
old/no/current acknowledgment, idempotent repeated decisions, retained deleted
account/group history, ordinary Profile access, and unavailable new persistence.
Hostile cases include non-Root callers, token substitution, forged CSRF, extra
identity/role fields, invalid identifiers/dates, and injected audit-write failure.

## Findings

| ID | Severity | Surface | Description and evidence | Required action and disposition | Status |
| --- | --- | --- | --- | --- | --- |
| M2-S01 | Medium | Browser authentication | The original `access_boundary` accepted a truthy `_user_id` with `current_user`; Flask-Login can fall through from a stale/deactivated identity to Flask-Security token authentication while preserving that marker. A valid Root token plus such a session and CSRF could therefore substitute for the required browser identity. | Require resolved `fs_authn_via == session` and binding to `current_user.get_id()`. The final guard does both before admission; six regression cases cover no/stale/inactive sessions with real Flask-Security tokens at both mutation routes. | Resolved |
| M2-S02 | Low | Authentication error boundary | Identity/role resolution originally preceded the SQL error handler, allowing account lookup failures to escape the specified correlated, sanitized unavailable response. | The mutation guard resolves identity/role inside `access_errors`. The admin GET also places `access_errors` outside its existing login/role decorators, preserving their normal behavior while catching authentication database failures. | Resolved |

No risk acceptance was requested or used. The reviewer independently read back
both fixes in `feature_access_web.py`; it uses Flask-Security's documented
request-local authentication provenance rather than treating token class or
session presence as identity proof.

## Verdict

- Gate status: **pass for M2 code security review**.
- Unresolved security findings: High **0**, Medium **0**, Low **0**.
- Release recommendation: focused database and browser acceptance have passed;
  record the pending broad-suite result before implementation closeout. This is no deployment,
  protected-feature enforcement, PowerUser onboarding, or Culvert compatibility
  approval.

## Surface Checks

### 0) Valid-State Non-Interference and User Experience

The new Profile subsection reads only the current account. A persistence failure
shows an explicit subsection error without deliberately disabling ordinary
Profile behavior. Empty membership/history states render normally. Duplicate
decisions retain explicit no-op results. Security approval does not replace
the independent correctness/UX review or real browser acceptance.

### 1) Auth, Session, and Authorization

Both mutations require an active session-authenticated user and exact session
identity binding. Membership mutation additionally checks Root at the route and
again against the account database within the transaction. Acknowledgment always
uses `current_user.id` and the server-owned statement version. Existing global
Flask-WTF CSRF protection remains enabled and the new endpoints are not exempt.
Templates supply the established CSRF meta token; fetch uses same-origin cookies.
No token issuance, conversion, verification, scopes, TTLs, or accepted service
classes change. Root administration does not itself confer group-only execution.

### 2) Secrets and Credential Handling

No secret dependency, credential creation, rotation, or credential publication
is added. The CLI uses the policy-designated email only for explicit deployment
initialization; request authorization uses the resolved account identity.
Reviewed tests keep synthetic authentication tokens in memory.

### 3) Input Validation and Output Safety

Mutation bodies require JSON objects and exact allowed keys. Canonical integer
IDs reject booleans and strings; acknowledgment is strictly `true`; version,
operation, registered group, nonblank reason, and UTC date checks are explicit.
Remove rejects add-only date fields. Clients cannot choose the actor, accepted
statement text, another acknowledgment subject, or a role. SQL uses bound values.
Templates escape account names, group metadata, audit reasons and scope snapshots;
JavaScript renders response text with `textContent`, not HTML. Profile exposes
own membership/acknowledgment only; audit reasons and the account list are Root-only.

### 4) File System and Run-Tree Boundaries

Not changed. M2 writes account records, not run artifacts, exports, or paths.
It adds no archive/restore exclusions or filesystem permissions.

### 5) Queue, Worker, and Subprocess Surfaces

Not changed. No jobs, cancellation/retry authorization, worker inputs, enqueue
edges, or subprocess execution are added; an RQ graph check is not required.

### 6) Agentic Tooling and MCP Surfaces

Not changed. M2 adds no MCP/agent permission, token, delegation, or network path.
The independent reviewer made no runtime mutation or account initialization.

### 7) Network and External Integrations

No new outbound call or external dependency. The new browser endpoints persist
bounded account decisions; they cannot launch restricted computations. Expensive
feature admission and deployed Culvert integration remain M3/later work.

### 8) CI/CD and Supply Chain

No dependency, workflow permission, runner scope, or deployment topology change.
Tests use the existing PostgreSQL configuration with fresh isolated schemas.

### 9) Data Integrity, Locking, and Concurrency

The public store mutation owns one transaction. The extracted internal mutation
helper retains active Root checks, account/group locking, expiry validation,
membership/event atomicity and idempotence. Effective membership status is read
inside the same transaction, including active account/group and expiration;
stored pre-grants to inactive users do not report effective access. Initialization locks the designated
account and both groups, checks sole-maintainer preconditions, then grants both
groups and inserts their events inside that same transaction. It neither erases
other grants nor silently renews dated grants or fabricates acknowledgment.
History readers page retained events instead of dropping old decisions.

### 10) Logging, Monitoring, and Incident Readiness

Mutation persistence/authentication lookup failures produce sanitized 503 errors
with an `error_id` and tagged server exception evidence. The post-commit response
does not issue another fallible database read that could falsely report an error
for a saved decision. Profile subsection failures have a visible reference ID.
Operational rollback retains schema and history under the existing account
records plan; this review does not approve a deployment or rollback execution.

## Validation Evidence

Reviewed real PostgreSQL/Flask-Security/CSRF test source covering grant,
acknowledgment, removal, no-op behavior, permission/CSRF/type denial, current-user
privacy, audit failure rollback, date conflicts, and initializer preconditions.
Post-fix token-substitution coverage tests both mutations with a real signed
Flask-Security token and no, stale, or inactive session bindings.

The reviewer independently inspected the final source and these parent-executed
logs, without rerunning the application suite or browser workflow:

- `/tmp/m2-focused-current.log`: **75 passed**, comprising 36 real PostgreSQL
  route cases and 39 store/evaluator cases. Includes all six token-substitution
  denials and failure on the initializer's second audit insert, which leaves
  both groups and the event table unchanged.
- `/tmp/m2-playwright.log`: **1 passed**. The reviewed opt-in browser harness
  uses the full application, isolated PostgreSQL records, and native
  Flask-Security/Redis sessions. Real form requests exercise standard CSRF,
  grant, acknowledgment, evaluator allow, removal, subsequent denial, and
  visible retained audit history. It checks keyboard submission and error
  focus. Axe assertions cover WCAG 2 A/AA and 2.1 AA with zero violations on
  the two scanned pages. This is bounded automated accessibility evidence,
  not a comprehensive accessibility conformance claim.
- Parent reports frontend lint and **112 suites / 919 tests** passed, plus
  store/web stubtest. The broader Python suite remains in progress at this
  review update; its final result belongs in the tracker.

The browser harness keeps disposable cookies in an ignored mode-0600 file,
does not print them, and removes its credentials, namespaced sessions and test
schema on normal shutdown. Evidence contains outcomes/screenshots rather than
credentials. The parent-designated retention path is `artifacts/m2-browser/`.

## Residual Risk

No Medium/High finding is waived. Restricted endpoint wiring is intentionally
not yet implemented; recording memberships cannot demonstrate enforcement by
existing feature routes. M3 must test trusted principal/resource adapters, group
removal with stale credentials, embargoed data paths, and legitimate Culvert
service behavior. Completed M2 browser/evaluator acceptance does not substitute
for production-equivalent restricted-feature enforcement or rollout evidence.

## Sign-off

- Security reviewer: `/root/contract_security`, 2026-10-01, bounded code verdict.
- Package owner: parent orchestrator to record M2 checkpoint disposition after
  the broad validation result. Local migration/initialization and backup/restore
  evidence remain operator-owned; no production rollout is covered here.
  No risk-acceptance acknowledgment is required.

## Artifact Observability Gate

Account events and acceptances use the canonical account database, with current
user status on Profile and retained decision history in the Root administration
page. This is not a new project artifact-producing workflow; run browser,
download, ZIP and restore contents are unchanged. Database writer/failure tests
provide retained audit/readback evidence. The passed parent-owned browser case
demonstrates current-user status and Root access to the retained decision
history through the actual application pages.


## Parent closeout record, 2026-10-02 UTC

After the independent review above, the parent recorded the completed full
Python suite: **10,198 passed, 126 skipped, 4,010 warnings in 2,535.69 seconds**.
Final route regression passed 73 cases; local migration/initialization passed
backup restore and audit readback. See [M2 acceptance](2026-10-01_m2_acceptance.md).
This is a parent execution record, not a claim that the reviewer reran those
checks or approved production rollout.
