# Checkpoint Security Review - Authentication Session Persistence Hardening

## Findings

### CHK-SEC-01 - High - Rolling remember-cookie replay lacks a bounded or accepted containment model

**Exploit path**: An attacker who copies a valid `remember_token` can replay it
after the victim's browser session expires. Flask-Security uses the user's
`fs_uniquifier` as the Flask-Login remember identity, while Flask-Login logout
only schedules deletion of the cookie presented by the browser making the
logout request. A copied token is therefore not revoked by ordinary logout.
Refreshing the cookie on every authenticated request lets the attacker extend
the token indefinitely by using it at least once per 90-day interval.

**Evidence**:

- `docs/schemas/weppcloud-session-contract.md`, "Flask Session Contract",
  requires refresh on every authenticated request.
- `docs/adrs/ADR-0028-rolling-remembered-login.md`, "Rationale" and
  "Alternatives Considered", calls the policy bounded and rejects an unbounded
  cookie even though the accepted policy has no absolute lifetime.
- `docs/work-packages/20260727_auth_session_persistence_hardening/artifacts/2026-07-27_contract_decision.md`,
  "Security Impact", lists logout as a stolen-cookie mitigation without
  distinguishing current-browser clearing from server-side revocation.
- The pinned environment uses Flask-Security-Too 5.6.1 and Flask-Login 0.6.3;
  their installed `UserMixin.get_id()` and `logout_user()` behavior confirms
  the replay and current-browser-only clearing model.

**Required action**: Before implementation, amend the ADR, contract decision,
package risks, and ExecPlan to describe 90 days as a rolling inactivity window,
not an absolute bound. Decide explicitly between an absolute maximum/server-side
revocation control and acceptance of copied-token replay until expiry. If the
latter is retained, record package-owner risk acceptance, document the
containment action that invalidates `fs_uniquifier`, and add regression evidence
for that containment path.

**Status**: Open.

### CHK-SEC-02 - High - Opt-out and logout are not verified at the cookie boundary

**Exploit path**: A form-unit assertion can report `remember=False` while an
integration error elsewhere in the Flask-Security login path still emits a
remember cookie. Likewise, configuration assertions do not prove that logout
expires both cookies using the deployed name, path, and domain. Either defect
would leave a shared-device user persistently authenticated despite opting out
or logging out.

**Evidence**:

- `docs/work-packages/20260727_auth_session_persistence_hardening/prompts/active/auth_session_persistence_execplan.md`,
  "Validation and Acceptance", requires only form construction for POST opt-out
  and configuration-value checks for persistence.
- `docs/work-packages/20260727_auth_session_persistence_hardening/artifacts/2026-07-27_contract_decision.md`,
  "Regression Evidence Plan", has no successful login-route assertion for
  omitted/unchecked `remember`, no cookie-attribute assertion, and no logout
  response assertion.
- `docs/schemas/weppcloud-session-contract.md`, "Flask Session Contract",
  normatively requires explicit logout to clear both session and remember
  cookies.

**Required action**: Add planned route-level regression cases that:

1. submit a successful password login with `remember` omitted or unchecked and
   prove no remember cookie is issued;
2. submit an opted-in login and prove the remember cookie has the intended
   90-day expiry plus `Secure`, `HttpOnly`, and `SameSite=Lax`;
3. make a later authenticated request and prove the expiry rolls; and
4. log out with both cookies present and prove both are expired with matching
   cookie scope.

Keep the form-unit and configuration tests as supporting evidence.

**Status**: Open.

### CHK-SEC-03 - High - The redaction plan does not cover every current secret-bearing sink

**Exploit path**: An attacker or normal OAuth/CAP flow can place a credential in
a differently named field, nested signal metadata, `next` URL, or referrer.
Field-name removal from the login form alone can then copy that credential into
the new persistent security log. Persistence under `/wc1` increases the impact
and lifetime of the confirmed disclosure.

**Evidence**:

- `wepppy/weppcloud/routes/_security/logging.py` currently logs
  `request.values["next"]`, `Referer`, signal extras converted with
  `object.__repr__`, and a debug form snapshot.
- The same module currently removes only `password` and `csrf_token` from form
  and request snapshots.
- `docs/work-packages/20260727_auth_session_persistence_hardening/artifacts/2026-07-27_contract_decision.md`,
  "Regression Evidence Plan", names only password, CSRF, `cap_token`, and
  `cap-token` redaction tests.
- `docs/schemas/weppcloud-session-contract.md`, "Authentication Logging
  Contract", prohibits password, CSRF, CAPTCHA, remember-cookie,
  session-cookie, OAuth-token, and bearer-token values in all authentication
  logs.

**Required action**: Replace the broad value logging plan with a safe-field
allowlist where practical, or specify recursive, case-insensitive key
normalization plus URL/query sanitization for every retained value sink. Expand
the regression plan to inject unique sentinels for every prohibited credential
class through request form data, signal extras, `next`, and referrer, including
hyphen/underscore and case variants, then assert the sentinels are absent from
all INFO and DEBUG output. Cookie values and authorization headers must never
be passed into diagnostic formatting.

**Status**: Open.

### CHK-SEC-04 - Medium - Persistent-log permissions and production-path validation are unspecified

**Exploit path**: A security log created with process-default directory and file
modes on the broadly mounted `/wc1` tree can expose identities, IP addresses,
user agents, and authentication timing to unrelated host/container principals.
A temporary-directory unit test also cannot detect an unwritable or incorrectly
mounted production path, and concurrent rotation failures can silently weaken
incident evidence.

**Evidence**:

- `docs/schemas/weppcloud-session-contract.md`, "Authentication Logging
  Contract", fixes the path but does not define ownership, modes, retention, or
  accessibility.
- `docs/work-packages/20260727_auth_session_persistence_hardening/prompts/active/auth_session_persistence_execplan.md`,
  "Validation and Acceptance", requires only a writable temporary-directory
  test.
- `wepppy/weppcloud/routes/_security/logging.py` creates parent directories and
  a `RotatingFileHandler` without explicit directory/file modes.
- `docker/docker-compose.dev.yml` mounts the host `WC1_DIR` at `/wc1` for
  multiple services.

**Required action**: Define the expected directory/file owner and least-privilege
modes, bounded rotation/retention, and confirmation that `/wc1/logs/weppcloud`
is not served by run-file routes. Add a production-compatible container check
running as the WEPPcloud uid that creates, writes, rotates, and reopens the
canonical path, while confirming setup failures remain visible in the main
service log. Record how multi-process rotation integrity is validated or
operationally guaranteed.

**Status**: Open.

### CHK-SEC-05 - Medium - Contract-first authority is not established for the UI-coupled change

**Exploit path**: Beginning implementation from a noncanonical checkpoint would
allow the checked-by-default authentication UI and persistence policy to become
the de facto security specification without the owner registration and
independent authority chain required for UI-coupled changes.

**Evidence**:

- `docs/standards/contract-first-change-standard.md`, "Covered Implementation
  Boundary", includes rendered templates, authentication, and defaults.
- Its "Canonical Authority" and "Required Pre-Implementation Checkpoint"
  sections require an operator-approved checkpoint in the registered child
  package, or the registered bounded-remediation process.
- The package and contract decision name a session contract and a general
  operator instruction to make the fixes, but do not cite a GOV-00A child or
  bounded-remediation registration, borrowed owner, or exact operator approval
  of the rolling 90-day normative delta.

**Required action**: Cite the existing registered child/remediation authority if
one exists. Otherwise complete the applicable GOV-00A registration and
cross-links before the ancestor commit. Record the operator's explicit approval
of the exact checked-by-default, rolling 90-day behavior rather than relying
only on the general instruction to fix the incident.

**Status**: Open.

## Verdict

- **Gate status**: `fail`
- **Unresolved findings**:
  - High: 3
  - Medium: 2
  - Low: 0
- **Release recommendation**: Hold implementation until CHK-SEC-01 through
  CHK-SEC-05 are resolved or, where allowed, explicitly accepted by the
  authorized package owner. The checkpoint must then receive independent
  rereview and be committed as the standalone ancestor required by the
  contract-first standard.

## Review Scope and Positive Controls

- **Reviewer**: Codex dedicated security reviewer
- **Date**: 2026-07-27
- **Starting implementation revision reviewed**: `4a748774f`
- **Security triage**: `high` is correct; a dedicated security review is
  mandatory.
- **Scope**: Package, tracker, active ExecPlan, contract decision, pending final
  security review, ADR-0028 and ADR index, session contract, project tracker,
  CSRF contract, contract-first standard, hardening lifecycle standard,
  parameterization ADR standard, work-package security gate, and read-only
  inspection of the referenced auth/config/logging/test surfaces.
- **Controls correctly preserved in the checkpoint**: rolling 12-hour Redis
  sessions, password-login opt-out intent, `Secure`/`HttpOnly`/`SameSite=Lax`
  intent, explicit logout intent, prohibition on credential-value logging,
  visible logger setup failure, no OAuth authorization-rule change, no new
  dependency, high-impact final review, and rollback without reverting token
  redaction.
- **Alternatives assessment**: Permanent Redis sessions, forced remember,
  cookie-value logging, and unwritable paths are reasonably rejected. The
  checkpoint does not yet assess an absolute remember lifetime, server-side
  revocation/token-version strategy, or current-browser-only logout as distinct
  alternatives.

## Required Closure Evidence

- Updated checkpoint documents resolving the five findings.
- Disposition entries in `tracker.md`, with owner acknowledgment for any
  accepted security risk.
- The second independent checkpoint review and rereview of material
  dispositions.
- A standalone checkpoint ancestor commit recorded in the tracker before any
  implementation-file edit.

## Residual Security Risk

Even after the listed regression plan is completed, a remembered-login bearer
credential remains a high-value target. If copied-token replay is accepted
without an absolute maximum or server-side revocation, that residual risk must
remain visible through package closeout and the 2026-10-25 observation window;
it must not be described as eliminated by ordinary logout.

## Rereview - 2026-07-27 19:29 UTC

### Scope

This rereview assessed the revised REM-03 checkpoint, the GOV-00A-M1C bounded
remediation decision, the ratification tracker, the child-package register,
ADR-0028, the session contract, the contract decision, the active ExecPlan, the
package tracker dispositions, and the independent correctness review. The
referenced implementation and test files remain unmodified at this checkpoint.

### Finding Dispositions

| Finding | Rereview disposition | Evidence and remaining action |
| --- | --- | --- |
| CHK-SEC-01 | **Open - High** | Disabling refresh and capping the browser cookie at 90 days removes the per-request extension defect, and `fs_uniquifier` rotation is now documented as containment. It does not create a server-enforced replay expiry. Flask-Login 0.6.3 signs only `fs_uniquifier`; its remember value contains no issuance time or expiry, and the loader performs no age check. A copied value can therefore be replayed after the browser's `Expires` date until `fs_uniquifier` or the signing key changes. ADR-0028's statement that a user can remain remembered for "no more than 90 days" and the tracker mitigation "bounded 90 days" are only true for a cooperative browser, not the stolen-cookie threat under review. Correct that distinction and either add a server-validated absolute bound or record explicit package-owner acceptance of unbounded copied-token replay with an actionable `fs_uniquifier` containment runbook. |
| CHK-SEC-02 | **Resolved at checkpoint; verify after implementation** | The session contract now requires matching cookie name/path/domain on logout. The contract decision and ExecPlan require successful opt-out, opt-in attributes and expiry, non-refresh on a later request, and logout clearing both cookies at the HTTP response boundary. These tests remain mandatory final-gate evidence. |
| CHK-SEC-03 | **Resolved at checkpoint; verify after implementation** | The revised plan replaces broad diagnostics with safe allowlists and recursive redaction. Final-record sentinel tests now cover every prohibited credential class, case/separator variants, nested signal extras, `next`, referrer, INFO, and DEBUG sinks. The final security review must confirm raw cookie and authorization values never reach diagnostic formatting. |
| CHK-SEC-04 | **Resolved at checkpoint; verify after implementation** | The session contract now mandates append-only worker writes, host-coordinated rotation/retention, `0700` directory and `0600` file modes, visible failures, and route non-exposure. The implementation plan adds uid 1002 canonical-path, reopen, multi-worker, handler-deduplication, and failure tests. Final review must verify that a concrete bounded host rotation/retention configuration ships with those controls. |
| CHK-SEC-05 | **Open - Medium** | GOV-00A-M1C now records an exact source boundary and exclusions, but its borrowed-owner mapping is not consistent with the binding child register. REM-03 claims SHR-03A, SHR-03B, and SURF-04; the same register defines those as status controls, bootstrap observability, and the fork console. It assigns login and account-exit flows to SURF-13 and session transport to SHR-02, with SURF-14 owning user-profile/session behavior. Reconcile every borrowed owner for the login, cookie, logout, and auth-log surfaces. Also record explicit operator approval of the revised absolute/no-refresh behavior: the current authority paragraph cites only the earlier general instruction to make fixes, while the exact policy changed after initial review. |

### Rereview Verdict

- **Gate status**: `fail`
- **Unresolved findings**:
  - High: 1
  - Medium: 1
  - Low: 0
- **Disposition summary**: CHK-SEC-02, CHK-SEC-03, and CHK-SEC-04 are closed
  for the pre-implementation checkpoint, subject to their required
  post-implementation evidence. CHK-SEC-01 and CHK-SEC-05 remain open.
- **Release recommendation**: Hold implementation. Correct or explicitly
  accept CHK-SEC-01 under package-owner authority, correct the GOV-00A-M1C
  borrowed-owner and exact-approval record for CHK-SEC-05, obtain passing
  independent rereviews, and commit the complete checkpoint as a standalone
  ancestor before editing implementation files.

### Rereview Residual Risk

The revised absolute browser expiry is materially safer than rolling refresh,
but it is not a cryptographic or server-side expiry for a copied Flask-Login
token. Ordinary logout clears the requesting browser only. The package must
retain that distinction in its threat model, monitoring, containment guidance,
and final security review even if the operator accepts the residual risk.

## Second Rereview - 2026-07-27 19:51 UTC

### Scope

This second rereview assessed the operator's 2026-07-27 19:45 UTC UX decision,
the revised session contract and ADR-0028, the REM-03 package, tracker, contract
decision and ExecPlan, the corrected GOV-00A-M1C decision, ratification tracker
and child-package register, and the expanded conformance-test requirements.
The referenced implementation and test files remain unmodified.

### Finding Dispositions

| Finding | Second-rereview disposition | Evidence and final-gate requirement |
| --- | --- | --- |
| CHK-SEC-01 | **Accepted risk; closed at checkpoint** | The session contract now accurately states that 90 days is a browser inactivity policy, not a server-side maximum for a copied raw token. The operator explicitly accepts that residual risk in the contract decision and GOV-00A-M1C authority, with the rationale that remembered login materially reduces demonstrated user friction and there is no current evidence requiring per-device server state. Ordinary logout's current-browser boundary and `fs_uniquifier` rotation containment, including its active-session blast radius, are explicit. Final operator documentation must provide the concrete rotation procedure, and final security review must confirm the accepted risk remains visible rather than being described as eliminated. |
| CHK-SEC-02 | **Resolved at checkpoint; verify after implementation** | The contract now requires opt-in-aware refresh only after a valid remember token is present, prohibits ordinary sessions from creating one, requires an opted-out login to clear any preexisting remember cookie, and requires scoped logout clearing. The ExecPlan requires HTTP-boundary opt-out, opt-in refresh, ordinary-session, attribute, and logout tests. Final security evidence must also cover invalid and user-mismatched remember values so a presence-only check cannot convert an untrusted cookie into a valid remembered login. |
| CHK-SEC-03 | **Resolved at checkpoint; verify after implementation** | Safe diagnostic allowlists, recursive redaction, prohibited credential classes, nested and URL/referrer sinks, and final INFO/DEBUG sentinel assertions remain normative and planned. No raw cookie or authorization value may reach diagnostic formatting. |
| CHK-SEC-04 | **Resolved at checkpoint; verify after implementation** | Append-only worker writes, host-coordinated rotation/retention, `0700`/`0600` modes, visible failures, uid 1002 canonical-path validation, handler deduplication, multi-worker behavior, reopen, and route non-exposure remain required. Final review must verify a concrete bounded host rotation/retention configuration. |
| CHK-SEC-05 | **Resolved at checkpoint** | GOV-00A-M1C, the ratification tracker, child-package register, package, contract decision, and ExecPlan now consistently borrow SURF-13, SHR-02, and SHR-04A for the exact login form, session transport, field-rendering, cookie-boundary, and auth-diagnostic remediation. They record the exact rolling 90-day opt-in-aware behavior, exclusions, high security classification, operator approval, dual review, and standalone-ancestor condition without advancing the borrowed owners. |

### Second-Rereview Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Disposition summary**: CHK-SEC-01 is closed by explicit authorized risk
  acceptance and containment. CHK-SEC-02 through CHK-SEC-04 are closed for the
  pre-implementation checkpoint subject to their mandatory implementation and
  final-review evidence. CHK-SEC-05 is closed by the corrected authority chain.
- **Release recommendation**: The security checkpoint may enter the standalone
  ancestor commit after the second independent rereview and all dispositions
  are recorded. Implementation remains prohibited until that ancestor exists.

### Nonblocking Precision Note

The GOV-00A-M1C decision's boundary sentence still says "absolute
remember-cookie duration/default" while its exact accepted behavior, the
session contract, ADR, tracker, and register consistently specify rolling
opt-in-aware refresh. Replace that stale adjective with
"remember-cookie duration/refresh" before the ancestor commit to avoid future
authority ambiguity. This wording defect does not reopen CHK-SEC-05 because the
same authority artifact's normative behavior paragraph is exact and consistent
with every linked checkpoint contract.

### Accepted Residual Security Risk

The remember token remains a signed bearer credential without a server-validated
issuance timestamp. A copied raw value can remain replayable until the affected
user's `fs_uniquifier` or the application signing key changes. That risk is now
explicitly accepted by the authorized operator for the documented UX objective,
with Secure, HttpOnly, SameSite=Lax, TLS, redaction, opt-out, logout, monitoring,
and `fs_uniquifier` rotation retained as exposure and containment controls.

## Final Checkpoint Confirmation - 2026-07-27 19:56 UTC

The prior security pass still applies to the current checkpoint.

- GOV-00A-M1C now consistently uses rolling inactivity wording, the corrected
  SURF-13/SHR-02/SHR-04A authority, actual review-sequence metadata, explicit
  exclusions, and the standalone-ancestor condition.
- The ExecPlan contains executable gates for every contract-listed Python and
  JavaScript suite and records path-specific `N/A` rationales while still
  requiring those suites as regression runs.
- Cookie-boundary acceptance now requires correctly scoped deletion when an
  opted-out login arrives with a preexisting remember cookie, and proves an
  invalid remember value beside an ordinary authenticated session is neither
  refreshed nor exchanged for a valid credential.
- CHK-SEC-01 remains closed by explicit authorized residual-risk acceptance and
  containment; CHK-SEC-02 through CHK-SEC-04 remain closed at checkpoint subject
  to final implementation evidence; CHK-SEC-05 remains closed by the corrected
  authority chain.

**Final checkpoint verdict**: `pass`.

There are zero unresolved high, medium, or low security findings. Implementation
remains prohibited until the complete reviewed checkpoint is committed as the
required standalone ancestor.
