# Final Security Review - Authentication Session Persistence Hardening

## Final Rereview Findings - 2026-07-27

No unresolved security findings remain.

## Final Rereview Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: Security review permits package closeout after
  the package owner records the final validation and review disposition in the
  living ExecPlan and tracker.

## Final Rereview Dispositions

| Finding | Final disposition | Evidence |
| --- | --- | --- |
| REM-RER-SEC-01 | **Resolved** | `docker/logrotate/weppcloud-security` now uses normal rename/create rotation with `create 0600 roger roger` and no `copytruncate`. Logrotate 3.21.0 parsed the policy without a configuration error and handled the canonical log. The application uses `WatchedFileHandler`; prior multi-process append and rename/reopen probes passed. README and incident documentation now describe the same loss-avoiding strategy. |
| REM-RER-SEC-02 | **Resolved** | `tools/rotate_user_fs_uniquifier.py` provides preview-by-default and explicit `--apply` operation through the supported `wctl exec` path. It resolves one exact account, prints only account id/action metadata, generates a fresh UUID, commits transactionally, and fails visibly. The runbook provides preview/apply commands and verification/blast-radius steps. `test_rotating_user_identity_invalidates_copied_remember_cookie` proves the old credential no longer authenticates. |
| REM-RER-SEC-03 | **Resolved** | The logout response hook now emits an explicit remember-cookie deletion using configured name, path, domain, Secure, HttpOnly, and SameSite attributes. A custom-scope response probe confirmed those attributes beside complete session-cookie deletion. The focused suite now asserts the 90-day lifetime, secure logout attributes, copied-token invalidation, and forced disabling of an environment request for global refresh. |

## Final Rereview Validation Evidence

- Focused Python gate:

  ```text
  wctl run-pytest tests/weppcloud/test_auth_cap_captcha.py \
    tests/weppcloud/test_auth_remember_cookie.py \
    tests/weppcloud/test_configuration.py \
    tests/weppcloud/routes/test_security_logging_role_cache.py --maxfail=1
  40 passed
  ```

- Rotation-policy parser:

  ```text
  reading config file docker/logrotate/weppcloud-security
  Handling 1 logs
  rotating pattern: /wc1/logs/weppcloud/security.log
  ```

- Supported containment command:

  ```text
  wctl exec weppcloud python tools/rotate_user_fs_uniquifier.py --help
  usage: rotate_user_fs_uniquifier.py [-h] [--apply] email
  ```

- Custom configured logout produced:

  ```text
  wc_remember=; Domain=example.test; ...; Secure; HttpOnly;
    Path=/weppcloud; SameSite=Lax
  wc_session=; Domain=example.test; ...; Secure; HttpOnly;
    Path=/weppcloud; SameSite=Lax
  ```

- The prior final-record probe excluded all password, CAPTCHA, remember,
  OAuth, bearer, Authorization, user-agent, forwarded-for, referrer, and
  redirect-location sentinels. The forced write-failure probe remained visible
  through `gunicorn.error`.
- The initial review's 90 adjacent Python and 15 JavaScript regression passes
  remain applicable because those surfaces did not change during the finding
  remediation.
- A broad repository sweep was not run for this bounded security rereview.

## Final Residual Security Risk

The authorized copied-token risk remains explicit and accepted: the 90-day
duration is a cooperative-browser inactivity policy, not a server-enforced
maximum, and a stolen raw Flask-Login remember token can remain valid until the
affected user's `fs_uniquifier` or the application signing key changes. Secure,
HttpOnly, SameSite=Lax, TLS, strict log redaction, opt-out, scoped logout,
bounded restricted logging, and the supported per-user rotation command reduce
exposure and provide containment. Ordinary logout still cannot revoke a copy
held elsewhere.

## Final Sign-Off

Security sign-off is granted for REM-03 at the reviewed working-tree state over
checkpoint ancestor `4fd02a7e1`.

## First Rereview Findings - 2026-07-27 (Historical)

### REM-RER-SEC-01 - Medium - The shipped rotation policy is invalid and can lose security records

**Exploit path**: The public login boundary can generate security records before
authentication succeeds. If the installed rotation policy is rejected, the
active file remains unbounded and can fill the shared filesystem. If the policy
is made to run without changing `copytruncate`, records written between the copy
and truncate operations can be discarded. An attacker generating concurrent
login traffic can increase that integrity gap during the event operators are
trying to preserve.

**Evidence**:

- `docker/logrotate/weppcloud-security:10` specifies `su 1002 1002`.
  `logrotate --debug docker/logrotate/weppcloud-security` rejected the file with
  `unknown user '1002'` and handled zero logs. The `su` directive requires host
  user and group names, not the container uid written as a name.
- `docker/logrotate/weppcloud-security:9` selects `copytruncate`. The installed
  logrotate 3.21.0 manual explicitly warns that data may be lost between copying
  and truncating.
- `wepppy/weppcloud/routes/_security/logging.py:21` uses
  `WatchedFileHandler`, which already supports the safer host rename/create
  strategy by detecting the inode change and reopening.
- The focused test suite has no concurrent host-rotation test and no parser
  validation for the shipped policy.
- `docs/infrastructure/incident-2026-07-27-flask-security-double-prefix-csrf.md:227`
  incorrectly describes `copytruncate` as keeping all Gunicorn workers
  appending safely.

**Required remediation**: Replace `copytruncate` with normal rename/create
rotation, set `create 0600` with the real production host account and group,
and make the installed policy parse successfully on the target host. Add a
concurrent multi-worker rotate/reopen test that proves all uniquely numbered
records are present across the rotated and active files. Correct the operator
documentation and record the production-host installation/rotation result.

**Status**: Open at first rereview; resolved by the final rereview.

### REM-RER-SEC-02 - Medium - Copied-token containment is described but not executable or regression tested

**Exploit path**: The accepted threat model permits a copied remember token to
remain replayable until `fs_uniquifier` changes. The new runbook identifies the
database mutation but does not name an actual application-shell command,
datastore query, failure/rollback behavior, or verification command. During a
live theft incident, an improvised mutation or incomplete verification can
leave the stolen credential valid.

**Evidence**:

- `docs/infrastructure/incident-2026-07-27-flask-security-double-prefix-csrf.md:210`
  now records the affected-user scope, `uuid.uuid4().hex`, transaction commit,
  verification intent, audit metadata, and the all-device blast radius.
- Step 2 says only "In a WEPPcloud application shell" and "load that user
  through the configured datastore"; it provides no supported command or exact
  immutable-id lookup.
- Step 3 says to confirm rejection but provides no safe verification method.
- No regression test rotates `fs_uniquifier` and proves that an old remember
  token and existing session cease to authenticate.
- The accepted copied-token risk in
  `docs/schemas/weppcloud-session-contract.md:72` depends on this containment
  remaining actionable.

**Required remediation**: Provide a copy-safe supported `wctl` or application
command that accepts an immutable user id, performs a unique replacement and
transactional commit, fails visibly with rollback, and emits only nonsecret
audit evidence. Document a concrete verification command. Add a regression
test proving old-token and old-session invalidation after rotation.

**Status**: Open at first rereview; resolved by the final rereview.

### REM-RER-SEC-03 - Low - Remember-cookie deletion attributes and the full boundary matrix remain untested

**Exploit path**: The logout fix deletes the remember cookie using the correct
name, domain, and path, so the observed browser credential is removed. The
framework deletion header omits `Secure`, `HttpOnly`, and `SameSite`, however,
and the synthetic route tests would not detect later drift in configured scope,
duration, user-mismatch handling, or Redis session-id invalidation.

**Evidence**:

- A configured response probe produced a fully attributed session-cookie
  deletion but a remember-cookie deletion containing only name, domain, expiry,
  maximum age, and path.
- `tests/weppcloud/test_auth_remember_cookie.py:144` proves both cookie names
  are expired, but uses a synthetic Flask-Login blueprint rather than the real
  Flask-Security and Redis-session boundary.
- The suite does not assert a roughly 90-day expiry, advancement of the rolling
  expiry, a valid token for a different user, a configured
  name/path/domain/security-attribute matrix, or rejection of a copied old
  Redis session id after re-login.
- The literal contract at
  `docs/schemas/weppcloud-session-contract.md:66` includes configured security
  attributes.

**Required remediation**: Add real Flask-Security response tests with the Redis
session interface and a custom cookie configuration matrix. Either emit the
configured remember deletion attributes or amend the contract with the
standards-based rationale that only name/domain/path participate in cookie
deletion matching.

**Status**: Open at first rereview; resolved by the final rereview.

## First Rereview Verdict (Historical)

- **Gate status**: `fail`
- **Unresolved findings**:
  - High: 0
  - Medium: 2
  - Low: 1
- **Release recommendation**: Hold package closeout. The implementation-level
  high findings are resolved, but REM-RER-SEC-01 and REM-RER-SEC-02 must be
  remediated and independently rereviewed. No risk acceptance covers an invalid
  rotation policy or a nonexecutable incident-containment procedure.

## Prior Finding Dispositions

| Finding | Rereview disposition | Evidence |
| --- | --- | --- |
| REM-SEC-01 | **Resolved** | Request logging now reduces remember input to boolean presence; raw user-agent, forwarded-for, and response location were removed; form telemetry is boolean; identity is hashed. A final-record probe found none of seven credential sentinels in INFO/DEBUG output. |
| REM-SEC-02 | **Resolved for the high exploit path** | The login POST hook schedules clear before remembered identity can short-circuit form validation. The logout response hook clears the complete session and retains `_remember=clear` for Flask-Login processing. Focused tests prove preexisting remember deletion and both session/remember deletion. The remaining attribute and integration-test precision is REM-RER-SEC-03. |
| REM-SEC-03 | **Partially resolved; remains open as REM-RER-SEC-01** | Initial `0700`/`0600`, append behavior, handler deduplication, multi-process append, watched-file reopen, and visible setup/write failure are confirmed. The new host policy is rejected by logrotate and selects a record-loss-prone rotation method. |
| REM-SEC-04 | **Partially resolved; remains open as REM-RER-SEC-02** | The runbook now captures scope, mutation, transaction intent, audit hygiene, verification intent, and blast radius. It still lacks an executable supported command and invalidation regression. |

## Rereview Validation Evidence

- Focused Python gate:

  ```text
  wctl run-pytest tests/weppcloud/test_auth_cap_captcha.py \
    tests/weppcloud/test_auth_remember_cookie.py \
    tests/weppcloud/test_configuration.py \
    tests/weppcloud/routes/test_security_logging_role_cache.py --maxfail=1
  37 passed
  ```

- Final-record probe:

  ```text
  BEARER_FORM_SENTINEL=False
  BEARER_UA_SENTINEL=False
  BEARER_XFF_SENTINEL=False
  LOCATION_SENTINEL=False
  PASSWORD_SENTINEL=False
  REFERRER_SENTINEL=False
  AUTHORIZATION_SENTINEL=False
  ```

- Forced handler failure with `logging.raiseExceptions=False`:

  ```text
  main_service_visible=True
  ```

- Rotation-policy parser:

  ```text
  error: docker/logrotate/weppcloud-security:10 unknown user '1002'
  Handling 0 logs
  ```

- The initial review's 90 adjacent Python and 15 JavaScript regression passes
  remain applicable because those surfaces did not change during finding
  remediation.
- A broad repository sweep was not run for this bounded rereview.

## Rereview Residual Security Risk

The authorized copied-token risk remains: browser expiry is not server-enforced,
and a stolen raw remember token remains valid until `fs_uniquifier` or the
application signing key changes. The code now prevents invalid, mismatched, and
ordinary-session requests from obtaining refresh, and the reviewed log records
no longer disclose credential sentinels. Until the two medium findings close,
operators still lack reliable bounded log retention and a fully executable
per-user containment action.

## First Rereview Sign-Off (Historical)

Security sign-off remains withheld pending closure of REM-RER-SEC-01 and
REM-RER-SEC-02.

## Initial Findings

### REM-SEC-01 - High - Persistent authentication logs retain credential-capable request values

**Exploit path**: A login request can place an OAuth code, bearer credential,
or other secret in the `remember` form value, `User-Agent`,
`X-Forwarded-For`, or a `next` URL. The login request and response hooks write
those values verbatim to the persistent security log. A legitimate redirect
whose query contains a credential is also copied through the response
`Location` field. Anyone or any support tooling with later access to the log
can recover the value.

**Evidence**:

- `wepppy/weppcloud/routes/_security/logging.py:215` records raw
  `X-Forwarded-For`.
- `wepppy/weppcloud/routes/_security/logging.py:245` allowlists the
  `remember` key but preserves its raw request value; it is not normalized to a
  boolean.
- `wepppy/weppcloud/routes/_security/logging.py:252` records raw
  `X-Forwarded-For` and `User-Agent` values.
- `wepppy/weppcloud/routes/_security/logging.py:284` and
  `wepppy/weppcloud/routes/_security/logging.py:293` record the complete
  response `Location`, including its query.
- A final-record probe placed unique sentinels in the request. The
  `remember`, `User-Agent`, `X-Forwarded-For`, and redirect-location sentinels
  were present in captured records. Password, referrer, and Authorization
  sentinels were absent.
- `tests/weppcloud/routes/test_security_logging_role_cache.py:59` checks one
  parsed-form helper and extra key names, but has no request/response
  final-record test. It does not exercise INFO and DEBUG output or any of the
  leaking sinks above.
- This violates `docs/schemas/weppcloud-session-contract.md:97` and the
  checkpoint evidence requirement in
  `docs/work-packages/20260727_auth_session_persistence_hardening/artifacts/2026-07-27_contract_decision.md:65`.

**Required remediation**: Normalize `remember` to an allowlisted boolean or
action, validate forwarded addresses as addresses, and omit or sanitize
user-agent and redirect-location values so no query or credential-bearing
content is retained. Add final-record sentinel tests for every prohibited
credential class and every request, response, form, signal, INFO, and DEBUG
sink named by the checkpoint. Do not rely on key-name filtering when a retained
value can contain an arbitrary token.

**Status**: Open.

### REM-SEC-02 - High - Logout does not invalidate the server-side session cookie and session id

**Exploit path**: Flask-Security logout removes authentication keys through
Flask-Login, but it does not clear the complete Flask session. Login and form
processing leave values such as CSRF state, `fs_cc`, and `fs_paa` in the
session. Because the Redis session remains nonempty, Flask-Session saves it
under the same session id and reissues the session cookie instead of deleting
the Redis record and expiring the cookie. A copied session id is unauthenticated
immediately after logout, but can become authenticated again if the same
browser later logs in using that retained id.

**Evidence**:

- `docs/schemas/weppcloud-session-contract.md:66` requires explicit logout to
  clear both session and remember cookies with configured scope.
- No implementation change adds complete session clearing or session-id
  regeneration to the logout path. `wepppy/weppcloud/routes/_security/ui.py`
  proxies login but has no logout hardening hook.
- Inspection of the pinned Flask-Security and Flask-Login logout path confirms
  that it removes login and two-factor keys rather than clearing the session.
  The pinned Flask-Session 0.4.0 Redis interface deletes the Redis record and
  cookie only when the session is empty; otherwise it persists the unchanged
  `session.sid`.
- A response-boundary probe with retained CSRF state produced a deleted
  `remember_token` cookie and a nondeleted `session` cookie.
- `tests/weppcloud/test_auth_remember_cookie.py:111` asserts only deletion of
  `remember_token`. It never asserts session-cookie deletion, Redis-record
  deletion, configured cookie scope, or session-id rotation.

**Required remediation**: Make explicit logout clear the complete server-side
session so the Redis record is deleted and the configured session cookie is
expired, while preserving correctly scoped remember-cookie deletion. If any
anonymous state must survive logout, generate a new session id and copy only
an explicitly reviewed allowlist after invalidating the old id. Add a
Flask-Security route-level test using the Redis session interface that proves
both cookies are deleted with configured name/path/domain and that a copied old
session id cannot become authenticated after a later login.

**Status**: Open.

### REM-SEC-03 - Medium - Durable logging lacks bounded rotation and visible runtime write failure

**Exploit path**: The public login request hook emits a record before
authentication succeeds. Without a deployed bounded rotation policy, repeated
requests can grow `/wc1/logs/weppcloud/security.log` until the shared
filesystem fills. If a write later fails, standard logging error handling can
discard the record silently when `logging.raiseExceptions` is false, removing
the very incident evidence the durable log is intended to provide.

**Evidence**:

- `wepppy/weppcloud/routes/_security/logging.py:50` correctly selects
  `WatchedFileHandler`, enforces `0700`/`0600`, and avoids worker-side
  rotation.
- A four-process local probe wrote 200 unique records without loss, and a
  rename/recreate probe reopened the new file successfully.
- The running development container had
  `/wc1/logs/weppcloud` at `0700` and `security.log` at `0600`.
- Repository and host searches found no concrete logrotate or equivalent
  rotation/retention configuration for the canonical file.
- A forced closed-stream write with `logging.raiseExceptions=False` returned
  without raising and emitted no `gunicorn.error` warning. The current code
  handles setup `OSError` only; it does not make runtime handler failures
  visible.
- `tests/weppcloud/routes/test_security_logging_role_cache.py:69` covers initial
  modes, handler deduplication, and one write only. It does not cover
  multi-process append, host rotation/reopen, default path, runtime write
  failure, or the required production uid 1002 check.
- Static inspection found no run-file route that references
  `/wc1/logs/weppcloud`; route non-exposure is preserved.

**Required remediation**: Ship and validate a bounded host rotation/retention
configuration, including `create 0600` with the production WEPPcloud owner and
group. Add rate-limited, secret-free reporting of handler write/reopen failures
to the main service log. Add automated multi-process, rotate/reopen, setup and
write failure, default-path, route non-exposure, and production-uid tests. Run
the canonical-path create/write/rotate/reopen check as uid 1002.

**Status**: Open.

### REM-SEC-04 - Medium - Accepted copied-token containment has no actionable operator runbook

**Exploit path**: A copied Flask-Login remember token remains replayable until
the user's `fs_uniquifier` or the application signing key changes. The risk is
explicitly accepted, but current operator documentation only says to rotate the
field. During an incident, an improvised database mutation can fail to commit,
target the wrong user, create a uniqueness conflict, or omit verification,
leaving the copied credential usable.

**Evidence**:

- `docs/schemas/weppcloud-session-contract.md:72` accurately preserves the
  copied-token threat boundary and the active-session blast radius.
- A local boundary probe confirmed that a copied valid token authenticates and
  is refreshed, while a valid token for another user is not refreshed.
- `docs/infrastructure/incident-2026-07-27-flask-security-double-prefix-csrf.md:205`
  and `wepppy/weppcloud/README.md` provide no executable, transactional
  `fs_uniquifier` rotation procedure or verification step.
- Repository search found no other operator runbook for this containment
  action.
- The checkpoint security pass explicitly required the final operator
  documentation to provide the concrete rotation procedure.

**Required remediation**: Add a least-privilege operator runbook that resolves
the exact user, generates a unique replacement, commits the mutation
transactionally through a supported application command, records nonsecret
audit evidence, and verifies that an old remember token and old active session
are rejected. State the blast radius and rollback/escalation behavior. Add
regression coverage for old-token invalidation after rotation.

**Status**: Open.

## Initial Verdict

- **Gate status**: `fail`
- **Unresolved findings**:
  - High: 2
  - Medium: 2
  - Low: 0
- **Release recommendation**: Hold package closeout. REM-SEC-01 through
  REM-SEC-04 require remediation and independent security rereview. No
  unresolved medium or high finding has a new explicit risk acceptance.

## Review Scope

- **Package**:
  `docs/work-packages/20260727_auth_session_persistence_hardening/`
- **Reviewer**: Codex dedicated security reviewer
- **Date**: 2026-07-27
- **Reviewed checkpoint ancestor**: `4fd02a7e1`
- **Current HEAD during review**: `283dde284`
- **Implementation state**: current working tree, including the untracked
  `tests/weppcloud/test_auth_remember_cookie.py`
- **Security triage**: high; dedicated final review required
- **Surfaces reviewed**:
  `wepppy/weppcloud/auth_forms.py`,
  `wepppy/weppcloud/configuration.py`,
  `wepppy/weppcloud/routes/_security/ui.py`,
  `wepppy/weppcloud/routes/_security/logging.py`, focused tests,
  `wepppy/weppcloud/README.md`, the incident document, the session contract,
  contract decision, ExecPlan, tracker, and checkpoint reviews.
- The unrelated dirty generated Usersum index was excluded as required by root
  repository guidance.

## Positive Controls

- The reviewed checkpoint is an ancestor of the implementation state and the
  implementation files were not edited before checkpoint `4fd02a7e1`.
- `REMEMBER_COOKIE_DURATION` defaults to 90 days; Secure, HttpOnly, and
  SameSite=Lax remain enabled; the Redis session duration remains 12 hours.
- Flask-Login's global remember refresh remains disabled.
- `refresh_presented_remember_cookie()` refreshes only a cryptographically
  valid token whose identity matches the authenticated user. Ordinary
  authenticated sessions and invalid or user-mismatched values are not
  promoted into remembered sessions.
- A successful password-login opt-out schedules remember-cookie clearing; that
  clear action wins over the earlier request refresh marker.
- The accepted copied-token replay boundary remains explicit rather than being
  described as eliminated by browser expiry or ordinary logout.
- The file logger uses append mode, restricted initial permissions,
  per-process handler deduplication, and an external-rotation-aware handler.
- No cookie value or Authorization header is intentionally passed to the
  reviewed diagnostic formatters.

## Validation Evidence

- Focused Python gate:

  ```text
  wctl run-pytest tests/weppcloud/test_auth_cap_captcha.py \
    tests/weppcloud/test_auth_remember_cookie.py \
    tests/weppcloud/test_configuration.py \
    tests/weppcloud/routes/test_security_logging_role_cache.py --maxfail=1
  35 passed
  ```

- Adjacent authentication/session regression gate:

  ```text
  wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py \
    tests/microservices/test_rq_engine_session_routes.py \
    tests/microservices/test_rq_engine_fork_archive_routes.py --maxfail=1
  90 passed
  ```

- JavaScript regression gate:

  ```text
  wctl run-npm test -- --runTestsByPath \
    wepppy/weppcloud/controllers_js/__tests__/session_heartbeat.test.js \
    wepppy/weppcloud/controllers_js/__tests__/console_smoke.test.js
  2 suites, 15 tests passed
  ```

- Passing submitted tests do not close the findings above because the
  checkpoint-required HTTP cookie boundary, final-record sentinel, failure,
  rotation, and production-path cases are absent.
- A broad repository test sweep was not run as part of this bounded security
  review.

## Residual Security Risk

The operator's accepted risk remains unchanged: a copied raw Flask-Login
remember token has no server-enforced issuance timestamp or absolute expiry and
can be replayed until `fs_uniquifier` or the signing key changes. The rolling
90-day duration is a cooperative-browser inactivity policy. Ordinary logout
clears the requesting browser's remember token but cannot revoke a copy held
elsewhere. That accepted boundary does not cover the newly identified log
disclosure, reusable session-id, logging-operability, or missing-runbook
findings.

## Initial Sign-Off

Security sign-off is withheld pending remediation and rereview of all open
medium and high findings.
