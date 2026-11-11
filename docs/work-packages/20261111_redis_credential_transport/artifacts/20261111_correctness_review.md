# Correctness review - Redis credential transport hardening

**Status**: Implementation review in progress; runtime acceptance pending
**Reviewer**: Codex independent reviewer `contract_correctness`
**Date opened**: 2026-11-11 UTC
**Last reviewed**: 2026-11-11 20:54 UTC
**Comparison**: working tree against M0 checkpoint `ca1034a2b`

## Required Valid States

Review each established logical DB and consumer: Redis lock/default, status DB
2, RQ DB 9, sessions/stream sessions DB 11, NoDb cache DB 13, README DB 14 and
log-level DB 15 where affected. Preserve credential-free local test fixtures only
where their explicit contract permits them.

## Review Checks

- [ ] Endpoint parsing preserves host, port, IPv6, TLS/query options and DB.
- [ ] Mounted-file precedence and legacy conflicts match the ratified matrix.
- [ ] Sync, async, session, RQ, status, preflight and streamauth use the intended
      DB and preserve timeouts/retries.
- [ ] Missing/wrong credentials fail explicitly without unauthenticated fallback.
- [ ] RQ queue names, counts, worker class, startup delay and registration remain
      unchanged.
- [ ] Redis restart, health and rollback do not flush or corrupt data.
- [ ] Focused tests exercise real AUTH rather than only mocks/miniredis.
- [ ] No full-suite success is required or claimed.

## Findings and Verdict

**Gate status: HOLD** while the open findings and real runtime acceptance below
remain outstanding. Findings were delivered promptly during implementation;
already corrected versions are identified separately.

1. **High, corrected — RQ adapter discarded caller pools.** The initial owned
   `Connection` ignored all constructor kwargs. Installed RQ WorkerPool rebuilds
   children with `connection_pool=...`; `wepppy/rq/webhook_hooks.py:132` also uses
   `type(job.connection)(connection_pool=...)` to enforce bounded notification
   I/O. Discarding that pool removed the timeout contract. Current
   `wepppy/config/rq_redis.py` uses an identity marker only for RQ-config
   construction and otherwise forwards normal args. A direct constructor probe
   confirmed supplied pool identity and its 0.25-second timeout are retained.
   The focused regression was added to `tests/test_redis_settings.py`.

2. **Medium, corrected — Python endpoint helpers re-emitted credential query
   options.** The initial helper validated query allowlists only when creating
   client kwargs, allowing `redis_url` to return `ssl_password` in an endpoint.
   Current ingestion performs shared query validation before endpoint emission;
   a direct probe now rejects the synthetic credential without printing it.
   Focused credential-query regression coverage was added.

3. **Medium, corrected — host-only environment input could inject URL fields.**
   `REDIS_HOST=cache?password=<canary>` initially bypassed ingestion checks in the
   environment-built URL path; `user@cache` also inserted userinfo. Current
   `wepppy/config/redis_settings.py` rejects host delimiters/whitespace while
   retaining IPv6. Focused host-only input cases were added.

4. **Medium, partial/open — native port fallback must preserve precedence.**
   The baseline sync/native helper used `REDIS_PORT` when a URL omitted its
   port, while session URL construction used Redis's normal 6379 default.
   Initial code dropped the native fallback. The follow-up restored it and
   added the absent-port regression, but currently calls
   `kwargs.setdefault('port', int(...))`: the default expression is evaluated
   even when the URL already supplies a port. An invalid ignored `REDIS_PORT`
   can therefore break an explicit valid URL and surface the input in a raw
   conversion error. Use a missing-key branch and constant error translation;
   test explicit URL precedence plus invalid fallback separately.

5. **Medium, open — Go parser admits malformed and explicit-empty states.**
   `services/streamauth/redis.go` currently delegates host/port checking entirely
   to go-redis. A direct Go caller confirmed acceptance of
   `redis://:@localhost/2` without a credential provider, port 0, port 99999 and
   `redis:///2` silently resolving localhost. The contract requires malformed
   input failure and permits password-free fixtures only without configured
   credential input. Validate TCP host/port and explicit empty password before
   parsing options; preserve valid Unix socket paths. Python already rejects
   these states.

## Review Evidence and Limits

Read installed RQ 2.12, redis-py 6.2 and go-redis 9.5.5 sources to compare
constructor, parser, credential-provider and worker-child behavior. Used local
constructor-only Python probes and a temporary Go caller with
`GOTOOLCHAIN=go1.25.8`. These probes made no Redis network connection and are not
real AUTH evidence. The default host Go toolchain attempted unavailable `go1.25`;
the cached explicit toolchain was used for the parser probe.

Review found the intended DB 11/0 streamauth clone behavior and existing
one-second auth timeout overrides retained. Python pool consumers now request
pool-specific TLS/Unix arguments. Their real connection behavior, all required
DBs, session expiry, worker registration/dequeue and preserved startup timing
still need the focused acceptance receipt.

Additional inventory was sent to the implementer: the operator-only
`scripts/redis_flush_rq_db.sh` environment bridge and the password-bearing CLI
example in `tools/perf/redis_nodb_cache_stress/README.md`. Confirm migration or
explicit disposition before claiming complete consumer coverage.

This review does not approve runtime completion, isolated Compose parity,
restart/rollback, deployment or the downstream F5 unblock checkpoint. No full
Python/frontend suite was run or claimed.
