# FA-01 review gates

Scope update, 2026-10-01: the operator clarified that only limited features become read-only for callers lacking access; ordinary anonymous creation/functionality is unchanged. Earlier general writer/creator-proof requirements in this historical review are superseded. Current scope and deployed evidence are in [the M0 record](2026-10-01_milestone_zero.md). Final narrowed-checkpoint reviews are separate from the earlier review confirmations.


Prepared: 2026-10-01 20:47 UTC. Updated after independent prepared-amendment review on 2026-10-01. Status: planning review passed after fixes; milestone-zero design reviews passed; implementation reviews pending.

## Contract reviews

[Prepared-amendment reviews and disposition](2026-10-01_contract_reviews.md) record four accepted findings and independent confirmation of all fixes. Both reviewers approve proceeding into milestone zero, not runtime implementation.

Two independent read-only reviewers must assess the exact prepared checkpoint after milestone-zero evidence is complete. One review must cover correctness/valid-state UX and cross-contract consistency; the other must cover authority, compatibility and security boundaries. Record reviewer identity, reviewed revision, findings, author disposition and post-fix confirmation. The author cannot sign off their own amendment.

The technical review must not reinstate two-person operational approval of group memberships. That workflow was explicitly rejected; code/contract review is a different repository requirement.

## Implementation correctness review

Create `artifacts/<date>_correctness_review.md` using `docs/prompt_templates/correctness_review_template.md`. Cover the source/state inventory, real database transactions, allowed and denied HTTP paths, public-read side effects, anonymous creator compatibility, group-only identity restrictions, retained service compatibility and actual generated outputs. Green mocked tests do not close those boundaries.

## Implementation security review

The [security review preparation](2026-10-01_security_review.md) records high impact and the evidence needed. Replace its pending state with an independent review against the implemented revision using the repository security template. No medium/high finding may remain open at closeout. No security or correctness approval is implied by documentation lint.

## Current evidence

Assessment tests: 275 passed before this planning increment. Documentation validation: 20 Markdown files passed lint with no errors/warnings; relative file links resolved; whitespace and root AGENTS size checks passed. Spelling previews inspected. Runtime/migration/browser/service acceptance: not performed. Prepared amendment commit: `4cd85e2d5`; accepted contract ancestor: recorded in the package tracker. Current M0 review: [two independent approvals after fixes](2026-10-01_m0_reviews.md), zero unresolved High/Medium findings. Runtime acceptance is pending.
