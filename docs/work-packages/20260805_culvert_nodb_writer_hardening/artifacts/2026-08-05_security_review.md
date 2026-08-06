# Security Review - Culvert NoDb Writer Hardening

## Metadata

- **Package**: `docs/work-packages/20260805_culvert_nodb_writer_hardening/`
- **Reviewer**: independent Codex reviewer `batch_runtime_station_review`
- **Date**: 2026-08-06 UTC
- **Scope reviewed**: culvert submit route, parent/child/finalizer RQ tasks,
  shared and run-local persistence, tests, and generated queue graph artifacts.
- **Commit/branch context**: `master`, base
  `bf88592dddd728df124edeff2ed78283148c2cdc`
- **Related artifacts**:
  - Code review: `2026-08-05_code_review_disposition.md`
  - QA review: `2026-08-05_qa_review_disposition.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: the package touches an authenticated public upload
  handler, queue workers, filesystem-backed run state, and concurrency/data
  integrity. The route change is removal-only after enqueue and does not widen
  its attack surface.
- **Threat model assumptions**:
  - rq-engine continues to authenticate submit/retry/finalize requests with the
    existing JWT scopes.
  - Batch UUIDs are server-reserved and RQ task arguments originate from the
    validated route/pipeline.
  - RQ workers and the `/wc1/culverts` storage boundary are trusted production
    infrastructure; uploaded payload contents remain untrusted.

## Findings

No security findings. The independent review's one Medium finding was a
correctness/data-freshness defect, remediated before sign-off; it did not permit
unauthorized access or stale writes to bypass the generation guard.

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: ship after normal deployment controls.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] `culvert:batch:submit` authentication and response contracts are
  unchanged.
- [x] Retry/finalize authorization paths are unchanged.
- [x] No CSRF, JWT, browse-token, session, or error-disclosure behavior changed.

### 2) Secrets and Credential Handling

- [x] No secret, credential, environment default, or token handling changed.
- [x] No secret material was added to code, tests, or package artifacts.

### 3) Input Validation and Output Safety

- [x] Upload size/archive/payload validation is unchanged.
- [x] Child tasks fail closed when the parent runner is absent or its UUID does
  not match the task argument.
- [x] Public response shape and status URL behavior remain unchanged.

### 4) File System and Run-Tree Boundaries

- [x] Writes remain under the existing `/wc1/culverts/<batch UUID>` boundary.
- [x] Children own only distinct `runs/<Point_ID>/` directories and do not
  create or lock the shared runner.
- [x] No path-join, symlink, archive extraction, or download policy changed.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] Queue names, task arguments, dependencies, timeouts, and retry endpoints
  are semantically unchanged.
- [x] Generated RQ graph artifacts are current and `wctl check-rq-graph` passes.
- [x] No subprocess or shell invocation changed.

### 6) Agentic Tooling and External Integrations

- [x] No agent/MCP permissions, network calls, external service trust, or
  dependency changed.

### 7) Data Integrity, Locking, and Concurrency

- [x] The NoDb generation guard is unchanged and remains mandatory.
- [x] Stale parent state is discarded and rehydrated before a bounded retry.
- [x] Parallel children no longer mutate shared `_runs`; the finalizer replaces
  its authoritative outcome fields from current run-local metadata.
- [x] Retry finalization cannot retain a previous error after current success.

### 8) Logging, Monitoring, Rollback, and Incident Readiness

- [x] Stale retry and exhaustion remain observable in RQ/log failures.
- [x] No new error handler swallows a persistence failure.
- [x] Rollback is a normal code rollback; no schema or data migration is needed.
- [x] The package defines 30-day health and danger signals.

## Validation Evidence

- `wctl run-pytest tests/microservices/test_rq_engine_culverts.py tests/culverts/test_culvert_batch_rq.py tests/culverts/test_culvert_orchestration.py tests/culverts/test_culverts_runner.py --maxfail=1` - `43 passed`.
- `wctl run-pytest tests --maxfail=1` - `5,842 passed`, `61 skipped`.
- `wctl check-rq-graph` - pass.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` - pass, net delta `-4`.
- `wctl doc-lint ...` and `git diff --check` - pass.

## Residual Risk

- Multi-process scheduling is represented by deterministic stale-generation
  simulation; production observation is required for 30 days.
- Concurrent manual finalizers can still cause one strict stale failure rather
  than silently merge. This is the intended safe failure mode.
- Manual retry RQ identity is authoritative in the retry response/RQ metadata;
  an older parent-planned receipt may remain in shared NoDb state.

## Sign-off

- **Security reviewer**: `batch_runtime_station_review`, 2026-08-06 UTC
- **Package owner**: Codex, 2026-08-06 UTC
