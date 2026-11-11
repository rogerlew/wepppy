# Redis transport scoped validation receipt

Status: initial acceptance passed; final candidate revision/re-review pending.
Date: 2026-11-11 UTC. Ancestor contract: `ca1034a2b`.

## Focused tests

`wctl run-pytest tests/test_redis_settings.py tests/weppcloud/test_configuration.py tests/weppcloud/test_session_cookie_migration.py tests/docker/unit/test_rq_worker_startup_contract.py tests/docker/unit/test_redis_password_transport.py tests/docker/test_canary_smoke_contract.py tools/wctl2/tests/test_rq_info_command.py tests/nodb/test_base_unit.py tests/nodb/test_base_misc.py tests/scripts/test_deploy_production_execution.py tests/scripts/test_deploy_production_plan.py --maxfail=1`

Result: 255 passed, 1 skipped (Docker unavailable inside the application
container), 4 dependency deprecation warnings. Seven host-side Compose renders
cover that skipped rendering boundary. No full Python/npm suites were run.

`wctl run --rm --no-deps status-build sh -lc 'cd /workspace/services/status2 && PATH=/usr/local/go/bin:$PATH go test -tags=integration ./...'`

`wctl run --rm --no-deps preflight-build sh -lc 'cd /workspace/services/preflight2 && PATH=/usr/local/go/bin:$PATH go test -tags=integration ./...'`

Both pass, including stream authorization integration tests. Isolated builder
`go test -v ./...` in `/workspace/services/streamauth` explicitly ran and passed
`TestRealRedisTransport`, not a skipped/miniredis substitute. Config parsing,
credential-provider rendering and malformed endpoints pass.

Broad exception changed-file enforcement against `ca1034a2b`: PASS, zero new
broad catches. Initial line-shift false positives disappeared when mechanical
pool-call edits retained existing line structure. `git diff --check`: PASS.

## Isolated canonical Compose acceptance

Private model and raw receipts live under
`/tmp/wepppy-redis-transport-acceptance` (directory 0700). Do not publish its
credential/config files. The model is derived from `wctl config --format json`,
retains service users, entrypoints and mount structure, replaces fixed names,
network, published ports, Redis data bind and Redis/signing secrets. Services:
Redis, default RQ worker, status, preflight, dashboard and disposable application
client. Build cache volumes are reused; model data and Redis state are isolated.

Commands use `docker compose -f /tmp/wepppy-redis-transport-acceptance/compose.json`:
`build status preflight`; `up -d --wait redis`; `up -d --no-deps rq-worker status
preflight rq-dashboard`; `run --rm --no-deps -T weppcloud
tests/docker/redis_transport_client_probe.py`. The committed probe directly
exercises real clients without the pytest Redis recorder.

Initial result: sync AUTH/set/get on DBs 0,2,9,11,13,14,15; async AUTH/PubSub;
Flask migrating-session round trip and expiry; six default RQ worker
registrations; isolated job `ab8934de-a403-4b28-ae33-b190c187f7d7` returned 42;
status/preflight HTTP health and dashboard HTTP passed. Wrong/absent passwords
and missing configured password file fail. A first session probe used disabled
migration and hit the legacy Flask-Session bytes-cookie incompatibility; the
retained probe uses the established deployed migrating-session configuration.
No application/session behavior was changed to accommodate the probe.

Production startup script directly passed readiness and a one-worker burst on
isolated queue `transport-startup`. RQ info with an unreachable RQ_REDIS_URL and
explicit empty --url still authenticated the canonical DB9, proving Click env
precedence handling. Native pool reconstruction preserves provided pool identity
and bounded timeouts. The host flush helper passed --dry-run --require-redis
against isolated DB9; no FLUSHDB was executed. Performance helper real AUTH
selected DB13. The application image lacks redis-cli, so the host helper probe
used the existing Redis image with the repository mounted read-only.

## Artifacts, restart and recovery

ACL readback: file mode 0600, parent 0700, seven expected ACL fields; no raw
password or hash was retained. AUTH probe returns exactly PONG. Wrong health
credential fails the PONG gate. Missing/empty server files and missing probe
file fail explicitly. Candidate restart retained an isolated marker. Baseline
`ca1034a2b` entrypoint rollback and candidate restore used the same image,
isolated data and password; both authenticated and retained the marker. The
baseline has its known legacy argv exposure; the final state is candidate.

Process argv, Docker inspect configuration and container logs for all five
running isolated services were scanned in memory against the unique canary,
with no matches. Raw credentials and ACL hashes were never printed or committed.
Final candidate scans will be repeated after the final rebuild.

Pinned `redis:8.2.1-alpine` canary image also authenticated through shared ACL
and probe scripts. `CONFIG GET save` returned an empty setting, preserving the
original no-snapshot fixture behavior. Debian and Alpine use existing od/awk and
sha256sum; no new dependency/image change was required.

Rendered dev, HPC, prod, prod+wepp1, worker-only, wepp3 and canary Compose models
passed parsing and synthetic-password scans. Worker queue names/counts/classes
and DB9 remain unchanged. No production environment was deployed.

## Shared development event and limits

The first post-Compose-change `wctl run-status-tests` unexpectedly recreated
shared dev Redis because the wrapper starts dependencies. See independent
operations review. Original image/password/data are retained and Redis is
healthy; native application AUTH passed. There is no pre-event snapshot, so
zero interruption or unchanged jobs cannot be claimed. All later builder runs
use --no-deps. This event is not used as synthetic acceptance evidence.

Production rollout remains separate; remote host identities/mounts must pass
its existing deployment workflow. TLS/Unix option preservation has constructor
and parser coverage; the real shared/default-user authentication acceptance is
TCP, matching the current canonical Compose topology.
