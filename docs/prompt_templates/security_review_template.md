# Security Review - [Package Title]

> Use this template when a work package has security impact beyond routine correctness/QA checks.
> Link this artifact from the package tracker and closeout notes.

## Metadata

- **Package**: `docs/work-packages/YYYYMMDD_slug/`
- **Reviewer**: [Name/agent]
- **Date**: YYYY-MM-DD
- **Scope reviewed**: [Files/routes/services]
- **Commit/branch context**: [SHA or branch]
- **Related artifacts**:
  - Code review: `docs/work-packages/.../artifacts/..._code_review.md`
  - QA review: `docs/work-packages/.../artifacts/..._qa_review.md`

## Security Triage Decision

- **Security impact level**: `none | low | high`
- **Dedicated security review required**: `yes | no`
- **Triage rationale**: [Why this package does/does not change attack surface]
- **Threat model assumptions**:
  - [Assumption 1]
  - [Assumption 2]
  - [Assumption 3]

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High/Medium/Low | [surface name] | [what can go wrong] | [file/test/log reference] | [specific fix] | Open/Resolved/Accepted-risk |

Risk acceptance authority: `Accepted-risk` requires security reviewer recommendation plus explicit package owner acknowledgment in Sign-off.

## Verdict

- **Gate status**: `pass | fail`
- **Unresolved findings**:
  - High: [count]
  - Medium: [count]
  - Low: [count]
- **Release recommendation**: [ship/ship-with-conditions/hold]

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
- [ ] Security-relevant events have observable signals (auth failures, denials, exfil attempts).
- [ ] New error handlers do not swallow exceptions silently.
- [ ] Alerting/operational checks are updated for new high-risk surfaces.
- [ ] Rollback and containment steps are documented for the changed scope.

## Validation Evidence

- Automated checks run:
  - `wctl run-pytest [target]`
  - `wctl check-rq-graph` (if queue wiring touched)
  - `wctl run-npm lint && wctl run-npm test` (if frontend changed)
  - `wctl doc-lint --path [changed docs]` (if docs changed)
- Manual checks run:
  - [Check name] - [result]
  - [Check name] - [result]

## Residual Risk

- **Accepted residual risks**:
  - [risk + justification + owner]
- **Follow-up packages/issues**:
  - [link/path + scope]

## Sign-off

- **Security reviewer**: [name/agent], YYYY-MM-DD
- **Package owner**: [name/agent], YYYY-MM-DD
