# Tracker - Forked Batch Identity Normalization

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-16 17:22 UTC
**Current phase**: Closed
**Last updated**: 2026-07-16 18:04 UTC
**Next milestone**: Permanent deployment when requested; backup review 2026-07-30
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `docs/work-packages/20260716_fork_batch_identity_normalization/artifacts/2026-07-16_security_review.md`

## Task Board

### Ready / Backlog

None.

### In Progress

None.

### Blocked

None.

### Done

- [x] Captured production failure evidence and exact persisted batch markers
      (2026-07-16 17:15 UTC).
- [x] Recorded the compatibility/regression contract in the authoritative fork
      documentation (2026-07-16 17:18 UTC).
- [x] Expanded scope at operator request to patch future forks
      (2026-07-16 17:22 UTC).
- [x] Implemented repair CLI with dry-run, guards, backup, rollback, atomic
      writes, verification, and root-scoped cache invalidation
      (2026-07-16 17:30 UTC).
- [x] Repaired and verified `subsequent-hotbed` on `wepp1`
      (2026-07-16 17:31 UTC).
- [x] Patched `prepare_fork_run` to clear root grouped identity and remove copied
      batch execution metadata; targeted tests pass (2026-07-16 17:34 UTC).
- [x] Remediated all review findings and completed exact-tree code and QA/security
      reviews with no unresolved high or medium findings (2026-07-16 17:55 UTC).
- [x] Passed 55 focused tests, 4,948 full-suite tests, documentation lint, Python
      compilation, broad-exception enforcement, and whitespace checks
      (2026-07-16 18:04 UTC).
- [x] Closed the package and archived the ExecPlan (2026-07-16 18:04 UTC).

## Timeline

- **2026-07-16 17:15 UTC** - Confirmed 13 root controllers retained Batch Runner identity.
- **2026-07-16 17:22 UTC** - Package and active ExecPlan created.
- **2026-07-16 17:30 UTC** - Production repair completed with backup and verification.
- **2026-07-16 17:34 UTC** - Permanent fork patch and initial focused tests passed.
- **2026-07-16 17:55 UTC** - Dual final reviews and 55 focused tests passed.
- **2026-07-16 18:04 UTC** - Full suite passed and package closed.

## Decisions Log

### 2026-07-16 17:22 UTC: Normalize copied state, not route interpretation

**Context**: Interactive routes correctly use `run_group` to distinguish native
batch leaves, but the fork copied that identity into a primary run.

**Options considered**:

1. Ignore `run_group` when the URL is a primary-run URL.
2. Clear only `ash.nodb` for this incident.
3. Clear root copied group identity during fork and supply a guarded repair CLI.

**Decision**: Option 3.

**Impact**: Native batch behavior remains authoritative while interactive forks
receive coherent identity across all root controllers.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Partial production mutation | High | Low | Preflight validation, timestamped backup, atomic replace/rollback, post-write verification | Mitigated |
| Wrong run/path mutation | High | Low | Explicit run root/run ID agreement, symlink rejection, and expected batch-name guard | Mitigated |
| Child workspace identity drift | High | Low | Root-only glob, scoped cache invalidation, and `_pups/` regression | Mitigated |
| Stale Redis NoDb cache | Medium | Medium | Explicit root-scoped clear plus hash-verified cache-only retry | Mitigated |

## Hardening Signal Log

- **Baseline health signals**: 13 root NoDb files report `run_group=batch`;
  WATAR submission returns the batch input-only message.
- **Post-change health signals**: All root identities clear; fresh Ash controller
  reports `batch_blocked=False`; `_pups` hash unchanged; repeat CLI is a no-op.
- **Danger signals observed**: Copied `run_metadata.json` still identifies source
  batch leaf `batch;;nasa-roses-202606-psbs;;WA-10`; resolved by backup/removal.
  Whole-run cache invalidation followed two `_pups` symlinks to source cache
  keys; no source files changed, and the CLI now invalidates only changed roots.
- **Temporary callus register**: Timestamped production backup, operator/Codex,
  introduced 2026-07-16, review 2026-07-30.
- **Softening experiments**: None during implementation.

## Verification Checklist

### Code Quality

- [x] Full Python tests pass.
- [x] Broad-exception changed-file gate passes.
- [x] Git whitespace check passes.

### Security

- [x] Security impact triage recorded as high.
- [x] Dedicated security review complete.
- [x] No unresolved medium/high findings.

### Documentation

- [x] Authoritative fork contract updated.
- [x] Package closure notes complete.

### Testing

- [x] CLI dry-run/apply/rejection/rollback/idempotence tests pass.
- [x] Fork normalization regression passes.
- [x] Production manual acceptance passes.

### Deployment

- [x] One-run repair applied on `wepp1`.
- [x] Permanent patch deployment explicitly deferred until requested.

## Progress Notes

### 2026-07-16 17:22 UTC: Incident scope and implementation contract

**Agent/Contributor**: Codex

**Work completed**:

- Confirmed the route predicate and serialized root-controller identity.
- Confirmed copied batch execution metadata remains active in the destination.
- Created package governance and an active ExecPlan.

**Blockers encountered**: None.

**Next steps**:

- Implement the CLI and tests.
- Dry-run and apply it to the verified production path.
- Patch the fork helper and complete review/validation.

**Test results**: Not yet run.

### 2026-07-16 17:34 UTC: Production repair and permanent prevention

**Agent/Contributor**: Codex

**Work completed**:

- Ran guarded dry-run and applied the repair on verified host `wepp1`.
- Captured timestamped backup, cache invalidation, root state, `_pups` hash, and
  fresh Ash-controller acceptance evidence.
- Added permanent fork normalization and copied batch metadata cleanup.
- Narrowed cache invalidation after observing symlink-reached cache entries.

**Blockers encountered**: None. A read-only lock probe initially used an obsolete
helper name; the corrected `lock_statuses` probe reported no active locks.

**Next steps**:

- Independent code/QA/security review and disposition.
- Full Python, documentation, broad-exception, and diff gates.

**Test results**: 32 focused tests passed.

### 2026-07-16 18:04 UTC: Review remediation, full validation, and closure

**Agent/Contributor**: Codex with independent code and QA/security reviewers

**Work completed**:

- Added strict source/root/metadata batch-name agreement and incomplete-metadata
  rejection.
- Added complete preflight, stale-plan revalidation, atomic forward and rollback
  publication, and explicit hash-verified cache-only retry.
- Staged the final script on `wepp1`; matching SHA-256 and zero-change production
  dry-run confirmed the repaired run remains stable.
- Completed code, QA, and dedicated security artifacts and closed the package.

**Blockers encountered**: None. An interrupted earlier full-suite invocation left a
second pytest process in the local container; that agent-owned stale process was
terminated before the clean final gate.

**Next steps**:

- Deploy the permanent fork patch when requested.
- Review the timestamped production backup after 2026-07-30.

**Test results**: 55 focused tests and 4,948 full-suite tests passed; 58 skipped.

## Watch List

- **WATAR submission**: Alex must receive a normal job ID after the repair.
- **Backup retention**: Review the one-run backup after 2026-07-30.

## Communication Log

### 2026-07-16 17:22 UTC: Permanent prevention requested

**Participants**: Roger Lew and Codex
**Question/Topic**: Repair the current run with a script and patch fork to clear
copied batch attributes afterward.
**Outcome**: Scope expanded to reusable repair plus permanent fork normalization.
