# `wepp.cloud` Production Rollout Runbook

**Status**: Bearhive rehearsal active; production execution prohibited
**Production origin**: `https://wepp.cloud`
**Development/test origins**: Bearhive deployments
**State store**: Redis DB 11; preserve throughout rollout

This document is the production execution ledger. Operators update it during
the rollout with UTC timestamps, immutable image digests, rendered
configuration evidence, commands used, metric snapshots, canary results, and
the responsible operator. Chat history is not rollout evidence.

## Global Gates

- [x] ADR-0044 accepted for Bearhive rehearsal.
- [x] Contract checkpoint committed as standalone ancestor `9f52eb879`.
- [ ] Every blocking review finding closed and dispositioned.
- [ ] Migration-aware rescue image built, pinned by digest, and tested.
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
- [ ] Exercise concurrent tabs, logout/reset, and late-response fencing.
- [ ] Exercise rq-engine token minting before and after cookie adoption.
- [ ] Complete Safari, Firefox, Chromium, and Edge canaries.
- [ ] Rehearse activation and rescue-image recovery.

Evidence: `artifacts/bearhive_rehearsal_summary.md`. Unchecked gates remain
required; the private-run recorder probe was authorization-limited and is not
recorded as a pass.

## Phase 1 — Production Shadow Observation

Deploy read-only candidate classification to every `wepp.cloud` consumer while
retaining existing session selection and continuing to write `session`.

- [ ] Capture pre-deploy instance inventory and digest.
- [ ] Deploy shadow-capable web and rq-engine images.
- [ ] Verify every instance digest and rendered session configuration.
- [ ] Confirm all instances still write `session`.
- [ ] Observe for the ratified interval.
- [ ] Quantify recoverable, signed-missing, corrupt, and conflicting cases.
- [ ] Confirm metrics contain no credential or identity material.
- [ ] Approve, hold, or revise the migration contract from observed evidence.

Execution ledger:

| UTC | Operator | Action/command | Digest/config evidence | Result |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Phase 2 — Production Reader-First Deployment

Deploy active dual-read migration support everywhere while still writing the
legacy name. This phase must complete before the cookie-name activation.

- [ ] Deploy migration-aware rq-engine consumers.
- [ ] Deploy migration-aware web consumers.
- [ ] Verify every instance understands primary and legacy names.
- [ ] Verify every instance still writes `session`.
- [ ] Run authenticated, anonymous, private-run, and token-bridge canaries.
- [ ] Prove the pinned rescue image against current production configuration.
- [ ] Confirm no legacy-only process remains.

Execution ledger:

| UTC | Operator | Action/command | Digest/config evidence | Result |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Phase 3 — Production Cookie Activation

Activate `__Host-weppcloud_session` for all `wepp.cloud` web writers without
overlap with legacy-only processes. Do not stop, flush, copy, or rekey Redis.

- [ ] Record final go/no-go decision and operator.
- [ ] Verify exact cookie invariants: Secure, HttpOnly, Path `/`, no Domain.
- [ ] Activate the new writer configuration.
- [ ] Verify all web process digests and effective configuration.
- [ ] Confirm legacy SIDs retain the same Redis keys and payloads.
- [ ] Run first-request POST, recorder, heartbeat, CAP, OAuth, logout/reset,
      concurrent-tab, and rq-engine canaries.
- [ ] Confirm users with remember disabled retain valid active sessions.
- [ ] Observe all abort signals for the ratified interval.
- [ ] Declare activation healthy or execute the rescue procedure.

Execution ledger:

| UTC | Operator | Action/command | Digest/config evidence | Result |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Rescue Procedure

Rollback to a legacy-only image is prohibited after activation. Recovery uses
the pinned migration-aware rescue image and keeps the new cookie name active.

- [ ] Stop further promotion/change activity.
- [ ] Preserve Redis DB 11 and capture value-free health evidence.
- [ ] Replace affected services with the pinned rescue digest.
- [ ] Verify the rescue image reads both names and writes the new name.
- [ ] Run authentication, CSRF, logout, and rq-engine canaries.
- [ ] Record incident linkage, exact commands, timestamps, and results.

Pinned rescue digest:

    Pending

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
