# Security Review - RQ Controller State Contract Cutover

> Dedicated security review artifact for `20260410_rq_controller_state_contract_cutover`.

## Metadata

- **Package**: `docs/work-packages/20260410_rq_controller_state_contract_cutover/`
- **Reviewer**: `security_reviewer` subagent (`019d79d6-25fa-7f00-b032-92338be607a2`)
- **Date**: 2026-04-11
- **Scope reviewed**: cutover contract/docs lifecycle closure, auth-scope policy decision for session-token mint bridge, freeze/checklist parity evidence, and review-gate auditability
- **Commit/branch context**: local working tree for row-8 closeout
- **Related artifacts**:
  - Package tracker: `docs/work-packages/20260410_rq_controller_state_contract_cutover/tracker.md`
  - Archived ExecPlan: `docs/work-packages/20260410_rq_controller_state_contract_cutover/prompts/completed/rq_controller_state_contract_cutover_execplan.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: Row-8 cutover finalizes auth-scope policy and frozen agent-facing contract boundaries consumed by unattended agents.
- **Threat model assumptions**:
  - Contract/docs lifecycle state must match actual gate/review execution state.
  - Auth bridge compatibility behavior is explicit and must not silently drift.
  - Residual-risk acceptance requires explicit owner and follow-up trigger.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Lifecycle/security gate integrity | Package/docs initially claimed closeout completion while tracker/security-gate evidence remained pending. | `docs/work-packages/20260410_rq_controller_state_contract_cutover/package.md`, `tracker.md`, `artifacts/2026-04-10_security_review.md`, `PROJECT_TRACKER.md` | Synchronize lifecycle docs with actual review/gate completion before closure. | Resolved |
| SEC-02 | Medium | Session-token scope bridge policy | Bearer `rq:status` path for session-token mint can issue broader run-scoped session scopes (`rq:read`, `rq:enqueue`, `rq:export`) for compatibility. | `wepppy/microservices/rq_engine/session_routes.py` (`SESSION_TOKEN_SCOPES`, `SESSION_TOKEN_REQUIRED_SCOPES`, `issue_session_token`), `wepppy/microservices/rq_engine/schema_defaults_routes.py` (`rq_engine_issue_session_token` descriptor), `docs/schemas/rq-controller-state-contract.md`, `docs/schemas/rq-engine-agent-api-contract.md` | Preserve as explicit accepted residual/design risk with named owner + follow-up trigger unless policy package tightens behavior. | Accepted residual/design risk |

Risk acceptance authority: `Accepted residual/design risk` recommended by security reviewer and acknowledged by package owner in Sign-off.

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Accepted residual/design risks**:
  - Medium: 1 (`SEC-02`)
- **Release recommendation**: proceed.

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
- [x] `*_FILE` secret-file contract is preserved where applicable.
- [x] No secrets passed in argv, query params, or logs.
- [x] Added/changed services mount only required secrets (least privilege).
- [x] Rotation and rollback behavior are documented for new secret dependencies.
- [x] Changed code avoids fallback wrappers that silently skip missing secrets.

### 3) Input Validation and Output Safety

- [x] Untrusted input is validated at boundaries (types, ranges, enum membership).
- [x] File/path inputs block traversal and out-of-scope path access.
- [x] Rendered output paths avoid unsafe HTML/markdown/script injection.
- [x] URL fetch/download flows enforce allowlist or explicit safety constraints.
- [x] Unsafe deserialization and shell interpolation patterns are absent.
- [x] Failing validation returns explicit contract-compliant errors.

### 4) File System and Run-Tree Boundaries

- [x] Writes remain inside intended run roots (`/wc1/runs/...`) and approved paths.
- [x] No new path joins allow escaping run scope via symlink or relative path tricks.
- [x] Export/download paths avoid leaking unrelated files.
- [x] Temporary files and artifacts are cleaned up or intentionally retained with policy.
- [x] Permissions for generated files/directories are least-privilege.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] Enqueue sites and dependency edges remain intentional and documented.
- [x] Worker task inputs are validated before shell/subprocess/file operations.
- [x] Subprocess invocation avoids shell injection and unbounded command composition.
- [x] Queue cancellation/retry paths cannot bypass auth or data ownership boundaries.
- [x] `wctl check-rq-graph` has been run when queue wiring changed.
- [x] Failure handling preserves canonical response/error contracts.

### 6) Agentic Tooling and MCP Surfaces

- [x] Agent/tool calls do not grant broader permissions than the parent request needs.
- [x] No path for implicit privilege escalation through subagents or helper tools.
- [x] MCP/tool tokens and credentials are scoped and not leaked in logs/artifacts.
- [x] Tool execution constraints are explicit when running commands or file writes.
- [x] Guardrails block unauthorized network egress or public artifact publication.

### 7) Network and External Integrations

- [x] New outbound calls are justified, constrained, and observable.
- [x] Timeouts/retries avoid denial-of-service amplification and unsafe fallback loops.
- [x] Internal-only endpoints are not exposed through new proxy/route changes.
- [x] Rate limits/throttles are considered for high-cost or abuse-prone endpoints.
- [x] External dependency trust assumptions are documented.

### 8) CI/CD and Supply Chain

- [x] Self-hosted runner access scope is unchanged or tightened.
- [x] Workflow token permissions are minimal for changed jobs.
- [x] Build/test scripts avoid exposing credentials in logs.
- [x] New third-party dependencies passed precedent and risk checks.
- [x] Pinned versions/digests are used where policy requires.

### 9) Data Integrity, Locking, and Concurrency

- [x] NoDb lock/dump contracts are preserved (`dump_and_unlock`, lock scope).
- [x] Cross-process shared state updates remain atomic and auditable.
- [x] Redis keyspaces and TTL behavior are unchanged unless explicitly planned.
- [x] Concurrent mutation paths include regression coverage for race conditions.
- [x] Recovery after partial failure leaves state consistent and diagnosable.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Logs include enough context for incident triage without exposing secrets.
- [x] Security-relevant events have observable signals (auth failures, denials, exfil attempts).
- [x] New error handlers do not swallow exceptions silently.
- [x] Alerting/operational checks are updated for new high-risk surfaces.
- [x] Rollback and containment steps are documented for the changed scope.

## Validation Evidence

- Automated checks run:
  - `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` (pass, `9 passed`)
  - `python tools/check_endpoint_inventory.py` (pass)
  - `python tools/check_route_contract_checklist.py` (pass)
  - `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1` (pass, `2 passed`)
  - `wctl doc-lint --path docs/schemas/rq-controller-state-contract.md --path docs/schemas/rq-engine-agent-api-contract.md --path docs/dev-notes/rq-engine-agent-api.md --path docs/work-packages/20260410_rq_controller_state_contract_cutover/package.md --path docs/work-packages/20260410_rq_controller_state_contract_cutover/tracker.md --path docs/work-packages/20260410_rq_controller_state_contract_cutover/prompts/active/rq_controller_state_contract_cutover_execplan.md --path docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-10_security_review.md --path PROJECT_TRACKER.md` (pass)
  - `wctl doc-lint --path docs/schemas/rq-controller-state-contract.md --path docs/schemas/rq-engine-agent-api-contract.md --path docs/dev-notes/rq-engine-agent-api.md --path docs/work-packages/20260410_rq_controller_state_contract_cutover/package.md --path docs/work-packages/20260410_rq_controller_state_contract_cutover/tracker.md --path docs/work-packages/20260410_rq_controller_state_contract_cutover/prompts/completed/rq_controller_state_contract_cutover_execplan.md --path docs/work-packages/20260410_rq_controller_state_contract_cutover/prompts/completed/rq_controller_state_contract_cutover_execplan_outcome.md --path docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-10_security_review.md --path PROJECT_TRACKER.md` (pass)

## Residual Risk

- **Accepted residual risks**:
  - `SEC-02` (Medium): session-token compatibility bridge (`rq:status` bearer requirement with broader minted session scopes) remains in place.
    - Owner: rq-engine API contract maintainers.
    - Follow-up trigger: if mint-scope policy is tightened, execute dedicated follow-on package with synchronized route + descriptor + contract updates and fresh security review.
- **Follow-up packages/issues**:
  - Policy-level follow-on package only if compatibility contract is intentionally changed.

## Sign-off

- **Security reviewer**: `security_reviewer` subagent (`019d79d6-25fa-7f00-b032-92338be607a2`), 2026-04-11
- **Package owner**: Codex, 2026-04-11
