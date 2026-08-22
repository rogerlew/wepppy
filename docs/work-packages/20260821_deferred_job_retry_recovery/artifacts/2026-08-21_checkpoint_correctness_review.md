# Initial independent checkpoint correctness review

**Reviewer**: Independent read-only correctness reviewer
**Date**: 2026-08-21 UTC
**Initial verdict**: Fail; four High and one Medium finding

## Findings

- **High — non-finite scope**: The first draft omitted an exact owner/source
  matrix and assumed saved hints plus existing submit locks. Batch Runner scans
  the registry and had no such lock.
- **High — promotion race**: A normal pipeline after a status read could cancel
  a job RQ concurrently promoted to queued or started.
- **High — incomplete graph semantics**: Canceling one recorded deferred job
  could leave deferred descendants or ignore executable siblings.
- **High — incomplete governance**: Borrowed owners, formal security artifact,
  review disposition, and post-fix confirmation were missing.
- **Medium — partial failures**: Cleanup, enqueue, and replacement-hint
  persistence failure outcomes were not fully specified.

## Required Corrections

The reviewer required an exhaustive finite matrix, a conditional RQ-state
transaction with transition-race evidence, graph-wide associated cleanup,
explicit failure ordering, complete governance records, and post-fix rereview.
All findings were accepted for correction; this raw review is retained and is
not rewritten as approval.
