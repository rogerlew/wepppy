# ADR catalog implementation review

Date: 2026-11-05 UTC. Checkpoint ancestor: `0b804f1ff`.

## Independent correctness review

Reviewer: `/root/adr_contract_correctness`, read-only review of discovery helper,
routes, templates and regression tests against the approved Usersum contract.

One low-severity finding: inline `Status: Accepted. Review Date: 2027-01-01`
was incorrectly interpreted as a recorded Date. The matcher now excludes Review
Date; plain and bold negative regressions were added. The reviewer independently
confirmed closure, including a true Date after a Review Date. Final result:
no remaining findings.

The reviewer confirmed discovery of all 138 repository ADRs (91 with recorded
dates), chronology, manifest precedence, prefix handling, public routes, existing
shell rendering and filesystem boundaries. Metadata supports the documented
formats; arbitrary Markdown metadata structures are outside the contract.

## Independent security review

Reviewer: `/root/adr_contract_security`, read-only implementation review.
Result: PASS, no blocking findings.

Shared discovery/detail checks constrain filenames and repository-root access,
reject symlinks and traversal. Jinja escapes listing/title/breadcrumb metadata;
full documents reuse the existing Markdown renderer. Manifest-first links and
generic source/raw role checks are unchanged. Public ADR access with strict
source-manifest mode matches the approved contract.

Residual behavior: eligible ADRs become public automatically, as requested.
No deployment was performed.
