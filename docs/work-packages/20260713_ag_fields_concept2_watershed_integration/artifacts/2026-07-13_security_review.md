# Security Review - AgFields Concept 2 Watershed Integration

## Metadata

- **Package**:
  `docs/work-packages/20260713_ag_fields_concept2_watershed_integration/`
- **Reviewer**: Codex implementation security review
- **Date**: 2026-07-13
- **Scope reviewed**: Planned AgFields NoDb collaborator, isolated run tree, RQ
  worker, rq-engine routes, runs-page control, WEPP subprocesses, and result access
- **Commit/branch context**: Working tree; Milestones 3-4 implementation

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: The package adds authenticated mutations, queue wiring,
  worker-controlled subprocess execution, filesystem staging/clearing, and result
  paths under a user-owned run.
- **Threat model assumptions**:
  - Route callers are untrusted until JWT scope and run access are verified.
  - All worker paths must be derived from the authorized run root and fixed artifact
    names, never directly from client-supplied paths.
  - Existing prepared WEPP and AgFields files may be missing or stale, but are not
    treated as attacker-authorized paths outside the run.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Run-tree filesystem | Recursive workspace prepare/clear and link/copy helpers could escape the isolated tree if they accept unvalidated paths or follow hostile symlinks. | Fixed root equality checks, run-root containment, regular-file checks, symlink rejection, and clear-boundary tests in `test_ag_fields_watershed_integration.py` | Derive fixed paths from `AgFields.wd`, reject escapes, constrain clear to the isolated subtree, and add symlink/path regression tests. | Resolved |
| SEC-02 | Medium | Queue/concurrency | A watershed-integration job could overlap AgFields input mutation, Stage 4 execution, another integration run, or clear. | `agfields_run_watershed` is included in submit-lock active enumeration, route conflicts, hydration, and tests. | Extend atomic submit locking and active-job enumeration; test conflicting submit/mutation/clear paths. | Resolved |
| SEC-03 | Medium | Worker/subprocess | A malformed or stale run plan could cause unbounded WEPP execution or consume unrelated run inputs. | Preflight validates translator ids, installed executable, single-OFE parents, every required file, observed climate, and bounded workers; WEPP calls remain argv-based runner calls. | Validate all ids/paths before enqueue execution, use installed binary enums and bounded worker counts, publish progress/failure, and keep subprocess argv shell-free. | Resolved |
| SEC-04 | Low | Result metadata | Absolute source paths or internal tracebacks could be exposed through manifests/API responses. | Manifest paths are run-relative; executable records omit paths; public failures redact run/application roots; canonical route tests pass. | Store run-relative paths in user-facing artifacts and preserve canonical error envelopes without secret/internal path disclosure. | Resolved |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: Proceed to generated-output acceptance; retain the
  internal/experimental label and scientific limitation.

## Surface Checks

### Auth, Session, and Authorization

- [x] New run-scoped routes require JWT scope and call `authorize_run_access`.
- [x] State/result reads and run/clear mutations preserve least-privilege scopes.
- [x] Canonical rq-engine response and error envelopes are regression-tested.

### Input Validation and Output Safety

- [x] Client payloads contain only bounded options, not arbitrary paths/binaries.
- [x] Source ids, areas, scales, calendars, and numeric fields reject invalid values.
- [x] API/manifests avoid unsafe rendered HTML and unintended absolute paths.

### File System and Run-Tree Boundaries

- [x] Writes and deletes remain under `wepp/ag_fields/watershed/`.
- [x] Link/copy and cleanup helpers handle symlinks without escaping run scope.
- [x] Baseline and independent AgFields files remain read-only to this stage.
- [x] Partial artifacts are terminally marked and safely retryable.

### Queue, Worker, and Subprocess Surfaces

- [x] Enqueue site and dependency edges are documented and graph-validated.
- [x] Existing AgFields single-flight admission includes the integration job.
- [x] Installed WEPP binary validation and bounded concurrency are preserved.
- [x] Subprocess calls avoid shell interpolation and publish contextual failures.

### Data Integrity, Locking, and Concurrency

- [x] NoDb mutations use canonical lock/dump behavior with long model execution
  outside the lock.
- [x] Source signature and terminal summary are committed atomically.
- [x] Clear, retry, state hydration, and upstream mutation invalidate correctly.

### Secrets, Network, Agent Tooling, and Supply Chain

- [x] No secrets, new external egress, MCP permission, CI permission, or third-party
  dependency is introduced.
- [x] The owned `wepppyo3` extension passes the repository dependency precedent and
  release-provenance checks without adding a dependency.

### Logging and Incident Readiness

- [x] Status/log events identify run, stage, parent/source counts, and failures
  without secrets or full internal tracebacks in user payloads.
- [x] Rollback is disabling the stage and clearing only its isolated tree.

## Validation Evidence

- `tests/nodb/mods/test_ag_fields_watershed_integration.py`: 12 passed, including
  aligned ownership, exact materialization, historical/completed state, timestamp
  staleness, and symlinked clear.
- `tests/rq/test_ag_fields_rq.py` plus rq-engine AgFields routes: 37 passed after
  adding the fourth job and two authenticated routes.
- Focused Jest: 11 passed; controller lint passed; pure-control contract: 3 passed.
- `wctl check-rq-graph`: up to date after regeneration.
- Changed-file broad-exception enforcement: pass with documented boundaries.
- Native kernel: 41 Rust tests, release import, and two Python closure tests passed;
  exhaustive replay passed all 1,869 affected acceptance parents.
- The final authenticated job completed in 59 minutes 25 seconds with 6.88 GB peak
  unique allocation. API state is `completed`, `stale=false`; all required outputs
  exist; the protected pre/post inventories are byte-identical.
- The public run URL returns HTTP 200 with the CAPTCHA gate after the dev compose
  service was aligned with the production CAP environment; the exact compose
  configuration regression passes.

## Residual Risk

The scientific limitation of outlet injection is not a security finding. It must
remain visible in manifests/UI and is dispositioned through Mariana's evaluation.

## Sign-off

- **Security reviewer**: Codex, 2026-07-13
- **Package owner**: Engineering acceptance complete, 2026-07-14; scientific
  evaluation pending
