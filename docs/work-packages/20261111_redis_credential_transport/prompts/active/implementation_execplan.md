# Remove Redis credentials from URLs and process arguments

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current, and update
this plan and `tracker.md` at every stopping point.

## Purpose / Big Picture

After this work, WEPPcloud's existing Redis password still comes from the same
mounted secret and authenticates the same services and logical databases, but it
is no longer copied into connection URLs or process arguments. An operator can
inspect rendered Compose, service configuration, process argv and sanitized logs
without finding the password. Sessions, RQ workers, status/preflight and their
health checks continue to work against a real password-protected Redis.

This package deliberately uses focused validation. It must finish before the
safe traceback/F5 package begins; F5 then runs the repository's full Python and
frontend gates.

## Progress

- [x] (2026-11-11 18:27 UTC) Inventory the confirmed Python, Go, RQ CLI,
      Redis-server and healthcheck secret URL/argv paths.
- [x] (2026-11-11 18:27 UTC) Scaffold package, tracker, contract/failure
      artifacts and independent review gates.
- [x] (2026-11-11 18:27 UTC) Record Redis-first ordering and the scoped-test
      waiver for this package.
- [ ] M0: ratify the transport contract and standalone checkpoint.
- [ ] M1: migrate Python native/session/async Redis clients.
- [ ] M2: migrate Go status/preflight/streamauth clients.
- [ ] M3: migrate RQ CLI, Redis server, healthchecks and operator helpers.
- [ ] M4: pass focused tests, real Compose acceptance and independent reviews.
- [ ] M5: record the checkpoint that unblocks F5.

## Surprises & Discoveries

- Observation: the repository already has both sides of the Python migration.
  `redis_connection_kwargs()` supplies separate password fields, while
  `redis_url()` reinserts the same password into cached URLs.
  Evidence: `wepppy/config/redis_settings.py`.

- Observation: RQ 2.12's CLI config path creates Redis with separate
  host/port/DB/password fields when `REDIS_URL` is absent. A small owned config
  module can preserve `worker-pool` without a fork or new dependency.
  Evidence: installed `rq.cli.helpers.get_redis_from_config`.

- Observation: F4 added shared streamauth clients on DBs 11 and 0 by cloning a
  parsed URL. The replacement must preserve those DBs and timeout/retry options.
  Evidence: `services/streamauth/auth.go`.

## Decision Log

- Decision: complete Redis credential transport before F5 implementation.
  Rationale: Roger selected this order so avoidable Redis credential strings are
  removed before traceback redaction is validated.
  Date/Author: 2026-11-11, Roger; recorded by Codex.

- Decision: focused validation replaces full pytest and npm gates for this
  package. Direct tests must cover every changed client/process/container
  boundary and an actual Compose Redis connection.
  Rationale: Roger explicitly requested scoped validation; broad suites will run
  in the dependent F5 package.
  Date/Author: 2026-11-11, Roger; recorded by Codex.

- Decision: preserve current secret lifecycle, password, default Redis user,
  logical DBs, topology and rotation behavior.
  Rationale: the task changes representation/transport, not authorization or
  secret management.
  Date/Author: 2026-11-11, Roger and Codex.

## Outcomes & Retrospective

No implementation outcome exists yet. Populate this section with exact
credential scans, connectivity evidence, compatibility limits and residual
deployment risk after each milestone.

## Context and Orientation

`wepppy/config/redis_settings.py` is the Python configuration hub. It accepts
endpoint URLs and a mounted password, but `redis_url()` combines them. Many
synchronous callers already use `redis_connection_kwargs()`, whereas Flask
sessions call `redis.from_url()` and some async callers request URLs.

The RQ worker startup script `docker/rq-worker-startup.sh` computes a
password-bearing URL, passes it as a Python argv for readiness and as `rq
worker-pool -u`. Development/HPC Compose files contain similar inline commands.
RQ's config mode can instead import an owned module that constructs separate
fields from the mounted secret.

status2, preflight2 and `services/streamauth` currently accept a `RedisURL` and
call go-redis `ParseURL`. Their installed go-redis version supports `Addr`,
`Username`, `Password`, `DB` and credential-provider fields. Preserve the
existing timeouts, retries and streamauth DB clones.

`docker/redis-entrypoint.sh` reads the file but passes its value through
`--requirepass`; healthchecks and docs use `redis-cli -a`. The proposed simplest
server path is a protected runtime ACL/config file representing the same default
user/password, referenced by filename. Ratify its quoting/hash, permissions,
restart and failure behavior before implementation.

## Plan of Work

### Milestone 0: Contract and consumer checkpoint

Create `docs/schemas/redis-credential-transport-contract.md`. Define a nonsecret
endpoint type (network, host, port, DB, TLS/query options) and a separately
resolved credential type. Define mounted-file precedence over legacy URL
userinfo, username handling, malformed/conflicting input behavior, logging and
string/repr rules. Inventory every URL, CLI, healthcheck and operator consumer;
disposition tests/fixtures separately from deployed paths.

Specify the RQ config module and Redis server ACL/config approach. Obtain
independent correctness/security/operations review and commit a standalone
checkpoint before code changes.

### Milestone 1: Python clients

Refactor `wepppy/config/redis_settings.py` so retained endpoint builders never
contain password userinfo. Provide sync and async constructor kwargs/pools,
including username, TLS/query options and explicit DB replacement. Convert Flask
session configuration and directly affected async clients. Legacy credential URL
input may be parsed once, but the secret is separated immediately and never
returned from a URL helper. Mounted-file credentials take ratified precedence.

Update focused tests in `tests/test_redis_settings.py`, session tests and direct
consumer modules. Add canary assertions against `repr`, exception and config
strings. Use a real password-protected Redis for sync/async/session round trips.

### Milestone 2: Go clients

Replace `Config.RedisURL` with a nonsecret endpoint plus a non-printing
credential field/provider in status2 and preflight2. Pass `redis.Options`
directly to service and streamauth constructors; clone options while changing
only DB 11/0 for auth state. Keep secret-file reads, timeouts and retry behavior.

Update config, server and streamauth tests. Use miniredis for deterministic
option/order cases and a real password-protected Redis for AUTH because miniredis
must not substitute for the changed authentication boundary. Assert string/error
rendering contains no canary.

### Milestone 3: RQ, Redis server and probes

Add a minimal owned RQ configuration module or launcher that reads the existing
secret file and exposes separate connection fields to RQ's config path. Update
the readiness probe and every dev/HPC/prod worker variant without changing queue
names/counts, classes, DB 9 or startup timing. Inspect actual worker argv.

Generate a protected runtime Redis ACL/config input for the same default-user
password and start Redis by file reference, not password argument. Fail closed on
missing/empty/unusable files and set restrictive permissions. Update healthchecks,
canary stacks and operator examples to avoid URL/`-a`/`--requirepass` password
arguments. Do not introduce new ACL identities or permissions.

### Milestone 4: Scoped acceptance and reviews

Run only focused tests named below and any directly added files. Render every
affected Compose variant and scan for the synthetic password. Start the canonical
development Redis and affected services with a unique canary password. Prove
authenticated PING, session set/get/expiry, RQ worker registration plus an
isolated harmless job, status/preflight health and streamauth DB access. Inspect
container process argv and sanitized logs. Wrong/missing credentials must fail.

Obtain independent correctness, QA, security and operations verdicts. Record the
exact revision and results as the checkpoint that permits F5 implementation. Do
not run or claim the full Python or npm suites.

## Concrete Steps

Work from `/home/workdir/wepppy`. Preserve unrelated dirty files. Re-run the
consumer inventory before editing:

    rg -n "redis://[^ ]*@|redis-cli -a|--requirepass|ParseURL\(|from_url\(" \
      docker wepppy services

Expected focused commands, refined to actual changed tests, are:

    wctl run-pytest tests/test_redis_settings.py
    wctl run-pytest tests/weppcloud/test_session_cookie_migration.py
    wctl run-pytest tests/docker/unit/test_rq_worker_startup_contract.py
    wctl run-status-tests
    wctl run-preflight-tests
    (cd services/streamauth && go test ./...)

Add direct tests for any new RQ config/launcher and Redis entrypoint helper. Run
rendered Compose validation and a service-scoped canonical development smoke;
record exact commands before execution. Do not run `wctl run-pytest tests
--maxfail=1`, `wctl run-npm lint` or `wctl run-npm test` for this package.

## Validation and Acceptance

Acceptance requires focused evidence that every deployed consumer authenticates
to its established DB; wrong/missing credentials fail; password-file values do
not appear in URLs, retained config, repr/error/log output, rendered Compose or
process argv; RQ workers register/dequeue; sessions round-trip; status/preflight
and streamauth retain their DB semantics; server restart and rollback work.

Fixtures or source scans alone cannot prove authentication. A green broad suite
is neither required nor a substitute for direct Redis/RQ/session/Go boundaries.

## Idempotence and Recovery

Configuration generation must be atomic, permissioned and repeatable. Never
overwrite the mounted secret. Before Compose mutation, retain rendered config and
known-good container/image mappings. If authentication/health fails, restore only
the affected local services; do not flush Redis, delete volumes, rotate the
password or cancel active jobs. Keep legacy ingestion until all confirmed
consumers are migrated and reviewed.

## Artifacts and Notes

- `artifacts/20261111_contract_decision.md`: proposed/ratified transport rules.
- `artifacts/20261111_failure_class_matrix.md`: consumer/variant inventory.
- `artifacts/20261111_correctness_review.md`: valid-state gate.
- `artifacts/20261111_security_review.md`: secret/auth gate.
- Add QA, operations and scoped validation receipts during execution.

## Interfaces and Dependencies

The final Python interface must expose nonsecret endpoint configuration and
separate sync/async client kwargs or constructors. The final Go interface must
accept or produce `redis.Options` without a secret-bearing `String` method. The
RQ adapter must use installed RQ config semantics. The Redis server helper may
use tools already present in the pinned image; a new binary/library requires the
dependency evaluation standard and an amended complexity decision.

## Revision Note

2026-11-11: Initial plan records the Redis-first order, focused-test waiver,
faithful current-auth behavior, no secret lifecycle/ACL redesign, and direct
Python/Go/RQ/server/health acceptance. No implementation or deployment occurred.
