# Correctness review - Redis credential transport hardening

**Status**: PASS — implementation and scoped candidate environment acceptance
**Reviewer**: Codex independent reviewer `contract_correctness`
**Date opened**: 2026-11-11 UTC
**Last reviewed**: 2026-11-11 UTC, candidate `db7ef7cb7`
**Comparison**: candidate `db7ef7cb7` against M0 checkpoint `ca1034a2b`

## Required Valid States

Review each established logical DB and consumer: Redis lock/default, status DB
2, RQ DB 9, sessions/stream sessions DB 11, NoDb cache DB 13, README DB 14 and
log-level DB 15 where affected. Preserve credential-free local test fixtures only
where their explicit contract permits them.

## Review Checks

- [x] Endpoint parsing preserves host, port, IPv6, TLS/query options and DB.
- [x] Mounted-file precedence and legacy conflicts match the ratified matrix.
- [x] Sync, async, session, RQ, status, preflight and streamauth use the intended
      DB and preserve timeouts/retries.
- [x] Missing/wrong credentials fail explicitly without unauthenticated fallback.
- [x] RQ queue names, counts, worker class, startup delay and registration remain
      unchanged.
- [x] Isolated Redis restart/rollback retain the acceptance marker and authenticate.
- [x] Focused tests exercise real AUTH rather than only mocks/miniredis.
- [x] No full-suite success is required or claimed.

## Findings and Verdict

**Implementation and scoped environment gates: PASS** for
`db7ef7cb7e1d05400b6acca333526dfe80c7b417`. Findings were delivered promptly during
implementation; all five source findings below are corrected. This verdict
supports the package's focused F5 prerequisite, subject to the independent QA,
security and operations gates. It does not authorize production deployment.

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

4. **Medium, corrected — native port fallback must preserve precedence.**
   The baseline sync/native helper used `REDIS_PORT` when a URL omitted its
   port, while session URL construction used Redis's normal 6379 default.
   Initial code dropped the native fallback. The follow-up restored it and
   added the absent-port regression. The first follow-up used an eagerly
   evaluated `setdefault` default, which still parsed an ignored invalid
   environment port. The final candidate uses an explicit missing-key branch
   and `_environment_port` with a constant error. A direct reviewer probe
   confirmed explicit port 6380 survives an invalid environment port through
   both native kwargs and installed RQ config construction. Focused regression
   coverage retains the session/native fallback distinction.

5. **Medium, corrected — Go parser admitted malformed and explicit-empty states.**
   Initial `services/streamauth/redis.go` delegated host/port checking entirely
   to go-redis. A direct Go caller confirmed acceptance of
   `redis://:@localhost/2` without a credential provider, port 0, port 99999 and
   `redis:///2` silently resolving localhost. The contract requires malformed
   input failure and permits password-free fixtures only without configured
   credential input. The final candidate validates TCP scheme/host/port and
   explicit empty password before parsing options, and retains Unix path
   support. `TestMalformedRedisEndpoints` retains all four cases and a forbidden
   credential query. The focused Go receipt records the passing parser tests.

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

Additional operator consumers were repaired: the DB9 flush helper uses the
reviewed file-reader and ephemeral child environment; the performance harness
uses native kwargs and normalizes retained endpoint output; the deployment
registration probe uses canonical native kwargs. The standalone dormant
dashboard launcher is explicitly excluded from deployed acceptance in the
failure-class matrix; it is not claimed as a validated deployment path.

## Candidate receipt re-review

Independently read the committed direct client probe and nonsecret private
receipts under `/tmp/wepppy-redis-transport-acceptance`, checking every displayed
receipt against the synthetic canary in memory first. The initial receipt
confirms native AUTH/set/get on DBs 0,2,9,11,13,14,15; async PubSub; migrating
Flask session round trip/expiry; six default workers and job result 42; Go health;
dashboard HTTP; and wrong/absent password plus missing-file rejection. Seven
Compose variants have render/scan receipts. Protected ACL readback, wrong
probe/server-file cases, same-data restart and baseline rollback/candidate
restore are recorded. Reviewer did not repeat live service mutations.

The final private `final-candidate.json` binds the exact committed revision and
records the rebuilt Go service image IDs and relevant users. Independently
checked its canary absence and the matching `final-client.log`: six workers
registered and fresh job `2c42074f-f19b-49c4-b26a-73f24fbb7267` returned 42 after
the restart/rollback sequence. All seven sync DBs, async PubSub, session expiry,
Go health and dashboard HTTP passed again. This closes the intermediate receipt's
zero-worker uncertainty for the final acceptance state; it does not assert that
workers recovered without orchestration or interruption.

`final-negative-services.json` records status/preflight wrong and missing
credentials exiting 1, production RQ startup with wrong credentials exiting 1,
and Redis private ACL write failure exiting 1. `final-candidate.json` records
argv/config/log scans passing for the five running service containers and the
preserved Redis umask 0022. Read those receipts directly without exposing their
credential inputs. Together with the focused Go real-AUTH and Python receipts,
the named scoped acceptance conditions are satisfied.

The shared development Redis recreation is disclosed in the operations artifact.
Without a pre-event workload snapshot, no zero-interruption or unchanged-job
claim is approved. Production deployment and production identity/mount parity
remain separate. No full Python/frontend suite was run or claimed.

Residual coverage limits: real authentication used the current TCP/default-user
Compose topology; TLS and Unix options have parser/constructor coverage. The
dormant standalone dashboard remains explicitly outside deployed acceptance.
Snapshot retention proves the isolated test marker survived; it is not a proof
of historical shared-development workload continuity. Doc lint for this review
artifact passes with zero errors/warnings.
