# REM-04 checkpoint review disposition

## Reviews

- `2026-07-28_checkpoint_security_governance_review.md`
- `2026-07-28_checkpoint_correctness_compatibility_review.md`

The initial reviews failed with one high, six medium, and one low finding when
overlapping forwarded-policy and report-catalog findings are counted by review
artifact. Every finding is accepted and addressed below. Post-fix reviewer
confirmation remains required before the checkpoint commit.

## Disposition

| Finding | Disposition |
| --- | --- |
| Security H1 / Correctness C-01 | Accepted-fixed. The session contract now delegates to the shared CSRF guard contract. The legacy rq-engine forwarded-origin variable remains accepted but inert, explicit external origin configuration replaces it, and a negative regression is mandatory. |
| Security M1 / Correctness C-02 | Accepted-fixed. The CSRF contract now names authoritative inputs and ingress preconditions per service, defines safe rejection when authority is unavailable, and specifies only the exact HTTP:80 to HTTPS:443 same-host bridge. WP04 now uses authoritative request fixtures and raw-header negative vectors. |
| Security M2 / Correctness C-03 | Accepted-fixed. Diagnostics section 9 now contains the complete immutable ID/title/severity catalog, duplicate/unknown behavior, sanitized overall derivation, locally generated timestamp, constrained path-only prefix, and hostile metadata tests. |
| Correctness C-04 | Accepted-fixed. WP04 now separates the shared predicate matrix from Flask-WTF, rq-engine authentication, and query-engine boundary vectors. It defines Flask token acquisition and CSRF-first error precedence. |
| Correctness C-05 | Accepted-fixed. Reset uses resolved Flask/Flask-Login configuration directly, never invents a session-domain fallback, and tests unset and distinct domains. |

## Post-Fix Status

Both independent reviewers confirmed PASS after rereview with zero unresolved
high, medium, or low findings. The checkpoint remains non-authoritative only
until the standalone ancestor is recorded.
