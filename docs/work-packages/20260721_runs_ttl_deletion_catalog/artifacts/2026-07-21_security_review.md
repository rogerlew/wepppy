# Security Review - Runs TTL Deletion Catalog

## Metadata

- **Package**: `docs/work-packages/20260721_runs_ttl_deletion_catalog/`
- **Reviewer**: `/root/rem02_security_qa_review` (independent, read-only)
- **Date**: 2026-07-21
- **Scope reviewed**: authenticated Runs catalog metadata, client rendering, and
  Usersum doc route
- **Commit context**: pre-implementation revision
  `a4bd3b63d5be56cfa3a5fe38448c5b972706d89e`

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The remediation borrows SURF-06, an authenticated
  catalog that exposes run metadata. TTL state must follow existing row-level
  ownership filtering and remain read-only.
- **Threat model assumptions**:
  - Users may see TTL metadata only for runs already returned by the catalog.
  - TTL metadata is read without altering expiration, access timestamps, or
    deletion state.
  - The documentation link is an internal, same-origin Usersum route.

## Findings

| ID | Severity | Surface | Description | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Governance authority | M1A was accepted for REM-01 only. | Register and review M1B before any implementation. | Corrected; post-fix confirmation pending |
| SEC-02 | Medium | Link/deployment safety | The draft hard-coded a root URL and conflicted with its server-generated-link claim. | Use a trusted Jinja-generated URL and add prefix/link-safety coverage. | Corrected; post-fix confirmation pending |
| SEC-03 | Medium | Authorization ordering | The plan did not prove an unselected row never triggered a TTL read. | Add sentinel no-read and allowed-row coverage. | Corrected; post-fix confirmation pending |
| SEC-04 | Medium | Metadata failure | Missing/malformed policy and timestamp handling were under-specified. | Define null fallback/no-touch/no-disclosure behavior and test each state. | Corrected; post-fix confirmation pending |
| SEC-05 | Medium | Usersum access | Least-privileged catalog readers were not guaranteed to resolve the guide. | Require `min_role: user` and normal-user resolution coverage. | Corrected; post-fix confirmation pending |

## Required Surface Checks

- Confirm owner/admin alias filtering occurs before any TTL read.
- Confirm a malformed/missing TTL file cannot turn into a catalog error, touch,
  or wider run-tree read.
- Confirm the Jinja template creates a deployment-prefix-aware href with
  `url_for`, never catalog JSON; timestamp values use text nodes.
- Confirm no new mutation route, CSRF exception, queue edge, or role rule is
  introduced.

## Verdict

- **Gate status**: pending independent post-fix confirmation and final
  implementation review.
- **Unresolved findings**: no unresolved finding if the named corrections are
  independently confirmed; implementation has not begun.
