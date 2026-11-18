# Independent contract review dispositions

Read-only reviewers: /root/contract_correctness (reviewer) and
/root/contract_security (security_reviewer), 2026-11-18 UTC. Neither authored edits.

| Reviewer | Finding | Disposition |
| --- | --- | --- |
| Correctness P1, security medium | Identical rebuilt bytes can validate stale source sidecar after publication failure | Accepted: invalidate old evidence before overwrite; atomically publish after success; preserve overwrite=False; verify hash |
| Correctness P2 | Secondary keys can round through try_parse decimal/exponent coercion | Accepted: exact signed-64-bit nonnegative integer strings for all identifiers; finite values |
| Both | Negative-only cache can suppress requests if treated as empty | Accepted: negative rows count as populated; partial/malformed provenance fails |
| Correctness P2 | Configured USDA endpoint is not proof of redirect destination | Accepted: separate configured endpoint from observed response origin or unknown |
| Security medium | Read timeouts permit unbounded slow-drip response | Accepted: absolute network deadline including headers/body; identity-only streamed size cap; slow-drip/compressed tests |

Residual requirements: direct NoDb lock/reload and SQLite/HTTP boundary tests, all six
call sites, rollback and externally isolated real-service generated-soil comparison.
No public deployment or scientific parameterization authority is inferred.
