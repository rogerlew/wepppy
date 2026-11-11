# Tracker - Redis credential transport hardening

## Quick Status

**Timezone**: UTC
**Started**: 2026-11-11 18:27 UTC
**Current phase**: M0 contract and inventory checkpoint pending
**Last updated**: 2026-11-11 18:27 UTC
**Next milestone**: ratify transport/legacy/server decisions
**Security impact**: high
**Starting revision**: `f0df22e5f8d2ae6255c6aa0e718394ad69a41b51`
**Security artifact**: `artifacts/20261111_security_review.md`

This package runs first. It uses focused validation only and must reach scoped
acceptance before F5 implementation begins. No code, configuration, secret,
service or deployment change has occurred.

## Task Board

- [x] Confirm current Python, Go, RQ, Redis-server and healthcheck
      credential-bearing URL/argv paths.
- [x] Scaffold package, active ExecPlan, contract, failure matrix and reviews.
- [x] Record the operator's focused-validation decision and package ordering.
- [ ] M0: ratify endpoint/credential types, legacy URL precedence, RQ adapter,
      Redis ACL/config file and healthcheck behavior.
- [ ] M1: convert Python native/session/async consumers with focused tests.
- [ ] M2: convert status2/preflight2/streamauth Go clients with focused tests.
- [ ] M3: convert RQ startup, server entrypoint, healthchecks and operator helpers.
- [ ] M4: run scoped unit/integration/Compose acceptance and independent reviews.
- [ ] M5: publish the reviewed checkpoint that unblocks F5.

## Confirmed Starting Evidence

- `redis_settings.redis_url()` inserts the password into a URL and caches derived
  URLs; `redis_connection_kwargs()` already proves separate fields are possible.
- Flask sessions still call `redis.from_url(...)`.
- status2, preflight2 and streamauth call `redis.ParseURL` after their configs
  inject the password into `RedisURL`.
- development/HPC RQ worker commands build `redis://:password@...` and pass it
  with `-u`; production startup also computes a secret-bearing URL for probe and
  CLI worker-pool use.
- Redis starts with `--requirepass <password>` and healthchecks/documented
  operator commands use `redis-cli -a <password>`.
- RQ 2.12 already supports a config-based Redis constructor with distinct
  host/port/DB/password fields, so no RQ fork or new dependency is presumed.

## Decisions

- Operator decision (2026-11-11): execute this package before F5 and use scoped
  validation rather than full pytest/npm gates.
- Preserve current password values, mounted secret lifecycle, logical DBs,
  default user, topology, persistence and rotation behavior.
- Remove credentials from URLs and argv; do not substitute a different
  long-lived plaintext environment variable.
- Prefer existing client constructor fields/providers and RQ config loading.
- Keep legacy credential-bearing URL input only as a transition contract if
  needed; never retain or re-emit its userinfo.
- Redis ACL authorization redesign is out of scope. A protected generated ACL
  file may represent the same default-user password without argv exposure.
- F5 is a strict downstream package, not a parallel implementation.

## Focused Validation Matrix

| Boundary | Required positive case | Required negative/security case |
| --- | --- | --- |
| Python config | File password authenticates correct DB through kwargs | Endpoint/diagnostic contains no password or userinfo |
| Flask session | Set/get/expiry survives | Wrong/missing secret fails explicitly |
| Async client | Authenticated PING/PubSub on expected DB | No secret-bearing URL retained |
| Go services | status/preflight/streamauth connect through `Options` | Config/log/error/argv contains no canary |
| RQ startup | Probe and worker registration/dequeue succeed | `/proc` argv and rendered command lack canary |
| Redis server | Default password authenticates after restart | server argv/config output lacks raw canary |
| Health/operator probe | PING succeeds through reviewed file path | no `-a`, URL userinfo or retained output secret |
| Legacy URL | explicit compatible input normalizes once | mounted-file conflict follows ratified precedence |

## Risks

- Redis-wide outage from omitted password/DB/TLS option: direct real-client and
  Compose tests plus rollback to reviewed images/config.
- RQ workers connect to DB 0 instead of DB 9: assert connection kwargs, worker
  registration and isolated queue execution.
- ACL/config quoting changes accepted password: prefer a password hash in a
  protected ACL file and test punctuation/newline policy explicitly.
- A compatibility fallback recreates secret URLs: source/rendered/argv/log scans
  are blocking tests.
- Scoped tests miss unrelated regressions: accepted operator tradeoff; F5 later
  runs the full suite after this package is complete.

## Review Gates

- [ ] Contract and failure matrix accepted.
- [ ] Correctness review passed.
- [ ] QA review passed.
- [ ] Dedicated security review passed.
- [ ] Operations/rollback review passed.
- [ ] Focused validation and actual Compose smoke pass.
- [ ] F5 unblock checkpoint recorded.

## Timeline

- 2026-11-11 18:27 UTC: scaffold and record order/test scope.
- Pending: M0 contract checkpoint.
- Pending: M1-M3 implementation.
- Pending: M4 scoped acceptance and reviews.

## Handoff

Continue from `prompts/active/implementation_execplan.md`. Preserve unrelated
dirty files. Do not start F5 implementation until this tracker records a green
scoped checkpoint. Do not claim full-suite coverage or production deployment.
