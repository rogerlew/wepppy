# Independent contract reviews and disposition

Review date: 2026-11-05. Scope: RUNS-TTL-BULK-01 checkpoint only;
implementation and deployment are not approved by these reviews.

## Correctness review

Independent agent `ttl_contract_correctness` reviewed the decision, three
current contract amendments, template, sort helper and TTL setter. One medium
finding: an HTTP-success setter response does not prove protection when TTL is
null or deletion is queued/trash. No other major contract finding.

Disposition: amended the domain contracts and decision to require real returned
active protected metadata; null and queued/trash/purged results are explicit
non-successes. Browser response regressions cover each state. The reviewer
confirmed this finding resolved with no outstanding high/medium findings.
The reviewer also confirmed valid batch exclusion, re-sorting and failed-selection
clarifications; no outstanding high/medium concern.

## Security review

Independent agent `ttl_contract_security` independently reported the same
medium response-integrity finding. No additional security findings. Per-run
authorization, CSRF, encoded same-origin URLs and text-only output remain intact.
The existing setter Content envelope is outside RQ job-submission success scope;
no shared envelope change is required.

Disposition: same correction as above. The security reviewer confirmed the fix
and valid batch-exclusion handling; no remaining high/medium contract findings.

## Implementation acceptance retained

Chronological precision, both directions and null placement; re-sort after
successful protection; preserve failed visible selections; reject stale scope
responses; valid batch exclusion; missing/null/queued/trash/purged responses;
CSRF/auth errors; actual browser-handler request and partial-failure behavior.
Final correctness and dedicated security reviews remain required.
