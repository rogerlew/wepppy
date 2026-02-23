# Redis Persistence Defaults and RQ DB9 Deploy Flush Policy

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` are updated as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Ensure Redis-backed sessions and runtime state remain durable across normal redeploys in stacks with Redis, while preserving explicit operator control to clear only RQ jobs (DB 9) during deploys.

## Progress

- [x] (2026-02-23 21:00Z) Package scaffold created and active plan initialized.
- [x] (2026-02-23 21:30Z) Baseline explorer inventory completed and baseline artifact captured.
- [x] (2026-02-23 22:10Z) Required worker orchestration completed (runtime/deploy/docs).
- [x] (2026-02-23 22:45Z) Runtime durability + deploy DB9 flush implementation integrated.
- [x] (2026-02-23 23:00Z) Required docs/contracts/runbook updates integrated.
- [x] (2026-02-23 23:15Z) Compose checks, targeted pytest, and broad-exception gate passed.
- [x] (2026-02-23 23:40Z) Docs lint completed across changed docs.
- [x] (2026-02-23 23:55Z) Final explorer review pass completed and follow-up findings resolved.
- [x] (2026-02-23 23:58Z) Closeout sync complete (tracker/package/project tracker/root pointer reset).

## Surprises & Discoveries

- Observation: `docker/docker-compose.prod.wepp1.yml` did not pass standalone `docker compose ... config` until override-only services had explicit image declarations in-file.
  Evidence: error `service "caddy" has neither an image nor a build context specified` before patch.
- Observation: `SESSION_REDIS_DB` exists for Flask session URL construction, but cross-service session-marker consumers still assume DB 11.
  Evidence: review of `weppcloud`/`rq_engine` marker paths and contract alignment.

## Decision Log

- Decision: Preserve deploy reset intent by making DB9 flush default-on in `deploy-production.sh`, with explicit opt-out.
  Rationale: Existing operations expected deploy-time queue reset; durable Redis requires explicit replacement behavior.
  Date/Author: 2026-02-23 / Codex
- Decision: Keep session DB at 11 in this package and document coordinated migration requirements.
  Rationale: Avoid partial migration regressions across session-marker consumers.
  Date/Author: 2026-02-23 / Codex
- Decision: Harden strict flush mode to fail when `redis-cli` is unavailable.
  Rationale: `--require-redis` must not silently skip flush.
  Date/Author: 2026-02-23 / Codex

## Outcomes & Retrospective

Package completed as intended. Redis persistence defaults are durable and tunable in stacks with Redis, deploy-time RQ reset behavior is explicit and DB9-scoped, and session durability expectations are documented with migration caveats. Required validation gates passed, required artifacts were published, and final explorer verification reported no remaining high/medium findings.

## Context and Orientation

Primary implementation surfaces:

- `docker/redis-entrypoint.sh`
- `docker/docker-compose.dev.yml`
- `docker/docker-compose.prod.yml`
- `docker/docker-compose.prod.wepp1.yml`
- `scripts/redis_flush_rq_db.sh`
- `scripts/deploy-production.sh`
- `docker/README.md`
- `docs/dev-notes/redis_dev_notes.md`
- `docs/dev-notes/redis_config_refactor.md`
- `docs/schemas/weppcloud-session-contract.md`

## Plan of Work

Completed through all milestones: baseline inventory, runtime/deploy implementation, documentation updates, validations, artifact capture, final explorer review, and closeout synchronization.

## Concrete Steps

Executed commands from `/workdir/wepppy`:

- `docker compose --env-file docker/.env -f docker/docker-compose.dev.yml config`
- `docker compose --env-file docker/.env -f docker/docker-compose.prod.yml config`
- `docker compose --env-file docker/.env -f docker/docker-compose.prod.wepp1.yml config`
- `wctl run-pytest tests/weppcloud/test_configuration.py`
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- `wctl doc-lint --path <each changed doc>`
- `bash -n scripts/deploy-production.sh scripts/redis_flush_rq_db.sh docker/redis-entrypoint.sh`

## Validation and Acceptance

Acceptance achieved:

1. Durable Redis defaults + env knobs are active in compose stacks with Redis.
2. Deploy flow includes explicit DB9-only flush behavior with opt-out and strict mode.
3. Session durability and DB migration implications are documented.
4. Required validation gates and artifacts completed.

## Idempotence and Recovery

- Config/document edits are idempotent.
- DB9 flush helper is DB-scoped and safe to repeat.
- Deploy script supports opt-out and strict failure control flags.

## Artifacts and Notes

- `artifacts/baseline_redis_runtime.md`
- `artifacts/postfix_redis_runtime.md`
- `artifacts/deploy_rq_flush_policy.md`
- `artifacts/final_validation_summary.md`

## Interfaces and Dependencies

Runtime env knobs:

- `REDIS_APPENDONLY`
- `REDIS_APPENDFSYNC`
- `REDIS_SAVE_SCHEDULE`
- `REDIS_AOF_USE_RDB_PREAMBLE`

Deploy control flags:

- `scripts/deploy-production.sh --flush-rq-db|--no-flush-rq-db [--require-rq-redis]`
- `scripts/redis_flush_rq_db.sh [--dry-run] [--require-redis]`

Revision note (2026-02-23 23:58Z): Finalized closure state after follow-up explorer verification and synchronized all package tracking surfaces.
