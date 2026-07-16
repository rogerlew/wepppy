# QA and Security Review - AgFields Watershed Parent Job

## Scope

Independent read-only review covered JWT scopes and run ownership, queue/job
metadata, cancellation blast radius, dependency release, response compatibility,
and browser/state hydration.

## Security Findings and Disposition

| Severity | Finding | Disposition |
| --- | --- | --- |
| High | `canceljob` used a session-only marker check, leaving user/service/MCP cross-run cancellation possible. | `rq:status` cancellation now calls `authorize_run_access`; wrong-owner and wrong-run user/service/MCP regressions deny before cancellation. |
| High | An already-failed dependency could strand finalization. | Added Batch Runner ready-deferred release behavior to all failure-tolerant suite dependents. |
| High | Cancellation could observe only a partial planned tree. | The route atomically stores all four planned IDs; dispatch and cancellation synchronize through a lock and marker. |
| Medium | Child/finalizer audit metadata had a publish-before-save window. | Metadata is now part of atomic RQ enqueue creation. |
| Medium | Response root/child semantics were absent from the canonical response contract. | Added the named-child compatibility contract and regression assertions. |

## Verification and Verdict

- Final reviewer-focused job-control suite: 28 tests passed, including the
  dual-scope Culvert compatibility path.
- No unresolved High, Medium, or Low findings.
- **Verdict**: pass.
