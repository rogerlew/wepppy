# Security Review - Advisory Queue Rank in RQ Job Status

## Metadata

- **Package**: `docs/work-packages/20260807_rq_jobstatus_queue_rank/`
- **Reviewer**: Carson (`security_reviewer` role), independent read-only subagent
- **Date**: 2026-08-07 UTC
- **Scope reviewed**: `GET /api/jobstatus/{job_id}`, `wepppy/rq/job_info.py`,
  polling auth/rate limiting, queue snapshot disclosure, and Culvert token docs
- **Commit/branch context**: Initial review at `a416e7dd7`; remediation at
  `97141ba44`; no branch was created
- **Related artifacts**:
  - Code review: `artifacts/20260807_code_review.md`
  - QA review: `artifacts/20260807_qa_review.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: A public/open-by-default polling response gains bounded
  shared queue-state disclosure and a same-tree child identifier.
- **Threat model assumptions**:
  - Existing polling auth and rate limiting remain active and authoritative.
  - Registered `jobs:*` links are the only permitted tree-membership source.
  - Queue lookup is advisory and may omit on races or Redis errors.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High (review classification) | One ordered queue snapshot materializes the selected queue list. | This is the exact multi-candidate strategy approved in the normative contract. The implementation performs one read, never fetches metadata for unrelated jobs, and does not expose the snapshot contents except the selected same-tree ID and offset count. The operator-approved contract is the explicit risk acknowledgment; no per-candidate scans or invented queue limits are introduced. | Closed by contract; accepted residual cost documented |
| SEC-02 | Medium (baseline) | Existing limiter behavior trusts the first `X-Forwarded-For` value and has no eviction. | This behavior predates the package, is outside the authorized scope, and is unchanged. It is recorded as pre-existing baseline drift, not accepted as a queue-rank defect. | Closed as pre-existing/out of scope |
| SEC-03 | Medium | Review initially identified duplicate queue entries as an ordering risk. | The implementation now retains the first offset in one local pass, with deterministic regression coverage. | Fixed in `97141ba44` |

## Verdict

- **Gate status**: `approved with documented contract limitation`
- **Unresolved findings**:
  - High: none
  - Medium: none
  - Low: none affecting this package
- **Release recommendation**: approve package closure. The one-snapshot queue
  read remains an explicit contract limitation and is not a cross-queue or
  queue-mutation capability.

## Required Surface Checks

The final review must explicitly assess: unrelated job/function/run/description/
submitter/token disclosure; registered-tree membership of `position_job_id`;
count and queue-name disclosure; open/optional/required auth invariants; active
rate limiting; large-tree Redis cost; Redis-error response preservation and
traceback behavior; browse-token non-broadening; and absence of queue mutation,
priority, cancellation, or worker control.

## Validation Evidence

Focused queue-rank, job-info, rq-engine route, OpenAPI, and Culvert tests passed;
the combined focused set passed 105 tests. Post-remediation implementation
tests passed 70 tests. RQ graph, endpoint inventory, route checklist,
stubtest, broad-exception enforcement, documentation lint, and `git diff --check`
passed. The full-suite result is recorded in the package tracker.

## Residual Risk

Residual risk is limited to the approved one ordered queue snapshot per
single-origin multi-candidate status calculation. The operator approval in the
contract decision and the subsequent explicit authorization to proceed are the
package-owner acknowledgment. No queue depth, worker capacity, unrelated job
metadata, queue mutation, priority, cancellation, or token broadening is
introduced.

## Sign-off

- **Security reviewer**: Carson, 2026-08-07 UTC
- **Package owner**: Operator-approved contract; Codex, 2026-08-07 UTC
