# Security Review - Advisory Queue Rank in RQ Job Status

## Metadata

- **Package**: `docs/work-packages/20260807_rq_jobstatus_queue_rank/`
- **Reviewer**: Dedicated independent security reviewer (pending)
- **Date**: Pending (UTC)
- **Scope reviewed**: `GET /api/jobstatus/{job_id}`, `wepppy/rq/job_info.py`,
  polling auth/rate limiting, queue snapshot disclosure, and Culvert token docs
- **Commit/branch context**: Pending implementation review revision
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
| Pending | Pending | Pending | Dedicated implementation security review not yet run. | Pending | Complete all ten required surface checks and resolve High/Medium findings. | Open |

## Verdict

- **Gate status**: `pending`
- **Unresolved findings**:
  - High: pending
  - Medium: pending
  - Low: pending
- **Release recommendation**: hold pending independent review.

## Required Surface Checks

The final review must explicitly assess: unrelated job/function/run/description/
submitter/token disclosure; registered-tree membership of `position_job_id`;
count and queue-name disclosure; open/optional/required auth invariants; active
rate limiting; large-tree Redis cost; Redis-error response preservation and
traceback behavior; browse-token non-broadening; and absence of queue mutation,
priority, cancellation, or worker control.

## Validation Evidence

Pending implementation and validation commands.

## Residual Risk

Pending independent security review and explicit package-owner acknowledgment of
any accepted residual risk.

## Sign-off

- **Security reviewer**: Pending, UTC
- **Package owner**: Pending, UTC
