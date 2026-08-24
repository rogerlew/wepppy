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
- [x] (2026-08-23 23:15Z) Ratified ambiguity detection, logout fencing, and
  two-phase deployment/rollback for Bearhive rehearsal implementation.
- [x] (2026-08-23 23:30Z) Committed the ratified contract checkpoint as
  `9f52eb879`.
- [x] (2026-08-24 00:35Z) Implemented bounded shared selection, Flask and
  rq-engine adapters, logout fencing, token revocation, and authentication SID
  rotation.
- [x] (2026-08-24 00:45Z) Deployed the migration configuration to Bearhive web
  and rq-engine services without restarting Redis or workers; health and live
  duplicate-legacy adoption passed.
- [ ] Execute regression, mixed-version, rollback, browser, and canary gates.
- [x] (2026-08-24 02:05Z) Passed the repository-wide Python suite (6,684
  passed, 63 skipped), frontend suite (105 suites/773 tests), lint, stub, broad
  exception, and documentation gates.
- [x] (2026-08-24 02:05Z) Closed independent security and QA code gates for
  Bearhive rehearsal; production evidence gates remain open.
- [x] (2026-08-24 17:20Z) Passed live logout/reset, concurrent-tab propagation,
  and a controlled late-response race against Bearhive Redis.
- [x] (2026-08-24 18:15Z) Passed Bearhive reader-first to owned-writer
  activation with identical SID, authenticated/CSRF continuity, and no Redis or
  worker restart.
- [x] (2026-08-24 18:25Z) Closed activation review defects by retiring a
  distinct owned primary during reader-first invalidation/rotation, routing
  rq-engine project cookie auth through the shared selector, enforcing SID
  tombstones on project session tokens, gating the one-time smoke canary, and
  wiring production/HPC Compose parity.
- [x] (2026-08-24 18:30Z) Passed the direct rq-engine cookie-authenticated
  session-token mint on the private Bearhive rehearsal run (HTTP 200 and scoped
  browse cookie issued).
- [x] (2026-08-24 18:52Z) Built and boot-tested packaged image
  `sha256:cad002e6aa36e79bfecb48475abe876eaac8b90cf901bc5796fa1d73950e4b18`
  from commit `42cf8319625a`. Both services ran without source binds and passed
  health, authentication/logout, remember opt-out, and direct rq-engine mint
  canaries. The test corrected image source ownership and required-ADR
  packaging, then restored the normal Bearhive deployment.
- [ ] Rehearse rollback from the migration-aware Git revision through
  `scripts/deploy-production.sh --targeted-web`. The ad hoc Compose image boot
  does not satisfy this gate and must not be treated as a production deployment
  precedent.
- [x] (2026-08-24 19:55Z) Rehearsed `--targeted-web` reader-first deployment on
  forest1. Only `weppcloud` and `rq-engine` rotated; workers, Redis, PostgreSQL,
  Caddy, and scheduler retained their exact container IDs. Both public health
  endpoints passed and effective configuration remained reader-first.
- [x] (2026-08-24 20:24Z) Deployed reader-first revision `c4f509634` to wepp1
  with targeted web mode after explicit approval to proceed alongside three
  active jobs. Only `weppcloud` and `rq-engine` rotated; both worker services,
  Redis, PostgreSQL, Caddy, and scheduler retained their container IDs. Both
  public health endpoints passed and both consumers report the reader-first
  profile.

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

- Observation: Logout fencing must cover derivative session JWTs, not only the
  Redis session payload, because issued run tokens can remain valid for four
  days.
  Evidence: Security review traced `token_class=session` authorization paths;
  the implementation now checks the SID tombstone centrally.

- Observation: Building `weppcloud` and `rq-engine` together starts two builds
  that race to publish the same `wepppy:latest` tag.
  Evidence: The first forest1 targeted rehearsal produced two image IDs while
  both recreated services ultimately used one shared image. Targeted mode now
  builds the shared image once through `weppcloud`.

- Observation: rq-engine needs the same bounded post-recreation health retry as
  WEPPcloud.
  Evidence: The first production probe returned HTTP 502 while Uvicorn workers
  started; the endpoint returned HTTP 200 about six seconds later. The deploy
  script now retries rq-engine health for the existing bounded interval.

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

- Decision: Rotate the SID atomically when an anonymous session becomes
  authenticated, and retain the old SID tombstone for four days.
  Rationale: Migration must not turn a sibling-origin signed anonymous SID into
  a session-fixation primitive, and logout must invalidate every derivative
  session JWT for its maximum lifetime.
  Date/Author: 2026-08-24 / Codex, after independent security review.

- Decision: Configure primary read precedence independently from the cookie
  writer during staged rollout.
  Rationale: Reader-first deployment must prefer an already-present owned
  cookie while continuing to write the legacy name; coupling read priority to
  the writer makes the ratified two-phase sequence impossible and can downgrade
  browsers that already carry both names.
  Date/Author: 2026-08-24 / Codex, discovered during Bearhive activation rehearsal.

- Decision: Deploy this browser-session change only to `wepp1` and recreate
  only `weppcloud` and `rq-engine`.
  Rationale: Those are the only production services that consume browser
  session cookies. Deploying worker-only `wepp2` or fork/archive-only `wepp3`,
  or restarting unrelated wepp1 services, adds risk without exercising the
  changed boundary.
  Date/Author: 2026-08-24 / WEPPcloud operator and Codex.

## Outcomes & Retrospective

Bearhive now runs the dual-read, primary-write configuration. Focused Python
tests, the repository-wide regression suite, frontend tests, health checks, and
a live duplicate legacy-cookie adoption probe pass. Cross-principal ambiguity,
over-bound remembered-login recovery, logout/reset resurrection,
derivative session-token revocation, and authentication fixation controls are
implemented. Production remains untouched; authenticated browser canaries and
mixed-version/rollback rehearsal evidence remain before a production gate.

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

Add a guarded `--targeted-web` mode to `scripts/deploy-production.sh`. It must
retain the script's safe fast-forward pull, local no-cache build, static asset
build, retries, and health checks, but replace only `weppcloud` and `rq-engine`
with `docker compose up -d --no-deps --force-recreate`. It must reject worker-only
topologies and Redis flushing, and it must leave every other service running.

Deploy reader support on `wepp1` while still writing `session`, then change only
the writer configuration and repeat the targeted deployment. Do not deploy
wepp2 or wepp3. Prove the supported version matrix and that restoring the
reader-first writer configuration retains both cookie populations. Finish with live
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
The first rollback is configuration-only: restore `SESSION_COOKIE_NAME=session`
and run the targeted deploy with `--skip-pull --no-flush-rq-db`. Source recovery
may use only a known migration-aware revision and the same targeted mode.

## Artifacts and Notes

ADR-0044, the contract checkpoint, and the regression risk register are the
authoritative planning artifacts. `artifacts/rollout_runbook.md` is the
production execution ledger and must contain exact Git revisions, local image
IDs, commands, timestamps, evidence, and sign-offs as each phase executes.

## Interfaces and Dependencies

No new external dependency. Use the pinned ItsDangerous signer and Redis client
already used by Flask-Session and rq-engine. The shared selector must return an
explicit outcome and selected SID/payload without exposing raw cookie values in
logs or metrics. Framework adapters remain thin.
