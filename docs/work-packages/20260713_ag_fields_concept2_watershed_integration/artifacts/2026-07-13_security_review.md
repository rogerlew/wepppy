# Security Review - AgFields Concept 2 Watershed Integration

## Metadata

- **Package**:
  `docs/work-packages/20260713_ag_fields_concept2_watershed_integration/`
- **Reviewer**: Pending final implementation review
- **Date**: 2026-07-13
- **Scope reviewed**: Planned AgFields NoDb collaborator, isolated run tree, RQ
  worker, rq-engine routes, runs-page control, WEPP subprocesses, and result access
- **Commit/branch context**: Working tree; package opening

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
| SEC-01 | Medium | Run-tree filesystem | Recursive workspace prepare/clear and link/copy helpers could escape the isolated tree if they accept unvalidated paths or follow hostile symlinks. | Planned `wepp/ag_fields/watershed/` staging | Derive fixed paths from `AgFields.wd`, reject escapes, constrain clear to the isolated subtree, and add symlink/path regression tests. | Open |
| SEC-02 | Medium | Queue/concurrency | A watershed-integration job could overlap AgFields input mutation, Stage 4 execution, another integration run, or clear. | Existing AgFields single-flight route guard must include the new job key. | Extend atomic submit locking and active-job enumeration; test conflicting submit/mutation/clear paths. | Open |
| SEC-03 | Medium | Worker/subprocess | A malformed or stale run plan could cause unbounded WEPP execution or consume unrelated run inputs. | Planned materialization of thousands of parent runs. | Validate all ids/paths before enqueue execution, use installed binary enums and bounded worker counts, publish progress/failure, and keep subprocess argv shell-free. | Open |
| SEC-04 | Low | Result metadata | Absolute source paths or internal tracebacks could be exposed through manifests/API responses. | Proposed source manifest and failure payloads. | Store run-relative paths in user-facing artifacts and preserve canonical error envelopes without secret/internal path disclosure. | Open |

## Verdict

- **Gate status**: `fail` (implementation has not yet been reviewed)
- **Unresolved findings**:
  - High: 0
  - Medium: 3
  - Low: 1
- **Release recommendation**: Hold until implementation evidence resolves all
  medium findings and the final surface checklist passes.

## Surface Checks

### Auth, Session, and Authorization

- [ ] New run-scoped routes require JWT scope and call `authorize_run_access`.
- [ ] State/result reads and run/clear mutations preserve least-privilege scopes.
- [ ] Canonical rq-engine response and error envelopes are regression-tested.

### Input Validation and Output Safety

- [ ] Client payloads contain only bounded options, not arbitrary paths/binaries.
- [ ] Source ids, areas, scales, calendars, and numeric fields reject invalid values.
- [ ] API/manifests avoid unsafe rendered HTML and unintended absolute paths.

### File System and Run-Tree Boundaries

- [ ] Writes and deletes remain under `wepp/ag_fields/watershed/`.
- [ ] Link/copy and cleanup helpers handle symlinks without escaping run scope.
- [ ] Baseline and independent AgFields files remain read-only to this stage.
- [ ] Partial artifacts are terminally marked and safely retryable.

### Queue, Worker, and Subprocess Surfaces

- [ ] Enqueue site and dependency edges are documented and graph-validated.
- [ ] Existing AgFields single-flight admission includes the integration job.
- [ ] Installed WEPP binary validation and bounded concurrency are preserved.
- [ ] Subprocess calls avoid shell interpolation and publish contextual failures.

### Data Integrity, Locking, and Concurrency

- [ ] NoDb mutations use canonical lock/dump behavior with long model execution
  outside the lock.
- [ ] Source signature and terminal summary are committed atomically.
- [ ] Clear, retry, state hydration, and upstream mutation invalidate correctly.

### Secrets, Network, Agent Tooling, and Supply Chain

- [ ] No secrets, new external egress, MCP permission, CI permission, or third-party
  dependency is introduced.
- [ ] The owned `wepppyo3` extension passes the repository dependency precedent and
  release-provenance checks without adding a dependency.

### Logging and Incident Readiness

- [ ] Status/log events identify run, stage, parent/source counts, and failures
  without secrets or full internal tracebacks in user payloads.
- [ ] Rollback is disabling the stage and clearing only its isolated tree.

## Validation Evidence

Pending implementation. Record focused controller/RQ/route/UI tests, queue graph,
broad-exception enforcement, native kernel tests/imports, path/symlink tests, and
the dev-project immutable-artifact proof here before changing the gate verdict.

## Residual Risk

The scientific limitation of outlet injection is not a security finding. It must
remain visible in manifests/UI and is dispositioned through Mariana's evaluation.

## Sign-off

- **Security reviewer**: Pending
- **Package owner**: Pending
