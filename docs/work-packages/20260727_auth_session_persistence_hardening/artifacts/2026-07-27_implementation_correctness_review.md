# Implementation Correctness Review - Authentication Session Persistence

## Metadata

- **Reviewer**: Codex `reviewer` agent, independent post-implementation review
- **Date**: 2026-07-27
- **Checkpoint ancestor**: `4fd02a7e10f05d7403c24eb545dbe31b6d453205`
- **Working-tree revision**: `283dde284` plus uncommitted REM-03 changes
- **Scope**: Remember-cookie lifecycle, password-login form behavior, logout and
  cookie scope, configuration compatibility, authentication logging, tests,
  operator/developer documentation, Flask-Login 0.6.3, and Flask-Security 5.6.1
- **Implementation files modified by this review**: none

## Verdict

**Fail.** The implementation must not proceed to final acceptance with
IMP-COR-01 open. Four medium findings also leave mandatory cookie-boundary,
logging, operational, and regression evidence incomplete.

| Severity | Open |
| --- | ---: |
| High | 1 |
| Medium | 4 |
| Low | 1 |

## Findings

### IMP-COR-01 - High - A valid remembered identity defeats a submitted opt-out

`refresh_presented_remember_cookie()` evaluates
`current_user.is_authenticated` before the login view runs. With no ordinary
session and a valid remember cookie, that access makes Flask-Login load the user
from the cookie. The hook then schedules `_remember="set"`. Flask-Security's
login view checks whether the user is already authenticated before calling
`form.validate_on_submit()`, so `ExtendedLoginForm.validate()` never gets the
opportunity to replace the marker with `"clear"`.

This was reproduced with the pinned Flask-Login/Flask-Security versions and a
real `Security` login view:

1. issue a valid remember cookie;
2. remove only the ordinary session cookie;
3. POST `/login` with credentials and no `remember` field;
4. observe a `302` and a new 90-day remember-cookie `Set-Cookie` header.

The new regression test does not exercise this flow. Its synthetic
`/login-opt-out` route explicitly writes `session["_remember"] = "clear"` after
calling `login_user()`, bypassing the framework ordering that causes the defect.
The separate form unit test also invokes `validate()` directly.

Evidence:

- `wepppy/weppcloud/routes/_security/ui.py`, lines 21-34
- `wepppy/weppcloud/auth_forms.py`, lines 46-59
- `tests/weppcloud/test_auth_remember_cookie.py`, lines 39-43 and 91-98
- Flask-Security 5.6.1 `views.login()`, authenticated-user short circuit before
  `validate_on_submit()`
- Flask-Login 0.6.3 `LoginManager._load_user()` and
  `LoginManager._update_remember_cookie()`

Required action: make a password-login POST that omits `remember` suppress
remember-cookie loading/refresh before `current_user` can short-circuit the
view, then clear the configured remember cookie at the HTTP response boundary.
Add a real Flask-Security route test using a signed preexisting token and no
ordinary session cookie; the response must delete rather than refresh the
remember credential.

### IMP-COR-02 - Medium - Logout does not satisfy the two-cookie boundary

The normative contract requires explicit logout to clear both session and
remember cookies with their configured scope and security attributes. The
implementation delegates remember deletion to Flask-Login 0.6.3
`_clear_cookie()`, which supplies only name, domain, and path. Its deletion
header omits `Secure`, `HttpOnly`, and `SameSite`.

The Flask-Security logout path also removes authentication keys without clearing
the whole Flask session. A real-view reproduction returned a replacement
session cookie rather than a session-cookie deletion and left `_roles`,
`_roles_mask`, and `fs_cc` in the session. The remember deletion header omitted
all three configured security attributes. This did not preserve an
authenticated `_user_id`, but it violates the explicit logout contract and
retains stale authorization-adjacent state.

The new logout test asserts only a remember-cookie 1970 expiry. It does not
assert session-cookie deletion, configured name/path/domain, or deletion
security attributes.

Evidence:

- `docs/schemas/weppcloud-session-contract.md`, lines 61-67
- `tests/weppcloud/test_auth_remember_cookie.py`, lines 109-117
- `wepppy/weppcloud/routes/_security/logging.py`, lines 133-143
- Flask-Login 0.6.3 `LoginManager._clear_cookie()`
- Flask-Security 5.6.1 `views.logout()` and `tf_clean_session()`

Required action: implement and test the complete configured logout boundary.
Clear stale role/session state, emit deletion for both cookies, and assert
configured names, paths, domains, Secure, HttpOnly, and SameSite attributes on
real Flask-Security logout responses.

### IMP-COR-03 - Medium - Raw `remember` form data can still disclose secrets

The request logger treats the `remember` field name as safe but logs its raw,
unparsed value. A crafted login POST with
`remember=BEARER_TOKEN_SENTINEL` produced a final INFO record containing that
sentinel. This violates the contract that authentication logs never contain
bearer or other credential values. The field is user-controlled at this hook;
it has not yet been normalized by WTForms to a boolean.

The added test calls `_sanitize_form()` and `_sanitize_extra()` directly. It
does not inject unique sentinels through the request, cookie, signal-extra, URL,
INFO, and DEBUG paths and assert against final emitted records as required by
the checkpoint.

Evidence:

- `wepppy/weppcloud/routes/_security/logging.py`, lines 241-260
- `tests/weppcloud/routes/test_security_logging_role_cache.py`, lines 52-66
- `docs/schemas/weppcloud-session-contract.md`, lines 97-102
- `docs/work-packages/20260727_auth_session_persistence_hardening/prompts/active/auth_session_persistence_execplan.md`,
  lines 161-163

Required action: log a normalized boolean/presence indicator rather than the raw
request value. Add final-record sentinel tests for every retained input sink and
both INFO and DEBUG output.

### IMP-COR-04 - Medium - Durable logging lacks its required operational boundary

Replacing per-process rotation with `WatchedFileHandler` is the right worker-side
direction, and the implementation creates `0700`/`0600` paths. The required
host-coordinated bounded rotation/retention configuration is absent from the
change set, however. No repository file provisions rotation for
`/wc1/logs/weppcloud/security.log`.

Write failures are also not guaranteed to reach the main service log.
`WatchedFileHandler` inherits the standard logging error path, which silently
ignores emission errors when `logging.raiseExceptions` is false. The only
failure handling added here covers setup-time `OSError`.

The test covers one process, one temporary path, handler deduplication, and one
successful append. It does not cover write failure, external rotate/reopen,
multi-worker append behavior, canonical-path access as uid 1002, bounded host
retention, or route non-exposure.

Evidence:

- `wepppy/weppcloud/routes/_security/logging.py`, lines 50-79
- `tests/weppcloud/routes/test_security_logging_role_cache.py`, lines 69-94
- `docs/schemas/weppcloud-session-contract.md`, lines 103-110
- `docs/work-packages/20260727_auth_session_persistence_hardening/artifacts/2026-07-27_checkpoint_security_review.md`,
  lines 283-284

Required action: ship the concrete host rotation/retention configuration,
provide a handler error boundary that reports write failures to the main service
log, and complete the production-compatible, multi-process, rotation/reopen,
permission, and route-exposure evidence.

### IMP-COR-05 - Medium - Cookie/config tests do not prove the accepted contract

The focused suite passes but several checkpoint-mandated assertions are absent:

- no valid user-mismatched remember-token case;
- no real login/logout Flask-Security route coverage;
- no assertion that response expiry is approximately 90 days;
- no assertion that a later refresh advances expiry;
- no configured remember-cookie name/path/domain matrix;
- no restoration request after removal of the ordinary session cookie;
- no assertion that `REMEMBER_COOKIE_REFRESH_EACH_REQUEST=true` in the
  environment is forcibly ignored.

The last configuration test sets the environment value to `false`, so it would
also pass if unsafe environment parsing were reintroduced. The positive refresh
test checks only that an `Expires` attribute and another remember header exist.

Evidence:

- `tests/weppcloud/test_auth_remember_cookie.py`, lines 69-117
- `tests/weppcloud/test_configuration.py`, lines 207-224
- `docs/work-packages/20260727_auth_session_persistence_hardening/artifacts/2026-07-27_checkpoint_security_review.md`,
  line 282

Required action: expand response-level coverage to the complete state and
configuration matrix above. Tests should fail for a presence-only refresh hook,
an unsafe global-refresh override, incorrect duration, wrong cookie scope, or
incomplete logout.

### IMP-COR-06 - Low - Living work-package status is stale

The working tree contains the implementation and tests, but the tracker still
reports `Contract checkpoint`, lists implementation as ready, and leaves all
verification gates unchecked. The ExecPlan likewise leaves both implementation
steps unchecked. The active-plan contract requires these living records to
remain current.

Evidence:

- `docs/work-packages/20260727_auth_session_persistence_hardening/tracker.md`,
  lines 9-32 and 108-117
- `docs/work-packages/20260727_auth_session_persistence_hardening/prompts/active/auth_session_persistence_execplan.md`,
  lines 27-31

Required action: after fixing the implementation findings, reconcile the phase,
task board, progress, verification results, danger signals, and outcomes before
handoff.

## Confirmed Correct Behavior

- The default duration is 90 days while positive `REMEMBER_COOKIE_DAYS`
  overrides remain supported.
- Flask-Login's unsafe global refresh configuration is forced off.
- Valid presented tokens are HMAC-validated and identity-matched before the
  custom hook schedules refresh; ordinary sessions and invalid token values do
  not refresh in the covered path.
- GET form construction selects remember by default, while explicitly supplied
  POST form data is not overwritten.
- The handler uses append mode, creates the canonical path with restricted
  modes, and avoids in-process rotation.
- The revised logger removes the previously confirmed password, CAPTCHA,
  `next`, referrer, and signal-extra value disclosures from their ordinary
  paths.

## Validation Evidence

- Focused REM-03 Python suites: **35 passed**.
- Contract-listed unaffected Python suites: **90 passed**.
- Targeted session-heartbeat and console Jest suites: **2 suites / 15 tests
  passed**.
- Changed-file broad-exception enforcement: **passed**.
- REM-03 package, incident document, and WEPPcloud README lint: **passed**.
- `git diff --check` against `4fd02a7e1`: **passed**.
- The broad Python sweep was started but stopped without a result at the
  orchestrator's request; it is not counted as validation evidence.

Passing focused tests do not change the verdict because IMP-COR-01 and
IMP-COR-03 were reproduced through paths the new tests do not exercise.

## Post-Fix Rereview - 2026-07-27 20:17 UTC

This section supersedes the initial open-finding count and verdict rationale
above. The original High defect is resolved. Four Medium findings and one Low
finding remain open.

### Rereview Verdict

**Fail.** The login POST ordering defect is fixed, server session state is now
cleared on logout, and the confirmed raw request-value disclosure is removed.
Final acceptance remains blocked by an incomplete logout-cookie boundary,
missing final-record secret tests, an invalid host logrotate configuration, and
the incomplete cookie/configuration evidence matrix.

| Severity | Open |
| --- | ---: |
| High | 0 |
| Medium | 4 |
| Low | 1 |

### Finding Dispositions

| Finding | Disposition | Rereview evidence |
| --- | --- | --- |
| IMP-COR-01 | **Resolved** | `refresh_presented_remember_cookie()` now schedules `"clear"` for a login POST without `remember` before evaluating `current_user`. The new endpoint-ordering regression carries a valid remember token without an ordinary session and observes deletion rather than refresh. |
| IMP-COR-02 | **Open - Medium** | The new logout after-hook clears session state, and the regression proves both session and remember-cookie expiry. Remember deletion still delegates to Flask-Login 0.6.3, whose deletion header omits the configured `Secure`, `HttpOnly`, and `SameSite` attributes required by the contract. |
| IMP-COR-03 | **Open - Medium** | Raw form metadata is replaced by a boolean presence indicator and identities are hashed. A request-level probe confirmed that injected bearer and password sentinels are absent. The checkpoint-mandated final INFO/DEBUG record tests across every retained sink are still absent. |
| IMP-COR-04 | **Open - Medium** | A visible handler error boundary, bounded policy file, deployment note, and containment runbook were added. `logrotate -d docker/logrotate/weppcloud-security` rejects line 10 with `unknown user '1002'`, and the required write-failure, multi-process, rotate/reopen, uid-1002, and route-exposure evidence remains absent. |
| IMP-COR-05 | **Open - Medium** | Two response-level regressions now cover the critical opt-out ordering and session-plus-remember logout path. The accepted state/configuration matrix remains materially incomplete, including exact duration/refresh advancement, configured scope, restoration, identity mismatch, and a forced-off `true` environment override. |
| IMP-COR-06 | **Open - Low** | The tracker still reports `Contract checkpoint`, leaves implementation and validation in `Ready`, and leaves every verification item unchecked. The ExecPlan still marks implementation and focused validation incomplete. |

### Remaining Required Actions

#### IMP-COR-02 - Complete the configured logout-cookie boundary

`clear_logged_out_session()` correctly clears the Flask session and schedules
remember deletion. The resulting remember-cookie deletion still comes from
Flask-Login 0.6.3 `_clear_cookie()`, which applies name, domain, and path but
does not apply `Secure`, `HttpOnly`, or `SameSite`. This remains a direct
violation of `docs/schemas/weppcloud-session-contract.md`, lines 66-67. The new
test asserts the two expirations but not configured names, scope, or security
attributes.

Evidence:

- `wepppy/weppcloud/routes/_security/ui.py`, lines 47-53
- `tests/weppcloud/test_auth_remember_cookie.py`, lines 144-160
- `docs/schemas/weppcloud-session-contract.md`, lines 61-67
- Flask-Login 0.6.3 `LoginManager._clear_cookie()`

Required action: emit the remember-cookie deletion with the complete configured
scope and security attributes, then assert both cookie deletions against
non-default name/path/domain settings and `Secure`, `HttpOnly`, and `SameSite`.

#### IMP-COR-03 - Add final emitted-record secret evidence

The implementation defect that exposed raw `remember` input is fixed.
`_log_login_request()` records only `remember_selected`, `_sanitize_form()`
returns only that boolean, signal extras are reduced to key names, and identity
labels are hashed. The current regression still tests sanitizing helpers
directly; it does not send unique values through request, cookie, URL, form,
signal-extra, INFO, and DEBUG paths and inspect the final emitted records.

Evidence:

- `wepppy/weppcloud/routes/_security/logging.py`, lines 195-272
- `tests/weppcloud/routes/test_security_logging_role_cache.py`, lines 52-66
- `docs/work-packages/20260727_auth_session_persistence_hardening/prompts/active/auth_session_persistence_execplan.md`,
  lines 156-169

Required action: add the final-record sentinel matrix required by the ExecPlan.
The request-level rereview probe is useful corroboration, but it does not
replace committed regression coverage across every retained sink and log level.

#### IMP-COR-04 - Make the bounded host policy deployable and prove its boundary

The custom watched handler now reports post-startup write errors through
`gunicorn.error`, and the incident document provides an actionable per-user
`fs_uniquifier` containment procedure with its all-device blast radius. The new
rotation policy is not valid in the review environment:

```text
error: docker/logrotate/weppcloud-security:10 unknown user '1002'
```

`logrotate` resolves `su` operands as account and group names. The repository
policy therefore cannot pass its own dry-run unless the deployment provisions
literal resolvable identities named `1002`. No automated evidence covers
handler write failure, multiple workers, external rotation/reopen,
canonical-path access as the runtime uid, bounded retention, or route
non-exposure.

Evidence:

- `docker/logrotate/weppcloud-security`, lines 1-11
- `wepppy/weppcloud/routes/_security/logging.py`, lines 21-29 and 61-95
- `tests/weppcloud/routes/test_security_logging_role_cache.py`, lines 69-94
- `docs/infrastructure/incident-2026-07-27-flask-security-double-prefix-csrf.md`,
  lines 204-230

Required action: use resolvable deployed host account/group names or explicitly
provision them, make `logrotate -d` succeed, and add the operational evidence
listed above.

#### IMP-COR-05 - Finish the accepted cookie/configuration matrix

The seven cookie tests now include the previously missing opt-out ordering and
two-cookie logout assertions. They still do not prove:

- a valid token whose identity does not match the active user is not refreshed;
- issued expiry is approximately 90 days and a later refresh advances it;
- custom remember-cookie name/path/domain are honored for issue and deletion;
- remembered identity is restored after the ordinary session cookie is removed;
- logout deletions retain all configured scope and security attributes; or
- `REMEMBER_COOKIE_REFRESH_EACH_REQUEST=true` from the environment is forcibly
  ignored.

The endpoint-ordering fixtures use handlers in a test blueprint named
`security`; they exercise the application hook order but not Flask-Security's
production login/logout handler bodies.

Evidence:

- `tests/weppcloud/test_auth_remember_cookie.py`, lines 19-160
- `tests/weppcloud/test_configuration.py`, lines 207-224
- `docs/work-packages/20260727_auth_session_persistence_hardening/prompts/active/auth_session_persistence_execplan.md`,
  lines 154-169

Required action: complete the response-level state and configuration matrix so
the suite fails on incorrect duration, refresh advancement, cookie scope,
identity matching, restoration, global-refresh override, or deletion
attributes.

#### IMP-COR-06 - Reconcile living work-package state

The implementation, focused validation, and rereviews now exist, but the
tracker and ExecPlan have not been updated to reflect them.

Evidence:

- `docs/work-packages/20260727_auth_session_persistence_hardening/tracker.md`,
  lines 9-32 and 100-117
- `docs/work-packages/20260727_auth_session_persistence_hardening/prompts/active/auth_session_persistence_execplan.md`,
  lines 23-31

Required action: update progress, verification results, danger signals,
dispositions, and next milestone before handoff.

### Post-Fix Validation Evidence

- Focused REM-03 Python suites: **37 passed**.
- Request-level logging probe with unique bearer and password values:
  **sentinels absent**.
- `git diff --check` against `4fd02a7e1`, excluding the ignored generated
  Usersum index: **passed**.
- `logrotate -d docker/logrotate/weppcloud-security`: **failed** because line 10
  names an unknown user.
- No broad Python sweep was run for this rereview.

## Final Rereview - 2026-07-27 20:28 UTC

This section supersedes both earlier verdict sections. The secure logout
deletion and valid rename/create rotation policy close IMP-COR-02 and the
configuration portion of IMP-COR-04. Three Medium evidence findings and one
Low work-package finding remain open.

### Final Verdict

**Fail.** No High implementation defect remains, but the new final-record test
passes without emitting an INFO or DEBUG record, and the mandatory logging
operability and cookie-state matrices remain incomplete.

| Severity | Open |
| --- | ---: |
| High | 0 |
| Medium | 3 |
| Low | 1 |

### Final Finding Dispositions

| Finding | Final disposition | Evidence |
| --- | --- | --- |
| IMP-COR-01 | **Resolved** | The pre-authentication login POST clear branch remains correctly ordered, and its endpoint-ordering regression passes. |
| IMP-COR-02 | **Resolved** | The logout after-hook now clears the complete session and emits remember deletion with configured name, path, domain, `Secure`, `HttpOnly`, and `SameSite`. A response probe confirmed the secure deletion plus session-cookie expiry. |
| IMP-COR-03 | **Open - Medium** | The implementation no longer exposes the reviewed raw values, but the new final-record test is vacuous: the logger's effective level is WARNING, so the test's INFO and DEBUG calls emit an empty string. It also exercises only `_log_event()`, not every retained request/signal sink. |
| IMP-COR-04 | **Open - Medium** | `logrotate -d` now accepts the rename/create policy, the handler reports runtime failures, and the containment command/runbook are present. Required automated write-failure, multi-process, rotate/reopen, canonical uid-1002, and route-exposure evidence remains absent. |
| IMP-COR-05 | **Open - Medium** | Approximate 90-day issue expiry, forced rejection of a `true` global-refresh override, and old-token invalidation after identity rotation are now covered. Refresh advancement, non-default cookie scope, positive restoration, valid mismatched identity, and production Flask-Security handler coverage remain absent. |
| IMP-COR-06 | **Open - Low** | The tracker and ExecPlan still describe implementation and validation as future work and leave the verification checklist unchecked. |

### Remaining Blocking Findings

#### IMP-COR-03 - The final-record sentinel test emits no records

`test_final_security_records_exclude_untrusted_sentinels()` adds a stream
handler but does not lower either the named logger or handler level. In the
same isolated runtime used by the test, `weppcloud.security` has level
`NOTSET`, inherits effective level `WARNING`, and has no configured handler.
Calling `_log_event()` therefore suppresses both its INFO and DEBUG messages:

```text
logger_level 0
effective_level 30
emitted_length 0
emitted_repr ''
```

All sentinel-absence assertions consequently pass even if either emitted
record would leak every sentinel. The test also invokes `_log_event()` directly
on a GET request; it does not exercise `_log_login_request()`, final login
response logging, request cookies, or signal dispatch. This does not meet the
ExecPlan requirement to inspect final INFO and DEBUG records from every
retained sink.

Evidence:

- `tests/weppcloud/routes/test_security_logging_role_cache.py`, lines 98-135
- `wepppy/weppcloud/routes/_security/logging.py`, lines 221-272
- `docs/work-packages/20260727_auth_session_persistence_hardening/prompts/active/auth_session_persistence_execplan.md`,
  lines 156-169

Required action: explicitly capture at DEBUG level, assert that the expected
INFO and DEBUG records are nonempty, drive the request and signal hooks rather
than only the helper, and then assert every unique request, cookie, URL, form,
and signal-extra sentinel is absent from the complete captured output.

#### IMP-COR-04 - Logging operability still lacks committed regression evidence

The policy defect itself is fixed. The new configuration uses host-coordinated
rename/create rotation, creates the replacement as `0600 roger roger`, and
passes `logrotate -d`. `WatchedFileHandler` is appropriate for worker reopen,
and `_VisibleWatchedFileHandler.handleError()` supplies the missing service-log
boundary.

The test suite remains limited to initial mode, handler deduplication, and one
successful append. It does not prove the new error handler is reached when
`logging.raiseExceptions` is false, that concurrent worker records survive,
that workers reopen after the shipped rotation policy renames the file, that
the canonical production path works as uid 1002, or that the directory remains
outside run-file routes. These cases were mandatory final evidence in the
checkpoint security review and ExecPlan, not optional follow-up coverage.

Evidence:

- `docker/logrotate/weppcloud-security`, lines 1-10
- `wepppy/weppcloud/routes/_security/logging.py`, lines 21-29 and 61-98
- `tests/weppcloud/routes/test_security_logging_role_cache.py`, lines 70-95
- `docs/schemas/weppcloud-session-contract.md`, lines 103-110

Required action: add the operational regression cases above and execute the
canonical create/write/rotate/reopen check with the production uid before
package acceptance.

The supported `tools/rotate_user_fs_uniquifier.py` command, documented
preview/apply workflow, and old-token invalidation test satisfactorily close
the containment-runbook concern. Command-level preview/apply tests would still
reduce incident-response regression risk.

#### IMP-COR-05 - The accepted cookie-state matrix remains incomplete

The final changes add three useful assertions: issue expiry falls within
89-90 days, a `REMEMBER_COOKIE_REFRESH_EACH_REQUEST=true` environment value is
ignored, and changing the remember identity invalidates a copied token. The
following checkpoint cases remain absent:

- a later opted-in request advances expiration rather than merely returning
  another header;
- non-default remember name, path, and domain apply to issue and deletion;
- a valid remembered identity is positively restored after ordinary session
  removal;
- a valid token for another existing identity is not refreshed beside an
  ordinary authenticated session; and
- the application hooks are exercised around Flask-Security's production login
  and logout handler bodies rather than test-blueprint stand-ins.

Evidence:

- `tests/weppcloud/test_auth_remember_cookie.py`, lines 20-181
- `tests/weppcloud/test_configuration.py`, lines 207-232
- `docs/work-packages/20260727_auth_session_persistence_hardening/prompts/active/auth_session_persistence_execplan.md`,
  lines 154-169

Required action: complete the remaining response-level cases so regressions in
refresh timing, restoration, identity matching, framework integration, or
configured cookie scope fail the suite.

### Remaining Low Finding

IMP-COR-06 remains open. The tracker still reports `Contract checkpoint` with a
2026-07-27 19:50 UTC update, lists implementation and validation in `Ready`,
and leaves all verification gates unchecked. ExecPlan progress also leaves the
implementation and validation tasks unchecked. Reconcile both living documents
after the blocking findings are resolved.

### Final Validation Evidence

- Focused authentication/configuration/logging suites: **40 passed**.
- `logrotate -d -s /tmp/weppcloud-security-logrotate.state
  docker/logrotate/weppcloud-security`: **passed**.
- Logout response probe: compliant secure remember deletion and session expiry
  observed.
- Final-record probe: **zero bytes emitted**, confirming the new negative test
  is vacuous at the inherited logger level.
- Containment command `--help` and Python compilation: **passed**.
- Changed-file broad-exception enforcement: **passed**.
- `git diff --check` against `4fd02a7e1`, excluding the ignored generated
  Usersum index: **passed**.
- No broad repository Python sweep was run for this bounded final rereview.

## Closeout Rereview - 2026-07-27 20:34 UTC

This section is the definitive implementation verdict and supersedes all
earlier verdict sections.

### Closeout Verdict

**Pass.** No unresolved correctness finding remains. The closeout changes make
the final-record assertions nonvacuous, cover watched-file reopen and visible
write failure, complete the material remember-cookie identity cases, provide
successful production uid-1002 evidence, and bring the living work-package
status current for final review.

| Severity | Open |
| --- | ---: |
| High | 0 |
| Medium | 0 |
| Low | 0 |

### Closeout Finding Dispositions

| Finding | Closeout disposition | Evidence |
| --- | --- | --- |
| IMP-COR-01 | **Resolved** | Login POST opt-out is handled before remembered identity can short-circuit Flask-Security form processing, and the endpoint-ordering regression passes. |
| IMP-COR-02 | **Resolved** | Logout clears complete session state and emits configured secure remember-cookie deletion beside session-cookie expiry. |
| IMP-COR-03 | **Resolved** | The final-record test now forces DEBUG, exercises event, login-request, and login-response paths, asserts three nonempty record signatures, and verifies all injected sentinels are absent. |
| IMP-COR-04 | **Resolved** | The shipped rename/create policy parses successfully; automated reopen and visible-error tests pass; prior multi-process evidence, static route inspection, and the final wepp1 uid-1002 canonical-path probe complete the operational boundary. |
| IMP-COR-05 | **Resolved** | Tests now cover 90-day issue expiry, positive restoration, invalid and valid-mismatched tokens, opt-out ordering, two-cookie logout, forced global-refresh disablement, and identity-rotation invalidation. The dedicated security review supplies the custom-scope response probe, and an independent timing probe confirms refresh expiry advances. |
| IMP-COR-06 | **Resolved** | Tracker phase, task status, risk disposition, post-change evidence, and verification state now reflect implementation and review. ExecPlan implementation and validation progress is current; final-review and retrospective fields appropriately remain pending until this review is dispositioned. |

### Closeout Validation Evidence

- Focused authentication/configuration/logging suites: **44 passed**.
- Refresh timing probe: the later opted-in response advanced expiry by one
  second.
- Rotation-policy parser: **passed**.
- Automated watched-file rename/reopen and visible-handler-error tests:
  **passed** within the focused suite.
- Dedicated security-review evidence: wepp1 uid 1002 successfully created,
  appended, closed, reopened, and removed a canonical-path probe; custom cookie
  scope and multi-process logging probes passed.
- Changed-file broad-exception enforcement: **passed**.
- Authentication work-package documentation lint: **8 files passed** with no
  errors or warnings.
- `git diff --check` against `4fd02a7e1`, excluding the ignored generated
  Usersum index: **passed**.
- No broad repository Python sweep was run for this bounded closeout rereview.

### Residual Risk and Coverage Gaps

The explicitly authorized copied-token risk remains: browser expiry is not a
server-enforced maximum for a stolen raw remember token. The supported
per-account `fs_uniquifier` rotation command is the immediate containment
mechanism and invalidates all of that account's existing sessions.

The following are non-blocking coverage and closeout improvements:

- commit an expiry-comparison assertion so the current manual refresh-advance
  probe becomes permanent regression coverage;
- explicitly assert the DEBUG `sanitized_form` record signature, although the
  current DEBUG-enabled combined output already checks its sentinel safety;
- convert the successful multi-process, custom-scope, and production uid-1002
  probes into repeatable automated or operator-check tooling where practical;
  and
- update the tracker from 40 to the observed 44 focused tests, record the final
  danger-signal assessment and retrospective, and check the dual-review item
  after this verdict is dispositioned.
