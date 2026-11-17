# Contract review round 2: independent CILogon identity

**Scope**: account identity/local verification contract; session, CSRF, diagnostic amendments; package/ExecPlan/decision checkpoint.  
**Reviewers**: `account_contract_security` (security) and `account_contract_correctness` (correctness/compatibility).  
**Date**: 2026-11-17 UTC.  
**Implementation revision**: `3950b57520c029c75df67565238b94543a31b03a`; documentation working-tree amendments, no implementation reviewed.

## Review findings and primary-agent disposition

| ID | Severity | Finding | Disposition and exact authority |
| --- | --- | --- | --- |
| SEC-C2 / COR-C1 | Medium | A verification timestamp could survive an address change and label a new address Verified. | Fixed: account contract “Local credential lifecycle” binds proof to the exact normalized address and invalidates old status; “Account boundaries” retains initial contact on repeat CILogon login; acceptance matrix covers address changes and provider drift. |
| SEC-C3 | Low | Draft incorrectly described recovery CAPTCHA as existing behavior. | Fixed: account contract “Verification messages and tokens” and CSRF “Account email verification” preserve registration CAPTCHA/CSRF and recovery CSRF separately; no new recovery CAPTCHA. |
| COR-C2 | Low | Last-method rule should explicitly cover new CILogon-only users. | Fixed: “Local credential lifecycle” forbids disconnecting any account’s last usable method; verified contact is not an alternate login. Matrix includes CILogon-only disconnect. |
| OPEN-P1 | Product decision | Select the new-local password before or after mailbox proof. | Pending operator: recommend email/name first and password selection after opening the verification/setup email. Retaining an initial password requires a reviewed design that cannot activate an attacker-selected password. No approval inferred. |

## Historical findings

Initial SEC-01 is closed by the operator’s independent CILogon policy, not risk acceptance: no CILogon email merge, local password, or shared recovery. Earlier token lifecycle ambiguity is addressed with purpose/account/email/security-state binding, existing expiry settings, POST completion, replay/concurrency rules, and cross-account handling. Prior correctness findings for populated `confirmed_at`, registration auto-login/JSON tokens, unknown legacy password usability, reset effects, flash retention, and superseded plan text have explicit current coverage.

Grandfathered local credential risk remains the operator-required compatibility boundary. Current contracts do not claim ordinary verification replaces old passwords or revokes sessions. Implementation must still prove migration/NULL-email consumer compatibility and actual auth boundaries; this review does not approve code or deployment.

## Final rereview

Both independent reviewers reread the amended sections and explicitly closed all security/correctness documentation findings. Security confirmed SEC-C2 and SEC-C3 closed; correctness confirmed address-bound status and last-method protection closed. Both identify OPEN-P1 as the sole unresolved product choice. The contract checkpoint is not implementation-ready while OPEN-P1 and the accepted standalone ancestor commit remain outstanding.


Approval update: operator explicitly approved email-first signup with password selection after the verification link and requested proceeding. OPEN-P1 is resolved. Implementation and its required standalone checkpoint commit are authorized; production deployment/migration remain deferred. Historical pending-choice statements above describe the preceding review state.
