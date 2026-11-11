# Tracker - Redis credential transport hardening

## Quick Status

**Timezone**: UTC
**Started**: 2026-11-11 18:27 UTC
**Current phase**: Complete — F5 prerequisite checkpoint PASS
**Last updated**: 2026-11-11 21:15 UTC
**Next milestone**: dependent F5 implementation (separate package)
**Security impact**: high
**Starting revision**: `f0df22e5f8d2ae6255c6aa0e718394ad69a41b51`
**Security artifact**: `artifacts/20261111_security_review.md`

This package runs first. It uses focused validation only and must reach scoped
acceptance before F5 implementation begins. Code and isolated acceptance are complete; no production deployment occurred.
The incidental shared-dev Redis recreation is recorded below.

## Task Board

- [x] Confirm current Python, Go, RQ, Redis-server and healthcheck
      credential-bearing URL/argv paths.
- [x] Scaffold package, active ExecPlan, contract, failure matrix and reviews.
- [x] Record the operator's focused-validation decision and package ordering.
- [x] M0: ratify endpoint/credential types, legacy URL precedence, RQ adapter,
      Redis ACL/config file and healthcheck behavior.
- [x] M1: convert Python native/session/async consumers with focused tests.
- [x] M2: convert status2/preflight2/streamauth Go clients with focused tests.
- [x] M3: convert RQ startup, server entrypoint, healthchecks and operator helpers.
- [x] M4: run scoped unit/integration/Compose acceptance and independent reviews.
- [x] M5: publish the reviewed checkpoint that unblocks F5.

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

- [x] Contract and failure matrix accepted.
- [x] Correctness review passed.
- [x] QA review passed.
- [x] Dedicated security review passed.
- [x] Operations/rollback review passed.
- [x] Focused validation and actual Compose smoke pass.
- [x] F5 unblock checkpoint recorded.

## Timeline

- 2026-11-11 18:27 UTC: scaffold and record order/test scope.
- 2026-11-11 UTC: M0 ratified and committed as `ca1034a2b`.
- 2026-11-11 UTC: M1-M3 implemented and committed as `db7ef7cb7`.
- 2026-11-11 UTC: M4/M5 scoped acceptance and all independent reviews PASS; F5 unblocked.

## Handoff

Execution is complete; see `prompts/completed/implementation_execplan.md`.
Preserve unrelated dirty files. F5 may start from the recorded green scoped
checkpoint. Do not claim full-suite coverage or production deployment.

## M0 execution receipt — 2026-11-11 UTC

Canonical contract: `docs/schemas/redis-credential-transport-contract.md`.
Independent M0 correctness, security and operations artifacts pass. Contract
lint passes. Standalone ancestor commit contains documentation only; existing
unrelated changes are excluded. RQ adapter/empty --url, streamauth own timeouts,
LF file framing and explicitly isolated Compose inputs are required.

## Execution update — 2026-11-11 21:02 UTC

M1-M3 implemented. Initial isolated real AUTH, session expiry, RQ registration
and job result 42, Go health, dashboard, ACL permissions, wrong/missing inputs,
restart and baseline rollback/candidate restore pass. Seven Compose variants
render and contain no synthetic password. Pinned Alpine Redis authenticates and
retains explicitly disabled snapshots. Focused Python/Go tests and final
independent re-review are still running; F5 remains blocked until M5.

The Go wrapper unexpectedly recreated shared dev Redis at 20:45:58 UTC. It is
healthy with original password/data/image and native AUTH succeeds. No prior
state snapshot exists; no zero-interruption claim is made. Further builders use
--no-deps. See operations review for the candid event record.

## Final checkpoint — 2026-11-11 UTC

Complete at implementation `db7ef7cb7`; all four independent verdicts PASS.
See `artifacts/20261111_f5_unblock_checkpoint.md` and final JSON receipts.
F5 is unblocked. No production rollout or uninterrupted shared-dev workload
claim is made. The isolated validation stack is cleaned up after evidence
retention; existing caches, volumes and shared services are preserved.
