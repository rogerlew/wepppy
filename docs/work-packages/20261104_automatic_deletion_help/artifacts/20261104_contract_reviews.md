# Independent contract reviews

Correctness reviewer: `ttl_review`. Security reviewer: `ttl_security`.
Both reviewed the proposed contracts read-only before implementation.

Correctness finding: disabled/excluded policy does not cancel queued/trash
removal. Resolved by explicit policy-vs-started-deletion caveat in the project
control contract and Usersum specification, without changing GC.
Conflicting Last Modified-only and sort-exclusion wording was reconciled.
Add readonly/batch re-enable regression using returned effective policy.

Security review: no high/medium findings; verify scope-before-read, fresh policy
only, and no success claims after uncertain mutation results.

Final verdicts: both approve checkpoint; no unresolved medium/high findings.
Implementation and production deployment are not certified by this review.
