# Security review - Browse listing output safety

## Metadata

- **Package**: `docs/work-packages/20261110_browse_listing_output_safety/`
- **Reviewer**: `/root/security` (independent agent)
- **Date**: 2026-11-11 UTC
- **Scope reviewed**: directory rows, action URLs, symlink display values,
  filesystem-derived breadcrumbs, and trusted-markup handoff
- **Commit context**: checkpoint `5e6de201b`; implementation `73d219877`
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
- **Gate status**: `pass` for local implementation; deployment pending.

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
| F3-S1 | High | Directory listing | Raw filename and symlink text enter trusted HTML | `listing.py:848-947`; `flow.py:580-589` | Contextual escaping and focused regression | Closed locally at `73d219877` |
| F3-S2 | High | Listing action URLs | Raw filename data enters path/attribute contexts | `listing.py:857-943` | Encode one path segment and escape attributes | Closed locally at `73d219877` |
| F3-S3 | High | Breadcrumbs | Stored path parts enter trusted breadcrumb markup | `flow.py:420-457,586` | Apply the same context rules | Closed locally at `73d219877` |

## Required Review Checks

- [x] Every filesystem-derived text value is HTML-escaped exactly once.
- [x] Every filename route component is encoded as exactly one path segment.
- [x] Query values are encoded independently and cannot be introduced by a name.
- [x] No event-handler attribute, element, URL authority, or extra path segment
      can arise from the hostile corpus.
- [x] The implementation has no sanitizer fallback or filename denylist.
- [x] Existing auth, containment, symlink traversal, and sensitive-path controls
      are unchanged.
- [x] Real temporary entries prove both a hostile case and a valid Unicode case.
- [x] Direct and action links resolve to the intended authorized entry.
- [x] Trusted-markup use is narrow and justified field by field.
- [x] No new dependency, external call, secret, queue, or process boundary exists.
- [x] Focused tests and exact implementation revision are retained.
- [x] Correctness review separately approves valid-state behavior.

## Rollout and Rollback Conditions

Production rollout requires separate authorization and a wepp1-equivalent smoke
under the real service identity and mounts. Do not create or browse a hostile
payload in production. Rollback must not knowingly restore the unsafe renderer;
if an unrelated behavior requires rollback, retain the output-encoding patch or
apply an equivalent containment response.

## Verdict

- **Gate status**: pass for local implementation
- **Unresolved findings**: none locally; rollout pending
- **Release recommendation**: local code approved; deployment separately gated.

## M0 independent review

Reviewer `/root/security` (`security_reviewer`), 2026-11-11 UTC, base
`c040d51d09530dee7f1562c467b98d74c8d6c5a4` plus contract amendment: design approved.
F3-S4 (High): missing-path breadcrumb labels, paths and raw diff query also
require repair. Disposition: confirmed in matrix and included in focused red
coverage and implementation. Release gate remains pending.

## Final independent review

Reviewer `/root/security`, 2026-11-11 UTC: approved scoped source/test candidate
committed as `73d219877`, descendant of reviewed checkpoint `5e6de201b`.
Observed validation: 10 focused tests passed; no unresolved High/Medium findings.
Real filesystem entries, parsed HTML/URL attributes, byte readback, nested literal
percent names, symlink targets and missing paths establish local output behavior.
Authorization, containment and parser capabilities are unchanged. Full suites
were waived; external action backends and production identities were not tested.
M4 remains pending separate authorization.

F3-S4 (High, missing-path breadcrumbs/raw diff) is also closed locally by the
reflected-path regression and contextual renderer. Security source/test diff
SHA-256 reviewed: `f0786324c3e2b8a09de3d3256b11a946e171bcb0834a5d880e8427d30e739339`.
