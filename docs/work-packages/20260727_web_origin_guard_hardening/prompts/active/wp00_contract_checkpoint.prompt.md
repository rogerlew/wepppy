# WP00 - Contract-first checkpoint and bounded-remediation registration

> **Purpose**: Establish reviewed authority and normative contracts before any
> implementation file changes.
> **Target**: Codex
> **Created**: 2026-07-28
> **Status**: Active
> **Security gate**: `high`; two independent checkpoint reviews are mandatory.

## Objective

Create and commit a documentation-only checkpoint that makes WP01-WP04
executable under `docs/standards/contract-first-change-standard.md`.

## Required Outputs

- `artifacts/2026-07-28_contract_decision.md`, completed from the draft.
- A new stable remediation ID and milestone in the Pure UI child-package
  register and both umbrella trackers/ExecPlans.
- A bounded-remediation decision artifact under the Pure UI ratification
  package naming borrowed owners, exact boundaries, exclusions, and authority.
- Normative amendments to `docs/schemas/weppcloud-csrf-contract.md` and
  `docs/ui-docs/diagnostics-page.spec.md`, marked implementation pending.
- Two independent read-only checkpoint reviews: one security/governance and one
  correctness/compatibility.
- A disposition resolving every finding.
- One standalone ancestor commit containing only checkpoint documentation.
- The full ancestor revision recorded in this package tracker and ExecPlan.

## Decisions That Must Be Explicit

1. The complete same-origin decision order, including exact behavior when
   `Origin`, `Referer`, and `Sec-Fetch-Site` are all absent.
2. Whether and how `Sec-Fetch-Site: same-origin` can authorize an upstream-TLS
   request, and why a conflicting present `Origin` always rejects.
3. The trusted source of allowed scheme/host/port values for each framework;
   raw client forwarded headers must not become authority.
4. Exact CSRF interaction per surface.
5. Exact owned reset-cookie names, paths, and domains.
6. The copied-report field and fixed-message allowlist.
7. Compatibility, rollback, security, and regression evidence.

## Review Requirements

Reviewers must be independent of the checkpoint author and read-only. One
review must focus on authority, scope containment, CSRF/origin spoofing,
forwarded-header trust, cookie boundaries, and disclosure. The other must focus
on contract completeness, cross-service parity, compatibility, and executable
test vectors.

All high and medium findings must be resolved. Record low findings as resolved
or explicitly accepted by the package owner. Re-run both reviews after material
contract changes.

## Commit Boundary

Do not edit or commit Python, JavaScript, templates, or tests in WP00. Before
creating the checkpoint commit, inspect its file list and verify it contains
only contract, governance, work-package, and review documentation. Record the
resulting full revision; WP01-WP04 remain blocked until it is an ancestor of
their implementation.

## Validation Gates

    wctl doc-lint --path \
      docs/work-packages/20260727_web_origin_guard_hardening
    wctl doc-lint --path docs/schemas/weppcloud-csrf-contract.md
    wctl doc-lint --path docs/ui-docs/diagnostics-page.spec.md
    git diff --check

## Outcome (Complete this when retiring the prompt)

**Completed**: 2026-07-28
**Agent**: Codex with two independent reviewers
**Checkpoint revision**: Pending commit; record immediately after commit
**Review artifacts**:
`2026-07-28_checkpoint_security_governance_review.md` and
`2026-07-28_checkpoint_correctness_compatibility_review.md`
**Result**: Both reviews PASS after disposition; zero unresolved findings
**Deviations**: None
