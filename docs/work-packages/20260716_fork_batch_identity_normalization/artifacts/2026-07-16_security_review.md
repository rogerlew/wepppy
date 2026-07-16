# Security Review - Forked Batch Identity Normalization

## Metadata

- **Package**: `docs/work-packages/20260716_fork_batch_identity_normalization/`
- **Reviewer**: Codex security review with independent QA/security review
- **Date**: 2026-07-16
- **Scope reviewed**: Explicit run-root repair CLI, fork destination NoDb mutation,
  copied execution metadata, backup/recovery, and cache invalidation
- **Commit/branch context**: Current `master` worktree; no branch created
- **Related artifacts**:
  - Code review: `artifacts/2026-07-16_code_review.md`
  - QA review: `artifacts/2026-07-16_qa_review.md`
  - Production repair: `artifacts/2026-07-16_wepp1_repair.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: The package accepts operator-supplied filesystem paths and
  mutates run-scoped production NoDb state.
- **Threat model assumptions**:
  - The repair CLI is executed by an authorized WEPPcloud operator.
  - Canonical run IDs do not contain path separators.
  - Interactive fork destinations are not hydrated until `prepare_fork_run` returns.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Run-tree paths | Symlinked root or backup paths could redirect inspection or mutation outside the selected run. | Symlink/escape regressions in both focused suites. | Require resolved run-root agreement and reject symlinked roots, backup parents, backup directories, manifests, metadata, and controllers. | Resolved |
| SEC-02 | Medium | Data integrity | Interleaved, direct, or rollback writes could leave partial or mixed controller state. | Preflight, injected forward-failure, and injected rollback-failure tests. | Validate the complete plan first; publish and restore atomically; report rollback conflicts explicitly. | Resolved |
| SEC-03 | Medium | Identity validation | Incomplete or disagreeing source, root, and metadata batch identity could be silently cleared. | Cross-file disagreement and incomplete metadata regressions. | Require one consistent batch name and fail before mutation. | Resolved |
| SEC-04 | Medium | Cache recovery | Whole-run invalidation could follow child symlinks, while post-write cache failure lacked a safe retry path. | Scoped cache assertions and prepared-manifest retry test. | Clear only changed root controllers and support explicit hash-verified cache-only retry. | Resolved |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: Ship after normal maintainer review. Permanent production
  deployment remains a separate operator action.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Existing fork route authorization, session, and CSRF behavior are unchanged.
- [x] The CLI is an operator tool and adds no network endpoint.

### 2) Secrets and Credential Handling

- [x] No secrets, tokens, environment defaults, or secret mounts are added.

### 3) Input Validation and Output Safety

- [x] Run ID, explicit run-root basename, JSON mappings, group enums, and batch names
  are validated before mutation.
- [x] Malformed, incomplete, conflicting, or non-batch identity fails explicitly.
- [x] No shell interpolation or unsafe deserialization is introduced.

### 4) File System and Run-Tree Boundaries

- [x] Root-only globs exclude `_pups/` and nested workspaces.
- [x] Run roots and recovery paths reject traversal, symlinks, and irregular files.
- [x] Atomic temporary files use the target directory and preserve source mode.
- [x] Timestamped backups and their retention/rollback contract are documented.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] No enqueue site, dependency edge, subprocess, or response contract changes.
- [x] `wctl check-rq-graph` is not required because queue wiring is unchanged.

### 6) Agentic Tooling and MCP Surfaces

- [x] Production mutation remained within the explicitly authorized run and host.
- [x] No external publication or privilege expansion occurred.

### 7) Network and External Integrations

- [x] No new external calls, endpoints, retries, or egress surfaces are introduced.

### 8) CI/CD and Supply Chain

- [x] No dependency, workflow, runner-permission, or build-chain changes are present.

### 9) Data Integrity, Locking, and Concurrency

- [x] Complete preflight and byte revalidation occur before publication.
- [x] Forward and rollback writes are atomic and regression-tested.
- [x] Cache invalidation is root-scoped; recovery validates manifest paths and hashes.
- [x] Production lock probes found no active filesystem or Redis mutation locks.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Dry-run is the default and reports exact planned controller/metadata changes.
- [x] Backup manifests record before/after hashes and completion state.
- [x] Rollback, cache-only retry, acceptance checks, and observation signals are
  documented.

## Validation Evidence

- Automated checks: 55 focused tests; Python compilation; broad-exception changed-file
  enforcement; documentation lint; `git diff --check`.
- Manual checks: production dry-run/apply/repeat-dry-run, root identity inspection,
  backup inspection, `_pups/` hash comparison, cache invalidation, and fresh Ash load.
- Independent reviews: exact-tree code and QA/security reviews both pass with no
  unresolved high or medium findings.

## Residual Risk

- **Accepted residual risks**: A narrow TOCTOU window exists between final byte
  verification and atomic replacement. Operators mitigate it by checking locks and
  targeting inactive repair state; fork destinations are not yet active. Owner:
  WEPPcloud operators.
- **Follow-up packages/issues**: None required. Review the production backup after the
  14-day observation window.

## Sign-off

- **Security reviewer**: Codex with independent QA/security reviewer, 2026-07-16.
- **Package owner**: Codex implementation owner; human maintainer merge approval and
  permanent deployment remain separate actions.
