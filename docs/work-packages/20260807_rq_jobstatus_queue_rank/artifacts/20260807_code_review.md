# Code Correctness Review - Advisory Queue Rank in RQ Job Status

## Metadata

- **Reviewer**: Poincare (`reviewer` role), independent read-only subagent
- **Initial review date**: 2026-08-07 UTC
- **Initial revision reviewed**: `a416e7dd7a30007fe67e74982db4d7fc0e16063d`
- **Follow-up revision**: `97141ba44` (review-remediation commit)
- **Scope**: `wepppy/rq/job_info.py`, queue-tree traversal, RQ 1.16.2 ordering,
  race handling, bounded Redis access, disclosure, and aggregate status

## Findings and Disposition

| ID | Severity | Finding | Disposition | Status |
| --- | --- | --- | --- | --- |
| CODE-01 | High (review classification) | `Queue.get_job_ids()` materializes one full ordered queue snapshot. | The approved contract explicitly permits one ordered queue snapshot for a multi-candidate single-origin calculation and forbids replacing it with one position lookup per descendant. The implementation performs one queue read, does not fetch unrelated metadata, and the package documents this intentional initial limitation. Operator approval of the exact contract is the disposition. | Closed by contract; accepted residual cost documented |
| CODE-02 | Medium | Duplicate queue-list entries could overwrite an earlier candidate offset. | Replaced the dictionary comprehension with a one-pass `setdefault` offset map and added `test_duplicate_queue_entry_uses_earliest_offset`. | Fixed in `97141ba44` |
| CODE-03 | Low | Direct module stubtest reported missing `QUEUE_RANK_BASIS`, `logger`, and the pre-existing `UNKNOWN_PROGRESS_UPDATED_AT`. | Added all three runtime symbols to `job_info.pyi`; direct stubtest now passes. | Fixed in `97141ba44` |

## Review Evidence

The reviewer reported no additional defects in tree membership, status
normalization, aggregate fields, auth, route pass-through, disclosure, or
Redis-error omission. Focused validation after remediation passed 70 tests for
the RQ/jobstatus implementation and route suites. `wctl run-stubtest
wepppy.rq.job_info` passed with no issues.

The full review text identified CODE-01 as an implementation concern, but its
requested per-candidate bounded position strategy would conflict with the
approved one-operation contract. No normative behavior was changed in response.

## Verdict

- **Implementation correctness**: Approved after CODE-02 and CODE-03 remediation.
- **Unresolved High/Medium implementation findings**: None. CODE-01 is a
  documented, operator-approved contract limitation rather than an open defect.
- **Follow-up**: No queue topology or cross-queue ranking work is authorized by
  this package.
