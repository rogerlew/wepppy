# Correctness Review - Project Config Builder API

## User Outcome and State Matrix

An authenticated creator can load a deterministic schema, validate a complete
proposal, and create one fixed-token project. Missing/unknown selections return
field-addressable 400; stale revision returns 409 before allocation; an
unauthorized override returns 403; disabled writer returns 503; acquired,
in-progress, conflict, replay, and initialization failure retain WP04 semantics.
No Interfaces or legacy project path changes.

## Findings

| ID | Severity | Finding | Resolution | Status |
| --- | --- | --- | --- | --- |
| COR-01 | High | Registry validation and creation could resolve different source revisions. | Both reload/check the same opaque registry digest and creation rejects a stale submitted revision. | Resolved |
| COR-02 | Medium | Manifest initially conflated registry digest with deployment provenance. | Manifest source revision now uses deployment revision; registry/component revisions remain independently recorded. | Resolved |
| COR-03 | Medium | Builder creation initially omitted standard run TTL initialization. | Initialize TTL after Ron and before ownership/readiness completion. | Resolved |

## Verdict

- Gate: pass
- Unresolved findings: High 0; Medium 0; Low 0
- Recommendation: ship default-off; UI is WP07 and Forest enablement is WP11.
- Reviewer: Codex, 2026-08-26
