# `wepp.cloud` Production Rollout Runbook

**Status**: Production owned-cookie writer active; observation in progress
**Production origin**: `https://wepp.cloud`
**Development/test origins**: Bearhive deployments
**State store**: Redis DB 11; preserve throughout rollout

This document is the production execution ledger. Operators update it during
the rollout with UTC timestamps, Git revisions, locally built image IDs, rendered
configuration evidence, commands used, metric snapshots, canary results, and
the responsible operator. Chat history is not rollout evidence.

## Global Gates

- [x] ADR-0044 accepted for Bearhive rehearsal.
- [x] Contract checkpoint committed as standalone ancestor `9f52eb879`.
- [ ] Every blocking review finding closed and dispositioned.
- [ ] Reader-first configuration recovery tested through
      `scripts/deploy-production.sh --targeted-web --no-flush-rq-db`. The
      packaged-image boot test is useful evidence, but it is not a deployment
      rehearsal.
- [ ] Production web and rq-engine instance inventory captured.
- [ ] Redis DB 11 connectivity and persistence verified; no flush/rekey planned.
- [x] Parser bounds, logout fence, payload failures, and duplicate semantics
      ratified.
- [ ] Focused, broad, browser, security, and mixed-version tests pass.
- [ ] Production baselines and abort thresholds recorded below.

No phase may begin while a preceding gate is incomplete.

## Production Inventory

| Component | Host/service | Count | Current digest | Config source | Target digest | Verified UTC/operator |
| --- | --- | ---: | --- | --- | --- | --- |
| Caddy/proxy | Pending inventory |  |  |  |  |  |
| WEPPcloud web | Pending inventory |  |  |  |  |  |
| rq-engine | Pending inventory |  |  |  |  |  |
| Redis session store | Pending inventory |  |  |  | unchanged |  |

Record signer-secret provenance without recording the secret. Confirm every
consumer targets the same intended Redis DB and session key prefix.

## Baselines and Abort Thresholds

| Signal | Pre-change baseline | Warning threshold | Abort/hold threshold | Evidence location |
| --- | ---: | ---: | ---: | --- |
| CSRF HTTP 400 rate |  |  |  |  |
| Authentication 401/403 rate |  |  |  |  |
| rq-engine session-token failures |  |  |  |  |
| Redis sessions created per minute |  |  |  |  |
| Legacy session adopted |  |  |  |  |
| Signed SID missing/corrupt |  |  |  |  |
| Cross-principal conflict |  |  |  |  |
| Session Redis errors |  |  |  |  |

Metrics and logs contain outcome enums, build/phase identity, and counts only.
They never contain cookies, SIDs, user IDs, CSRF values, or remember tokens.

## Phase 0 — Bearhive Rehearsal

- [x] Deploy the candidate to development/test only.
- [x] Exercise invalid-before-valid duplicate legacy cookies.
- [ ] Exercise same-principal and cross-principal live candidates.
- [ ] Exercise first-request form and `X-CSRFToken` POSTs.
- [ ] Preserve anonymous CAP and in-flight OAuth state.
- [x] Exercise concurrent tabs, logout/reset, and late-response fencing.
- [ ] Exercise rq-engine token minting before and after cookie adoption.
- [ ] Complete Safari, Firefox, Chromium, and Edge canaries.
- [ ] Rehearse recovery from the migration-aware Git revision using
      `scripts/deploy-production.sh` and the installed `wctl` preset.

Evidence: `artifacts/bearhive_rehearsal_summary.md`. Unchecked gates remain
required; the private-run recorder probe was authorization-limited and is not
recorded as a pass.

## Phase 1 — Production Reader-First Deployment

Deploy the migration-aware code to `wepp1` while continuing to write `session`.
Only `weppcloud` and `rq-engine` consume browser sessions; `wepp2` and `wepp3`
are outside this rollout and remain untouched.

- [x] Verify host identity, clean Git state, effective full-stack topology, and
      current `weppcloud`/`rq-engine` container IDs.
- [x] Confirm the production profile is reader-first: writer `session`, primary
      reader `__Host-weppcloud_session`, legacy reader `session`, migration on.
- [x] Pull and deploy with
      `./scripts/deploy-production.sh --targeted-web --no-flush-rq-db`.
- [x] Prove Redis, PostgreSQL, Caddy, scheduler, and every RQ worker retained
      their pre-deploy container IDs and active jobs were not interrupted.
- [x] Verify both rebuilt services use the expected Git revision and effective
      reader-first configuration.
- [ ] Run authenticated, anonymous, private-run, CSRF, and token-bridge
      canaries, then observe for the ratified interval.
- [ ] Quantify recoverable, signed-missing, corrupt, and conflicting cases.
- [ ] Confirm metrics contain no credential or identity material.
- [ ] Approve or hold activation from observed evidence.

Execution ledger:

| UTC | Operator | Action/command | Digest/config evidence | Result |
| --- | --- | --- | --- | --- |
| 2026-08-24 20:14–20:24Z | Codex, explicit operator approval | HTTPS fast-forward; `./scripts/deploy-production.sh --targeted-web --skip-pull --no-flush-rq-db` | Git `c4f509634`; writer `session`; primary `__Host-weppcloud_session`; legacy `session`; migration enabled | Targeted deployment passed. Web/rq-engine rotated; workers, Redis, PostgreSQL, Caddy, and scheduler IDs unchanged. Public health passed after transient rq-engine startup 502. Production canaries and observation remain. |

## Phase 2 — Production Cookie Activation

Activate `__Host-weppcloud_session` for all `wepp.cloud` web writers without
overlap with legacy-only processes. Do not stop, flush, copy, or rekey Redis.

- [x] Record final go/no-go decision and operator.
- [x] Verify exact cookie invariants: Secure, HttpOnly, Path `/`, no Domain.
- [x] Change only the wepp1 writer setting to
      `SESSION_COOKIE_NAME=__Host-weppcloud_session`.
- [x] Deploy with
      `./scripts/deploy-production.sh --targeted-web --skip-pull --no-flush-rq-db`.
- [x] Prove non-target service container IDs did not change.
- [x] Verify all web process digests and effective configuration.
- [ ] Confirm legacy SIDs retain the same Redis keys and payloads.
- [ ] Run first-request POST, recorder, heartbeat, CAP, OAuth, logout/reset,
      concurrent-tab, and rq-engine canaries.
- [ ] Confirm users with remember disabled retain valid active sessions.
- [ ] Observe all abort signals for the ratified interval.
- [x] Declare activation healthy or execute the rescue procedure.

Execution ledger:

| UTC | Operator | Action/command | Digest/config evidence | Result |
| --- | --- | --- | --- | --- |
| 2026-08-25 02:13–02:20Z | Codex, operator-approved activation | Set only `SESSION_COOKIE_NAME=__Host-weppcloud_session`; `./scripts/deploy-production.sh --targeted-web --skip-pull --no-flush-rq-db` | Git `c4f509634`; writer/primary `__Host-weppcloud_session`; legacy `session`; migration enabled; image `sha256:4ad919f8edcc0c94fe88e3ef36c099235826843dc4f36f70003dcaa20c6b1c98` | Activation passed. Only web/rq-engine rotated; every non-target container ID remained unchanged. Web and rq-engine returned HTTP 200 after the bounded rq-engine startup delay. Immediate session/CSRF/Redis/5xx signals were zero. |
| 2026-08-25 02:20–02:29Z | WEPPcloud operator and Codex | Existing-session production browser canary and post-canary log review | Hard refresh retained authentication; owned cookie present; heartbeat HTTP 204; recorder and rq-engine functional; cross-tab logout propagated; 2/2 observed session-token mints returned HTTP 200 | Critical continuity canaries passed without logout, login, or site-data clearing. Zero CSRF, conflict, Redis-session, or severe errors. One cross-tab logout-time migration rejection was duplicated across two log handlers; fencing succeeded, but the production formatter omitted its rejection class. |
| 2026-08-25 02:29Z | WEPPcloud operator | Fresh authentication canary | Local and OAuth login functional with the owned-cookie writer | Activation declared healthy. Continue dual-reading and review telemetry/legacy usage at 2026-08-26 02:20Z before any retirement decision. |

## Recovery Procedure

The first recovery action is configuration rollback, not source rollback.
Restore the reader-first writer value `session` while keeping migration enabled
and both readers configured. Browsers carrying either cookie remain usable and
retain the same Redis SID. A legacy-only source revision is prohibited after
activation.

- [ ] Stop further promotion/change activity.
- [ ] Preserve Redis DB 11 and capture value-free health evidence.
- [ ] Record the current production Git revision and effective cookie profile.
- [ ] Restore `SESSION_COOKIE_NAME=session` without changing the primary or
      legacy reader settings.
- [ ] Run
      `./scripts/deploy-production.sh --targeted-web --skip-pull --no-flush-rq-db`.
- [ ] Verify both names remain readable, responses write `session`, and all
      non-target services retained their container IDs.
- [ ] Run authentication, CSRF, logout, and rq-engine canaries.
- [ ] Record incident linkage, exact commands, timestamps, and results.

If the application code itself must be recovered, deploy only a reviewed,
migration-aware Git revision through the same targeted mode. Keep the desired
reader-first or activated cookie profile explicit. Never deploy legacy-only
code once any browser may hold only the owned cookie.

Known migration-aware revision:

    Git commit: 42cf8319625a
    Deploy entry point: ./scripts/deploy-production.sh --targeted-web
    Required Redis policy: --no-flush-rq-db

Bearhive packaged-image boot test, 2026-08-24 18:39Z–18:52Z:

- Built the production Dockerfile as `wepppy:session-rescue-42cf8319625a`.
- Replaced only web and rq-engine with the final rescue image using
  `--no-build --no-deps --force-recreate`; Redis was not restarted during the
  successful attempt and DB 11 remained populated.
- Confirmed both services used the pinned image ID, had no source-tree bind
  mount, read both cookie names, and wrote `__Host-weppcloud_session`.
- Passed web/rq health, authenticated profile, CSRF-backed login/logout,
  remember opt-out, and direct rq-engine session-token canaries (3 Playwright
  tests passed).
- Restored the normal activated Bearhive deployment with a targeted,
  dependency-free web/rq-engine recreation.

Two failed attempts exposed and corrected image packaging defects before the
successful boot test: runtime source ownership prevented the entrypoint bundle
build, and excluding all documentation omitted ADR files required by feature
registry startup validation. The first command also demonstrated that
`--force-recreate` without `--no-deps` unnecessarily recreates Redis and
Postgres. Neither command is a deployment precedent; the existing production
deploy script owns service sequencing and Redis persistence policy.

## Phase 4 — Observation and Legacy Retirement

The retirement clock starts only after the final legacy writer is removed from
`wepp.cloud`. Legacy reading remains through at least the 12-hour inactivity TTL
plus the ratified deployment and observation margin.

- [ ] Record retirement-clock start in UTC.
- [ ] Meet the ratified zero/near-zero legacy-adoption threshold.
- [ ] Confirm no supported client or service depends on the generic name.
- [ ] Open a separate reviewed retirement change.
- [ ] Remove legacy reading and migration-only telemetry.
- [ ] Confirm `__Host-weppcloud_session` is the sole production session cookie.
- [ ] Archive this ExecPlan and complete the final validation summary.

## Final Sign-Off

| Role | Name | Decision | UTC | Evidence |
| --- | --- | --- | --- | --- |
| Production operator |  |  |  |  |
| Correctness reviewer |  |  |  |  |
| Security reviewer |  |  |  |  |
| Operations reviewer |  |  |  |  |
| UX/governance reviewer |  |  |  |  |
