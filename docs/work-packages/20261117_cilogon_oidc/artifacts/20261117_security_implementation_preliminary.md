# Preliminary implementation security review

**Reviewer**: independent security reviewer (`account_contract_security`).
**Observed**: 2026-11-17 20:11 UTC.
**Base revision**: `9eb2dfcf01096fc316415f2f39a17104e00f465c` plus changing uncommitted implementation.
**Status**: PRELIMINARY / HOLD. Implementation and tests are still being edited; this is not final acceptance.

## Scope

Read-only review of `wepppy/weppcloud/account_security.py`, OAuth routes, User-model additions, account migration, provider configuration/overlay, and verification/profile templates against `docs/schemas/weppcloud-account-email-verification-contract.md`. No application tests were run by this reviewer. Production was not contacted or modified.

## Findings

| ID | Severity | Evidence and required action | Status |
| --- | --- | --- | --- |
| SEC-I1 | Medium | OAuth callback logged raw external error descriptions on the new provider path. The primary agent replaced that logging during review; source now records only provider. Add/retain a canary test that raw provider error/code/description values do not reach logs. | Source fix observed; regression evidence pending |
| SEC-I2 | Medium | Google callback still accepts fetched UserInfo subject/email without requiring the ID token or binding UserInfo subject to validated token identity. CILogon correctly performs both checks. Canonical Account boundaries requires Google ownership from validated OIDC claims. Require the Google ID token/validated claims and matching subject, or use validated claims directly for identity/email. Add a real signed subject-A token plus subject-B UserInfo rejection case and prove zero identity writes. | Open at observation |

## Positive evidence and limits

New local registration explicitly creates `password=None` and pending state, instead of activating a registration-selected password. CILogon creation stores NULL shared-login email, separate contact, no password, and independent provider-subject mapping. Recovery lookup filters shared identities. Setup token data includes purpose, user/security identity, exact address, and nonce; compare-and-swap update consumes the nonce with account/address checks. Ordinary verification does not rotate existing sessions; setup rotates the uniquifier. Migration refuses normalized-email collisions and preserves a compatible rollback requirement. These are source observations, not executed boundary proofs.

The implementation must still demonstrate real signature rejection, HTML/JSON registration and recovery bypass coverage, CSRF, token replay/concurrent redemption, normalized-email races, CILogon/shared recovery isolation, populated migration, and actual generated-link consumption. In particular, never claim that the lack of a usable initial password alone proves every framework credential entry point is guarded. Confirm owned completion response headers/log handling preserve the signed-link diagnostic contract. Final review must use the finished candidate and its validation receipts.

## Disposition

The earlier unconditional CILogon email-matching concern remains closed by the accepted independent-account policy. Do not reopen rejected linking designs. The email-first new-local signup decision is now explicitly authorized. Grandfathered legacy-password risk remains the accepted compatibility boundary; ordinary verification must not be presented as credential replacement.
