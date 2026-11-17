# CILogon and account verification tracker

**Timezone**: UTC  
**Updated**: 2026-11-17 19:50 UTC  
**Phase**: Contract revision and independent review; implementation pending.  
**Security impact**: High.  
**Next milestone**: Review disposition and remaining new-local password setup decision.

## Task board

- [x] Inspect existing OAuth/registration/profile and stage inactive wepp1 credentials.
- [x] Record independent CILogon account policy and exact accepted login wording.
- [x] Rewrite canonical account contract and ExecPlan; amend session/CSRF/diagnostic contracts.
- [x] Obtain independent security and correctness reviews; fix and close every documentation finding on reviewer readback.
- [ ] Resolve open product decision and commit accepted preimplementation checkpoint.
- [ ] Implement additive migration, provider/lifecycle/UI, tests, and documentation.
- [ ] Complete local and environment acceptance; retain deployment hold.

## Current authority

CILogon is separate by issuer/subject regardless of email. Verified Google/GitHub email may access the shared local account. New local credentials require verification; existing local access remains. Login copy is accepted verbatim; User Profile becomes a normal responsive page with a verification card. Earlier CILogon email-matching/allowlist/challenge proposals are superseded. See [account contract](../../schemas/weppcloud-account-email-verification-contract.md) and [decision checkpoint](artifacts/20261117_contract_decision.md).

## Evidence and reviews

[Staging receipt](artifacts/20261117_secret_staging.md) proves inactive mode-0600 credentials on wepp1, not container wiring or live login. [Initial review](artifacts/20261117_contract_review.md) and [research](artifacts/20261117_cilogon_email_trust_research.md) are historical evidence. [Round-2 review and disposition](artifacts/20261117_contract_review_round2.md) records three distinct fixes and both reviewers’ final closure. No unresolved security/correctness documentation findings; OPEN-P1 is the sole product decision. Implementation security/correctness template artifacts remain unassessed.

## Outstanding decisions and limits

New signup password selection after mailbox proof is recommended but not yet approved. Reviewers may identify other concrete product decisions. No forced legacy password reset, CILogon/shared merge, contact-editing workflow, or production activation is authorized. Registration approval and nonproduction callback availability are unverified. Browser/mail/real-provider and migration acceptance remain pending.

## Validation and handoff

All 15 relevant Markdown files pass individual absolute-path `wctl doc-lint` (zero errors/warnings); `git diff --check` passes. Spelling preview showed only preexisting/shared-text substitutions, left untouched. No app tests run for docs-only changes. Worktree `/home/workdir/wepppy-cilogon-oidc`, branch `work/cilogon-oidc-scaffold`; original checkout WIP untouched. Installed wctl changes to shared checkout, so lint changed files by absolute path. No commit, merge, implementation, or deployment is claimed.

## Review outcome

The reviewed policy and UI wording are recorded. OPEN-P1 asks whether new local signup uses email/name first and password choice after the mailbox link (recommended); no user approval inferred. After that decision, update the lifecycle and obtain the standalone accepted checkpoint commit before implementation. No production changes occurred in this review task.


Approval update: operator explicitly approved email-first signup with password selection after the verification link and requested proceeding. OPEN-P1 is resolved. Implementation and its required standalone checkpoint commit are authorized; production deployment/migration remain deferred. Historical pending-choice statements above describe the preceding review state.
