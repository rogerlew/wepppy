# Account security contract reviews

**Status**: HOLD; draft reviewed, no implementation sign-off.  
**Reviewers**: independent `account_contract_security` and `account_contract_correctness` agents.  
**Scope**: proposed `docs/schemas/weppcloud-account-email-verification-contract.md` and existing OAuth, registration, confirmation, recovery, and profile paths.

## Findings and disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| SEC-01 | High | Unverified federated email matching can grant existing account access independently of local registration safeguards. | Open: informed operator trust decision pending. Earlier assistant ownership assertion corrected; no risk acceptance inferred. |
| SEC-02 | Medium | New-local verification/password setup needs exact expiry, replay, account/email binding, and session invalidation rules. | Open: password-selection decision pending, then finalize lifecycle before checkpoint. |
| COR-01 | Medium | Framework confirmation exits early for existing OAuth rows with `confirmed_at`, preventing separate local provenance. | Open: define actual verification completion supporting those rows without clearing history. |
| COR-02 | Medium | Existing OAuth-created random password hashes are not proof of usable local credentials; last-method disconnect uses hash presence. | Open: define credential classification and preserve a usable sign-in method. |
| COR-03 | Medium | Registration auto-login and JSON tokens bypass a login-form-only gate; reset/change/confirmation also consume policy. | Open: explicitly cover all framework entry points in accepted contract and direct tests. |
| COR-04 | Low | ExecPlan has superseded text plus a scope amendment. | Open: rewrite milestones around final accepted policy before checkpoint commit. |

Grandfathered local login remains operator-required compatibility. Verification alone does not invalidate a possibly attacker-selected legacy password. Existing reset helper rotates `fs_uniquifier` and therefore sessions; default reset tokens do not explicitly bind email. Preserve profile flash messages when replacing the auth-card wrapper.

## Provider evidence

Live CILogon discovery at `https://cilogon.org/.well-known/openid-configuration` advertises `email` but not `email_verified`. Official [OIDC guidance](https://www.cilogon.org/oidc) warns some upstream providers do not supply stable or verified email. No documented generic uncertainty flag was found. Absence is unknown, not proof of either verified or unverified status. A provider-specific assurance policy or mailbox verification would be needed before claiming safe automatic matching across arbitrary CILogon providers.

## Checkpoint boundary

No implementation files were edited and no checkpoint approval/commit is claimed. Resolve operator choices, finalize current contracts and migration/lifecycle details, repeat independent review of amendments, then commit the accepted checkpoint before implementation. Production deployment and migration remain deferred.
