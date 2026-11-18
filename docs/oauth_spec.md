# WEPPcloud sign-in implementation

The authoritative rules are in the [account identity and verification contract](schemas/weppcloud-account-email-verification-contract.md). This guide describes the implementation and replaces the earlier OAuth rollout proposal.

## Account selection

Google and GitHub share the local account whose normalized login email matches a provider-verified address on first login. Google requires validated OIDC claims; GitHub uses its authenticated emails API. Later logins resolve the saved provider ID, even if the provider email changes. Account/link creation is atomic; inactive and ambiguous matches fail.

CILogon uses its fixed issuer and validated subject to select a separate account. Its optional contact email is not a login/recovery identifier. Matching contacts never merge accounts or projects. ORCID retains its established behavior. Users cannot disconnect their only usable login; legacy password provenance requires password proof before removing the final provider.

## Local signup and verification

New registration collects name/email and retains CAPTCHA and CSRF. It stores no password and grants no session. The mailbox link opens a password form; a CSRF-protected POST sets the password and records verification. Google/GitHub users can use the same mailbox setup flow to add local credentials. Existing local credentials remain usable.

`account_security.py` owns registration, confirmation requests, password-recovery dispatch, and mailbox completion. Established local password recovery uses Flask-Security reset primitives; pending/passwordless shared users receive setup instructions. CILogon contact verification never enables local credentials. Stock change/reset/confirm routes cannot bypass first-password setup. JSON registration follows the same rules.

Verification records bind the exact address, and grants bind purpose, user ID, security identity, address, and a one-use nonce. Address changes invalidate proof/grants and rotate security identity. Sending mail does not verify anything. Resends reserve a per-account 60-second interval before mail delivery; see [ADR-0147](adrs/ADR-0147-account-email-resend-interval.md). The existing confirmation lifetime governs mailbox links.

The User Profile shows verification status, send/setup actions, and existing account controls on a responsive page. Verification alone does not replace an existing password or revoke its sessions. Deliberate setup/reset rotates the security identity.

## CILogon registration and configuration

Register a confidential client with callback `https://wepp.cloud/weppcloud/oauth/cilogon/callback`, scopes `openid email profile`, and no refresh tokens. Callback matching is exact. Use a separately registered development client/callback for testing; never copy production credentials into development.

Set `OAUTH_CILOGON_CLIENT_ID` and `OAUTH_CILOGON_CLIENT_SECRET_FILE` (or the existing inline secret convention). Optional `OAUTH_CILOGON_REDIRECT_URI` overrides the derived external host/site-prefix callback. Discovery/issuer are fixed to CILogon. Missing credentials hide the option; an explicitly configured unreadable secret file fails configuration. The opt-in `docker/docker-compose.cilogon.yml` overlay adds only the web secret mount; base Compose stacks do not require it. The secret participates in diagnostic redaction.

The callback validates state, PKCE, nonce, signature, issuer, audience, expiry, and matching UserInfo subject using Authlib. CILogon tokens are not persisted. Google retains its configured token metadata and uses validated claims for email ownership. Callback errors do not log provider error descriptions or tokens.

## Migration and deployment hold

Migration `a7c1106e42b9` adds account class, contact, credential state, and mailbox provenance. Existing IDs, passwords, roles, links, and projects remain unchanged. It rejects duplicate `lower(trim(email))` values before changing the schema. Downgrade refuses once new account states exist; retain additive data and prepare a compatible rollback.

Coordinate all database consumers with the schema before activating new signup/CILogon states. Nullable login email is supported by ID-based authorization, role assignment, personal/run token issuance, and Bootstrap; contact email is never an authorization substitute. Email-based sharing/search still targets shared login identities, so CILogon project access administration must use IDs.

Production remains deferred. Credentials are staged inactive on wepp1; see the [staging receipt](work-packages/20261117_cilogon_oidc/artifacts/20261117_secret_staging.md). Future rollout must use the installed `wctl` preset and `scripts/deploy-production.sh`, retaining its build/topology/Redis/static/health/cleanup checks. Do not replace it with ad hoc Compose activation or run old code against new account states. Before separately authorized rollout, complete populated PostgreSQL migration/concurrency, production-identity secret-mount readability, real mail delivery, and registered nonproduction-provider acceptance. Local synthetic tests are not these rollout proofs.
