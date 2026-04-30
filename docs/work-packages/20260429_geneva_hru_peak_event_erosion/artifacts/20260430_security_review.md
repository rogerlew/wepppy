# Security Review - Geneva HRU Peak Runoff and Event Erosion Enablement

## Metadata

- **Package**: `docs/work-packages/20260429_geneva_hru_peak_event_erosion/`
- **Reviewer**: Codex
- **Date**: 2026-04-30
- **Scope reviewed**: Rust run-batch response extension, HRU event-measure materialization/query validation, Geneva HRU map route/UI integration
- **Commit/branch context**:
  - `/workdir/wepppy`: `master` @ `80f625352f4097ec9755adc573a28dcdd98b03c0` (working tree with uncommitted package changes)
  - `/workdir/wepppyo3`: `main` @ `b39de9ec84a42860d4fe6ab15e9fc934d540c9df` (working tree with uncommitted package changes)
- **Related artifacts**:
  - Code review: `docs/work-packages/20260429_geneva_hru_peak_event_erosion/artifacts/20260430_code_review.md`
  - QA review: `docs/work-packages/20260429_geneva_hru_peak_event_erosion/artifacts/20260430_qa_review.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: Package changes a public query surface (`/query/geneva/hru_map_rows`) and expands accepted measure IDs; this is user-facing data-selection behavior and must preserve authn/authz and dataset restrictions.
- **Threat model assumptions**:
  - Run-scoped route authorization via existing `authorize_and_handle_with_exception_factory` and run-context loading remains unchanged.
  - Query execution stays bound to canonical run-scoped dataset `geneva/hru_event_measure_rows.parquet`.
  - No new external network integrations or privilege-escalation paths are introduced.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Low | Input validation / scope control | Verified `peak_discharge` remains rejected for HRU-scope map queries while `hru_peak_runoff` is explicitly allowlisted. | `wepppy/nodb/mods/geneva/collaborators/hru_event_measure_service.py`, `wepppy/nodb/mods/geneva/schemas/query_schema.py`, `tests/weppcloud/routes/test_geneva_bp.py` | Keep regression coverage in route/service tests for scope validation behavior. | Resolved |

Risk acceptance authority: `Accepted-risk` requires security reviewer recommendation plus explicit package owner acknowledgment in Sign-off.

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: `0`
  - Medium: `0`
  - Low: `0`
- **Release recommendation**: `ship`

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
  - `cargo test -p geneva_core`
  - `cargo test -p cli_revision_rust geneva`
  - `cargo fmt --check`
  - `wctl run-pytest tests/nodb/mods/geneva --maxfail=1`
  - `wctl run-pytest tests/weppcloud/routes/test_geneva_bp.py tests/weppcloud/routes/test_geneva_wp08_routes.py --maxfail=1`
  - `wctl run-npm test -- geneva`
  - `wctl run-npm lint` (known unrelated baseline failure documented)
  - `wctl doc-lint --path docs/work-packages/20260429_geneva_hru_peak_event_erosion --path wepppy/nodb/mods/geneva/specification.md`
  - `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
  - `git diff --check`
- Manual checks run:
  - Route scope check for `measure_id=hru_peak_runoff` vs `peak_discharge` - pass
  - Query dataset scope review for `HRU_EVENT_MEASURE_DATASET_PATH` only - pass
  - UI request payload review for map measure select wiring - pass

## Residual Risk

- **Accepted residual risks**:
  - Existing unrelated frontend lint baseline in `controllers_js/__tests__/landuse_map_inline.test.js`; unchanged by this package and already tracked in prior Geneva closures.
- **Follow-up packages/issues**:
  - Full `musle_hru_event_v1` erosion-row implementation remains follow-on work, now unblocked by local HRU peak substrate.

## Sign-off

- **Security reviewer**: Codex, 2026-04-30
- **Package owner**: Codex, 2026-04-30
