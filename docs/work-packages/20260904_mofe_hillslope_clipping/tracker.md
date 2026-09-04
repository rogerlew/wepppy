# Tracker – Multiple-OFE Hillslope Clipping

## Quick Status

**Timezone**: UTC  
**Started**: 2026-09-04 11:31 UTC  
**Current phase**: Contract checkpoint  
**Last updated**: 2026-09-04 11:49 UTC  
**Next milestone**: Close contract/security findings and commit the ancestor checkpoint  
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `artifacts/2026-09-04_security_review.md`

## Task Board

### In Progress

- [ ] Complete and commit the pre-implementation contract checkpoint.

### Ready / Backlog

- [ ] Implement and test per-OFE clipping.
- [ ] Update UI and user/developer documentation.
- [ ] Run focused and broad local gates plus correctness review.
- [ ] Deploy to `forest`, submit `dainty-signature` at 60 m through rq-engine,
      and capture generated-output evidence.
- [ ] Close and archive the package.

### Blocked

- None.

### Done

- [x] Package and active ExecPlan scaffolded (2026-09-04 11:31 UTC).
- [x] Canonical contract and ADR drafted (2026-09-04 11:31 UTC).
- [x] Two initial contract reviews completed and findings dispositioned in the
  checkpoint draft (2026-09-04 11:49 UTC).
- [x] Correctness, governance, and security post-fix confirmations approve the
  checkpoint with no unresolved high/medium findings (2026-09-04 12:02 UTC).

## Decisions Log

- **2026-09-04 11:31 UTC** – Apply the threshold independently to every OFE and
  scale shared width by original-total-length divided by clipped-total-length.
  This preserves the existing area contract and the operator's requested
  per-OFE meaning.
- **2026-09-04 11:31 UTC** – Retain all existing request aliases, persisted
  fields, and defaults; limit the behavior change to generated slope geometry.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Incorrect shared-width scaling changes area | High | Low | Direct numeric tests and Forest artifact comparison | Open |
| Multi-OFE parser corrupts slope rows/header | High | Low | Exact structural preservation assertions | Open |
| Stale Forest workers run old code | High | Medium | Record revision and container deployment identity before submit | Open |
| Transform partially writes or mutates a hardlinked source | High | Low | Same-directory temp + `os.replace`; direct failure and inode tests | Open |

## Verification Checklist

- [ ] Contract checkpoint ancestor recorded.
- [ ] Focused slope and WEPP prep tests pass.
- [ ] rq-engine route regression tests pass.
- [ ] Full Python suite passes.
- [ ] Frontend lint/tests pass if affected.
- [ ] Changed documentation passes `wctl doc-lint`.
- [ ] Correctness review has no unresolved medium/high findings.
- [ ] Security review has no unresolved medium/high findings.
- [ ] Forest generated-output acceptance passes.

## Progress Notes

### 2026-09-04 11:31 UTC: Package initialization

**Agent/Contributor**: Codex

Created the package, recorded the operator-approved behavior, drafted the
canonical contract and ADR, and identified the existing multi-OFE copy path as
the implementation seam. No production implementation file has been edited.

**Next steps**: obtain two independent read-only contract reviews, disposition
findings, and commit the checkpoint before implementation.

### 2026-09-04 11:49 UTC: Initial contract review disposition

**Agent/Contributor**: Codex

Two independent reviewers rejected the initial draft. The checkpoint now
defines separate request and stored-state matrices, expected async failure
behavior, single-OFE invalid-state compatibility impact, all-file Forest proof,
exact development Compose deployment/rollback commands, and high security
triage for the changed file boundary. Post-fix confirmation remains pending.
