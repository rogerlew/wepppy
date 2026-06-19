# Security Review - SSURGO Project SQLite Cache

> Initial security review artifact for a high-impact work package. Gate status is `fail` until implementation, evidence, and finding disposition are complete.

## Metadata

- **Package**: `docs/work-packages/20260619_ssurgo_project_sqlite_cache/`
- **Reviewer**: Codex
- **Date**: 2026-06-19
- **Scope reviewed**: Package scope only; implementation pending.
- **Commit/branch context**: Working tree package authoring state.
- **Related artifacts**:
  - Code review: `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/code_review_findings.md` (pending implementation)
  - QA review: `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/qa_review_findings.md` (pending implementation)
  - Package authoring review: `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/package_authoring_review_findings.md`

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The implementation will modify an authenticated build endpoint payload and create/delete run-scoped SQLite files under `<wd>/soils/`.
- **Threat model assumptions**:
  - Request payload fields are untrusted even when sent by the first-party UI.
  - Cache file paths must be derived from `Soils.soils_dir`, not from request payloads or serialized absolute paths.
  - Cache clearing must not delete generated `.sol` files, user uploads, or artifacts outside the run's `soils` directory.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | File system boundary | Implementation evidence is pending for path confinement and safe cache-sidecar deletion. | Package authoring only. | Prove cache paths are derived from `Soils.soils_dir`, resolve under `soils_dir`, and delete only `<cache_path>`, `<cache_path>-wal`, and `<cache_path>-shm`. | Open |
| SEC-02 | Medium | RQ route payload | Implementation evidence is pending for typed boolean parsing and batch/no-enqueue persistence. | Package authoring only. | Add route tests for checked, absent, and batch-mode payloads. | Open |
| SEC-03 | Medium | Queue/worker consistency | Implementation evidence is pending that queue shape and directory-root locking remain safe. | Package authoring only. | Preserve `build_soils_rq(runid)` queue shape unless catalog/docs are updated; keep cache clearing inside existing directory-root/NoDb lock boundaries. | Open |

Risk acceptance authority: `Accepted-risk` requires security reviewer recommendation plus explicit package owner acknowledgment in Sign-off.

## Verdict

- **Gate status**: fail
- **Unresolved findings**:
  - High: 1
  - Medium: 2
  - Low: 0
- **Release recommendation**: hold until implementation evidence and security finding disposition are complete.

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
- [ ] Added/changed services mount only required secrets (least privilege).
- [ ] Rotation and rollback behavior are documented for new secret dependencies.
- [ ] Changed code avoids fallback wrappers that silently skip missing secrets.

### 3) Input Validation and Output Safety

- [ ] Untrusted input is validated at boundaries (types, ranges, enum membership).
- [ ] File/path inputs block traversal and out-of-scope path access.
- [ ] Rendered output paths avoid unsafe HTML/markdown/script injection.
- [ ] URL fetch/download flows enforce allowlist or explicit safety constraints.
- [ ] Unsafe deserialization and shell interpolation patterns are absent.
- [ ] Failing validation returns explicit contract-compliant errors.

### 4) File System and Run-Tree Boundaries

- [ ] Writes remain inside intended run roots (`/wc1/runs/...`) and approved paths.
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

- [ ] NoDb lock/dump contracts are preserved (`dump_and_unlock`, lock scope).
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
  - Pending implementation.
- Manual checks run:
  - Package scoping reviewed by `reviewer` and `qa_reviewer` subagents.

## Residual Risk

- **Accepted residual risks**: none
- **Follow-up packages/issues**: none

## Sign-off

- **Security reviewer**: Pending implementation review.
- **Package owner**: Pending implementation review.

