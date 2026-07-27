# Harden authentication persistence and security logging

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. The `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective`
sections must remain current.

## Purpose / Big Picture

WEPPcloud users should not repeatedly enter credentials during normal active use.
After this work, password login visibly opts into a rolling 90-day remembered
identity while allowing shared-device opt-out. Security logs persist across
container recreation and never contain credential or token values.

## Progress

- [x] (2026-07-27 19:12 UTC) Collected production configuration, Redis TTL, form
  render, and logging evidence.
- [x] (2026-07-27 19:12 UTC) Drafted package, tracker, contract decision, ADR,
  and session-contract amendment.
- [x] (2026-07-27 19:29 UTC) Obtained initial dual checkpoint reviews and
  dispositioned their findings.
- [x] (2026-07-27 19:57 UTC) Obtained passing dual checkpoint rereviews after
  the operator's UX-first decision and corrected GOV-00A-M1C authority.
- [x] (2026-07-27 19:57 UTC) Committed reviewed contract checkpoint as
  standalone ancestor `4fd02a7e1`.
- [ ] Implement remembered-login behavior and regression tests.
- [ ] Implement secure persistent logging and regression tests.
- [ ] Run focused and repository validation.
- [ ] Obtain dual independent final reviews and resolve findings.
- [ ] Close package documentation and commit implementation.

## Surprises & Discoveries

- Observation: `SECURITY_DEFAULT_REMEMBER_ME=True` does not result in a checked
  production checkbox.
  Evidence: public login HTML contains the checkbox without `checked`.
- Observation: all 405 inspected Redis sessions use the 12-hour TTL.
  Evidence: maximum TTL was 43,197 seconds.
- Observation: security file logging has been disabled by permissions.
  Evidence: production warning names `/workdir/wepppy/.docker-data` as denied.
- Observation: login request logging redacts `csrf_token` but not `cap_token` or
  `cap-token`.
  Evidence: production container logs contained CAPTCHA token fields.
- Observation: the current response hook runs before Flask saves session cookies.
  Evidence: successful login logs `set_cookie=False` despite Flask-Login
  scheduling remember behavior.
- Observation: Flask-Login 0.6.3 refreshes a remember cookie for every
  authenticated session, including a login that explicitly used
  `remember=False`.
  Evidence: both checkpoint reviewers confirmed the pinned implementation and
  one reproduced the response behavior in a minimal application.

## Decision Log

- Decision: Keep Redis sessions rolling at 12 hours and refresh the 90-day
  remember cookie only for browsers already carrying a valid remember token.
  Rationale: separates active session storage from durable browser identity.
  Date/Author: 2026-07-27, operator and Codex.
- Decision: Set checkbox data only when no submitted form data exists.
  Rationale: renders the default while preserving POST opt-out.
  Date/Author: 2026-07-27, Codex.
- Decision: Persist security logs under `/wc1/logs/weppcloud/security.log`.
  Rationale: `/wc1` is writable by uid 1002 and host-mounted in production.
  Date/Author: 2026-07-27, Codex.
- Decision: Log Flask-Login's safe remember action, never cookie values.
  Rationale: proves scheduling without exposing credentials or relying on
  response-hook ordering.
  Date/Author: 2026-07-27, Codex.

## Outcomes & Retrospective

Pending.

## Context and Orientation

This plan executes REM-03 under GOV-00A-M1C and borrows only SURF-13, SHR-02,
and SHR-04A as registered in the umbrella child-package register.

`wepppy/weppcloud/auth_forms.py` supplies the custom password login form.
`wepppy/weppcloud/configuration.py` defines Redis and remember-cookie defaults.
`wepppy/weppcloud/routes/_security/logging.py` records Flask-Security signals and
request summaries. `wepppy/weppcloud/templates/security/login_user.html` renders
the checkbox. Production runs as uid 1002 and mounts host storage at `/wc1`.

The ordinary session cookie contains a signed Redis session identifier and is
discarded when the browser session ends. A Flask-Login remember cookie can
restore identity after that ordinary session disappears. The cookie value is a
credential and must never be logged.

## Plan of Work

First, complete the contract-first checkpoint: obtain two independent reviews,
resolve findings in the checkpoint documents, and commit them without
implementation files.

Second, update `ExtendedLoginForm` so GET construction sets `remember.data=True`
only when form data is absent. Change remember duration to 90 days, keep
Flask-Login's unsafe global refresh disabled, add opt-in-aware refresh, and
retain the 12-hour session lifetime.

Third, replace broad value diagnostics with safe allowlists and recursive
secret redaction for password, CSRF, CAPTCHA, cookie, OAuth, bearer, URL query,
and signal-extra inputs. Add safe `remember_action` metadata restricted to
`set`/`clear`/absent. Remove the misleading early `set_cookie` diagnostic.
Configure append-only persistence under `/wc1` with restricted modes and
host-coordinated rotation.

Fourth, add focused unit and render tests. Update operator/developer docs and the
2026-07-27 incident report. Run canonical gates.

Finally, dispatch two independent final reviewers: one security/correctness
review and one QA/maintainability review. Resolve all medium/high findings,
record dispositions, close the package, and commit.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/test_auth_cap_captcha.py \
      tests/weppcloud/test_auth_remember_cookie.py \
      tests/weppcloud/test_configuration.py \
      tests/weppcloud/routes/test_security_logging_role_cache.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py \
      tests/microservices/test_rq_engine_session_routes.py \
      tests/microservices/test_rq_engine_fork_archive_routes.py --maxfail=1
    wctl run-npm test -- --runTestsByPath \
      wepppy/weppcloud/controllers_js/__tests__/session_heartbeat.test.js \
      wepppy/weppcloud/controllers_js/__tests__/console_smoke.test.js
    wctl doc-lint --path \
      docs/work-packages/20260727_auth_session_persistence_hardening
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    git diff --check

Run the broader test sweep before handoff:

    wctl run-pytest tests --maxfail=1

The following contract-listed suites are behaviorally unaffected because
REM-03 changes only the Flask-Security remember cookie and authentication
diagnostics, but each remains an executable regression gate:

- `tests/weppcloud/routes/test_rq_engine_token_api.py`: no rq-engine browse JWT
  minting, cookie scope, or Flask-session bridge change.
- `tests/microservices/test_rq_engine_session_routes.py`: no rq-engine session
  endpoint or JWT contract change.
- `tests/microservices/test_rq_engine_fork_archive_routes.py`: no fork/archive
  authorization or session-token change.
- `wepppy/weppcloud/controllers_js/__tests__/session_heartbeat.test.js`: no
  heartbeat request, interval, or stale-session UX change.
- `wepppy/weppcloud/controllers_js/__tests__/console_smoke.test.js`: no
  console authentication-failure behavior change.

## Validation and Acceptance

The login template test must find a checked remember field on GET. Route tests
must prove successful opt-out emits no remember cookie, successful opt-in emits
a 90-day Secure/HttpOnly/SameSite=Lax cookie, later opted-in requests refresh
it, ordinary sessions do not create one, and logout expires both cookies at
matching scope. Configuration tests must report 90 days, global refresh false,
and 12 hours
unchanged. Logging tests must inject unique secret sentinels through every
retained sink and prove they are absent from final INFO and DEBUG records. The
cookie-boundary suite must also prove that an opt-out submission with a
preexisting remember cookie emits a correctly scoped deletion and that an
invalid remember value beside an ordinary authenticated session is neither
refreshed nor exchanged for a valid credential. The
append-only handler must use restricted modes, deduplicate handlers, and make
initialization/write failures visible. Production validation must create,
append, close, and reopen the canonical path as uid 1002 and confirm it is not
served by run-file routes.

## Idempotence and Recovery

All edits are source-controlled and test-only operations are repeatable.
Rollback restores the 30-day nonrefreshing default and prior form behavior, supersedes
ADR-0028, and amends the session contract. It does not shorten already-issued
90-day cookies; rotate an affected user's `fs_uniquifier` for immediate
invalidation. Do not roll back durable logging or token redaction unless an
alternative secure implementation is ready.

## Artifacts and Notes

Production evidence is summarized without cookie or token values in
`artifacts/2026-07-27_contract_decision.md`.

## Interfaces and Dependencies

Use the existing Flask-Security `ExtendedLoginForm`, Flask-Login session marker,
Redis session backend, Python logging, and `wctl` tooling. Add no dependencies.

Revision note: Initial ExecPlan created from production evidence and operator
authorization on 2026-07-27 19:12 UTC.
