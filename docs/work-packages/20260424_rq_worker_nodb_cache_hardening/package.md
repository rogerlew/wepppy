# RQ Worker Startup and NoDb Redis Cache Hardening (Retroactive)

**Status**: Complete (2026-04-24 18:07 UTC)
**Timezone**: UTC

## Overview
This retroactive package captures the incident-response hardening completed after repeated `modify_landuse_mapping_rq` failures with `RuntimeError: Redis NoDb cache client is unavailable`. The completed work tightens NoDb lock/cache safety, makes worker startup resilient during Redis AOF load windows, and closes review findings found during two independent review rounds.

## Trigger and Scope Freeze
- **Primary incident timestamp**: 2026-04-24 17:01 UTC.
- **Confirmed failing job**: `fceb9433-598e-499f-ae2b-24d38407399f`.
- **Route/job surface**: `modify_landuse_mapping_rq` path during landuse mutation flow.
- **Incident signature**: `RuntimeError: Redis NoDb cache client is unavailable`.
- **Operator-visible impact**: repeated mapping-job failures, manual retries, and queue/operator toil during Redis readiness windows.
- **Scope boundary**: Fix confirmed Redis NoDb cache/lock availability and worker-startup timing paths without broad queue-topology or landuse business-logic refactors.

## Precedent Discovery (Required)
Primary discovery sources used:
- `PROJECT_TRACKER.md` (`Done` entries for related hardening work).
- `docs/work-packages/20260411_rq_operator_experience_hardening/`.
- `docs/work-packages/20260424_landuse_legacy_flask_state_route_removal/`.
- `docs/standards/hardening-lifecycle-standard.md`.

Reuse vs intentional difference:
- **Reused**: explicit failure contracts (no silent fallback), targeted regression-first hardening, and independent code/QA/security review closure discipline.
- **Reused**: worker/operator ergonomics pattern of fail-fast config validation before runtime work.
- **Intentionally different**: this package focused on Redis client lifecycle + lock ownership + startup readiness contracts, not API surface migration/cutover policy.
- **Intentionally different**: this package accepted temporary startup-readiness calluses with explicit sunset review dates, instead of permanent behavior expansion.

## Hardening Hypotheses and Signals
Observation window for production signals: **2026-04-24 to 2026-05-24** (30 days).

| ID | Hypothesis | Primary health signal(s) | Guardrail signal(s) |
| --- | --- | --- | --- |
| H1 | If NoDb Redis reconnect helpers clear stale globals and reconnect deterministically, `Redis NoDb cache client is unavailable` runtime failures should stop recurring on normal worker startup paths. | Count of incident-signature failures in RQ job traces trends to `0` over the observation window. | No increase in lock/cache client initialization crash loops; queue startup remains successful on both default and batch workers. |
| H2 | If `dump()` requires matching distributed lock ownership, cross-owner stale writes and force-unlock corruption risks are eliminated. | No new lock-ownership corruption incidents; no regressions in lock-related NoDb tests. | No material increase in false-positive persistence failures under normal lock ownership. |
| H3 | If worker startup waits for Redis readiness (plus optional delay), startup/AOF timing failures reduce without introducing sustained queue latency. | Startup-time worker failures during Redis warm-up windows trend to `0`. | Worker start latency remains within acceptable operator envelope; startup timeout events stay rare/absent. |

## Redis NoDb Cache Connection Configuration Strategy (Post-Incident)
Strategy intent: keep Redis NoDb cache writes fail-fast and observable across local-Redis (`wepp1`) and external-Redis worker hosts (`wepp2`).

Current wiring points:
- NoDb cache pool instantiation: `wepppy/nodb/base.py` (`RedisDB.NODB_CACHE` pool kwargs).
- Shared Redis kwargs builder: `wepppy/config/redis_settings.py::redis_connection_kwargs`.
- Runtime library behavior baseline: redis-py `6.2.0` in the container runtime.

Recommended connection posture for `RedisDB.NODB_CACHE` pool:

```python
pool_kwargs = redis_connection_kwargs(
    RedisDB.NODB_CACHE,
    decode_responses=True,
    extra={
        "max_connections": 50,
        "socket_timeout": 5,
        "socket_connect_timeout": 5,
        "socket_keepalive": True,
        "health_check_interval": 30,
        "retry_on_timeout": True,
    },
)
```

Rationale:
- `socket_connect_timeout`/`socket_timeout` bound dead/stale path waits and prevent multi-minute hangs.
- `health_check_interval` enables pre-command connection health checks instead of discovering stale sockets only on critical writes.
- `socket_keepalive=True` enables TCP keepalive at socket level; this helps long-lived idle pooled connections.
- `retry_on_timeout=True` in redis-py 6.2.0 yields one bounded retry path for timeout-class failures; treat this as transitional because client-level `retry_on_timeout` is deprecated in newer docs and should eventually move to explicit retry policy configuration.

Host-level keepalive alignment:
- Current Linux defaults (`tcp_keepalive_time=7200`, `tcp_keepalive_intvl=75`, `tcp_keepalive_probes=9`) are too slow for short idle-NAT failure detection.
- Follow-up should tune either host sysctls or per-socket `socket_keepalive_options` (Linux constants) for worker hosts that traverse external network paths.

Validation plan for this strategy:
- Add/extend unit tests to assert pool kwargs include timeout/health-check/keepalive settings for `RedisDB.NODB_CACHE`.
- Run targeted NoDb regression suite (`tests/nodb/test_base_misc.py`, `tests/nodb/test_base_unit.py`) and worker startup contract tests.
- Capture post-deploy evidence on `wepp1`/`wepp2` worker logs showing stable startup and absence of recurring signature.

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
- `docs/standards/hardening-lifecycle-standard.md`
- `https://redis.readthedocs.io/en/v6.2.0/connections.html`
- `https://redis.readthedocs.io/en/v6.2.0/_modules/redis/connection.html`
- `https://redis.readthedocs.io/en/v6.2.0/_modules/redis/client.html`

## Deliverables
- NoDb lock/cache reconnect and ownership hardening with targeted regression coverage.
- Worker startup wrapper script with Redis readiness probe and configurable startup delay.
- Production and worker-only compose updates for readiness, env contracts, and startup wrapper adoption.
- Updated operator docs for worker host setup and scaling guidance.
- Closed code/QA/security review artifacts with finding dispositions.

## Follow-up Work
- Collect post-deploy live evidence from wepp1/wepp2 (`rq-worker`, `rq-worker-batch`) showing healthy startup and no recurring NoDb cache-unavailable failures.
- Add targeted runtime alerting for recurring `Redis NoDb cache client is unavailable` signatures if incident frequency increases.
- Execute the Redis NoDb cache connection configuration strategy above (timeouts/health-check/keepalive posture) with targeted regression and rollout evidence.

## Callus Register and Sunset Criteria

| Callus | Type | Status | Owner | Sunset criteria | Review date |
| --- | --- | --- | --- | --- | --- |
| `RQ_WORKER_STARTUP_DELAY_SECONDS` optional delay | Startup delay | Active | RQ operators + NoDb maintainers | If no Redis warm-up startup incidents are observed during the 30-day window, reduce default delay pressure (prefer readiness-only) and document any retained non-zero default with explicit rationale. | 2026-05-25 |
| Redis readiness poll loop (`RQ_REDIS_WAIT_*`) | Readiness wrapper | Active | RQ operators | If startup failure rate remains `0` and measured startup latency is stable, evaluate reducing timeout budget or simplifying probe cadence while preserving fail-fast diagnostics. | 2026-05-25 |
| `retry_on_timeout=True` in NoDb cache pool strategy | Retry callus | Proposed follow-up | NoDb maintainers | Replace with explicit retry policy wiring (or documented keep) once pool-level retry semantics are validated and tested for redis-py runtime version in production containers. | 2026-06-30 |

Sunset enforcement:
- If review dates pass without disposition, open a follow-up mini package documenting keep/reduce/remove decision and current signal evidence.

## Closure Notes

**Closed**: 2026-04-24

**Summary**: Incident-response hardening was completed and validated across NoDb lock/cache boundaries and worker startup contracts. The final implementation eliminated force-unlock behavior on foreign locks, added lock-ownership checks for `dump()`, made Redis reconnect helpers retry-safe after failed pings, enforced explicit worker Redis URL contracts, and introduced startup gating to absorb Redis AOF load timing.

**Lessons Learned**: The initial patch set resolved the primary runtime failure but second-round independent review still found meaningful medium/high gaps (lock ownership edge branches, docs/compose drift, and startup-url fail-fast details). Running a required second review round was critical to achieving closure-quality hardening.

**Archive Status**: Package retained in `docs/work-packages/20260424_rq_worker_nodb_cache_hardening/` with completed prompt and review artifacts.

## Kickoff Prompt
- Completed ExecPlan: `docs/work-packages/20260424_rq_worker_nodb_cache_hardening/prompts/completed/rq_worker_nodb_cache_hardening_execplan.md`
