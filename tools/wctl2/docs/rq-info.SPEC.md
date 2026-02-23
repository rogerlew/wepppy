# wctl2 rq-info Command Specification

## Overview

`wctl rq-info` wraps `rq info` for WEPPcloud's RQ pools, targeting Redis DB 9 and the `default` + `batch` queues by default. The command runs inside the `rq-worker` service so the output matches what operators expect from the container environment.

## Goals

1. Provide a single command that always shows both `default` and `batch` queues.
2. Preserve `rq info` behavior while appending user-provided flags (for example `--interval 1`).
3. Keep the invocation explicit about Redis DB 9 while supporting both env-based and secret-file Redis auth.
4. In interval mode, avoid stale worker state by deriving status from registry/job ownership and by discovering active queues automatically.

## Command Definition

```
wctl rq-info [RQ_INFO_ARGS...]
wctl rq-info --detail [RQ_INFO_ARGS...]
wctl rq-info --detail --detail-limit 10 [RQ_INFO_ARGS...]
```

## Behavior

- Executes `rq info` inside the `rq-worker` container for default one-shot usage.
- When arguments are exactly `--interval <seconds>`, executes the registry-backed
  snapshot loop (`python -m wepppy.rq.info_snapshot`) inside `rq-worker` instead
  of `rq info` so worker busy/idle status is derived from active job ownership
  rather than stale worker state.
  - Interval snapshots inspect all currently discovered queues by default
    (falling back to `default,batch` when queue discovery is empty).
- Resolves the Redis URL *inside the container* via `wepppy.config.redis_settings.redis_url(RedisDB.RQ)` so it can:
  - force Redis DB 9
  - inject credentials from `REDIS_PASSWORD_FILE` (preferred) or `REDIS_PASSWORD` (legacy)
- Appends any extra CLI args after `default batch`.
- Returns the exit code from the underlying `rq info` command.
- Logs the docker compose exec invocation at INFO level (Redis URLs are redacted if present in the logged command).
- `--detail` appends a job summary (runid, description, auth actor) using the RQ Python API.
- `--detail-limit` caps the number of jobs per state and queue (default: 50; 0 = unlimited).

## Examples

```bash
wctl rq-info
wctl rq-info --detail
wctl rq-info --detail --detail-limit 10
wctl rq-info --interval 1
wctl rq-info --raw
```

## Implementation Notes

- Command module: `tools/wctl2/commands/rq.py`.
- Registration: `tools/wctl2/commands/__init__.py`.
- See also: `tools/wctl2/docs/SPEC.md` for CLI context and passthrough behavior.
