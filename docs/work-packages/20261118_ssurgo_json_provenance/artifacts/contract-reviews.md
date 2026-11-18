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

Implementation review refinement: the reviewers identified that general 16 MiB
metadata could be repeated into every event and artifact sidecar. Adopt the explicit
64 KiB metadata bound and 64-level JSON nesting bound in the canonical contract;
query bodies retain 16 MiB. This narrows the client profile, so larger manifests
fail explicitly rather than claiming compatibility. Stdlib resolver calls were
confirmed to exceed socket timeouts; a killable short-lived resolver child is the
smallest bounded fix, with addresses cached per collection to avoid per-query
process cost. No external dependency/service is added. These reviewed refinements
are committed separately before the implementation commit.

## Final implementation review

Both independent read-only reviewers rechecked implementation 39f24ce92 and closed
all prior findings. Correctness: no remaining blockers. Security: no remaining
medium/high findings for this operator-selected scope. Reviewers did not author
changes or independently rerun the full suite. The security reviewer directly
confirmed resolver-launch exception translation. Real-service artifact validation
is retained separately; neither review establishes public deployment acceptance.

Additional closed findings: process-launch OSError and malformed-cache RecursionError
translate to SoilDataSourceError; metadata fields/events/table schemas validate
before reuse; invalid NoDb endpoint input is validated before logging/locking.
The 75 focused tests include real HTTP/SQLite, real disposable Redis lock/reload,
all six consumer arguments, and rollback of failed later batches. HTTPS was not
independently exercised by the reviewers.
