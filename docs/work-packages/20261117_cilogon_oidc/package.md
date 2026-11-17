# CILogon accounts, local email verification, and responsive profile

**Status**: Contract update and independent review; implementation pending; deployment deferred.  
**Started**: 2026-11-17 19:13 UTC  
**Updated**: 2026-11-17 19:50 UTC  
**Owner**: WEPPcloud operator; Codex implementation support.

## Overview

Add independent CILogon accounts alongside shared local/Google/GitHub accounts. Require mailbox verification before enabling new local credentials, retain existing local access, and explain account boundaries in simple login-page text. Migrate User Profile to the standard responsive page layout with an Email Verification card.

## Scope and authority

The current task is to update the work package/contracts, dispatch independent reviews, and disposition findings. Earlier execution authorization is retained, but this turn stops at the reviewed documentation checkpoint and any unresolved product decisions. No code, production migration, deployment, service restart, credential activation, or image publication is included.

The [account contract](../../schemas/weppcloud-account-email-verification-contract.md) is the intended authority for identity boundaries, exact approved login copy, local verification, profile UX, and migration compatibility. CILogon issuer/subject determines its separate account regardless of email. Google/GitHub verified email may match the shared local account. Existing roles, runs, and ORCID behavior remain compatible.

## Registration decisions

Provider `cilogon`, display name `CILogon`, confidential client, `openid email profile`, and production callback `https://wepp.cloud/weppcloud/oauth/cilogon/callback`. No extra institutional scope or refresh tokens are required for independent identities. Registration approval/scopes/callback and a permitted nonproduction callback still need verification. Production credentials are staged, inactive, on wepp1; see [receipt](artifacts/20261117_secret_staging.md).

## Complexity budget

Reuse Authlib, Flask-Security signing/mail/recovery primitives, SQLAlchemy/Alembic, existing session/security machinery, Pure responsive layout, and Compose secrets. Permit one provider, additive identity/contact/verification fields, bounded credential lifecycle changes, UI, tests, and documentation. No new service, datastore, dependency, privilege, or deployment topology. Preserve the existing unique shared-login email by storing separate nonunique contact email for CILogon accounts; validate all consumers before implementing that representation. No CILogon/shared account merging or project transfer.

## Security and review

Security impact: **high**. Independent security and correctness review are mandatory. Review durable identity separation, shared verified-email matching, new-local pre-registration attacks, verification provenance, framework HTML/JSON paths, last-sign-in protection, migration compatibility, and session/token noninterference. Historical research and rejected trust policies remain evidence only.

The remaining product decision is whether new-local signup selects the password after mailbox proof (recommended) or retains a password entered at registration. Existing local users must not be silently reset or revoked. See the account contract’s Open product decision section.

## Acceptance and evidence

Prove same-email CILogon/shared accounts are distinct through real persistence, login, password recovery, and project access. Prove local/Google/GitHub reach the same shared account and preserve roles/runs. New local pending users cannot obtain sessions/tokens via any framework entry point. Contact verification cannot create a CILogon local password or merge identities. Preserve existing local access and truthful verification status. Browser evidence covers approved copy and profile at mobile and desktop widths. Inspect actual generated mail links, token completion, secret mounts under the web identity, and redacted effective configuration; file existence or job success alone is insufficient.

Implementation, local validation, environment validation, and deployment are separate claims. No run-model artifacts are produced; credentials and tokens remain outside browsable project storage. Provider interaction and real mail delivery remain explicit environment gates if unavailable.

## Work

[ExecPlan](prompts/active/implementation_execplan.md) defines milestones; [tracker](tracker.md) records status. The preimplementation checkpoint must include canonical amendments, operator decisions, independent review disposition, and a standalone ancestor commit before code changes. No commit or implementation approval is inferred for the unresolved password-selection choice.


Approval update: operator explicitly approved email-first signup with password selection after the verification link and requested proceeding. OPEN-P1 is resolved. Implementation and its required standalone checkpoint commit are authorized; production deployment/migration remain deferred. Historical pending-choice statements above describe the preceding review state.
