# Security Review - RQ Worker Startup and NoDb Redis Cache Hardening

## Metadata

- **Package**: `docs/work-packages/20260424_rq_worker_nodb_cache_hardening/`
- **Reviewer**: Codex + independent `ops_security_control_agent` review rounds
- **Date**: 2026-04-24
- **Scope reviewed**:
  - `docker/rq-worker-startup.sh`
  - `docker/docker-compose.prod.yml`
  - `docker/docker-compose.prod.worker.yml`
  - `docker/README.md`
  - `wepppy/nodb/base.py`
  - related regression tests under `tests/nodb/` and `tests/docker/unit/`
- **Commit/branch context**: local working tree (retroactive package capture)
- **Related artifacts**:
  - Code review: `docs/work-packages/20260424_rq_worker_nodb_cache_hardening/artifacts/2026-04-24_code_review.md`
  - QA review: `docs/work-packages/20260424_rq_worker_nodb_cache_hardening/artifacts/2026-04-24_qa_review.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: scope changes queue worker startup behavior, Redis connection enforcement, and lock-ownership safety in shared NoDb state paths.
- **Threat model assumptions**:
  - Worker hosts use secret-file based Redis credentials (`REDIS_PASSWORD_FILE`).
  - Redis availability can be delayed during persistence/AOF recovery windows.
  - Multiple workers/processes can contend for the same run-scoped NoDb lock.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Data integrity / locking | `dump()` path allowed write with any lock, not owner-verified token. | `wepppy/nodb/base.py` pre-fix review finding | Require ownership token check before persist. | Resolved |
| SEC-02 | Medium | Queue/worker startup | Malformed Redis URL could degrade to localhost semantics via resolver fallback. | review finding + startup script path | Validate raw URL and fail-fast before probing/worker start. | Resolved |
| SEC-03 | Medium | Secrets/logging | Invalid URL fail-fast message initially printed raw URL text, risking credential leakage when inline credentials are used. | review finding on `rq-worker-startup.sh` | Redact/omit raw URL from error text. | Resolved |
| SEC-04 | Medium | Deployment contract | Worker docs and compose dependency semantics drifted (`weppcloudr` dependency, startup wrapper bypass example). | review findings in compose/docs | Align docs with enforced compose contracts and startup wrapper usage. | Resolved |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: `0`
  - Medium: `0`
  - Low: `0`
- **Release recommendation**: `ship`

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] No new authn/authz bypass surfaces introduced.
- [x] No CSRF/session boundary changes introduced in this package.

### 2) Secrets and Credential Handling

- [x] No secrets added to repo defaults or docs examples.
- [x] Secret-file contract preserved (`REDIS_PASSWORD_FILE`, `*_FILE` envs).
- [x] Startup error logging avoids emitting raw Redis URL credentials.

### 3) Input Validation and Output Safety

- [x] Startup path now validates raw Redis URL shape before use.
- [x] No unsafe shell interpolation was added to worker command composition.

### 4) File System and Run-Tree Boundaries

- [x] No broadened run-tree write surfaces introduced.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] Worker startup now gates on Redis readiness with bounded timeout/interval controls.
- [x] Worker-only compose enforces explicit external Redis URL contract.
- [x] Failure handling remains explicit (no silent skip/fallback for unavailable cache client).

### 6) Agentic Tooling and MCP Surfaces

- [x] No MCP permission widening in implementation scope.

### 7) Network and External Integrations

- [x] No new external egress surfaces added.
- [x] Redis probing uses bounded socket/connect timeouts.

### 8) CI/CD and Supply Chain

- [x] No new third-party dependency introduced.

### 9) Data Integrity, Locking, and Concurrency

- [x] Lock ownership must match local token before `dump()` persists.
- [x] `locked()` no longer force-unlocks foreign-owner locks on persistence failure.
- [x] Reconnect helper behavior is regression tested for failed ping retry safety.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Incident-signature failure paths remain explicit and diagnosable.
- [x] Startup-readiness controls documented for operators.

## Validation Evidence

- Automated checks run:
  - `wctl run-pytest tests/nodb/test_base_misc.py tests/nodb/test_base_unit.py tests/docker/unit/test_rq_worker_startup_contract.py --maxfail=1` (`61 passed`)
  - `docker compose --env-file docker/.env -f docker/docker-compose.prod.yml config -q`
  - `RQ_REDIS_URL=redis://redis:6379/9 docker compose --env-file docker/.env -f docker/docker-compose.prod.worker.yml config -q`
  - `wctl doc-lint --path docker/README.md`
- Manual checks run:
  - startup wrapper shell syntax check (`bash -n docker/rq-worker-startup.sh`) - pass.

## Residual Risk

- **Accepted residual risks**:
  - None.
- **Follow-up packages/issues**:
  - Optional follow-up for production-host evidence capture (`wepp1`/`wepp2` worker health snapshots after deploy).

## Sign-off

- **Security reviewer**: Codex + `ops_security_control_agent`, 2026-04-24
- **Package owner**: Codex, 2026-04-24
