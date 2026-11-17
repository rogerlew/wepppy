# Account implementation security review

**Reviewer**: independent security reviewer (`account_contract_security`).
**Observed**: 2026-11-17 20:23 UTC.
**Checkpoint base**: `874de621c` (nullable identity consumer checkpoint), with the current uncommitted candidate.
**Verdict**: PASS for the reviewed local implementation security scope, subject to the separate validation/deployment gates below. No production authorization or package-wide completion is implied.

## Scope and authority

Reviewed account-security lifecycle, CILogon/Google/GitHub callback and identity handling, User fields/migration, credential secret registration, Bootstrap identity/authorization, nullable-email token consumers, and verification/profile templates against the current canonical account, session, CSRF, token, Bootstrap, and safe-diagnostic contracts. No production files or services were changed. Code continued evolving during review; this artifact identifies source readback and retained test outcomes rather than claiming review of an immutable release SHA.

CILogon remains independent by issuer/subject; contact email never selects a shared account. Google/GitHub use provider-established email ownership for initial shared matching. The operator approved email-first new-local signup; existing local credentials retain access. Earlier rejected CILogon email-matching policies are not reopened.

## Findings and disposition

| ID | Severity | Finding | Closure evidence |
| --- | --- | --- | --- |
| SEC-I1 | Medium | Raw external callback error description could enter diagnostics. | OAuth provider-error/token/UserInfo paths now use value-free messages. Source fix reviewed. |
| SEC-I2 | Medium | Google UserInfo was not bound to required validated ID-token claims. | Google now requires ID token and local nonce, validates issuer/claims, checks UserInfo subject equality, and uses validated claims for email assurance. Actual RSA/Authlib tests cover valid, issuer/audience/expiry/nonce/signature/missing-token/subject-mismatch cases. |
| SEC-I3 | Medium | New Bootstrap ID lookup returned detached ORM users before lazy role/membership checks, risking denial of valid CILogon admins/collaborators. | Both ID and legacy-email resolution eagerly load roles; run resolution loads members; membership compares stable IDs. Real ORM tests exercise owner, CILogon collaborator/admin, and revoked membership. |
| SEC-I4 | Low | Bootstrap audit identity always used ID despite a current shared login email. | Header now uses current resolved shared login email where present, otherwise stable user ID. No contact fallback. |

No unresolved security finding was identified in the read-back candidate. The low JSON input-shape observation is fixed in source: `_form` requires a dictionary and aborts with HTTP 400 before constructing `MultiDict`. `test_nonobject_json_is_bad_request` covers array, string, and null inputs with a real CSRF header and asserts rejection without mail. Source/test readback is complete. The primary agent reported the final isolated focused batch passed: 429 tests, 30 warnings, 32.47 seconds, including these malformed-JSON cases. No authentication bypass was observed.

## Security evidence

Source review confirms initial local registration stores no usable password and does not call login. Existing shared-email registration cannot replace a password. Mailbox setup uses the actual Flask-Security password validator, purpose/account/address/security identity/nonce binding, expiry, CSRF-protected completion, and compare-and-swap consumption. Setup changes the security identity; ordinary verification preserves the existing password/session. Address changes clear proof and invalidate grants. CILogon contact verification cannot establish local credentials. Last-provider disconnect is serialized by a user-row lock and requires a usable alternate sign-in method.

CILogon creation preserves independent User IDs even for duplicate contact email and accepts absent contact. Shared normalized-email and provider-identity uniqueness prevent duplicate bindings; account/link creation rolls back on conflicts. Signed Bootstrap IDs reject invalid values rather than falling back to email; active account and current run access are checked. Missing optional shared email does not become contact-based authority in personal/run tokens.

Primary-agent reported executed validation (reviewer inspected the associated tests, did not rerun the suite):

- Final isolated focused batch: 429 passed, 30 warnings in 32.47 seconds. Includes malformed JSON, owner display, Bootstrap ID/real ORM authorization, signed OIDC, generated mail-sink lifecycle, and remember/session regressions. This closes the pending focused execution-evidence note; the separate full Redis/PostgreSQL gates remain unavailable as documented.

- 88 combined lifecycle/Bootstrap/configuration checks passed, including real detached ORM owner/collaborator/admin/revoked membership and rq-adapter identity checks.
- Prior 64 lifecycle/OIDC checks passed, including actual Authlib RSA validation, SQLAlchemy persistence, Flask-Security forms, and generated mail-sink link redemption.
- Prior 111 migration/Bootstrap/token/auth regression checks passed.
- Browser checks passed at 320/375/1280 CSS pixels across nine combinations with screenshots retained; no horizontal overflow.
- Frontend lint passed; 126 suites/1,091 tests plus nine Node tests passed.
- Broad Python run remains incomplete: stopped after 332 passed/29 skipped at one unrelated culvert test requiring unavailable Redis in the isolated container. Do not report a full-suite pass.

## Separate rollout and evidence gates

Live registered-provider login, actual mail delivery, production PostgreSQL migration/row-lock concurrency parity, mounted-secret readability under the web identity, full consumer/environment acceptance, and production rollout are separate gates. Local tests and source review do not prove them. Retain the deployment hold and do not activate staged wepp1 credentials through this review.

In particular, row-lock implementation is not itself evidence of concurrent PostgreSQL behavior. Signed mailbox links must remain excluded from actual proxy/application diagnostics and retained artifacts; synthetic local logs do not establish production transport logging behavior. The broad-test environment limitation must be resolved or explicitly dispositioned by the owning validation process before claiming the full required gate.

## Residual accepted behavior

Grandfathered unverified local passwords remain usable as the operator requested. A verified badge confirms mailbox proof only; it does not claim that an old password was replaced. CILogon contact verification neither merges projects nor adds local recovery. No new external dependency, service, privilege, or deployment topology was introduced.
