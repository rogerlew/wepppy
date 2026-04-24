# Tracker - RQ Worker Startup and NoDb Redis Cache Hardening (Retroactive)

> Living document tracking incident-response progress, decisions, risks, and verification for this package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-24 17:01 UTC  
**Current phase**: Complete (retroactive capture closed)  
**Last updated**: 2026-04-24 18:07 UTC  
**Next milestone**: None (package complete).  
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `docs/work-packages/20260424_rq_worker_nodb_cache_hardening/artifacts/2026-04-24_security_review.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Captured incident failure context and runtime signature (`Redis NoDb cache client is unavailable`) (2026-04-24 17:01 UTC).
- [x] Hardened Redis reconnect helpers to avoid stale-global poisoning after failed `ping()` (2026-04-24 17:18 UTC).
- [x] Added NoDb lock-ownership guard before `dump()` and removed foreign-lock force-unlock fallback in `locked()` failure paths (2026-04-24 17:27 UTC).
- [x] Added worker startup gate script (`docker/rq-worker-startup.sh`) with Redis readiness polling and startup delay controls (2026-04-24 17:34 UTC).
- [x] Wired startup gate + readiness/env contracts in `docker-compose.prod.yml` and `docker-compose.prod.worker.yml` (2026-04-24 17:41 UTC).
- [x] Expanded regression coverage for NoDb lock/cache edge cases and startup contract assertions (2026-04-24 17:48 UTC).
- [x] Completed two independent review rounds and dispositioned all medium/high findings (2026-04-24 18:03 UTC).
- [x] Retroactive work-package documentation completed and linked in project tracker (2026-04-24 18:07 UTC).

## Timeline

- **2026-04-24 17:01 UTC** - Incident observed from failed job (`fceb9433-598e-499f-ae2b-24d38407399f`) with `RuntimeError: Redis NoDb cache client is unavailable`.
- **2026-04-24 17:18 UTC** - Reconnect helper hardening landed for lock/cache client creation and failure reset behavior.
- **2026-04-24 17:34 UTC** - Worker startup gate script introduced to absorb Redis readiness/AOF windows.
- **2026-04-24 17:48 UTC** - First targeted validation pass green.
- **2026-04-24 18:03 UTC** - Second-round review findings dispositioned; post-fix validation green.
- **2026-04-24 18:07 UTC** - Retroactive package finalized and marked complete.

## Decisions Log

### 2026-04-24 17:18 UTC: Preserve explicit failure semantics for unavailable Redis clients
**Context**: Incident failures came from explicit `RuntimeError` contracts in NoDb cache clear paths.

**Options considered**:
1. Add silent fallback and continue without Redis cache operations.
2. Keep explicit failures but harden reconnect behavior so transient startup failures recover.

**Decision**: Option 2.

**Impact**: Preserves diagnosability and canonical contracts while reducing false-negative startup failures.

---

### 2026-04-24 17:27 UTC: Enforce lock ownership token checks before persistence
**Context**: Review identified stale/foreign lock ownership risks around `dump()` and failure cleanup.

**Options considered**:
1. Keep `islocked()` (any-owner) check and force unlock fallback on persistence failures.
2. Require local-token ownership match for `dump()` and never force-unlock foreign locks.

**Decision**: Option 2.

**Impact**: Prevents cross-owner lock corruption and protects shared run state under race conditions.

---

### 2026-04-24 17:34 UTC: Add startup gating instead of fixed-only sleep
**Context**: User requested startup delay practicality for AOF windows.

**Options considered**:
1. Fixed sleep only.
2. Redis readiness polling + configurable optional delay.

**Decision**: Option 2.

**Impact**: Workers start promptly when Redis is ready, but can still absorb post-ready warm-up windows with a tuned delay.

---

### 2026-04-24 17:57 UTC: Treat package as security-impact high
**Context**: Scope includes worker subprocess startup path and queue/Redis operational boundaries.

**Options considered**:
1. Low-impact triage with no dedicated security artifact.
2. High-impact triage with dedicated security gate artifact.

**Decision**: Option 2.

**Impact**: Required a dedicated security review and explicit closure of ops/security medium findings.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Redis startup timing causes transient worker failures | High | Medium | Readiness polling + configurable startup delay | Closed |
| NoDb writes under foreign lock ownership | High | Low-Medium | Token ownership check in `dump()` and no force unlock fallback | Closed |
| Worker host misconfiguration (`RQ_REDIS_URL`) points to wrong Redis | Medium | Medium | Required env contract and startup URL validation | Closed |
| Compose/docs drift after hardening edits | Medium | Medium | Contract tests + doc updates + second-round review | Closed |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/nodb/test_base_misc.py tests/nodb/test_base_unit.py tests/docker/unit/test_rq_worker_startup_contract.py --maxfail=1` (`61 passed`).
- [x] Added regression tests for lock-ownership guard branches and reconnect retries.
- [x] Added/updated compose/startup contract assertions.

### Security
- [x] Security impact triage recorded (`high`) with rationale.
- [x] Dedicated security review artifact completed.
- [x] No unresolved medium/high security findings remain.

### Documentation
- [x] `docker/README.md` updated for worker startup/readiness contracts.
- [x] Retroactive package docs and artifacts captured.
- [x] `PROJECT_TRACKER.md` updated with completed package entry.

### Testing and Config Validation
- [x] `bash -n docker/rq-worker-startup.sh`.
- [x] `docker compose --env-file docker/.env -f docker/docker-compose.prod.yml config -q`.
- [x] `RQ_REDIS_URL=redis://redis:6379/9 docker compose --env-file docker/.env -f docker/docker-compose.prod.worker.yml config -q`.
- [x] `wctl doc-lint --path docker/README.md`.

## Progress Notes

### 2026-04-24 17:01 UTC: Incident triage and first hardening pass
**Agent/Contributor**: Codex

**Work completed**:
- Traced repeated runtime failure path from `modify_landuse_mapping_rq` into `clear_nodb_file_cache()`.
- Hardened reconnect behavior for NoDb Redis clients.
- Added worker startup gate script and compose integration.

**Blockers encountered**:
- No blocker; review pass identified additional medium/high gaps that required follow-up fixes.

**Next steps**:
- Run targeted validation.
- Run independent code/QA/ops-security reviews.

**Test results**: targeted suite passed (`59 passed`) before second-round follow-up fixes.

### 2026-04-24 18:03 UTC: Second-round finding closure
**Agent/Contributor**: Codex

**Work completed**:
- Dispositioned second-round high/medium findings (lock-ownership branch coverage, compose/docs consistency, startup URL fail-fast/redaction).
- Updated docs/examples to align with startup wrapper contract.
- Re-ran targeted validation and review gate.

**Blockers encountered**:
- None.

**Next steps**:
- Finalize retroactive package docs and tracker integration.

**Test results**: targeted suite passed (`61 passed`).

## Communication Log

### 2026-04-24 17:01 UTC: Incident report and retry confirmation
**Participants**: User, Codex  
**Question/Topic**: Repeat job failure with `Redis NoDb cache client is unavailable`.  
**Outcome**: Root cause narrowed to Redis client availability/reconnect and worker startup timing.

### 2026-04-24 17:08 UTC: Startup delay practicality
**Participants**: User, Codex  
**Question/Topic**: Whether startup delay for `rq-worker` and `rq-worker-batch` is practical for Redis AOF windows.  
**Outcome**: Implemented readiness probe + configurable delay strategy.

### 2026-04-24 17:12 UTC: Multi-agent review request
**Participants**: User, Codex  
**Question/Topic**: Dispatch agents for code and container configuration review.  
**Outcome**: Two review rounds executed; all medium/high findings dispositioned and validated.

### 2026-04-24 18:07 UTC: Retroactive package request
**Participants**: User, Codex  
**Question/Topic**: Capture completed hardening as a retroactive work-package.  
**Outcome**: Package created and closed with full artifact set and tracker integration.
