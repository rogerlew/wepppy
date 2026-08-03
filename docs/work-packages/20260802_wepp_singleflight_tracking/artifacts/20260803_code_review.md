# WEPP single-flight implementation code review

**Reviewer**: Independent `reviewer` agent
**Date**: 2026-08-03 UTC
**Final disposition**: Approved; no unresolved High or Medium findings

## Findings

- **High, resolved**: RQ 1.16.2 `dependency_ids` are byte Redis keys, not raw IDs. Runtime now decodes and strips `rq:job:` before fetch; regressions use production-shaped byte keys.
- **Medium, accepted residual**: A root receipt could expire while children remain queued through an outage longer than seven days. This exceeds normal duration and the 12-hour job timeout, so it does not block the incident fix. Durable receipts are recorded as follow-up if production delay approaches retention.
- **Low, resolved**: Package text now names pinned RQ 1.16.2 rather than RQ 2.x.

The reviewer re-reviewed the remediated implementation and approved enum normalization, byte-key handling, transitive dependency viability, unrelated-failure behavior, and coverage of all five keys.
