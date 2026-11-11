# Redis credential transport failure-class matrix

**Status**: Initial inventory; re-audit before implementation
**Date**: 2026-11-11 UTC

| Consumer/variant | Current secret representation | Required disposition/evidence |
| --- | --- | --- |
| Python sync clients | Mixed kwargs and password-bearing URLs | Canonical kwargs; direct AUTH/DB tests |
| Python async clients | URL helper | Separate async kwargs/pool; PubSub/PING test |
| Flask sessions | `redis.from_url` | Client/pool kwargs; session round trip/expiry |
| RQ production startup | generated secret URL passed to probe/`-u` | RQ config path; registration/dequeue/argv proof |
| RQ dev/HPC inline commands | shell-built secret URL in `-u` | Same owned adapter; Compose contract tests |
| RQ dashboard/HPC | exported secret URL | Inventory and migrate or explicitly exclude with evidence |
| status2 | password injected into `RedisURL` | `redis.Options`; real AUTH and health |
| preflight2 | password injected into `RedisURL` | `redis.Options`; real AUTH and health |
| streamauth | parses/clones URL for DB 11/0 | clone options; session/JTI integration |
| Redis server | `--requirepass` argv | protected ACL/config file; restart/argv proof |
| Compose healthchecks | `redis-cli -a` argv | reviewed file-aware probe; wrong-secret failure |
| Canary/aux stacks | inline `--requirepass`/`-a` | migrate test infrastructure or documented synthetic exception |
| Operator documentation | `redis-cli -a` examples | non-argv helper and lint/source scan |
| Legacy external worker URL | may include userinfo | transition normalize/fail matrix; never re-emit |

## Completion Rule

Re-run repository-wide inventory across Compose overlays, scripts, docs and
runtime code. Every deployed row requires a positive real-auth case, a
wrong/missing-secret case and a canary non-disclosure check. Test-only synthetic
credentials must be dispositioned rather than silently counted as production
leaks. F5 traceback work is not a substitute for this repair.
