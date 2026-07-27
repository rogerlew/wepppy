# Checkpoint Correctness Review - Authentication Session Persistence

## Metadata

- **Reviewer**: Codex `reviewer` agent, independent checkpoint review
- **Date**: 2026-07-27
- **Starting implementation revision**: `4a748774f`
- **Scope**: Pre-implementation checkpoint documents, pinned framework source,
  current WEPPcloud authentication/session/logging implementation, focused tests,
  and production Compose wiring
- **Implementation files modified by this review**: none

## Verdict

**Fail.** The checkpoint must not be committed as the implementation ancestor
until COR-01 is redesigned and all high/medium findings below are dispositioned.

| Severity | Open |
| --- | ---: |
| High | 1 |
| Medium | 4 |
| Low | 0 |

## Findings

### COR-01 - High - Global remember refresh defeats explicit opt-out

The ExecPlan directs the implementation to set
`REMEMBER_COOKIE_REFRESH_EACH_REQUEST=True` while requiring a password-login POST
without `remember` to remain opted out. Those behaviors are incompatible in the
pinned Flask-Login 0.6.3 implementation.

`LoginManager._update_remember_cookie()` schedules `_remember="set"` whenever
the refresh configuration is true and the marker is absent. It then emits a
remember cookie whenever `_user_id` is in the session. On a successful
`login_user(..., remember=False)` response, `_user_id` is present and no
`_remember` marker was set by `login_user`, so the refresh hook creates the
remember cookie anyway.

This was reproduced against the pinned framework with a minimal Flask app:
both `login_user(..., remember=False)` and `login_user(..., remember=True)`
returned a `remember_token` `Set-Cookie` header when refresh-each-request was
true. A form-only assertion that `remember.data is False` therefore cannot prove
the user-visible opt-out contract.

Evidence:

- `prompts/active/auth_session_persistence_execplan.md`, lines 85-87 and 119-122
- `docs/schemas/weppcloud-session-contract.md`, lines 39-43
- `docs/adrs/ADR-0028-rolling-remembered-login.md`, lines 23-27 and 43-46
- `docker/requirements-uv.txt`, Flask-Login 0.6.3 pin
- `.venv/lib/python3.12/site-packages/flask_login/login_manager.py`, lines
  448-462

Required actions:

1. Replace the global refresh design with opt-in-aware rolling refresh. The
   implementation must distinguish an opted-in remembered identity from an
   ordinary authenticated session and must not infer opt-in merely from
   `_user_id`.
2. Update the ExecPlan, contract decision, ADR implementation notes, risks, and
   regression plan before implementation begins.
3. Add response-level tests proving:
   - unchecked/omitted `remember` from a cookie-free client emits no remember
     cookie;
   - checked `remember` emits a cookie expiring approximately 90 days later;
   - a later authenticated request for an opted-in client refreshes expiration;
   - logout emits the remember-cookie deletion; and
   - opt-out does not preserve or recreate a preexisting remembered identity
     when the supported UI flow allows that state.

### COR-02 - Medium - Secret-redaction evidence does not cover the contract

The normative contract prohibits password, CSRF, CAPTCHA, remember-cookie,
session-cookie, OAuth-token, and bearer-token values. The contract decision's
regression list names only password, CSRF, `cap_token`, and `cap-token`.
Current logging has multiple input paths: request form data, login-form data,
signal extras, `next`, and referrer values. Testing a sanitizer return value or
only the four named fields would not prove that secret sentinels are absent from
the emitted log records.

Evidence:

- `artifacts/2026-07-27_contract_decision.md`, lines 50-59
- `docs/schemas/weppcloud-session-contract.md`, lines 52-61
- `wepppy/weppcloud/routes/_security/logging.py`, lines 143-221 and 235-300

Required actions:

1. Expand the checkpoint regression plan to cover every prohibited secret class
   and every changed logging entry point, including signal extras and logged URL
   fields where token-bearing values can occur.
2. Use distinct sentinel values and assert against captured final log messages,
   not only sanitized intermediate mappings.
3. Cover case and separator variants for token/cookie field names, nested
   mappings if accepted by the sanitizer, and confirm that safe
   `remember_action` output is restricted to `set`, `clear`, or absent.
4. Add a failure-path test proving logger initialization failure remains visible
   in the main service log, as required by the contract.

### COR-03 - Medium - Rollback cannot restore the stated 30-day policy

The ExecPlan says one implementation revert restores the 30-day absolute policy,
while also saying not to revert redaction. Those are not the same revert.
Furthermore, Flask-Login remember tokens contain signed identity data but no
server-enforced issue time. Restoring a 30-day configuration affects future
`Set-Cookie` headers; remember cookies already issued with a 90-day browser
expiration remain usable until they expire or are invalidated.

A code-only rollback would also leave the accepted ADR and normative session
contract requiring rolling 90-day behavior, creating deliberate contract drift.

Evidence:

- `prompts/active/auth_session_persistence_execplan.md`, lines 125-130
- `docs/adrs/ADR-0028-rolling-remembered-login.md`, lines 82-87
- `artifacts/2026-07-27_contract_decision.md`, lines 29-33
- Flask-Login 0.6.3 `_set_cookie()` and cookie encoding behavior

Required actions:

1. Document separate, targeted rollback units for remembered-login behavior and
   the security redaction/logging repair.
2. State that restoring the old duration does not shorten already-issued
   cookies, and document the operator-approved containment/invalidation option
   if immediate rollback of the exposure window is required.
3. Include the required ADR status and session-contract update in a policy
   rollback procedure.

### COR-04 - Medium - Absolute contract wording conflicts with supported overrides

The new contract says remember cookies MUST use 90 days and MUST refresh on every
authenticated request. Current public configuration supports
`REMEMBER_COOKIE_DAYS` and `REMEMBER_COOKIE_REFRESH_EACH_REQUEST` overrides, and
the existing test suite expressly validates those overrides. The package and
README-facing intent describe new defaults, not removal of operator overrides.
The checkpoint does not decide whether these settings remain supported, become
constrained, or are removed.

The refresh override is additionally unsafe if it retains Flask-Login's global
meaning described in COR-01.

Evidence:

- `docs/schemas/weppcloud-session-contract.md`, lines 41-43
- `wepppy/weppcloud/configuration.py`, lines 341-356
- `tests/weppcloud/test_configuration.py`, lines 207-224
- `wepppy/weppcloud/README.md`, current remember-cookie configuration table

Required action: make one explicit compatibility decision before implementation.
Either define 90 days and opt-in-aware rolling refresh as defaults with bounded
operator overrides, or remove/constrain the overrides and document the breaking
change. Align the contract, ADR, configuration documentation, and tests.

### COR-05 - Medium - Persistent path is valid, but the handler design is not
production-safe

`/wc1` is a durable host bind mount in both the base production stack and the
wepp1 override, so the selected path is correct. The proposed temporary-directory
write test alone does not validate the production logging design, however.
WEPPcloud runs four Gunicorn workers in the base production stack and ten on
wepp1, while the current logger gives every worker a `RotatingFileHandler` for
the same file. Standard rotating file handlers do not coordinate rollover
across processes; enabling the formerly unwritable file can therefore cause
rotation races, lost records, or visible handler errors during an incident.

Evidence:

- `docker/docker-compose.prod.yml`, lines 121-143
- `docker/docker-compose.prod.wepp1.yml`, lines 58-80
- `wepppy/weppcloud/routes/_security/logging.py`, lines 15-18 and 50-81

Required actions:

1. Select and document a multi-process-safe persistence/rotation strategy, such
   as non-rotating app writes with host-side rotation, a centralized stream
   collector, or another explicitly coordinated approach.
2. Test the exact default path resolution, restricted file permissions, handler
   deduplication, and visible initialization/write failure behavior.
3. Add an operational validation that the rendered production Compose mount and
   runtime uid can create and append the canonical path.

## Confirmed Assumptions

- **Flask-Security/WTForms default timing**: confirmed. Flask-Security 5.6.1
  assigns `remember.default` after WTForms has already processed field data, so
  `SECURITY_DEFAULT_REMEMBER_ME=True` alone does not check the rendered field.
  Setting field data only when constructor `formdata` is actually absent is a
  valid direction, provided submitted `MultiDict` data remains authoritative.
- **Redis session lifetime**: confirmed for the pinned Flask-Session 0.4.0 path.
  Each save of a non-empty Redis session calls `SETEX` with
  `PERMANENT_SESSION_LIFETIME`; current configuration remains 12 hours and
  `SESSION_PERMANENT=False`. The browser session cookie remains nonpermanent.
- **Remember-cookie compatibility**: confirmed in the forward direction.
  Changing duration and refresh behavior does not change Flask-Login signing, so
  existing valid remember cookies are not immediately invalidated.
- **Persistent path**: confirmed. `/wc1` is bind-mounted from durable host
  storage in production and the collected wepp1 evidence says uid 1002 can write
  it. COR-05 concerns concurrent file handling and validation, not the selected
  path.
- **Response-hook ordering**: confirmed. The current security logging hook runs
  before Flask-Login's app-level remember-cookie hook and before Flask saves the
  server-side session. Logging a strictly allowlisted `_remember` action can be
  accurate without logging cookie values, but actual response cookie behavior
  still requires the tests in COR-01.

## Residual Coverage Requirements

After the checkpoint is corrected, retain the planned configuration assertions
for 90 days and the unchanged 12-hour/nonpermanent Redis settings. The final
gate should also exercise actual HTTP cookie headers and at least one Redis
session save/refresh path; configuration-only tests cannot prove the separation
between ordinary sessions and remembered identity.

## Rereview - 2026-07-27

### Rereview Scope

This rereview assessed the revised REM-03 package, tracker, ExecPlan, contract
decision, ADR-0028, session contract, `PROJECT_TRACKER.md`, ADR index, the
GOV-00A-M1C bounded-remediation decision, the child-package register, and the
GOV-00A tracker. Implementation files remained read-only.

### Disposition of Original Findings

| Finding | Rereview disposition | Evidence |
| --- | --- | --- |
| COR-01 | Resolved as originally framed. | The policy now keeps `REMEMBER_COOKIE_REFRESH_EACH_REQUEST` disabled, removes its unsafe environment override, and requires route-level opt-out/opt-in/no-refresh/logout assertions. |
| COR-02 | Resolved at checkpoint. | The revised plan uses safe allowlists plus recursive redaction and requires unique sentinels across form, cookie, OAuth/bearer, nested signal-extra, `next`, and referrer sinks, asserted against final INFO/DEBUG records. |
| COR-03 | Resolved as originally framed. | Remember-policy rollback is separated from logging/redaction, requires the ADR and contract to move together, acknowledges that configuration rollback does not shorten issued cookies, and names `fs_uniquifier` rotation for containment. |
| COR-04 | Resolved at checkpoint. | The contract now defines a 90-day default, permits only a shorter 1-90-day operator duration, prohibits per-request refresh, and the plan removes the unsafe refresh override. |
| COR-05 | Resolved at checkpoint, subject to final implementation evidence. | The contract prohibits worker-side rotation, assigns rotation to the host, requires `0700`/`0600`, and the plan requires handler deduplication, multi-worker append validation, visible failures, canonical-path uid 1002 validation, and route non-exposure. |

The original findings are closed, but the revised checkpoint introduces or
reveals the following unresolved findings.

### RER-COR-06 - High - The signed remember token has no absolute expiry

The revised ADR and authority decision describe the remembered identity as
absolutely bounded to 90 days and state that existing cookies remain valid only
until browser expiry. That is true for a conforming browser's cookie jar, but it
is not a server-side validity bound.

Flask-Login 0.6.3 `encode_cookie()` signs only
`<fs_uniquifier>|<HMAC>`. It records no issuance or expiry timestamp.
`decode_cookie()` verifies only the HMAC, and
`_load_user_from_remember_cookie()` performs no age check. A copied raw token can
therefore be presented manually after the browser expiration and remains valid
until the user's `fs_uniquifier` or the application secret changes. Disabling
refresh fixes opt-out and prevents the application from extending the browser
expiration, but it does not create the claimed absolute replay bound.

Evidence:

- `docs/adrs/ADR-0028-rolling-remembered-login.md`, lines 50-53 and 68-74
- `docs/work-packages/20260716_pure_ui_contract_ratification/artifacts/2026-07-27_auth_session_bounded_remediation_decision.md`,
  lines 18-22 and 38-44
- `docs/work-packages/20260727_auth_session_persistence_hardening/artifacts/2026-07-27_contract_decision.md`,
  lines 37-42 and 73-79
- `.venv/lib/python3.12/site-packages/flask_login/utils.py`,
  `encode_cookie()` and `decode_cookie()`
- `.venv/lib/python3.12/site-packages/flask_login/login_manager.py`,
  `_load_user_from_remember_cookie()`

Required action: make an explicit, operator-approved choice before implementation:

1. add a server-enforced issuance/expiry mechanism inside a separately reviewed
   source and compatibility boundary; or
2. retain the browser-only 90-day policy, remove claims of an absolute
   credential/replay bound, and explicitly accept that copied raw tokens remain
   replayable until `fs_uniquifier` or secret rotation.

The second choice must record the owner, rationale, containment blast radius
(`fs_uniquifier` rotation also invalidates that user's active login sessions),
and date as an accepted residual high risk. Tests that inspect only the
`Expires` response attribute cannot prove server-side expiry.

### RER-COR-07 - High - GOV-00A-M1C borrows the wrong registered owners

The M1C decision and REM-03 register row borrow SHR-03A, SHR-03B, and SURF-04.
The same authoritative register defines those IDs as StatusStream/control,
bootstrap observability, and the Fork console. They do not own the password
login form or its session behavior.

The register assigns the inherited login/security form family and
authentication/session/account mutation to SURF-13. SHR-02 owns shared session
transport, and SHR-04A owns shared field rendering/macros. The exact applicable
set requires owner reconciliation, but SURF-04 and the two SHR-03 packages do
not establish authority over this defect merely by being named.

Evidence:

- `docs/work-packages/20260716_pure_ui_contract_standardization_c/artifacts/child_package_register.md`,
  lines 118-151, 289-301, and 303-325
- `docs/work-packages/20260716_pure_ui_contract_ratification/artifacts/2026-07-27_auth_session_bounded_remediation_decision.md`,
  lines 10-22
- `docs/standards/contract-first-change-standard.md`, "Bounded Cross-Owner
  Remediation"

Required action: reconcile and register every actual borrowed owner, beginning
with SURF-13, and remove unrelated owners unless a concrete borrowed obligation
is documented. Cross-link the corrected M1C authority from the REM-03 package,
contract decision, and ExecPlan. Because owner identity defines the authority
boundary, the corrected registration requires the mandated independent reviews
and disposition before the standalone ancestor.

### RER-COR-08 - Medium - Checkpoint and authority metadata still contradict
the revised policy

The canonical and navigation documents do not yet describe one coherent
checkpoint:

- `PROJECT_TRACKER.md` still calls remembered login "rolling for 90 days."
- `docs/adrs/README.md` still labels ADR-0028 "Rolling 90-Day Remembered Login."
- `PROJECT_TRACKER.md` still reports 73 total units and two bounded remediations,
  while the child register reports 74 and three.
- The REM-03 and GOV-00A trackers retain older `Last updated` values despite
  later decision/review entries, and the REM-03 ExecPlan progress does not record
  completion and disposition of the initial reviews.
- REM-03's package, contract decision, and ExecPlan do not cite GOV-00A-M1C, so
  the executable checkpoint is not self-contained with respect to its borrowed
  authority.

Additionally, the REM-03 tracker records the initial reviews at
`2026-07-27 20:05 UTC`, although the host clock during this rereview was
`2026-07-27 19:29 UTC`. The checkpoint's review/ancestor sequence cannot be
audited from a future completion timestamp.

Required action: reconcile policy wording, counts, authority cross-links,
progress, and actual UTC timestamps across the checkpoint before committing the
ancestor.

### RER-COR-09 - Medium - The normative conformance-test manifest omits the
changed surfaces

The session contract says its listed suites MUST be updated whenever session
behavior changes, but the list does not include the planned authentication-form,
successful-login cookie-boundary, or security-logging tests. Conversely, the
ExecPlan names only the auth/CAP, configuration, and logging suites as focused
targets and does not say why the contract's existing rq-engine and controller
suites require changes or are unaffected.

Evidence:

- `docs/schemas/weppcloud-session-contract.md`, lines 132-142
- `docs/work-packages/20260727_auth_session_persistence_hardening/prompts/active/auth_session_persistence_execplan.md`,
  lines 109-137

Required action: add the exact REM-03 conformance suites to the normative list
and either update every suite the contract currently marks mandatory or record
a reviewed `N/A` rationale and run it as a regression gate. The focused command
must include the actual successful-login/logout cookie-boundary suite once its
location is chosen.

### Rereview Verdict

**Fail.** COR-01 through COR-05 are dispositioned, but implementation remains
blocked by two high and two medium rereview findings.

| Severity | Open after rereview |
| --- | ---: |
| High | 2 |
| Medium | 2 |
| Low | 0 |

The checkpoint may proceed only after RER-COR-06 through RER-COR-09 are resolved
or, where the governance permits risk acceptance, explicitly accepted by the
authorized owner and independently rereviewed. The corrected REM-03/GOV-00A-M1C
checkpoint and reviews must then be committed as the standalone ancestor before
any implementation-file edit.

## Second Rereview - 2026-07-27

### Second Rereview Scope

This rereview assessed the operator's UX-first policy decision and the current
REM-03 package, tracker, ExecPlan, contract decision, ADR-0028, session contract,
`PROJECT_TRACKER.md`, ADR index, GOV-00A-M1C decision, child-package register,
and GOV-00A tracker. The host clock was `2026-07-27 19:52 UTC` during the
metadata check. Implementation files remained read-only.

### Disposition of Prior Findings

| Finding | Second rereview disposition | Evidence |
| --- | --- | --- |
| COR-01 | Resolved in design; remaining negative-test gaps are tracked under RER-COR-09. | The global Flask-Login refresh setting remains disabled, and the normative design restricts custom refresh to a valid remember token already carried by the browser. |
| COR-02 | Resolved at checkpoint. | The plan requires recursive redaction, unique sentinels across every retained secret sink, and assertions against final INFO and DEBUG records. |
| COR-03 | Resolved at checkpoint. | Policy rollback remains separate from logging/redaction, moves the ADR and contract together, acknowledges already-issued cookies, and names `fs_uniquifier` rotation for immediate containment. |
| COR-04 | Resolved at checkpoint. | Ninety days is the documented default; an explicit operator duration override remains supported and must document its security/UX tradeoff, while unsafe global refresh remains disabled. |
| COR-05 | Resolved at checkpoint, subject to final implementation evidence. | The contract requires append-only worker writes, host-coordinated rotation, restricted permissions, visible failures, and route non-exposure. |
| RER-COR-06 | Resolved by explicit authorized risk acceptance. | The session contract now distinguishes browser inactivity expiry from server-side token validity, the operator decision accepts copied-token replay risk, and `fs_uniquifier` containment and its active-session blast radius are documented. |
| RER-COR-07 | Resolved. | GOV-00A-M1C and REM-03 now borrow SURF-13, SHR-02, and SHR-04A, with an exact source boundary and explicit exclusions. |
| RER-COR-08 | **Open - Medium.** | Counts and navigation policy are reconciled, but the GOV-00A tracker and M1C decision still contradict the auditable checkpoint; see below. |
| RER-COR-09 | **Open - Medium.** | The normative manifest is expanded, but the executable gate and cookie-state coverage remain incomplete; see below. |

### RER-COR-08 - Medium - Checkpoint reconciliation remains incomplete

The revised navigation count, policy title, authority links, and borrowed-owner
mapping are now consistent. Three checkpoint records remain inconsistent:

- `docs/work-packages/20260716_pure_ui_contract_ratification/tracker.md` reports
  `Last updated` as `2026-07-21 22:15 UTC`, although it contains the new M1C
  decision.
- That decision is dated `2026-07-27 20:05 UTC`, thirteen minutes after the host
  clock observed during this rereview. A future authority event cannot establish
  the ancestor's actual review sequence.
- `docs/work-packages/20260716_pure_ui_contract_ratification/artifacts/2026-07-27_auth_session_bounded_remediation_decision.md`
  still calls the borrowed behavior an “absolute remember-cookie
  duration/default,” while the next paragraph and every revised normative
  document require rolling browser inactivity.
- The REM-03 ExecPlan still leaves “Obtain and disposition two independent
  checkpoint reviews” entirely unchecked and does not record the completed
  initial review/disposition or the now-pending passing rereviews. The REM-03
  tracker records those as distinct states.

Required action: use actual UTC timestamps, update the GOV-00A tracker metadata,
replace the stale “absolute” authority wording with rolling inactivity wording,
and make the ExecPlan's living progress distinguish completed initial
review/disposition from pending passing rereviews.

### RER-COR-09 - Medium - Required conformance remains only partially executable

The session contract now names the changed form, cookie-boundary, and logging
coverage, and the focused pytest command includes
`tests/weppcloud/test_auth_remember_cookie.py`. That resolves the original
manifest omission. The complete mandatory gate is still not executable as
written:

- The contract requires the session-heartbeat and console JavaScript suites, but
  the ExecPlan has no `wctl run-npm test` command. Its broad
  `wctl run-pytest tests` command cannot run those suites.
- The reviewed-`N/A` paragraph does not identify every unaffected suite by path,
  including the rq-engine token API and fork/archive route suites. The contract
  requires a reviewed rationale and a regression run for every listed unaffected
  suite.
- The response-level acceptance text proves opt-out only for a response that
  emits no remember cookie. It does not prove the stronger contract requirement
  that an opt-out submission with a preexisting remember cookie emits the
  correctly scoped deletion.
- The acceptance text proves a positive later refresh but does not test the
  contract's word “valid.” An invalid remember-cookie value presented alongside
  an ordinary authenticated session must not be treated as opt-in and exchanged
  for a fresh valid credential. Without this negative case, a presence-only
  implementation could pass the listed tests while violating the contract and
  recreating remembered identity.

Required action: add exact commands that run every normative Python and
JavaScript suite, record the reviewed `N/A` rationale per unaffected suite, and
add response-level cases for preexisting-cookie opt-out deletion and
invalid-cookie non-refresh/non-creation.

### Second Rereview Verdict

**Fail.** RER-COR-06 and RER-COR-07 are resolved, and the original COR-01
through COR-05 designs are dispositioned. RER-COR-08 and RER-COR-09 remain open
at medium severity, so the checkpoint is not yet ready for its standalone
ancestor or implementation.

| Severity | Open after second rereview |
| --- | ---: |
| High | 0 |
| Medium | 2 |
| Low | 0 |

Residual copied-token replay is an explicitly accepted high security risk, not
an undispositioned review finding. The final implementation review must still
verify token validity rather than cookie-name presence, response cookie
attributes and scope, redaction at final log records, append-only multi-worker
behavior, host rotation, permissions, and production-path operability.

## Final Checkpoint Confirmation - 2026-07-27 19:56 UTC

RER-COR-08 is resolved. The GOV-00A tracker now uses actual timestamps and
current metadata, the M1C authority consistently specifies rolling
remember-cookie inactivity, and the ExecPlan separately records the completed
initial review/disposition and pending passing rereviews.

RER-COR-09 is resolved. The ExecPlan now provides exact Python and targeted Jest
commands for every contract-listed suite, records a per-suite reviewed `N/A`
rationale, and requires response-level coverage for preexisting-cookie opt-out
deletion and invalid-cookie non-refresh/non-creation. The targeted Jest command
was executed during this confirmation: both named suites passed, with 15 tests
passing.

### Final Checkpoint Verdict

**Pass.** COR-01 through COR-05 and RER-COR-06 through RER-COR-09 have no
unresolved high or medium findings.

| Severity | Open after final confirmation |
| --- | ---: |
| High | 0 |
| Medium | 0 |
| Low | 0 |

The corrected checkpoint may enter the required standalone ancestor commit.
Implementation remains prohibited until that ancestor exists. The accepted
copied-token replay risk and the final implementation-evidence requirements
recorded above remain in force.
