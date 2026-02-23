# Deploy Runbook: RQ Redis DB9 Flush Policy

Work package: `20260224_redis_persistence_session_durability`  
Last updated: 2026-02-23

## Purpose

WEPPcloud uses Redis DB 9 for RQ queues and job metadata. Deploy policy allows an explicit “reset RQ jobs” operation during deploys while preserving Redis-backed sessions (DB 11) and other Redis databases.

## Policy (non-negotiable)

- Only flush Redis DB 9 (`FLUSHDB` on DB 9).
- Never run `FLUSHALL` as part of deploy automation.
- Stop RQ workers before flushing DB 9.

## How deploy automation behaves

`scripts/deploy-production.sh` includes a DB9 flush step by default:

- Default: flush DB 9 after `wctl down` (before `wctl up -d`).
- Opt-out: pass `--no-flush-rq-db`.
- If you want the deploy to fail when Redis is unreachable for the flush step: pass `--require-rq-redis`.

## Manual operator procedure (safe, DB9-only)

### 1) Stop workers

```bash
wctl down rq-worker rq-worker-batch
```

If the web app is actively enqueueing jobs, consider stopping `weppcloud` briefly to avoid new enqueues while you flush:

```bash
wctl down weppcloud
```

### 2) Dry-run the flush

```bash
./scripts/redis_flush_rq_db.sh --dry-run
```

### 3) Flush DB 9

```bash
./scripts/redis_flush_rq_db.sh
```

Notes:

- The helper refuses to flush anything except DB 9 (fails closed if `REDIS_DB` is provided and is not `9`).
- By default it is best-effort: if Redis is unreachable it warns and skips. Use `--require-redis` for hard failure.

### 4) Bring services back and validate

```bash
wctl up -d
wctl rq-info
```

Expected outcomes:

- DB 9 is empty immediately after flush; RQ queue depth is zero.
- Any previously queued jobs are gone. Any in-flight workers will see missing job metadata if they were running during the flush (this is why we stop workers first).
- Flask sessions (DB 11) are not affected by DB9 flush.

