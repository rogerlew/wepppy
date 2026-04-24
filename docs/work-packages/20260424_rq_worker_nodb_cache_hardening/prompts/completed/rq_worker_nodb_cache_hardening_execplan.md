# RQ Worker Startup and NoDb Redis Cache Hardening ExecPlan (Retroactive)

This ExecPlan is recorded retroactively to capture the implementation that was completed during the 2026-04-24 incident response. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` reflect final state.

Reference process: `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Workers should no longer fail early because Redis is not ready during startup windows, and NoDb should never persist state when lock ownership has been lost. After this package, Redis readiness and startup delay are explicit worker controls, and NoDb dump behavior is ownership-safe under lock contention.

## Progress

- [x] (2026-04-24 17:18 UTC) Harden reconnect helpers for lock/cache clients with safe failed-ping retry behavior.
- [x] (2026-04-24 17:27 UTC) Enforce lock ownership checks before NoDb persistence and preserve foreign-owner locks on failure.
- [x] (2026-04-24 17:34 UTC) Add `docker/rq-worker-startup.sh` with Redis readiness probe and startup delay support.
- [x] (2026-04-24 17:41 UTC) Wire startup script and readiness contracts in prod and worker-only compose files.
- [x] (2026-04-24 17:48 UTC) Add/extend regression tests for lock/cache and startup contracts.
- [x] (2026-04-24 18:03 UTC) Complete second-round review finding disposition.
- [x] (2026-04-24 18:07 UTC) Capture retroactive package docs and close package.

## Surprises & Discoveries

- Observation: resolving the primary runtime failure was not sufficient; second-round review still found high/medium lock ownership and contract drift issues.
  Evidence: second-round reviewer findings in package artifacts.
- Observation: startup readiness needs both probe and optional delay; fixed-only sleep would either over-wait or remain brittle.
  Evidence: startup gate design in `docker/rq-worker-startup.sh` and compose timeout/delay env controls.

## Decision Log

- Decision: preserve explicit failure semantics for unavailable Redis cache clients.
  Rationale: explicit contracts are needed for diagnosability and operator triage.
  Date/Author: 2026-04-24 / Codex.

- Decision: prevent force unlock on ownership mismatch in `locked()` failure cleanup.
  Rationale: forcing unlock can clear another process lock and corrupt concurrency guarantees.
  Date/Author: 2026-04-24 / Codex.

- Decision: require `RQ_REDIS_URL` in worker-only compose and align `REDIS_URL` with it.
  Rationale: worker stacks do not host local Redis; fail-fast reduces silent misconfiguration.
  Date/Author: 2026-04-24 / Codex.

## Outcomes & Retrospective

The package goals were met. No unresolved medium/high findings remain after two review rounds. Targeted test matrix and compose/doc validations are green. The largest lesson was that second-round review materially improved incident hardening quality by surfacing lock-edge and contract-consistency gaps not covered in first-pass fixes.

## Context and Orientation

- NoDb runtime and lock/cache behavior: `wepppy/nodb/base.py`.
- Worker startup shell wrapper: `docker/rq-worker-startup.sh`.
- Compose contracts:
  - `docker/docker-compose.prod.yml`
  - `docker/docker-compose.prod.worker.yml`
- Regression tests:
  - `tests/nodb/test_base_unit.py`
  - `tests/nodb/test_base_misc.py`
  - `tests/docker/unit/test_rq_worker_startup_contract.py`

## Plan of Work

Retroactive capture only. Work was executed directly in implementation and validation steps listed below.

## Concrete Steps

Working directory: `/home/workdir/wepppy`

1. Implement NoDb reconnect and lock ownership safety changes.
2. Implement worker startup gate script and compose wiring.
3. Update docs and tests for contract invariants.
4. Run validation commands.
5. Run review rounds and disposition findings.

## Validation and Acceptance

Acceptance evidence:
- `wctl run-pytest tests/nodb/test_base_misc.py tests/nodb/test_base_unit.py tests/docker/unit/test_rq_worker_startup_contract.py --maxfail=1` (`61 passed`).
- `docker compose ... config -q` checks pass for both prod compose files.
- `wctl doc-lint --path docker/README.md` passes.
- Review artifacts report no unresolved medium/high findings.

## Idempotence and Recovery

Startup and lock/cache changes are idempotent and safe to re-run in validation. If worker startup contracts require rollback, revert compose command wiring to direct `rq worker-pool` and remove wrapper envs as a full-unit rollback.

## Artifacts and Notes

- `docs/work-packages/20260424_rq_worker_nodb_cache_hardening/artifacts/2026-04-24_code_review.md`
- `docs/work-packages/20260424_rq_worker_nodb_cache_hardening/artifacts/2026-04-24_qa_review.md`
- `docs/work-packages/20260424_rq_worker_nodb_cache_hardening/artifacts/2026-04-24_security_review.md`

## Interfaces and Dependencies

No new external dependencies were introduced. Changes rely on existing Redis client libraries and existing compose/runtime infrastructure.

## Plan Revision Log

- 2026-04-24 / Codex: Retroactively authored completed ExecPlan to capture incident-response implementation and closure evidence.
