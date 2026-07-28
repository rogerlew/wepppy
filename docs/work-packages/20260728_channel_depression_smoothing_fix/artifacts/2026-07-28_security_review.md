# Security Review - Channel Depression Smoothing Propagation Fix

## Metadata

- **Package**:
  `docs/work-packages/20260728_channel_depression_smoothing_fix/`
- **Reviewer**: Independent operations/security control agent
- **Date**: 2026-07-28
- **Scope reviewed**: REM-05 checkpoint, DOM-05 field boundary, RQ/NoDb
  integrity, deployment containment, and rollback
- **Commit/branch context**: Uncommitted documentation checkpoint on local
  `master` based on `e07bb10668f5ac59b8bba4b8bb111e89f5d735a2`
- **Related artifacts**:
  - Contract decision: `2026-07-28_contract_decision.md`
  - Governance review: `2026-07-28_checkpoint_governance_review.md`
  - Disposition: `2026-07-28_checkpoint_review_disposition.md`

## Security Triage Decision

- **Security impact level**: `high` (inherited from DOM-05)
- **Dedicated security review required**: yes
- **Triage rationale**: The repaired value crosses an authenticated browser,
  RQ worker, and durable NoDb mutation boundary even though no attack surface or
  queue edge is intended to change.
- **Threat model assumptions**:
  - Existing authentication, session, origin, and CSRF controls remain intact.
  - The worker continues to accept only the three validated enum tokens.
  - Production verification remains read-only unless a disposable run is
    separately authorized.

## Raw Initial Findings

### Blocking

- Mandatory checkpoint evidence is absent: no dedicated security review, second
  review, disposition, or post-fix confirmation exists. Add and link them before
  the ancestor commit.
- The contract decision does not enumerate every applicable canonical contract.
  Add an explicit applicability table for the shared controller, NoDb
  persistence, RQ response, and CSRF contracts.

### Medium

- Production verification is mutation-ambiguous. Do not submit Fill against the
  named user run; require non-mutating markup/request evidence or a separately
  authorized disposable/cloned run.
- Rollback lacks the pre-deploy revision, revert/redeploy procedure, abort
  criteria, and post-rollback verification.
- Persistence evidence is weaker than the normative request-to-reload claim.
  Add focused non-production evidence for worker assignment, null compatibility,
  hydration, and partial-build failure semantics.
- The umbrella tracker places REM-05 under Done and strands the REM-01
  completion sentence. Repair lifecycle placement and sentence integrity.

## Findings Disposition Status

| ID | Severity | Surface | Required action | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | Blocking | Checkpoint evidence | Add raw reviews, this dedicated artifact, disposition, links, and confirmations | Resolved pending confirmation |
| SEC-02 | Blocking | Contract authority | Enumerate applicable canonical contracts and no-impact/conflict disposition | Resolved pending confirmation |
| SEC-03 | Medium | Production integrity | Make production verification explicitly read-only | Resolved pending confirmation |
| SEC-04 | Medium | Deployment rollback | Add revision capture, abort criteria, explicit revert/redeploy, and verification | Resolved pending confirmation |
| SEC-05 | Medium | RQ/NoDb integrity | Add worker/null/hydration/failure characterization to regression plan | Resolved pending confirmation |
| SEC-06 | Medium | Governance lifecycle | Repair REM-01 sentence and move REM-05 to In Progress | Resolved pending confirmation |
| SEC-07 | Medium | Registered source boundary | Add the planned worker characterization test to both exact scope lists | Resolved pending confirmation |

## Initial Verdict

- **Gate status**: fail pending post-fix confirmation
- **Unresolved findings at initial review**:
  - Blocking: 2
  - Medium: 4
  - Low: 0
- **Release recommendation**: hold until both checkpoint reviewers confirm the
  dispositions.

## Surface Checks

### Auth, Session, and Authorization

- Existing controls remain unchanged; no new route or input is authorized.

### Input Validation and Output Safety

- The existing three-token Watershed setter remains the validation authority.
- REM-05 adds no alias, parser fallback, or new token.

### Queue, Worker, and Subprocess Surfaces

- Queue wiring and job dependencies are unchanged.
- Regression characterization must prove the existing non-null/null behavior.

### Data Integrity, Locking, and Concurrency

- The NoDb setter, lock, atomic dump, and cache behavior remain unchanged.
- Production verification must not mutate the reported run.

### Logging, Monitoring, and Incident Readiness

- The plan records pre-deploy revision, queue/service gates, targeted logs, and
  an explicit revert/redeploy path.

## Validation Evidence

- Checkpoint docs lint: pass for REM-05, GOV-00A, and umbrella packages.
- `git diff --check`: pass.
- Implementation checks: pending the standalone ancestor.

## Residual Risk

- The named user run still contains least-cost-breach artifacts until its owner
  deliberately rebuilds it after deployment.
- The complete DOM-05 audit remains planned and unverified.

## Sign-off

- **Security reviewer**: Independent operations/security control agent,
  post-fix PASS, 2026-07-28
- **Package owner**: Codex, 2026-07-28

## Post-fix Confirmation

**PASS**. No blocking or medium findings remain. The worker characterization
test is registered in both authoritative scope lists, and all initial findings
are corrected and dispositioned. The documentation-only checkpoint is safe to
commit as the standalone pre-implementation ancestor.
