# FA-01 review gates

Prepared: 2026-10-01 20:47 UTC. Status: pending; no independent review has been claimed.

## Contract reviews

Two independent read-only reviewers must assess the exact prepared checkpoint after milestone-zero evidence is complete. One review must cover correctness/valid-state UX and cross-contract consistency; the other must cover authority, compatibility and security boundaries. Record reviewer identity, reviewed revision, findings, author disposition and post-fix confirmation. The author cannot sign off their own amendment.

The technical review must not reinstate two-person operational approval of group memberships. That workflow was explicitly rejected; code/contract review is a different repository requirement.

## Implementation correctness review

Create `artifacts/<date>_correctness_review.md` using `docs/prompt_templates/correctness_review_template.md`. Cover the source/state inventory, real database transactions, allowed and denied HTTP paths, public-read side effects, anonymous creator compatibility, group-only identity restrictions, retained service compatibility and actual generated outputs. Green mocked tests do not close those boundaries.

## Implementation security review

The [security review preparation](2026-10-01_security_review.md) records high impact and the evidence needed. Replace its pending state with an independent review against the implemented revision using the repository security template. No medium/high finding may remain open at closeout. No security or correctness approval is implied by documentation lint.

## Current evidence

Assessment tests: 275 passed before this planning increment. Documentation validation: 20 Markdown files passed lint with no errors/warnings; relative file links resolved; whitespace and root AGENTS size checks passed. Spelling previews inspected. Runtime/migration/browser/service acceptance: not performed. Contract ancestor: not created. Current task is the prepared amendment and plan, not implementation acceptance.
