# Security Review - Batch and Culvert Climate Rehydration

## Metadata

- **Package**: `docs/work-packages/20260904_batch_culvert_climate_rehydration_b/`
- **Reviewer**: Codex (independent security review pass)
- **Date**: 2026-09-05
- **Scope reviewed**: `wepppy/nodb/batch_runner.py`,
  `wepppy/rq/culvert_rq.py`, changed RQ tests, NoDb cache/lock boundary, and
  Forest development restart procedure
- **Commit/branch context**: `master` at `87559fe26`; uncommitted working-tree
  implementation on Forest
- **Related artifacts**:
  - `artifacts/2026-09-05_correctness_review.md`
  - `artifacts/2026-09-05_qa_review.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: The change runs inside RQ workers and changes the
  ordering of run-tree cache invalidation, hydration, locking, and persistence.
  It does not add routes, credentials, subprocesses, dependencies, queue
  edges, or new filesystem roots.
- **Threat model assumptions**:
  - Run IDs and working directories continue to be resolved by existing
    helpers and authorization boundaries.
  - The existing directory-root lock and NoDb distributed lock remain the
    authoritative mutation controls.
  - Redis cache invalidation remains best-effort only within the canonical
    exact run-local path contract; malformed state must still fail explicitly.
- **Valid states that controls must preserve**: absent optional RAP/OpenET,
  populated current Climate, supported legacy Climate, and explicit failure for
  missing/empty/malformed required Climate state.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | NoDb concurrency | A stale Climate instance could overwrite or reject a newer generation if reused after long earlier stages. | Incident signature in `package.md`; direct same-size real NoDb test in `tests/rq/test_climate_rehydration.py:51-129` | Clear only `climate.nodb`, hydrate inside the existing climate root lock, and build the returned current instance | Resolved |
| SEC-02 | High | Cache/path scope | Broad cache invalidation could affect unrelated controllers or escape the run root. | `wepppy/nodb/base.py:2853-2938`; exact caller arguments at `batch_runner.py:206` and `culvert_rq.py:146` | Preserve fixed relative `pup_relpath="climate.nodb"` and canonical helper validation | Resolved |
| SEC-03 | High | Error handling | A retry of `NoDbStaleWriteError` on the same stale object could mask a lost update. | No catch/retry in changed production paths; persistence contract and tests retain strict rejection | Do not add retry or suppression | Resolved |
| SEC-04 | Medium | Queue/worker | Queue topology or worker routing could drift while changing orchestration. | Diff is limited to helper placement and tests; no enqueue/dependency edits | Record RQ graph as not applicable and retain existing worker procedure | Resolved |

Risk acceptance authority: not required; all High/Medium findings are
resolved by the implementation and validation evidence.

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: `ship-with-conditions` with the documented
  culvert fixture limitation and unrelated repository baseline failure.

## Surface Checks

### 0) Valid-State Non-Interference and User Experience

- [x] Correctness review enumerates absent, empty, populated, legacy, and
  malformed states.
- [x] Direct unmocked valid and invalid persistence-boundary tests pass.
- [x] Optional absence remains a no-op through existing `tryGetInstance` paths.

### 1) Auth, Session, and Authorization

- [x] No routes, auth checks, sessions, JWTs, or CSRF paths changed.

### 2) Secrets and Credential Handling

- [x] No secrets, environment contracts, or credential mounts changed.

### 3) Input Validation and Output Safety

- [x] No new user path input or shell interpolation was introduced.
- [x] Cache helper retains canonical relative-path and run-root validation.

### 4) File System and Run-Tree Boundaries

- [x] Writes remain in the existing run working directory and fixed Climate
  NoDb path.
- [x] Existing atomic dump and permissions behavior is unchanged.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] Enqueue sites, dependency edges, queues, and subprocess calls are
  unchanged; RQ graph gate is not applicable.
- [x] Existing exception/status boundaries remain intact.

### 6) Agentic Tooling and MCP Surfaces

- [x] No agent or MCP surface changed.

### 7) Network and External Integrations

- [x] No outbound integration, retry loop, or rate-limit behavior changed.

### 8) CI/CD and Supply Chain

- [x] No dependency, image, registry, workflow, or deployment topology change.

### 9) Data Integrity, Locking, and Concurrency

- [x] Existing climate root and NoDb locks remain authoritative.
- [x] Same-size generation advancement is covered with real signature checks.
- [x] No stale-object retry or broad exception suppression was added.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Existing worker error/status logging remains unchanged.
- [x] Forest acceptance will record worker logs, run metadata, RQ status, and
  rollback without editing run data manually.

## Validation Evidence

- Focused RQ/NoDb tests: pass; see QA artifact.
- Changed-file broad-exception enforcement: pass.
- Code-quality observability: pass, observe-only.
- Documentation lint and diff check: pass after the final artifact additions.
- Forest service restart, successful batch receipt, culvert fixture failures,
  source-bind verification, and rollback are recorded in
  `artifacts/2026-09-05_forest_acceptance.md`. No target stale-write signature
  appeared in the accepted batch or culvert attempts.

## Residual Risk

- **Accepted residual risks**: The repository-wide shape-converter compose
  contract mismatch remains a separate baseline defect and is not masked by
  this package. Rollback restores the prior stale-hydration risk but does not
  weaken NoDb protections.
- **Follow-up packages/issues**: Repair the committed
  `docker/docker-compose.prod.wepp1.yml` / shape-converter hardening contract
  separately.

## Sign-off

- **Security reviewer**: Codex, 2026-09-05
- **Package owner**: Codex, 2026-09-05
