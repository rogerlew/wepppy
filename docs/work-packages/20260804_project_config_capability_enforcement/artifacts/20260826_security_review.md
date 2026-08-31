# Security Review - Project Config Capability Enforcement

## Triage and Threat Model

- Impact: high; dedicated review required.
- Request catalog IDs, soil modes, and land-use database tokens are untrusted.
- Authorization remains at the existing route boundary and capability checks
  run before NoDb mutation or RQ enqueue.

## Findings

| ID | Severity | Finding | Resolution | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | High | Hidden UI choices could be invoked directly. | Submission paths consume the same project capability authority as presentation. | Resolved |
| SEC-02 | High | Enforcement could break legacy or persisted state. | Missing authority bypasses enforcement; checks govern new submissions only. | Resolved |
| SEC-03 | Medium | Soil enum aliases are unsuitable durable IDs. | Exact semantic-ID/runtime map is checked in and tested. | Resolved |

## Surface Checks and Verdict

Auth scopes/decorators, CSRF/CAP boundaries, run-root resolution, NoDb locking,
canonical errors, and queue topology are unchanged. No dependency, secret,
network call, or deployment default was added. Generated configs remain scanned
by WP00A and atomically written by WP04.

- Gate: pass
- Unresolved findings: High 0; Medium 0; Low 0
- Release recommendation: dormant only; deployed exercise remains WP11
- Reviewer/package owner: Codex, 2026-08-26
