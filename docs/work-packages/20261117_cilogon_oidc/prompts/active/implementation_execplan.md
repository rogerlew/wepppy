# Implement independent CILogon accounts and secure local signup


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Update Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective with the package tracker. Current scope is execution of the accepted plan after the required checkpoint; production deployment remains deferred.

## Purpose / Big Picture


People can sign in through CILogon to a separate WEPPcloud account. Local credentials, Google, and GitHub use a shared account based on verified email. The login page explains this distinction before sign-in. New local credentials require mailbox verification, existing local users retain access, and a responsive User Profile displays verification status with a send action.

## Progress

- [x] Inspect OAuth/registration/profile and stage inactive wepp1 credentials (2026-11-17).
- [x] Obtain two independent contract reviews and approve email-first signup; checkpoint `9eb2dfcf0`.
- [x] Review nullable-identity consumer extension; checkpoint `874de621c`.
- [x] M2: Implement additive identity/provenance migration and repair nullable-email consumers; SQLite compatibility evidence retained.
- [x] M3: Implement isolated CILogon, verified shared-provider matching, mailbox setup/verification, and responsive account pages.
- [x] M4 local review: close security/correctness source findings; execute signed-token, real ORM, mail-sink, browser and frontend checks.
- [ ] M4 environment gates: populated PostgreSQL migration/concurrency, registered nonproduction providers, real mail delivery, and production-equivalent secret mounts. Full Python gate currently encounters isolated-environment prerequisites; see validation artifact.
- [x] M5: Deliver local implementation/review handoff with 429 focused Python passes, 36 diagnostic/asset passes, frontend/browser evidence, and explicit environment gates; production migration/activation/deployment remain deferred.

## Surprises & Discoveries


Generic OAuth callback routes already exist. `_link_identity` uses email fallback and assigns a random password plus `confirmed_at` to OAuth-created users. A nonempty hash is therefore not proof of a usable local password, and `confirmed_at` is not proof of mailbox verification. Generic disconnect checks hash presence. `User.email` is unique but nullable: separate contact email can accommodate CILogon duplicates without dropping shared-login uniqueness.

`SECURITY_LOGIN_WITHOUT_CONFIRMATION=True` causes Flask-Security registration to issue authenticated sessions and JSON tokens. Checking only the login form would leave that bypass. Stock confirmation short-circuits on populated `confirmed_at`; reset changes `fs_uniquifier`, invalidating sessions, and its token does not explicitly bind email. These existing primitives need deliberate integration, not a second token service.

## Decision Log


The operator authorized inactive credential installation on wepp1 while deferring deployment. Credentials are already staged; do not reinstall/rotate or activate them merely to implement this feature.

The latest accepted policy makes CILogon accounts independent regardless of contact email, superseding all proposals for CILogon email matching, upstream allowlists, or mailbox-assisted linking. Google/GitHub retain provider-established email ownership for shared matching. The operator approved the exact login copy now in the canonical account contract.

The operator requires new-local email verification, existing local login preservation, OAuth prompts for unverified local credentials, and responsive User Profile. Choosing the new-local password after opening an emailed setup link is approved. Do not silently reset grandfathered passwords.

## Outcomes & Retrospective


Implementation and local review evidence are retained in the task worktree. Separate CILogon identity, mailbox-first password setup, legacy access, and responsive account UI are implemented. Independent reviews found consumer gaps in recovery, token issuance, Bootstrap, and nullable owner display; these were repaired. See tracker and validation artifact for executed counts and rollout evidence still pending. Production code/configuration/database state remains unchanged. Prior research records trust uncertainty, not a demonstrated arbitrary-email exploit against CILogon.

## Context and Orientation


Worktree `/home/workdir/wepppy-cilogon-oidc`, branch `work/cilogon-oidc-scaffold`, starting source `3950b57520c029c75df67565238b94543a31b03a`. Preserve unrelated WIP in the original checkout. Read nearest AGENTS before editing app, tests, Docker, CSS, and browser tests.

`configuration.py::_load_oauth_providers` registers providers. `utils/oauth.py` creates Authlib clients and PKCE. `routes/_security/oauth.py` implements login, callback, email selection, linking, and disconnect. `auth_forms.py` extends registration/login. `app.py` defines User/OAuthAccount/datastore and initializes Flask-Security. `routes/user.py` renders profile; `templates/user/profile.html` now extends the normal page layout. `templates/security/login_user.html` renders provider buttons. Alembic lives under `wepppy/weppcloud/migrations`.

Canonical authority is `docs/schemas/weppcloud-account-email-verification-contract.md`, with session, CSRF, and safe-traceback contracts amended in this checkpoint. Preserve existing current contracts rather than treating code or old work-package proposals as behavioral authority.

## Plan of Work


### M1: Accepted contract checkpoint


Record starting revision, exact normative changes, user authority, compatibility/security impact, and regression evidence in `artifacts/20261117_contract_decision.md`. Resolve the password setup choice; obtain two independent read-only contract reviews and disposition every finding. Commit the current canonical amendments and accepted review checkpoint as a standalone ancestor before implementation. If approval or commit authority is missing, stop at a concrete reviewable checkpoint and report exactly what remains. Keep review-only artifacts distinct from implementation approvals.

### M2: Additive data compatibility


Before code, retain `artifacts/account_migration_plan.md` with actual Alembic heads, User readers/writers, data state matrix, unique-email race behavior, and rollback gates. Keep existing unique nullable `User.email` as shared login/recovery identity; add separate CILogon contact email/account class and explicit verification/local-credential state. CILogon-only rows must have no shared login email or usable password. Existing rows remain shared, preserving IDs, hashes, roles, OAuth links, and run ownership. No fabricated verification backfill.

Inventory and repair all consumers: login/register/confirm/reset/change-password, admin email search/edit, notification destinations, token claims, profile/run-owner displays, exports, account deletion, OAuth linking/disconnect, and serialization. Test NULL login email and duplicate contact emails through real persistence and representative project authorization. Preserve ORCID behavior. Do not deploy incompatible old code against new states; document coordinated migration/activation and compatible rollback, leaving additive fields intact.

### M3: Provider, verification, and UI


Add CILogon settings using existing secret loader and optional credential configuration. Use fixed issuer/discovery, `openid email profile`, confidential authorization-code flow, and the exact public callback. Require validated ID token, nonce, state, PKCE and matching UserInfo subject. Resolve CILogon only by issuer/subject; create distinct accounts even when contact email matches. Missing CILogon contact email is valid. Reuse Authlib validation and narrow expected failure handling.

For Google/GitHub unlinked identities require provider proof for the exact email and match only shared accounts uniquely. Returning links remain authoritative after email changes. Make account/link writes atomic and prevent current-session callback confusion. Preserve roles/runs and OAuth-only provider behavior. Document secret registration/redaction in existing inventory; optional Compose wiring must not break deployments without CILogon files. No live host configuration changes.

Implement accepted new-local registration/setup, explicit provenance, and owned mailbox completion using Flask-Security primitives. Cover all HTML/JSON consumers rather than just login forms. Ordinary verification cannot activate a provisional password; first password setup requires mailbox proof even after OAuth login. Confirmation supports legacy OAuth-confirmed rows. Tokens bind purpose/account/email/security state, expire, and complete once on CSRF-protected POST; account/email changes and concurrency must be tested. Grandfathered existing access remains usable. Last-provider disconnect requires a proven alternate login, not merely an old random hash.

Move User Profile to `base_pure.htm`, retain flash messages and existing feature/token controls, and add the Email Verification card with account-class-specific behavior from the contract. CILogon contact verification never enables local login or merging. Google/GitHub login prompts users with unverified local credentials without blocking OAuth or losing safe navigation. Put the exact approved explanations beside login options and preserve mobile usability. Update current user help and developer/operator docs in the same change.

### M4: Validation and independent review


Test real cryptographic and datastore boundaries with synthetic keys/disposable data. Include same-email independent/shared accounts, duplicate CILogon contacts, missing contact, Google/GitHub shared matching, local registration pre-hijack, existing OAuth email registration, HTML/JSON login bypasses, contact/local verification separation, recovery isolation, token replay/expiry/account mismatch, concurrency, last-login protection, and legacy compatibility. Profile/browser tests at 320/375 CSS pixels and desktop must show approved text and no page overflow. Mail-sink tests follow the actual generated link through completion. Existing provider/login/session/run authorization regressions must pass.

Run tests from the actual checkout mounted in the test container; do not remount the shared stack implicitly. Use separate nonproduction provider credentials and registered callback. If unavailable, mark real-provider acceptance pending and continue local tests. Validate mounted-secret readability with production-equivalent web UID/GID/mounts using synthetic values. Close medium/high implementation review findings and retain evidence before claiming readiness.

### M5: Handoff without deployment


Record tested revision, counts, environment gaps, migration compatibility, registration state, and credential receipt. Update `docs/infrastructure/secrets.md` and established user/developer/operator help. Inspect canonical `scripts/deploy-production.sh` and production deployment policy before documenting future rollout/rollback. Do not execute rollout, restart/reload, publish, or migrate wepp1. Production acceptance remains separate.

## Concrete Steps


After checkpoint acceptance and implementation, in the checkout used by the running test container:

    wctl run-pytest tests/weppcloud/test_configuration.py tests/weppcloud/routes/test_security_oauth_routes.py tests/weppcloud/routes/test_security_oauth_callback.py tests/weppcloud/routes/test_security_auth_forms.py tests/weppcloud/routes/test_user_profile_token.py
    wctl run-pytest tests --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master

Add new lifecycle/migration suites discovered during implementation. Run stub gates when changing API surfaces. Record actual results and source identity, not predicted pass counts. Lint each changed Markdown file through `wctl doc-lint --path /absolute/path/file.md`; installed wctl currently resolves relative paths from the shared checkout. Local test runs now use the operator-approved isolated container and this exact worktree.

## Validation and Acceptance


A person reading the login page understands which account contains their projects. A shared user can use local credentials or verified Google/GitHub login without losing projects. CILogon with the same email reaches separate projects. New-local unverified credentials and any cross-account email recovery fail to grant access. Existing local users keep access. Verification indicators are backed by actual mailbox proof, and profile controls work at mobile and desktop widths. Real provider/browser/mail evidence is distinct from fixture validation.

## Idempotence and Recovery


Repeated staging refuses differing secrets. Repeated mailbox actions cannot activate or link twice. Existing IDs, credential hashes, roles, and runs are retained during additive migration. Do not drop identity/verification fields or run incompatible old code to roll back. Disabling CILogon must not erase its accounts or links. Preserve original checkout WIP and no production mutations beyond already completed inactive credential staging.

## Artifacts and Interfaces


Credential staging receipt is completed evidence. Historical `20261117_contract_review.md` and email-trust research record superseded proposals. Current reviews/disposition and contract decision are dated revision artifacts in `artifacts/`. Retain no secrets/tokens/cookies/personal claims. Reuse Authlib, Flask-Security, SQLAlchemy/Alembic, owned templates and secret loader; no new dependencies or services.

Revision note (2026-11-17 19:50 UTC): rewritten around independent CILogon identity, verified shared-provider matching, approved login wording, complete lifecycle/consumer gates, and unresolved new-local password setup choice. Superseded proposals are historical only.


Approval update: operator explicitly approved email-first signup with password selection after the verification link and requested proceeding. OPEN-P1 is resolved. Implementation and its required standalone checkpoint commit are authorized; production deployment/migration remain deferred. Historical pending-choice statements above describe the preceding review state.

Implementation discoveries: role/token/Bootstrap consumers assumed a nonempty login email. The reviewed consumer checkpoint replaces those assumptions with stable user IDs; contacts remain nonauthoritative. Bootstrap eager loading and ID membership comparison are necessary across resolver app contexts. Browser checks exposed a wide theme selector and token-row overflow, fixed in the account-page stylesheet. Tests use synthetic credentials and real signed claims/mailbox tokens; production parity remains a distinct gate.

Final source checkpoint: `679dc65d4`; 429 focused Python checks and 36 diagnostic/generated-asset checks passed. Independent source findings closed. The isolated container was stopped after validation; Redis/PostgreSQL/live-provider/mail/mount acceptance remains open as recorded in the validation receipt.
