# Security Review - Dedicated Download Service for Critical Run Artifacts

> Initial security artifact for the dedicated download service package. This artifact must be completed with implementation evidence before production rollout.

## Metadata

- **Package**: `docs/work-packages/20260619_dedicated_download_service/`
- **Reviewer**: Codex scaffold; final reviewer TBD
- **Date**: 2026-06-19
- **Scope reviewed**: Planned dedicated archive download service, browse auth/path reuse, Docker Compose service wiring, Caddy route changes.
- **Commit/branch context**: `master` during package scaffold.
- **Related artifacts**:
  - Code review: TBD
  - QA review: TBD

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The package introduces a new externally reachable file-serving service and changes proxy routing for run-scoped artifacts. Auth, path traversal, route shadowing, logging privacy, and operational rollback must be reviewed explicitly.
- **Threat model assumptions**:
  - Attackers may know or guess public route shapes and may try traversal, symlink, encoded-path, or range-header abuse.
  - Some runs are public, while private and root-only paths must remain protected by the canonical browse auth contract.
  - Reverse proxy routing mistakes can expose unintended files or bypass existing browse checks even if service code is correct.
  - Logs may be accessible to operators and must not contain secrets, raw JWTs, raw query filters, or sensitive full filesystem paths.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Auth/path extraction | New service could drift from canonical browse auth and path-boundary behavior. | Implementation pending. | Reuse or faithfully extract existing helpers; add regression tests for private, public, root-only, traversal, missing, and symlink/path-boundary cases. | Open |
| SEC-02 | High | Caddy routing | Exact archive matcher could accidentally capture non-archive downloads or route broader `/download/*` traffic to incomplete service behavior. | Implementation pending. | Add precise route matcher before broad browse matcher; add negative route probes for browse/schema/dtale/files/gdalinfo/parquet CSV/culvert/batch. | Open |
| SEC-03 | Medium | Logging privacy | Enhanced observability could log raw tokens, raw query strings, or full sensitive filesystem paths. | Implementation pending. | Use sanitized path category and basename only; explicitly exclude Authorization, cookies, raw JWTs, raw filters, and full absolute paths from logs. | Open |
| SEC-04 | Medium | Range handling | Malformed or extreme range headers could trigger resource waste or incorrect responses. | Implementation pending. | Parse single ranges defensively; reject invalid ranges with `416`; test open-ended, suffix, malformed, and unsatisfiable ranges. | Open |

Risk acceptance authority: `Accepted-risk` requires security reviewer recommendation plus explicit package owner acknowledgment in Sign-off.

## Verdict

- **Gate status**: fail until implementation evidence closes open findings.
- **Unresolved findings**:
  - High: 2
  - Medium: 2
  - Low: 0
- **Release recommendation**: hold until implementation, tests, route-smoke evidence, and final security review are complete.

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

- [x] Agent/tool calls do not grant broader permissions than the parent request needs.
- [x] No path for implicit privilege escalation through subagents or helper tools introduced by scaffold-only docs.
- [x] MCP/tool tokens and credentials are scoped and not leaked in logs/artifacts.
- [x] Tool execution constraints are explicit when running commands or file writes.
- [x] Guardrails block unauthorized network egress or public artifact publication.

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
- [ ] Security-relevant events have observable signals (auth failures, denials, exfil attempts).
- [ ] New error handlers do not swallow exceptions silently.
- [ ] Alerting/operational checks are updated for new high-risk surfaces.
- [ ] Rollback and containment steps are documented for the changed scope.

## Validation Evidence

- Automated checks run:
  - Pending implementation.
  - Docs scaffold lint pending.
- Manual checks run:
  - Pending implementation.

## Residual Risk

- **Accepted residual risks**:
  - None accepted.
- **Follow-up packages/issues**:
  - Potential follow-up for non-NFS/object-storage archive publication if service telemetry shows NFS remains the main reliability limit.

## Sign-off

- **Security reviewer**: TBD
- **Package owner**: TBD
