# Migrate the WEPPcloud session cookie without user disruption

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`. The sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must
remain current.

## Purpose / Big Picture

After this change, deployments stop using the collision-prone generic
`session` browser cookie. Existing users keep their authenticated Redis session,
CSRF state, CAP state, and active workflow without logging out, clearing site
data, or signing in again. The first safe request automatically adopts the old
session and writes `__Host-weppcloud_session`; rq-engine continues working throughout
mixed-version rollout.

## Progress

- [x] (2026-08-23 21:45Z) Captured triggering HTTP and Redis evidence.
- [x] (2026-08-23 21:45Z) Drafted ADR-0044 and the proposed contract matrix.
- [x] (2026-08-23 21:45Z) Scaffolded package and initial regression-risk register.
- [x] (2026-08-23 22:30Z) Completed independent design reviews and recorded
  blocking findings in `artifacts/review_disposition.md`.
- [ ] Ratify revisions for ambiguity detection, logout fencing, and two-phase
  deployment/rollback before implementation.
- [ ] Obtain operator acceptance and commit the contract checkpoint ancestor.
- [ ] Implement shared parsing/selection and Flask/rq-engine adapters.
- [ ] Execute regression, mixed-version, rollback, browser, and canary gates.
- [ ] Close reviews and package.

## Surprises & Discoveries

- Observation: The corrected recorder transport and single-cookie public HTTPS
  path work; the remaining 400 is authenticated-session-specific.
  Evidence: Served bundle contains same-origin credentialed Fetch, and a
  controlled Bearhive request returned 204.

- Observation: Redis contains widespread remembered identities without CSRF
  session state and rapid creation of many SIDs for one identity.
  Evidence: 244 authenticated/no-CSRF sessions versus 11 authenticated/CSRF
  sessions during investigation.

- Observation: Flask/Werkzeug chooses the first duplicate cookie while
  Starlette's parsed cookie mapping chooses the last.
  Evidence: Framework probes and current adapters demonstrate divergent
  selection for the same raw Cookie header.

## Decision Log

- Decision: No migration step may require routine user logout, login, or site
  data clearing.
  Rationale: Deployment compatibility is an application responsibility and the
  canonical session contract prioritizes minimizing authentication friction.
  Date/Author: 2026-08-23 / WEPPcloud operator and Codex.

- Decision: Preserve the Redis SID and payload instead of copying session data.
  Rationale: Reissuing the same validated SID under a namespaced cookie retains
  all session semantics and minimizes mutation/race risk.
  Date/Author: 2026-08-23 / proposed by Codex, acceptance pending.

- Decision: Never resolve cross-identity ambiguity by cookie order.
  Rationale: Browser ordering is not an authentication authority and silent
  account switching is worse than a fail-closed recovery path.
  Date/Author: 2026-08-23 / proposed by Codex, acceptance pending.

- Decision: Skip invalid signatures, but never scan past the first correctly
  signed legacy SID, even if its Redis record is absent.
  Rationale: This recovers from unrelated parent-domain collisions without
  allowing a later valid cookie to undo explicit logout.
  Date/Author: 2026-08-23 / proposed by Codex, acceptance pending.

- Decision: Use `__Host-weppcloud_session` in production.
  Rationale: Browser-enforced Secure, host-only, root-path ownership prevents
  recurrence rather than relying only on a less-common name.
  Date/Author: 2026-08-23 / proposed by Codex, acceptance pending.

- Decision: `wepp.cloud` is the sole production rollout origin. Bearhive
  origins are development/test validation targets only.
  Rationale: Separate browser origins need no cross-origin session continuity;
  production controls should reflect the actual operator boundary.
  Date/Author: 2026-08-23 / WEPPcloud operator.

## Outcomes & Retrospective

Planning review found three blocking gaps: cross-principal duplicate handling,
logout/reset resurrection, and mixed-worker rollback safety. Proposed controls
are recorded in `artifacts/review_disposition.md`. No production implementation
has begun, and the package is not authorized for deployment.

## Context and Orientation

Flask stores only a signed session ID in the browser and stores the payload in
Redis DB 11 under `session:<sid>`. `wepppy/weppcloud/configuration.py` currently
leaves Flask's cookie name at `session`. The pinned Flask-Session interface reads
only one parsed cookie value. `wepppy/microservices/rq_engine/session_routes.py`
independently reads and unsigns the same cookie to mint run-scoped JWTs. Both
consumers must share the migration selection rules.

## Plan of Work

First ratify ADR-0044 and amend the session, CSRF, and token/lifecycle contracts
in a standalone checkpoint. Define a pure helper that extracts bounded,
duplicate-preserving exact-name cookie values, skips invalid signatures, and
treats the first signed SID as authoritative. Test the helper
without Flask or FastAPI.

Add a Flask-Session adapter, invoked before request hooks, that treats the
presence of `__Host-weppcloud_session` as authoritative, otherwise
loads the selected legacy SID into the existing Redis session class. Saving the
session naturally emits the new cookie. Add equivalent rq-engine selection for
the session-token bridge. Configure every relevant Compose service with the
same new/legacy names and add startup checks against drift.

Deploy reader support to every `wepp.cloud` web and rq-engine instance while
still writing `session`, then cut over all production web workers without
overlapping legacy-only and new Gunicorn generations. Prove the supported version
matrix and that rollback retains the migration reader. Finish with live
authenticated canaries in Safari, Chromium, and Firefox that exercise page
render, heartbeat, recorder, and rq-engine token mint without a login prompt.

## Concrete Steps

All commands run from `/home/workdir/wepppy`. Exact focused commands will be
finalized after review, with these minimum gates:

    wctl run-pytest tests/weppcloud/test_session_cookie_migration.py
    wctl run-pytest tests/weppcloud/test_configuration.py
    wctl run-pytest tests/weppcloud/test_auth_remember_cookie.py
    wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py
    wctl run-pytest tests/microservices/test_rq_engine_session_routes.py
    wctl run-npm test -- session_heartbeat recorder_interceptor
    wctl run-pytest tests --maxfail=1
    wctl run-npm test
    wctl run-npm lint

## Validation and Acceptance

Acceptance is user-observable continuity. An authenticated browser with a valid
legacy session and no remember token loads an existing run across deployment,
keeps the same Redis SID, receives the new cookie, posts heartbeat and recorder
events successfully, and mints an rq-engine token without navigation or login.
An invalidly signed collision does not break a later valid session, while a
signed-but-absent SID prevents onward fallback. Logout cannot revive a legacy
session. Rollback keeps both cookie populations usable.

## Idempotence and Recovery

Migration is idempotent because presence of the new cookie blocks downgrade and
the Redis SID is not copied. Repeated requests merely refresh the same session.
Rollback retains dual-read compatibility and does not delete either cookie.

## Artifacts and Notes

ADR-0044, the contract checkpoint, and the regression risk register are the
authoritative planning artifacts. `artifacts/rollout_runbook.md` is the
production execution ledger and must contain immutable digests, exact commands,
timestamps, evidence, and sign-offs as each phase executes.

## Interfaces and Dependencies

No new external dependency. Use the pinned ItsDangerous signer and Redis client
already used by Flask-Session and rq-engine. The shared selector must return an
explicit outcome and selected SID/payload without exposing raw cookie values in
logs or metrics. Framework adapters remain thin.
