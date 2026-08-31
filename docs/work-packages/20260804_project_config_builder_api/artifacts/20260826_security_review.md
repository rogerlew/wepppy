# Security Review - Project Config Builder API

## Triage

Impact is high because authenticated input can create run-scoped artifacts.
JWT scope validation precedes parsing/resolution. Only exact registered IDs,
fixed integer overrides, registry revision, and a bounded idempotency key are
accepted; token, filename, paths, config keys, environment references, and raw
options are not accepted.

## Findings

| ID | Severity | Finding | Resolution | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | High | Hiding an override control cannot authorize a resolution change. | Submission rechecks current normalized PowerUser/Admin/Root claims and returns canonical 403. | Resolved |
| SEC-02 | High | Duplicate or stale submissions could create ambiguous projects. | Staleness precedes allocation; actor-scoped WP04 reservation handles replay/conflict/in-progress. | Resolved |
| SEC-03 | High | Browser input could influence config path/token. | Exact payload allowlist and server-owned `config.cfg`/`config` token. | Resolved |
| SEC-04 | Medium | Successful overrides need safe audit identity. | Structured actor user ID/run ID log excludes claims and bearer tokens. | Resolved |

## Verdict

Existing JWT/session-token bridge, canonical response, sanitizer, run-root,
ownership, cleanup, and atomicity boundaries are preserved. No queue edge,
dependency, secret, arbitrary path, or enabled deployment default was added.

- Gate: pass
- Unresolved findings: High 0; Medium 0; Low 0
- Recommendation: dormant only pending WP07/WP11
- Reviewer/package owner: Codex, 2026-08-26
