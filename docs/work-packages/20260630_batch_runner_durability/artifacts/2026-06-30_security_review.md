# Security Review - Batch Runner Durability

## Metadata

- **Package**: `docs/work-packages/20260630_batch_runner_durability/`
- **Reviewer**: Codex
- **Date**: 2026-06-30
- **Scope reviewed**: `wepppy/rq/batch_rq.py`, `wepppy/nodb/batch_runner.py`, `wepppy/microservices/rq_engine/batch_routes.py`, Batch Runner README, RQ graph artifacts, and focused tests.
- **Commit/branch context**: local uncommitted implementation after scaffold commit `82d7b8805`
- **Related artifacts**:
  - Production evidence: `docs/work-packages/20260630_batch_runner_durability/artifacts/wepp1_exception_evidence_20260630.md`
  - Dual-agent disposition: `docs/work-packages/20260630_batch_runner_durability/artifacts/2026-06-30_dual_agent_review_disposition.md`
  - Tests: `tests/rq/test_batch_rq_retry_selection.py`, `tests/microservices/test_rq_engine_batch_routes.py`

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The package changes admin-triggered queue orchestration, worker retry selection, active-job conflict behavior, and run-tree metadata written by workers. Queue and worker surfaces are high impact by repository policy.
- **Threat model assumptions**:
  - Run Batch remains admin-only through existing JWT scope and role checks.
  - Batch names are validated before run/delete route path resolution.
  - Worker task inputs remain internal watershed feature objects produced from a validated batch resource and safe generated leaf run IDs.
  - Run metadata is written inside the resolved per-leaf batch run directory, not from user-supplied paths.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Queue orchestration | Retry filtering could accidentally bypass active-job conflict checks and enqueue overlapping work. | Route and worker changes touch `batch_routes.py` and `batch_rq.py`. | Add route-level and worker-side active batch tests. | Resolved |
| SEC-02 | Medium | Data integrity | Stale failure metadata could force repeated reruns or hide successful reruns if status precedence is wrong. | Existing success path did not write metadata. | Add tests for stale failed metadata superseded by completed task timestamps and success metadata. | Resolved |
| SEC-03 | Low | Exception boundary hygiene | Changed-file broad exception enforcement flags existing broad boundary catches in touched files. The implementation did not add new broad catches. | `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` fails on existing catches in `batch_routes.py` and `batch_rq.py`. | Track as residual broad-exception cleanup or allowlist review; do not block local retry-selection behavior. | Accepted-risk |
| SEC-04 | High | Lock integrity | Delete worker cleared NoDb caches/locks before its active-job guard. | Dual-agent review found cleanup before `_active_batch_job_summaries()` in `delete_batch_rq`. | Move active-job guard before all cleanup and add regression coverage. | Resolved |
| SEC-05 | Medium | Run-tree boundary | Retry classifier hand-joined leaf run IDs into paths. | Dual-agent review found generated run IDs were not rejected for `/`, `\\`, `.`, or `..`. | Reject unsafe generated run IDs and fail closed in classifier. | Resolved |
| SEC-06 | Medium | Worker diagnostics | Metadata task-status collection could alter worker outcome on corrupt RedisPrep state. | Dual-agent review found `RedisPrep.lazy_load()` decode failures could escape metadata collection. | Make diagnostic task status best-effort and record metadata warnings. | Resolved |
| SEC-07 | Medium | Operational truthfulness | Finalizer emitted completion without failed/incomplete counts. | Dual-agent review found unconditional `BATCH_RUN_COMPLETED` after leaf jobs can return `(False, elapsed)`. | Publish final summary and failure-specific trigger while preserving compatibility trigger. | Resolved |
| SEC-08 | Medium | Lock integrity | Batch child NoDir runtime locks used legacy leaf-name scope, allowing stale/cross-batch keys to block retries. | Local `durability_test` retry failed with `NODIR_LOCKED` on climate/soils after cancellation. | Use effective-root path scope with bounded retry for batch child root locks. | Resolved |
| SEC-09 | Medium | Lock integrity | Reused batch child workspaces could retain stale NoDb controller locks from canceled climate builds and crash retry startup. | Local `durability_test` retry failed with empty `AssertionError`; climate logs stopped at `assert not self.islocked()`. | Clear child-scoped NoDb cache and locks before `RedisPrep` and controller loading on every watershed worker start. | Resolved |
| SEC-10 | Medium | Lock integrity | Stale path-scoped runtime locks from dead prior worker containers could block selected leaves for the full TTL. | Local WA-174 retry failed with `NODIR_LOCKED` held by old owner `fbdc2c500f0a:199`; that container was no longer running. | Clear exact child/root path-scoped runtime locks after active-job preflight and before enqueue. | Resolved |
| SEC-11 | Low | Operational truthfulness | Parent Run Batch job returned an unserializable RQ `Job` object, causing dashboard failed/canceled status after successful child enqueue. | RQ job `871f4334-479d-4e63-95f8-f80fe9e01c98` had `result=Unserializable return value` and no `exc_info`. | Return a serializable summary dict with finalizer job id and selection counts. | Resolved |
| SEC-12 | Medium | Data integrity | Watershed retry could resume after a hillslope timestamp while required hillslope interchange parquet was missing from an interrupted conversion. | Local `OR,WA-101`/`OR,WA-102` retries failed missing `H.wat.parquet`/`H.pass.parquet` with partial `.tmp` files present. | Ensure hillslope interchange before watershed execution whenever watershed is selected. | Resolved |

Risk acceptance authority: `Accepted-risk` requires security reviewer recommendation plus explicit package owner acknowledgment in Sign-off.

## Verdict

- **Gate status**: pass with low residual risk
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 1 accepted residual
- **Release recommendation**: ship locally for review; production rollout still requires active-job preflight and operator approval.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Entry points enforce expected authn/authz checks for changed routes/services.
- [x] Role checks and scope checks are explicit, least-privilege, and regression-tested.
- [x] Session/JWT token validation paths preserve canonical contracts.
- [x] CSRF protections are preserved for browser session mutation paths.
- [x] Cross-service auth token mint/verify flows are not widened unintentionally.
- [x] Error paths do not disclose token contents or auth internals.

### 2) Secrets and Credential Handling

- [x] No new plaintext secrets in repository files, env defaults, or docs examples.
- [x] `*_FILE` secret-file contract is not changed.
- [x] No secrets passed in argv, query params, or logs.
- [x] No new service secret mounts are introduced.
- [x] No new secret dependencies require rotation/rollback handling.
- [x] Changed code avoids fallback wrappers that silently skip missing secrets.

### 3) Input Validation and Output Safety

- [x] No new public request payload is introduced.
- [x] Batch names and generated leaf run IDs are validated before path-sensitive operations.
- [x] File/path writes remain derived from `BatchRunner` working directories and composite run id resolution.
- [x] No rendered HTML/markdown/script output is introduced.
- [x] No URL fetch/download flow is changed.
- [x] Unsafe deserialization and shell interpolation patterns are absent.
- [x] Failing validation returns explicit contract-compliant errors for the route change.

### 4) File System and Run-Tree Boundaries

- [x] Writes remain inside intended batch leaf run roots.
- [x] Generated leaf run IDs reject path separators, nulls, `.`, and `..`; legacy invalid leaves classify as `invalid`.
- [x] Export/download paths are unchanged.
- [x] Temporary files and artifacts are not introduced.
- [x] Permissions for generated files/directories follow existing run metadata write behavior.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] Enqueue sites and dependency edges remain intentional and documented.
- [x] Worker task inputs remain existing batch name and watershed feature arguments.
- [x] Subprocess invocation is unchanged.
- [x] Queue retry paths cannot bypass auth through the normal route and include a worker-side active-job guard for manually enqueued parents.
- [x] Delete worker checks active jobs before any cache/lock cleanup.
- [x] `wctl check-rq-graph` has been run and graph artifacts are current.
- [x] Failure handling preserves the existing `(False, elapsed)` worker contract while adding durable metadata.

### 6) Agentic Tooling and MCP Surfaces

- [x] No agent/tool runtime surface is changed.
- [x] No path for implicit privilege escalation through subagents or helper tools is introduced.
- [x] No MCP/tool tokens or credentials are involved.
- [x] Tool execution constraints are documented in the package tracker.
- [x] No unauthorized network egress or public artifact publication is introduced.

### 7) Network and External Integrations

- [x] No new outbound calls are introduced.
- [x] Timeout/retry behavior for RQ jobs is unchanged.
- [x] Internal-only endpoints are not exposed through new proxy/route changes.
- [x] Active-job conflict handling reduces high-cost duplicate submissions.
- [x] No external dependency trust assumptions changed.

### 8) CI/CD and Supply Chain

- [x] Self-hosted runner access scope is unchanged.
- [x] Workflow token permissions are unchanged.
- [x] Build/test scripts avoid exposing credentials in logs.
- [x] No new third-party dependencies are introduced.
- [x] No pinned versions/digests are changed.

### 9) Data Integrity, Locking, and Concurrency

- [x] NoDb lock/dump contracts are preserved.
- [x] Cross-process shared state updates remain existing RQ/NoDb patterns.
- [x] Redis keyspaces and TTL behavior are unchanged.
- [x] Concurrent duplicate mutation is guarded by active-job checks at route and worker boundaries.
- [x] Worker-side delete cleanup cannot clear locks while active batch jobs are detected.
- [x] Batch child root mutations use path-scoped NoDir maintenance locks to avoid stale legacy leaf-name collisions.
- [x] Reused batch child runs clear stale NoDb cache/locks before loading `RedisPrep` and controllers.
- [x] Parent Run Batch clears exact selected-leaf path-scoped runtime locks after active-job preflight and before child enqueue.
- [x] Watershed retries ensure hillslope interchange outputs before watershed post-processing consumes them.
- [x] Recovery after partial failure leaves state diagnosable through run metadata and runstate classification.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Logs/status messages include enough context for incident triage without exposing secrets.
- [x] Finalizer publishes run summary counts and a failure-specific trigger when leaves remain retry-eligible.
- [x] Active duplicate submissions return explicit `batch_busy` signals.
- [x] Parent Run Batch returns a serializable result so dashboard status reflects enqueue success.
- [x] No new broad exception handlers were introduced.
- [x] Operational checks are documented in the package tracker.
- [x] Production rollout remains gated by active-job preflight.

## Validation Evidence

- Automated checks run:
  - `wctl run-pytest tests/runtime_paths/test_mutations_thaw_freeze_contract.py::test_clear_runtime_locks_for_scope_only_deletes_exact_path_scope --maxfail=1` - 1 passed.
  - `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1` - 18 passed.
  - `wctl run-pytest tests/microservices/test_rq_engine_batch_routes.py --maxfail=1` - 10 passed.
  - `wctl run-pytest tests/weppcloud/test_batch_runner_endpoints.py --maxfail=1` - 9 passed.
  - `wctl check-rq-graph` - passed after regenerating graph artifacts.
  - `git diff --check` - passed.
  - `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` - failed on pre-existing broad catches in touched files; no new broad catches were added.
- Manual checks run:
  - Reviewed `git diff` for changed queue, metadata, status, route, and test surfaces.
  - Dispatched independent correctness/RQ and security/data-integrity review agents; disposition recorded in `2026-06-30_dual_agent_review_disposition.md`.
  - Confirmed unrelated dirty WEPP binaries remain outside this package scope.

## Residual Risk

- **Accepted residual risks**:
  - Existing broad exception boundary catches in touched files remain. They predate this implementation and should be handled by broad-exception cleanup work or allowlist review, not hidden by this package.
- **Follow-up packages/issues**:
  - Consider UI preview of retry set after backend contract lands.
  - Consider a focused broad-exception cleanup for `wepppy/rq/batch_rq.py` and `wepppy/microservices/rq_engine/batch_routes.py`.

## Sign-off

- **Security reviewer**: Codex, 2026-06-30
- **Package owner**: Codex, 2026-06-30
