# WEPPcloud account identity and local email verification

**Status**: Operator-approved product direction; implementation pending. Two independent contract reviews completed; documentation findings closed. Email-first local signup and password choice after mailbox proof are operator-approved; implementation conformance remains pending.

## Authority and scope

The operator selected independent CILogon accounts regardless of email, while Google, GitHub, and local credentials share an account when email ownership is established. This supersedes earlier proposals to merge CILogon by email or introduce a CILogon mailbox-linking challenge. The operator approved the exact login-page text below and requested new-local email verification, retained existing local access, and a responsive User Profile with verification status/action.

This contract governs identity selection, account linking, local credential eligibility, and the associated UI. Existing roles, run ownership/membership, sessions, and ORCID workflows remain compatible. Production deployment, live database migration, and credential activation remain deferred. Code changes require the standalone contract checkpoint and independent reviews under the contract-first standard.

## Account boundaries

There are two account classes: **shared** (existing/local/Google/GitHub accounts, including preserved legacy ORCID records) and **CILogon-only**. A CILogon-only account has its own user ID, runs, roles, and permissions. It is keyed by fixed issuer `https://cilogon.org` plus validated `sub`. Neither matching nor verified contact email permits merging it into a shared account. Multiple CILogon subjects with the same contact email remain separate. Do not link Google/GitHub, set a local password, or use email recovery to enter a CILogon-only account. No cross-account merge or project transfer is in scope.

First resolve an existing provider identity to its original user; an email change must not reassign that link or overwrite a shared login email. Inactive users are denied. A previously unlinked CILogon subject creates a CILogon-only user atomically with its OAuth link, with no usable password. Names/contact email are optional; absent email must not prevent CILogon login. A returned contact email is informational, not proof of ownership or authority for local access. Store the initial contact address (if any); repeat CILogon login does not replace it, even if the provider supplies a different or newly available address. Adding a contact-edit/update workflow requires a separate accepted contract; any future or existing administrative address change must invalidate old verification as specified below. No arbitrary upstream IdP trust list, extra institutional scope, or CILogon email-matching fallback is needed.

For a previously unlinked Google/GitHub identity, establish ownership of the exact email via the provider: Google requires boolean `email_verified=true` from validated OIDC claims; GitHub requires a verified email record from its authenticated email API. Do not treat strings, a missing flag, or a different verified address as verification of the email being matched. Normalize surrounding whitespace and case consistently with the shared-account lookup; exactly one eligible shared match may be linked. Ambiguous case-insensitive matches fail safely, with no administrator preference or first-row selection. Otherwise create one shared OAuth user without a usable local password. Missing/unverified first-login email produces a helpful failure with no mutation. Already-linked identities authenticate by stable provider ID; provider email drift must not route to another account.

All new account/link writes are atomic. Unique identity and normalized shared-login email races must fail/retry without orphan users, reassignment, or duplicate accounts. Linking must not change roles or project access. A callback initiated for anonymous login must not silently merge into a different currently authenticated user; account switching and callbacks after session changes must follow a tested explicit flow.

## CILogon protocol and optional configuration

Use confidential authorization-code OIDC with `openid email profile`, no offline access/refresh tokens, fixed issuer and discovery `https://cilogon.org/.well-known/openid-configuration`. Production callback is `https://wepp.cloud/weppcloud/oauth/cilogon/callback`. Require valid signature, issuer, audience, expiry, state, nonce, and PKCE. A UserInfo response must have the same subject as the validated ID token. Never substitute email or a generic `id` for CILogon `sub`.

Use existing Authlib, route conventions, and secret loader. Credentials absent means CILogon is unavailable and other login methods remain usable; an explicitly configured missing secret must fail clearly rather than silently weakening authentication. The secret is `OAUTH_CILOGON_CLIENT_SECRET` / `OAUTH_CILOGON_CLIENT_SECRET_FILE`; the client ID uses `OAUTH_CILOGON_CLIENT_ID`. No production settings are activated by this contract. Configuration and Compose changes must preserve deployments that have no CILogon secret file.

## Login-page wording

Display these exact operator-approved explanations beside the respective sign-in options, in both desktop and mobile layouts:

**Google, GitHub, or email and password**  
Use the same email address to access the same WEPPcloud account and projects.

**CILogon — university or organization sign-in**  
CILogon uses a separate WEPPcloud account, even if your email address is the same. Projects from your other account won’t appear here.

Show the CILogon explanation when its option is available. Do not display unavailable login buttons or imply a password has already been set for an OAuth-only shared account. Preserve the approved wording; supplementary password-setup help may explain that enabling local credentials requires mailbox verification. No protocol jargon belongs in these explanatory blocks.

## Local credential lifecycle

Existing local accounts retain login access even if no explicit local verification record exists. Migration must preserve that compatibility without manufacturing verification timestamps. New local registrations must not receive authenticated sessions, remember cookies, JSON auth tokens, or protected-project access before mailbox verification and local credential setup complete. Google/GitHub login may access the shared account independently; it must not activate an unverified local password. CILogon login always enters its separate account.

Public registration with an existing shared account's email must never install or replace its password. Account creation using an email found only as a CILogon contact creates a separate shared account subject to normal new-local verification. Recovery/confirmation must look up the unique shared login identity, never a contact-email match or an arbitrary user among duplicates. Responses must avoid account enumeration.

`confirmed_at` is not sufficient evidence of local mailbox verification: legacy OAuth creation populates it. Store explicit verification provenance and local credential eligibility separately. Mailbox-verification evidence MUST bind the exact normalized address it verified, not just the user ID or a timestamp. Replacing a shared login email or CILogon contact email clears/supersedes verification for the old address; the new address is unverified until its own proof completes. A later provider contact update cannot carry forward the old address’s Verified badge. No new email-edit UI is authorized; these rules apply to any existing/admin/provider writer that changes an address. A historical random OAuth password hash is not proof of a usable local password. Preserve legacy hashes and access without guessing which were user-selected. Before disconnecting the last provider from a legacy account of uncertain local-password provenance, require successful proof of another usable sign-in method (for example the current local password) or mailbox-based password setup; do not force a reset during normal existing local login. New records must explicitly distinguish “no local credential,” “pending verification/setup,” and “usable local credential.” No account may disconnect its last usable sign-in method, including a CILogon-only account. A verified contact address is not another sign-in method and cannot authorize disconnecting that account’s only provider.

Framework consumers include registration, login, confirmation, password reset/change, HTML and JSON responses, remember-cookie restoration, and token issuance. A login-form-only check is insufficient: current Flask-Security auto-logs-in registrations when `LOGIN_WITHOUT_CONFIRMATION=True`. Never enable a new pending local credential through a password-change form reached via OAuth, a confirmation callback, or a JSON alternative. An authenticated OAuth user must use the mailbox-bound setup path to first establish a local credential.

A normal email-verification completion records mailbox proof only. It must not silently replace a grandfathered password or revoke existing sessions. A deliberate password setup/reset uses established password policy and revokes previous credentials/sessions through the existing `fs_uniquifier` mechanism; explain that consequence in the UI. Grandfathered accounts retain the residual risk of preexisting unverified passwords until the owner deliberately secures them. A “verified” badge must not claim those passwords or sessions were replaced.

## Verification messages and tokens

Email requests use authenticated CSRF-protected POSTs for the current account's stored address, with bounded resend behavior and truthful delivery failure feedback. No mail-on-GET or arbitrary supplied recipient. Public registration retains its existing CAPTCHA and CSRF. Public recovery retains its existing recovery controls and CSRF; it currently has no CAP-backed custom form, and adding recovery CAPTCHA is not authorized here. Both flows use generic responses. Mail sending alone never records verification or activates access.

Use existing Flask-Security signing, expiry, and mail facilities; add no token service. Verification/setup tokens must bind purpose, user ID/security identity, exact normalized email, and credential/email revision. Validate expiry using the existing configured confirmation/reset lifetime. Reject wrong-purpose, expired, replayed, or superseded tokens; address/password changes invalidate outstanding setup grants. A token cannot act on whichever account is currently logged in. If the logged-in principal differs, require the explicit sign-out/continue flow before mutation. Concurrent redemption must yield at most one activation. Presenting a link in GET renders the confirmation/setup form; CSRF-protected POST completes the action so mail scanners cannot activate credentials.

Completion must support rows whose legacy `confirmed_at` is already populated without clearing history. The stock confirmation view returns “already confirmed” for these rows; use its token-validation primitives with an owned completion path and explicit local verification provenance. Preserve source token checks; do not bypass them. Existing signed reset tokens bind identity/password but not explicitly email, so email changes must rotate/invalidate the relevant security identity or use a token binding the exact email. Do not duplicate confirmation and reset state machines without evidence that existing primitives cannot implement the accepted lifecycle.

## User Profile and prompts

Move `user/profile.html` from the narrow auth-card wrapper to `base_pure.htm` and established responsive cards. Explicitly retain `security/_messages.html`, account details, linked providers, preferences, logout, role-gated API-token controls, and internal feature-access controls. At 320/375 CSS-pixel mobile widths cards stack without horizontal page overflow; long email/identity/token text wraps or scrolls within its own control. Desktop uses normal page width. Preserve semantic headings, labels, keyboard navigation, and focus visibility.

Add an **Email Verification** card. Show **Verified** with the recorded mailbox-verification time when evidence exists; otherwise **Email verification not recorded** with **Send verification email**. Already verified state is idempotent. CILogon-only users may verify an available contact address for correspondence, but the card must explain **Verifying this email does not connect your other WEPPcloud accounts.** It must not offer local password setup, local recovery, or account merging. If no contact email was supplied, explain that there is no email to verify; no new contact-editing workflow is authorized. Separate contact verification provenance from local credential eligibility.

After Google/GitHub login to a shared account with unverified local credentials, show a visible prompt to verify email and secure local sign-in. Do not block the authorized OAuth session, revoke grandfathered local access, or lose safe post-login navigation. CILogon-only accounts have no local credential to secure and must not receive that prompt. Preserve normal existing local login; verification status remains visible on their profile.

## Approved email-first signup

The operator approved email/name first, followed by password selection after opening the verification/setup email (“yes, let's proceed as recommended”). No password entered before mailbox proof may become active. Reuse the mailbox-bound setup form for shared OAuth accounts that choose to enable local credentials. Existing local credentials are preserved; ordinary verification does not force a reset. This resolves OPEN-P1 and rejects activation of an initial registration password.

## State and acceptance matrix

| State | Required outcome |
| --- | --- |
| Shared local account; verified Google/GitHub email matches | Same shared user, roles, and runs; local credential eligibility unchanged. |
| Same email on shared and CILogon account | Separate users and projects; password recovery targets shared account only. |
| Two CILogon subjects with same contact email | Separate users; neither linked nor merged. |
| CILogon with missing email/name | Valid subject login succeeds; no placeholder login email. |
| CILogon contact verification | Only that account's exact contact address status changes; no local credential or shared access. |
| Shared login/contact email changes after verification | New address displays unverified; old-address evidence and tokens cannot verify it. |
| Existing unverified local user | Local access retained; Google/GitHub login prompts verification. |
| New local pending signup then Google/GitHub login | OAuth session allowed; pending local password remains unusable. |
| Shared OAuth user then public local signup using same email | No password mutation or duplicate shared account; mailbox setup required. |
| Returning linked provider with changed email | Original account by provider identity; no email-based reassignment. |
| Missing first Google/GitHub email assurance / ambiguous shared email | No link or account mutation; useful failure. |
| Inactive account / conflicting identity | Denied; no role or identity reassignment. |
| Legacy `confirmed_at` populated without mailbox proof | No fabricated verified status; mailbox workflow can establish explicit proof. |
| CILogon-only last-provider disconnect, even with verified contact | Denied; contact verification is not an alternate sign-in method. |
| Repeat CILogon login with changed/newly available contact claim | Stored contact and its address-bound status remain unchanged; account resolves by subject. |
| Last-provider disconnect with unknown local-password usability | Require proof of alternate sign-in before unlinking; ordinary existing login unchanged. |
| Token expiry/replay/cross-account use or concurrent mutation | No unauthorized activation or partial link; safe recovery path. |
| Mail send failure or repeated request | No false verification; bounded retry and explicit feedback. |

Test protocol inputs separately from stored states: malformed email types, absent/false/string verification flags, external `next`, CSRF, nonce/state/PKCE, issuer/audience/expiry/signature, UserInfo mismatch, and duplicate callbacks. Browser evidence must show the approved login wording and profile at mobile/desktop sizes. Real signed-token, datastore, token lifecycle, and mail-sink tests must exercise actual boundaries, not only mocks.

## Data compatibility and migration

Preserve `User.id`, roles, project foreign keys, hashes, existing OAuth links, and the current unique shared login email. Preferred additive representation: keep `User.email` for shared login/recovery (already nullable), add nonunique contact email and account-class/provenance fields, and store NULL shared login email for CILogon-only users. Do not remove the uniqueness constraint or insert fabricated deliverable-looking addresses to accommodate duplicate contacts. This is a migration design to validate against all consumers before implementation.

Inventory email-based login, registration, recovery, admin user lookup/edit, API/token claims, run owner display, notifications/mail, exports, account deletion, provider linking/disconnect, and account serialization. Explicitly separate display/contact lookup from identity lookup; a CILogon contact update cannot become a shared login identifier. Existing consumer assumptions requiring non-null email must be repaired or dispositioned with real tests before CILogon activation. Existing ORCID rows stay in their current class and mappings; no opportunistic rewrite is authorized.

On a disposable populated database, prove upgrade preserves existing user IDs/hashes/roles/runs and classifies existing users as shared while leaving verification unknown unless retained proof exists. Prevent old application writers from treating new CILogon NULL-email records or pending credentials as legacy usable local accounts: a tested coordinated migration/activation compatibility gate is required. Rollback must not run incompatible old code over new account states or drop new fields in a way that enables pending passwords. Prefer leaving additive data intact and disabling new enrollment while a compatible rollback is prepared. No production migration runs in this work package without separate deployment authorization.

## Rationale and related contracts

Independent CILogon identities remove dependence on upstream email ownership for account matching while retaining institutional sign-in. Verified Google/GitHub emails preserve the familiar shared-account experience. New-local verification prevents attacker-created credentials gaining access; preserving existing access is an explicit compatibility choice with recorded residual risk.

See [sessions](weppcloud-session-contract.md), [CSRF](weppcloud-csrf-contract.md), and [safe diagnostics](safe-traceback-contract.md). Research and prior rejected alternatives are retained in the work package as provenance, not current policy.
