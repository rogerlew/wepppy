# SURF-10 Security Review

## Metadata

- **Package**: `docs/work-packages/20260728_pure_ui_disturbed_csv_editor_contract/`
- **Reviewer**: Codex
- **Date**: 2026-07-28
- **Scope reviewed**: shared editor render/client, disturbed render/meta/snapshot/
  mutation routes, disturbed lookup snapshot/write helpers, and Geneva producer
- **Commit/branch context**: local SURF-10 closeout diff

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: yes
- **Triage rationale**: an authenticated browser mutates run-scoped model input
  across CSRF, session-token, filesystem, locking, and concurrency boundaries.
- **Threat model assumptions**:
  - hostile users may control rendered run/config text and submitted cells;
  - concurrent authorized editors may load and save different versions;
  - CDN, session, network, or fingerprint services may fail independently.

## Findings

No finding. The audit added executable evidence and retained production code
unchanged.

## Verdict

- **Gate status**: pass
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: ship

## Surface Checks

### Auth, Session, CSRF, and Authorization

- Disturbed mutation retains route authorization and browser CSRF.
- Client session authorization occurs before snapshot download.
- Snapshot/meta/save URLs remain producer-supplied and run-scoped.
- Rejected session and HTTP errors render through text-only status content.

### Input, Output, and File Boundaries

- Jinja autoescape protects hostile data attributes and run-link text.
- Errors use `textContent`; HTML error bodies are reduced to HTTP status.
- Disturbed route validation retains row type/shape/completeness checks.
- Lookup paths are selected from controller-owned base/extended paths, not
  request paths.

### Data Integrity, Locking, and Concurrency

- Snapshot/fingerprint data comes from one read lock.
- Writes require `if_match_sha256`, execute under controller lock, and return a
  new fingerprint.
- Stale, missing, or unavailable fingerprints fail closed.
- The NoDb writer validates before atomic replacement.
- Executable client tests prove duplicate/stale guards and failed-recovery lock
  retention.

### External Runtime and Supply Chain

- No dependency or external call was added.
- Existing JSpreadsheet/JSuites CDN failure is explicit: the table does not
  initialize, the status identifies runtime failure, and Save remains disabled.
- Vendoring/replacing those existing assets is outside SURF-10 and no silent
  fallback was introduced.

### Queue, Secrets, CI/CD, and Agentic Surfaces

- No queue, worker, subprocess, secret, credential, CI/CD, MCP, or permission
  surface changed.

### Logging and Recovery

- Existing mutation logs cover missing precondition, stale mismatch,
  fingerprint failure, and committed writes without cell contents.
- Recovery reload is idempotent; a failed stale reload stays visibly locked.

## Validation Evidence

- Focused render/routes: 195 passed.
- Focused disturbed lookup contract: 31 passed.
- Focused inline client: 1 suite, 4 tests passed.
- Frontend lint passed.
- Full frontend: 99 suites, 707 tests passed.
- Repository Python: 5,541 passed, 58 skipped.
- Documentation lint and `git diff --check`: required at final closeout.

## Residual Risk

- The existing editor depends on two remote spreadsheet asset hosts. Failure is
  safe and visible but prevents editing. This is availability, not an unsafe
  mutation fallback; replacement requires a separately evaluated dependency
  decision.
- No follow-up is required for SURF-10 closure.

## Sign-off

- **Security reviewer**: Codex, 2026-07-28
- **Package owner**: Codex under operator execution authority, 2026-07-28
