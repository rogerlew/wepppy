# Security Review - WP12 Production Cutover

## Metadata

- **Package**: `docs/work-packages/20260804_project_config_production_cutover/`
- **Reviewer**: Codex promotion review, retaining independent WP11/WP12B-D
  security reviews
- **Date**: 2026-08-31
- **Scope reviewed**: authenticated project creation/update, session and RQ
  identity handoff, run-tree writes, queues, deployment flags, and rollback
- **Commit/branch context**: final `feature/project-owned-config` pre-merge
  checkpoint
- **Related artifacts**: `20260831_scope_audit.md`,
  `20260831_validation.md`, and `20260831_correctness_review.md`

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: WP12 promotes authenticated project mutation and worker
  execution paths and must preserve reader-safe rollback.
- **Threat model assumptions**:
  - Browser/RQ tokens are signed and validated under the canonical audience,
    scope, revocation, and role contracts.
  - Run-local artifacts are untrusted inputs and cannot self-authorize graph or
    source identities.
  - Production deploy credentials and host configuration remain outside the
    repository and are used only by canonical operator tooling.
- **Valid states controls must preserve**: no project config, supported legacy
  preset projection, stored schema-v2/v3 authority, current eligible schema-v3
  refresh, and authorized owner/Admin/Root mutation.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Low | Public type surface | Snapshot stub did not expose the runtime locale-projection helper | Scoped stubtest | Add exact signature; rerun stub/direct tests | Resolved |
| SEC-02 | Low | Queue evidence | Static graph recorded a stale source line for an unchanged enqueue edge | Graph checker/diff | Canonically regenerate and verify 144 edges | Resolved |

## Verdict

- **Gate status**: pass for merge and staged deployment
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: ship with the roadmap's reader-before-writer
  staging, exact revision checks, and rollback observation

## Surface Checks

### Valid-State Non-Interference and User Experience

- [x] The correctness review enumerates absent, populated, legacy, current, and
  hostile states.
- [x] Auth/security tests and Forest evidence preserve valid owner and legacy
  workflows.
- [x] Optional absent capability state remains a contracted live-authority or
  unavailable state rather than an internal exception.
- [x] Direct Forest reader/writer/rollback evidence supplements mocked tests.

### Auth, Session, and Authorization

- [x] Creation/update entry points retain authenticated owner/Admin/Root checks.
- [x] PowerUser presentation does not grant mutation authorization.
- [x] Signed numeric `user_id` handoff preserves audience, scope, revocation,
  and worker-time reauthorization.
- [x] Browser mutation uses the canonical token/CSRF boundary; token contents
  are not exposed in errors or artifacts.

### Secrets and Credential Handling

- [x] Scope audit and secret scanner evidence found no committed token/secret.
- [x] Production flags contain no credential value and tracked defaults remain
  safe.
- [x] Canonical deployment keeps secrets outside command arguments and docs.

### Input, Output, and Run-Tree Safety

- [x] Locale, dataset, climate mode, graph identity, manifest digest, filename,
  and path inputs are server validated.
- [x] Project writes remain in the authorized run root with locking and atomic
  config/manifest replacement.
- [x] Rendered titles, diagnostics, tables, and modal content retain escaping
  and themed accessible presentation.

### Queue, Worker, and Subprocess Surfaces

- [x] RQ dependency graph is current at 144 edges.
- [x] Worker authorization is repeated at execution time; stale/unauthorized
  updates do not enqueue or mutate.
- [x] Provider commands use bounded registered paths/options; real Forest
  provider execution is recorded.
- [x] Failure/recovery retains a consistent config/manifest pair and canonical
  diagnostic error contracts.

### Network, Supply Chain, and Agent Tooling

- [x] No new dependency, CI permission, agent capability, proxy exposure, or
  external egress is introduced by WP12.
- [x] Production commands remain limited to the operator-authorized canonical
  deployment workflow and exact hosts.

### Data Integrity, Logging, and Incident Readiness

- [x] Project lock, journal, stale-preview, idempotency, and recovery tests pass.
- [x] Logs and user details expose diagnostics without token contents.
- [x] Reader-first activation, danger signals, rollback revision, and shared
  alias retention are explicit WP12 gates.

## Validation Evidence

- Complete Python: 7,280 passed, 63 skipped.
- Frontend: 108 suites, 833 tests; lint passed.
- Stub completeness and all scoped public runtime comparisons passed after the
  one resolved stub finding.
- Broad-exception enforcement, Vulture, RQ graph, diff, and scoped docs gates
  passed or have the exact final rerun recorded in `20260831_validation.md`.
- Forest real-provider, authenticated refresh, legacy reopen, and rollback
  evidence is retained from WP11 and WP12B-D.

## Residual Risk

- Production-specific configuration drift remains possible until the exact
  merged revision and staged flags are observed on each service. WP12 owns this
  as a deployment condition, not accepted risk.
- The test-isolation tool's unbounded default workflow did not complete; the
  successful full suite and prerequisite isolation evidence reduce but do not
  redefine that tooling gap.
- WP13, not WP12, owns shared `_defaults.toml` alias retirement.

## Sign-off

- **Security reviewer**: Codex promotion review, 2026-08-31
- **Package owner**: pending production completion

