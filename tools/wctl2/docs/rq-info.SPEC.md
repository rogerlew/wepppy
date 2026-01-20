# wctl2 rq-info Command Specification

## Overview

`wctl rq-info` wraps `rq info` for WEPPcloud's RQ pools, targeting Redis DB 9 and the `default` + `batch` queues by default. The command runs inside the `rq-worker` service so the output matches what operators expect from the container environment.

## Goals

1. Provide a single command that always shows both `default` and `batch` queues.
2. Preserve `rq info` behavior while appending user-provided flags (for example `--interval 1`).
3. Keep the invocation explicit about Redis DB 9 while honoring optional auth from `docker/.env`.

## Command Definition

```
wctl rq-info [RQ_INFO_ARGS...]
wctl rq-info --detail [RQ_INFO_ARGS...]
wctl rq-info --detail --detail-limit 10 [RQ_INFO_ARGS...]
```

## Behavior

- Executes: `/opt/venv/bin/rq info -u redis://redis:6379/9 default batch` inside the `rq-worker` container.
- If `RQ_REDIS_URL` or `REDIS_URL` is defined in `docker/.env`, the command reuses its host and credentials while forcing DB 9.
- If `REDIS_PASSWORD` is defined (and no password is already embedded in the URL), the command injects it as `redis://:<password>@host:port/9`.
- Appends any extra CLI args after `default batch`.
- Returns the exit code from the underlying `rq info` command.
- Logs the full docker compose exec invocation at INFO level.
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
