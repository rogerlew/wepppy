# Security Review - Batch Runner Durability

> Initial placeholder for the required security review. Complete this after implementation and before production rollout.

## Metadata

- **Package**: `docs/work-packages/20260630_batch_runner_durability/`
- **Reviewer**: TBD
- **Date**: 2026-06-30
- **Scope reviewed**: Planned changes to `wepppy/rq/batch_rq.py`, `wepppy/nodb/batch_runner.py`, `wepppy/microservices/rq_engine/batch_routes.py`, batch run metadata, and focused tests.
- **Commit/branch context**: TBD
- **Related artifacts**:
  - Production evidence: `docs/work-packages/20260630_batch_runner_durability/artifacts/wepp1_exception_evidence_20260630.md`

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The package changes admin-triggered queue orchestration, worker retry selection, active-job conflict behavior, and run-tree metadata written by workers. Queue and worker surfaces are high impact by repository policy.
- **Threat model assumptions**:
  - Run Batch remains admin-only through existing JWT scope and role checks.
  - Batch names continue to be validated by existing route/config constraints.
  - Worker task inputs remain internal watershed feature objects produced from a validated batch resource.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Queue orchestration | Retry filtering could accidentally bypass active-job conflict checks and enqueue overlapping work. | Planned changes touch `batch_routes.py` and `batch_rq.py`. | Add route-level and worker-side active batch tests. | Open |
| SEC-02 | Medium | Data integrity | Stale failure metadata could force repeated reruns or hide successful reruns if status precedence is wrong. | Existing success path does not write metadata. | Add tests for stale failed metadata superseded by completed task timestamps and success metadata. | Open |

Risk acceptance authority: `Accepted-risk` requires security reviewer recommendation plus explicit package owner acknowledgment in Sign-off.

## Verdict

- **Gate status**: fail
- **Unresolved findings**:
  - High: 0
  - Medium: 2
  - Low: 0
- **Release recommendation**: hold until implementation and review are complete.

## Surface Checks

### 1) Auth, Session, and Authorization

- [ ] Entry points enforce expected authn/authz checks for changed routes/services.
- [ ] Role checks and scope checks are explicit, least-privilege, and regression-tested.
- [ ] Session/JWT token validation paths preserve canonical contracts.
- [ ] CSRF protections are preserved for browser session mutation paths.
- [ ] Cross-service auth token mint/verify flows are not widened unintentionally.
- [ ] Error paths do not disclose token contents or auth internals.

### 2) Secrets and Credential Handling

- [ ] No new plaintext secrets in repository files, env defaults, or docs examples.
- [ ] `*_FILE` secret-file contract is preserved where applicable.
- [ ] No secrets passed in argv, query params, or logs.
- [ ] Added/changed services mount only required secrets.
- [ ] Rotation and rollback behavior are documented for new secret dependencies.
- [ ] Changed code avoids fallback wrappers that silently skip missing secrets.

### 3) Input Validation and Output Safety

- [ ] Untrusted input is validated at boundaries.
- [ ] File/path inputs block traversal and out-of-scope path access.
- [ ] Rendered output paths avoid unsafe HTML/markdown/script injection.
- [ ] URL fetch/download flows enforce allowlist or explicit safety constraints.
- [ ] Unsafe deserialization and shell interpolation patterns are absent.
- [ ] Failing validation returns explicit contract-compliant errors.

### 4) File System and Run-Tree Boundaries

- [ ] Writes remain inside intended run roots.
- [ ] No new path joins allow escaping run scope via symlink or relative path tricks.
- [ ] Export/download paths avoid leaking unrelated files.
- [ ] Temporary files and artifacts are cleaned up or intentionally retained with policy.
- [ ] Permissions for generated files/directories are least-privilege.

### 5) Queue, Worker, and Subprocess Surfaces

- [ ] Enqueue sites and dependency edges remain intentional and documented.
- [ ] Worker task inputs are validated before shell/subprocess/file operations.
- [ ] Subprocess invocation avoids shell injection and unbounded command composition.
- [ ] Queue cancellation/retry paths cannot bypass auth or data ownership boundaries.
- [ ] `wctl check-rq-graph` has been run when queue wiring changed.
- [ ] Failure handling preserves canonical response/error contracts.

### 6) Agentic Tooling and MCP Surfaces

- [ ] Agent/tool calls do not grant broader permissions than the parent request needs.
- [ ] No path for implicit privilege escalation through subagents or helper tools.
- [ ] MCP/tool tokens and credentials are scoped and not leaked in logs/artifacts.
- [ ] Tool execution constraints are explicit when running commands or file writes.
- [ ] Guardrails block unauthorized network egress or public artifact publication.

### 7) Network and External Integrations

- [ ] New outbound calls are justified, constrained, and observable.
- [ ] Timeouts/retries avoid denial-of-service amplification and unsafe fallback loops.
- [ ] Internal-only endpoints are not exposed through new proxy/route changes.
- [ ] Rate limits/throttles are considered for high-cost or abuse-prone endpoints.
- [ ] External dependency trust assumptions are documented.

### 8) CI/CD and Supply Chain

- [ ] Self-hosted runner access scope is unchanged or tightened.
- [ ] Workflow token permissions are minimal for changed jobs.
- [ ] Build/test scripts avoid exposing credentials in logs.
- [ ] New third-party dependencies passed precedent and risk checks.
- [ ] Pinned versions/digests are used where policy requires.

### 9) Data Integrity, Locking, and Concurrency

- [ ] NoDb lock/dump contracts are preserved.
- [ ] Cross-process shared state updates remain atomic and auditable.
- [ ] Redis keyspaces and TTL behavior are unchanged unless explicitly planned.
- [ ] Concurrent mutation paths include regression coverage for race conditions.
- [ ] Recovery after partial failure leaves state consistent and diagnosable.

### 10) Logging, Monitoring, and Incident Readiness

- [ ] Logs include enough context for incident triage without exposing secrets.
- [ ] Security-relevant events have observable signals.
- [ ] New error handlers do not swallow exceptions silently.
- [ ] Alerting/operational checks are updated for new high-risk surfaces.
- [ ] Rollback and containment steps are documented for the changed scope.

## Validation Evidence

- Automated checks run:
  - TBD: `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1`
  - TBD: `wctl run-pytest tests/microservices/test_rq_engine_batch_routes.py --maxfail=1`
  - TBD: `wctl run-pytest tests/weppcloud/test_batch_runner_endpoints.py --maxfail=1`
  - TBD: `wctl check-rq-graph`
  - TBD: `wctl doc-lint --path docs/work-packages/20260630_batch_runner_durability`
- Manual checks run:
  - TBD

## Residual Risk

- **Accepted residual risks**:
  - None yet.
- **Follow-up packages/issues**:
  - Consider UI preview of retry set after backend contract lands.

## Sign-off

- **Security reviewer**: TBD
- **Package owner**: TBD
