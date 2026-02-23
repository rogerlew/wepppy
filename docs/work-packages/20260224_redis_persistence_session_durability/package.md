# Redis Persistence and Session Durability Across Deployments

**Status**: Closed (2026-02-23)

## Overview

Enabled durable Redis persistence defaults for stacks that run Redis so Flask sessions and non-RQ runtime state survive normal restarts/redeploys, while preserving explicit deploy-time reset behavior for RQ by flushing only DB 9.

## Objectives

- Enable durable Redis persistence defaults while keeping keyspace notifications and password-file auth.
- Expose durability runtime knobs via environment variables in compose-managed Redis services.
- Preserve deploy-time RQ reset behavior as explicit DB9-only logic with opt-out.
- Document session durability expectations and DB-index migration implications.
- Publish runbook and validation artifacts.

## Scope

### Included

- `docker/redis-entrypoint.sh`
- `docker/docker-compose.dev.yml`
- `docker/docker-compose.prod.yml`
- `docker/docker-compose.prod.wepp1.yml`
- `scripts/redis_flush_rq_db.sh`
- `scripts/deploy-production.sh`
- Documentation and artifact updates required by this package

### Explicitly Out of Scope

- Introducing a Redis service into worker-only stacks.
- Queue topology redesign.
- Session architecture redesign beyond durability/contract clarification.

## Success Criteria

- [x] Durable Redis defaults implemented (`appendonly yes`, `appendfsync everysec`, save schedule, AOF RDB preamble) with keyspace/auth behavior preserved.
- [x] Durability knobs exposed and wired in compose files.
- [x] Deploy-time RQ reset path explicit, automated, and scoped to DB 9 only.
- [x] Session durability expectations + DB-index migration implications documented.
- [x] Required validation gates passed.
- [x] Package/tracker/ExecPlan/project tracker/root pointer synchronized at closure.

## Deliverables

- `docs/work-packages/20260224_redis_persistence_session_durability/package.md`
- `docs/work-packages/20260224_redis_persistence_session_durability/tracker.md`
- `docs/work-packages/20260224_redis_persistence_session_durability/prompts/active/redis_persistence_session_durability_execplan.md`
- `docs/work-packages/20260224_redis_persistence_session_durability/artifacts/baseline_redis_runtime.md`
- `docs/work-packages/20260224_redis_persistence_session_durability/artifacts/postfix_redis_runtime.md`
- `docs/work-packages/20260224_redis_persistence_session_durability/artifacts/deploy_rq_flush_policy.md`
- `docs/work-packages/20260224_redis_persistence_session_durability/artifacts/final_validation_summary.md`

## References

- `AGENTS.md`
- `docker/AGENTS.md`
- `docs/prompt_templates/codex_exec_plans.md`
- `docker/README.md`
- `docs/dev-notes/redis_dev_notes.md`
- `docs/dev-notes/redis_config_refactor.md`
- `docs/schemas/weppcloud-session-contract.md`

## Closure Notes

- Redis entrypoint now defaults to durable persistence and supports env-tunable durability knobs.
- Dev/prod compose Redis services now wire durability env variables.
- `scripts/redis_flush_rq_db.sh` added for explicit DB9-only flush; `deploy-production.sh` now uses default-on DB9 flush with opt-out and hard-fail options.
- Session contract and Redis/deploy operational docs updated and linted.
- Required gates passed: compose render checks, targeted pytest, broad-exception enforcement, docs lint.
- Workspace note: a later broad-exception re-run failed due unrelated concurrent edits in `wepppy/nodir/materialize.py` (outside this package scope).
