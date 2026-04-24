# RQ Worker Startup and NoDb Redis Cache Hardening (Retroactive)

**Status**: Complete (2026-04-24 18:07 UTC)
**Timezone**: UTC

## Overview
This retroactive package captures the incident-response hardening completed after repeated `modify_landuse_mapping_rq` failures with `RuntimeError: Redis NoDb cache client is unavailable`. The completed work tightens NoDb lock/cache safety, makes worker startup resilient during Redis AOF load windows, and closes review findings found during two independent review rounds.

## Objectives
- Prevent stale or unavailable Redis clients from poisoning NoDb cache/lock behavior.
- Ensure NoDb persistence only occurs while the current process still owns the distributed lock token.
- Add worker startup gating so `rq-worker` and `rq-worker-batch` wait for Redis readiness and optional startup delay.
- Harden worker-compose contracts for external Redis worker hosts.
- Capture code review, QA review, and security review findings with full disposition.

## Scope

### Included
- NoDb lock/cache hardening in `wepppy/nodb/base.py`.
- Worker startup gate script and compose wiring updates for production and worker-only stacks.
- Regression tests for lock ownership, reconnect retry behavior, and compose/startup contract invariants.
- Docker operations documentation updates for worker startup/readiness contracts.
- Two-round review disposition (code, QA, ops/security).

### Explicitly Out of Scope
- New queue topology or queue dependency graph rewiring.
- Business-logic changes to landuse mapping operations beyond cache/lock safety.
- Host-specific deploy execution steps (compose up/down) on wepp1/wepp2.

## Stakeholders
- **Primary**: RQ operators, NoDb maintainers, landuse pipeline maintainers.
- **Reviewers**: `reviewer`, `qa_reviewer`, `ops_security_control_agent`.
- **Security Reviewer**: required (queue/worker/subprocess and lock semantics are in scope).
- **Informed**: platform maintainers supporting wepp1/wepp2 worker fleets.

## Success Criteria
- [x] `clear_nodb_file_cache()` reconnects Redis cache client on demand and preserves explicit failure contract when reconnect fails.
- [x] `NoDbBase.dump()` rejects writes when distributed lock ownership is missing or token-mismatched.
- [x] `NoDbBase.locked()` no longer force-unlocks foreign-owner locks on persistence failure paths.
- [x] Worker startup uses explicit Redis readiness probes and a configurable startup delay.
- [x] Worker-only compose requires explicit `RQ_REDIS_URL` and aligns `REDIS_URL` with it.
- [x] Worker services gate on `weppcloudr` health in worker-only compose.
- [x] Targeted regression suite passes with no unresolved medium/high review findings.

## Dependencies

### Prerequisites
- Existing Redis URL resolver contract in `wepppy/config/redis_settings.py`.
- Existing NoDb distributed lock/token scheme in `wepppy/nodb/base.py`.

### Blocks
- None.

## Related Packages
- **Related**: [20260411_rq_operator_experience_hardening](../20260411_rq_operator_experience_hardening/package.md)
- **Related**: [20260424_landuse_legacy_flask_state_route_removal](../20260424_landuse_legacy_flask_state_route_removal/package.md)
- **Follow-up**: Optional operator evidence package for post-deploy wepp1/wepp2 live verification snapshots.

## Timeline Estimate
- **Expected duration**: Incident-response same-day hardening.
- **Complexity**: Medium-High.
- **Risk level**: High.

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: changes touch queue worker startup, Redis connection contracts, subprocess startup wrapper behavior, and distributed lock ownership guarantees.
- **Security review artifact**: `docs/work-packages/20260424_rq_worker_nodb_cache_hardening/artifacts/2026-04-24_security_review.md`

## Validation Commands (executed)
- `bash -n docker/rq-worker-startup.sh`
- `docker compose --env-file docker/.env -f docker/docker-compose.prod.yml config -q`
- `RQ_REDIS_URL=redis://redis:6379/9 docker compose --env-file docker/.env -f docker/docker-compose.prod.worker.yml config -q`
- `wctl run-pytest tests/nodb/test_base_misc.py tests/nodb/test_base_unit.py tests/docker/unit/test_rq_worker_startup_contract.py --maxfail=1` (`61 passed`)
- `wctl doc-lint --path docker/README.md`

## References
- `wepppy/nodb/base.py`
- `tests/nodb/test_base_unit.py`
- `tests/nodb/test_base_misc.py`
- `docker/rq-worker-startup.sh`
- `docker/docker-compose.prod.yml`
- `docker/docker-compose.prod.worker.yml`
- `tests/docker/unit/test_rq_worker_startup_contract.py`
- `docker/README.md`

## Deliverables
- NoDb lock/cache reconnect and ownership hardening with targeted regression coverage.
- Worker startup wrapper script with Redis readiness probe and configurable startup delay.
- Production and worker-only compose updates for readiness, env contracts, and startup wrapper adoption.
- Updated operator docs for worker host setup and scaling guidance.
- Closed code/QA/security review artifacts with finding dispositions.

## Follow-up Work
- Collect post-deploy live evidence from wepp1/wepp2 (`rq-worker`, `rq-worker-batch`) showing healthy startup and no recurring NoDb cache-unavailable failures.
- Add targeted runtime alerting for recurring `Redis NoDb cache client is unavailable` signatures if incident frequency increases.

## Closure Notes

**Closed**: 2026-04-24

**Summary**: Incident-response hardening was completed and validated across NoDb lock/cache boundaries and worker startup contracts. The final implementation eliminated force-unlock behavior on foreign locks, added lock-ownership checks for `dump()`, made Redis reconnect helpers retry-safe after failed pings, enforced explicit worker Redis URL contracts, and introduced startup gating to absorb Redis AOF load timing.

**Lessons Learned**: The initial patch set resolved the primary runtime failure but second-round independent review still found meaningful medium/high gaps (lock ownership edge branches, docs/compose drift, and startup-url fail-fast details). Running a required second review round was critical to achieving closure-quality hardening.

**Archive Status**: Package retained in `docs/work-packages/20260424_rq_worker_nodb_cache_hardening/` with completed prompt and review artifacts.

## Kickoff Prompt
- Completed ExecPlan: `docs/work-packages/20260424_rq_worker_nodb_cache_hardening/prompts/completed/rq_worker_nodb_cache_hardening_execplan.md`
