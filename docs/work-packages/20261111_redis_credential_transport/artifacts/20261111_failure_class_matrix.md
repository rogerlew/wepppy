# Redis credential transport failure-class matrix

**Status**: Implemented consumer inventory; final acceptance review in progress
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

## Execution disposition

Python pool consumers in NoDb base, WEPPcloud helpers/agent/README routes and
agent RQ use `for_pool=True`; direct constructors retain native kwargs. There
are no production callers of `redis_async_url`; the new async client receives
real AUTH/PubSub coverage. Flask construction uses session-specific kwargs.

Dev/HPC default/batch/fork workers and production startup use the config adapter
plus empty `--url`. `wctl rq-info` uses the same path. The performance harness
now separates credentials for both canonical-resolver and explicit legacy URL
inputs. Its operator examples no longer place credentials in argv. The
host-side DB9 flush helper preserves dry-run/flush semantics, gives configured
files authority and restricts REDISCLI_AUTH to its ephemeral command child.
The deployment worker-registration probe now uses canonical native kwargs.

The dev/HPC sibling dashboard already supports separate password config; an
owned mounted module uses that API without editing the sibling repository.
`wepppy/webservices/rq_dashboard.py` is a dormant standalone launcher: the only
repository reference is the type-hints inventory, and no current Compose or
operator launcher invokes it. It does not consume the changed URL helper or
synthesize mounted-file credentials. Its external legacy URL input remains
outside deployed acceptance; do not treat it as a validated deployment path.

Canary/aux Redis launchers now use the same ACL entrypoint and explicit empty
snapshot setting. Historical benchmark examples containing `<redacted>` are
retained as historical evidence, not executable credential recommendations.
Current deployment/helper scans found no generated password URL, `redis-cli -a`
or `--requirepass` invocation. Unit fixtures and the private baseline rollback
probe intentionally exercise legacy input/behavior and are not deployed sinks.
