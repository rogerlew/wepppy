# Security Review - Fork Console Status Backpressure and Recovery

## Metadata

- **Package**: `docs/work-packages/20260715_fork_console_status_backpressure/`
- **Reviewer**: Codex security review pass
- **Date**: 2026-07-15
- **Scope reviewed**: Fork RQ subprocess arguments/output handling, browser session storage, StatusStream rendering, and fork-console lifecycle behavior.
- **Commit/branch context**: Current user worktree; no branch created.
- **Related artifacts**:
  - Code review: `docs/work-packages/20260715_fork_console_status_backpressure/artifacts/20260715_code_review.md`
  - QA review: `docs/work-packages/20260715_fork_console_status_backpressure/artifacts/20260715_qa_review.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: Repository policy classifies changes to a worker subprocess boundary as high impact. The planned change narrows output and flags without adding shell execution, routes, permissions, secrets, dependencies, or queue edges.
- **Threat model assumptions**:
  - Existing fork route authorization and run-path resolution remain unchanged.
  - Rsync continues to receive list arguments with no shell interpolation.
  - Browser storage contains only run/job identifiers and never authorization material.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Subprocess diagnostics | Suppressing publication must not move an unbounded buffer into worker memory. | Each stream drains concurrently into a `deque(maxlen=200)`; success and failure tests generate more than 200 lines and assert bounded tails. | Add bounded-tail tests and implementation. | Resolved |
| SEC-02 | Medium | Browser storage and DOM | Reload recovery must not persist tokens or allow modified storage identifiers to inject markup. | The exact five stored keys are asserted; restored labels use text nodes, links use encoded paths, and a malicious-record test proves no element injection. | Store identifiers only and render them as text. | Resolved |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: Ship repository change after normal maintainer review; production deployment remains a separate operator action.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Existing fork authorization and token flows are unchanged.
- [x] No token material is persisted in browser storage.

### 2) Secrets and Credential Handling

- [x] No secrets are added to code, argv, status messages, storage, or docs.

### 3) Input Validation and Output Safety

- [x] New fork progress and restored identifiers render through `textContent` or text nodes; link paths are URL encoded.
- [x] Session-state parsing validates version, source run, config, job ID, and destination run ID as expected scalar identifiers.

### 4) File System and Run-Tree Boundaries

- [x] Existing source/destination path resolution is unchanged.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] Rsync remains list-argument invocation without shell interpolation.
- [x] Captured process output is bounded.
- [x] Nonzero return codes remain explicit failures.
- [x] Queue wiring and dependency edges remain unchanged.

### 6) Agentic Tooling and MCP Surfaces

- [x] Work remains within the user-authorized repository scope.
- [x] No external publication or deployment is performed.

### 7) Network and External Integrations

- [x] Existing Redis/WebSocket endpoints are unchanged.

### 8) CI/CD and Supply Chain

- [x] No dependencies or workflow permissions are added.

### 9) Data Integrity, Locking, and Concurrency

- [x] Fork data mutation and RQ lifecycle behavior remain unchanged.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Stage/heartbeat telemetry remains sufficient for operators.
- [x] Failure details remain explicit and bounded.
- [x] Rollback and observation signals are documented.

## Validation Evidence

- Automated checks run: bounded worker success/failure/heartbeat tests; exact storage-key and malicious-storage DOM tests; template contract tests; StatusStream batching/retention/visibility tests; complete 629-test frontend suite; lint.
- Manual checks run: reviewed subprocess construction, storage call sites, dynamic DOM construction, path encoding, queue/route diffs, and generated asset parity.

## Residual Risk

- **Accepted residual risks**: The source-run fork channel remains shared and ephemeral. The console now connects only while tracking and requires authoritative job-status confirmation, so unrelated or lost channel messages cannot terminally resolve the UI.
- **Follow-up packages/issues**: Job-scoped fork channels remain an optional future improvement if production observation shows continued ambiguity.

## Sign-off

- **Security reviewer**: Codex, 2026-07-15.
- **Package owner**: Codex implementation owner; human maintainer merge approval remains required.
