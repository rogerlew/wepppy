# Tracker - Redis Persistence and Session Durability Across Deployments

## Quick Status

**Started**: 2026-02-23  
**Current phase**: Closed  
**Last updated**: 2026-02-23  
**Next milestone**: none

## Task Board

### Ready / Backlog

- [ ] None.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Package scaffold and active ExecPlan authored.
- [x] Required orchestration completed: baseline explorer + workers A/B/C + final explorer review pass.
- [x] Runtime durability implementation completed (`redis-entrypoint` + compose wiring).
- [x] Explicit deploy-time DB9 flush mechanism completed (`scripts/redis_flush_rq_db.sh` + deploy hook flags).
- [x] Documentation and contract updates completed.
- [x] Required validation gates passed.
- [x] Required artifacts completed.
- [x] Closeout synchronization completed (package/tracker/ExecPlan/project tracker/root pointer reset).

## Milestones

- [x] Milestone 0: baseline inventory artifacts and decisions.
- [x] Milestone 1: Redis persistence defaults + env knobs implementation.
- [x] Milestone 2: deploy-time DB9 flush implementation.
- [x] Milestone 3: docs/contracts/runbook updates.
- [x] Milestone 4: final validation, explorer review, closeout sync.

## Decisions

### 2026-02-23: Durable Redis defaults

**Decision**: Set durable Redis defaults in entrypoint and keep them env-tunable.

**Impact**: Sessions and non-RQ Redis state are durable across normal restarts/redeploys.

### 2026-02-23: Deploy flush policy

**Decision**: Make DB9 flush explicit and default-on in production deploy script with opt-out.

**Impact**: Preserves operational intent to clear jobs on deploy without broad Redis wipe.

### 2026-02-23: Session DB index handling

**Decision**: Keep DB 11 session index unchanged; document coordinated migration requirements.

**Impact**: Avoids immediate cross-service contract drift while clarifying safe future migration behavior.

## Risks and Mitigations

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Mis-scoped flush clears sessions | High | Low | DB index hard-guard (`REDIS_DB` must be `9`) and `FLUSHDB` only | Closed |
| Deploy flush silently skipped in strict mode | Medium | Low | `--require-redis` now hard-fails if `redis-cli` is unavailable/unreachable | Closed |
| Session DB override drift across services | Medium | Medium | Contract + dev-notes explicitly require coordinated migration | Closed |

## Verification Checklist

- [x] `docker compose --env-file docker/.env -f docker/docker-compose.dev.yml config`
- [x] `docker compose --env-file docker/.env -f docker/docker-compose.prod.yml config`
- [x] `docker compose --env-file docker/.env -f docker/docker-compose.prod.wepp1.yml config`
- [x] `wctl run-pytest tests/weppcloud/test_configuration.py`
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (initial package run)
- [x] `wctl doc-lint --path <each changed doc>`
- [x] Final explorer review pass (no remaining high/medium findings).

## Progress Notes

### 2026-02-23: Baseline and implementation

- Baseline inventory confirmed non-durable Redis defaults and no explicit DB9 deploy flush path.
- Runtime, deploy, docs, and contract changes implemented.

### 2026-02-23: Validation and closure

- Required gates passed (compose config checks, targeted pytest, broad-exception enforcement, docs lint).
- Follow-up explorer review identified medium findings; mitigations applied.
- Final explorer verification reported no high/medium issues.
- A later workspace-wide broad-exception re-run flagged unrelated edits in `wepppy/nodir/materialize.py`; package files remain unaffected.
- Package closed with full sync updates.
