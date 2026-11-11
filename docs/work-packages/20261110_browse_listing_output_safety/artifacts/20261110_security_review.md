# Security review - Browse listing output safety

## Metadata

- **Package**: `docs/work-packages/20261110_browse_listing_output_safety/`
- **Reviewer**: unassigned; must be independent of implementation author
- **Date**: pending
- **Scope reviewed**: directory rows, action URLs, symlink display values,
  filesystem-derived breadcrumbs, and trusted-markup handoff
- **Commit context**: scaffold at `c040d51d0`; implementation revision pending
- **Related artifacts**:
  - Contract decision: `artifacts/20261110_contract_decision.md`
  - Failure class: `artifacts/20261110_failure_class_matrix.md`
  - Correctness review: `artifacts/20261110_correctness_review.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: attacker-controlled persistent filesystem metadata is
  rendered in an authenticated same-origin page used by collaborators and
  administrators.
- **Mapping**: CWE-79; OWASP Top 10 2021 A03 Injection.
- **Gate status**: `fail` until implementation and evidence are reviewed.

## Threat Assumptions

- A legitimate project writer can introduce at least one filesystem name chosen
  by that writer.
- A different user with browser authority can later view the directory.
- Existing run access and filesystem containment are preserved and are not a
  substitute for output encoding.
- The test corpus is inert and remains local; no validation runs on wepp1.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F3-S1 | High | Directory listing | Raw filename and symlink text enter trusted HTML | `listing.py:848-947`; `flow.py:580-589` | Contextual escaping and focused regression | Open |
| F3-S2 | High | Listing action URLs | Raw filename data enters path/attribute contexts | `listing.py:857-943` | Encode one path segment and escape attributes | Open |
| F3-S3 | High | Breadcrumbs | Stored path parts enter trusted breadcrumb markup | `flow.py:420-457,586` | Apply the same context rules | Open |

## Required Review Checks

- [ ] Every filesystem-derived text value is HTML-escaped exactly once.
- [ ] Every filename route component is encoded as exactly one path segment.
- [ ] Query values are encoded independently and cannot be introduced by a name.
- [ ] No event-handler attribute, element, URL authority, or extra path segment
      can arise from the hostile corpus.
- [ ] The implementation has no sanitizer fallback or filename denylist.
- [ ] Existing auth, containment, symlink traversal, and sensitive-path controls
      are unchanged.
- [ ] Real temporary entries prove both a hostile case and a valid Unicode case.
- [ ] Direct and action links resolve to the intended authorized entry.
- [ ] Trusted-markup use is narrow and justified field by field.
- [ ] No new dependency, external call, secret, queue, or process boundary exists.
- [ ] Focused tests and exact implementation revision are retained.
- [ ] Correctness review separately approves valid-state behavior.

## Rollout and Rollback Conditions

Production rollout requires separate authorization and a wepp1-equivalent smoke
under the real service identity and mounts. Do not create or browse a hostile
payload in production. Rollback must not knowingly restore the unsafe renderer;
if an unrelated behavior requires rollback, retain the output-encoding patch or
apply an equivalent containment response.

## Verdict

- **Gate status**: fail (scaffold only)
- **Unresolved findings**: three High
- **Release recommendation**: hold until focused evidence and independent review
  close all High/Medium findings.

## M0 independent review

Reviewer `/root/security` (`security_reviewer`), 2026-11-11 UTC, base
`c040d51d09530dee7f1562c467b98d74c8d6c5a4` plus contract amendment: design approved.
F3-S4 (High): missing-path breadcrumb labels, paths and raw diff query also
require repair. Disposition: confirmed in matrix and included in focused red
coverage and implementation. Release gate remains pending.
