# CILogon accounts, local email verification, and responsive profile

**Status**: Merged to local master; CILogon registration approval and rollout gates pending; deployment deferred.
**Started**: 2026-11-17 19:13 UTC
**Updated**: 2026-11-17 19:50 UTC
**Owner**: WEPPcloud operator; Codex implementation support.

## Overview

Add independent CILogon accounts alongside shared local/Google/GitHub accounts. Require mailbox verification before enabling new local credentials, retain existing local access, and explain account boundaries in simple login-page text. Migrate User Profile to the standard responsive page layout with an Email Verification card.

## Scope and authority

The operator authorized implementation after accepting email-first signup and the reviewed contracts. Code, tests, user/operator documentation, and independent findings disposition are in scope. Production migration, deployment, service restart, credential activation, and image publication remain deferred.

The [account contract](../../schemas/weppcloud-account-email-verification-contract.md) is the intended authority for identity boundaries, exact approved login copy, local verification, profile UX, and migration compatibility. CILogon issuer/subject determines its separate account regardless of email. Google/GitHub verified email may match the shared local account. Existing roles, runs, and ORCID behavior remain compatible.

## Registration decisions

Provider `cilogon`, display name `CILogon`, confidential client, `openid email profile`, and production callback `https://wepp.cloud/weppcloud/oauth/cilogon/callback`. No extra institutional scope or refresh tokens are required for independent identities. The operator confirmed on 2026-11-17 that CILogon registration has not yet been approved. Provider approval is an explicit activation gate; scopes/callback and a permitted nonproduction callback still need verification. Production credentials are staged, inactive, on wepp1; see [receipt](artifacts/20261117_secret_staging.md).

## Complexity budget

Reuse Authlib, Flask-Security signing/mail/recovery primitives, SQLAlchemy/Alembic, existing session/security machinery, Pure responsive layout, and Compose secrets. Permit one provider, additive identity/contact/verification fields, bounded credential lifecycle changes, UI, tests, and documentation. No new service, datastore, dependency, privilege, or deployment topology. Preserve the existing unique shared-login email by storing separate nonunique contact email for CILogon accounts; validate all consumers before implementing that representation. No CILogon/shared account merging or project transfer.

## Security and review

Security impact: **high**. Independent security and correctness review are mandatory. Review durable identity separation, shared verified-email matching, new-local pre-registration attacks, verification provenance, framework HTML/JSON paths, last-sign-in protection, migration compatibility, and session/token noninterference. Historical research and rejected trust policies remain evidence only.

Email-first signup with password selection after mailbox proof is approved and implemented. Existing local users must not be silently reset or revoked. No product decision remains open; provider registration approval and deployment remain on hold.

## Acceptance and evidence

Prove same-email CILogon/shared accounts are distinct through real persistence, login, password recovery, and project access. Prove local/Google/GitHub reach the same shared account and preserve roles/runs. New local pending users cannot obtain sessions/tokens via any framework entry point. Contact verification cannot create a CILogon local password or merge identities. Preserve existing local access and truthful verification status. Browser evidence covers approved copy and profile at mobile and desktop widths. Inspect actual generated mail links, token completion, secret mounts under the web identity, and redacted effective configuration; file existence or job success alone is insufficient.

Implementation, local validation, environment validation, and deployment are separate claims. No run-model artifacts are produced; credentials and tokens remain outside browsable project storage. Provider interaction and real mail delivery remain explicit environment gates if unavailable.

## Work

[ExecPlan](prompts/active/implementation_execplan.md) defines milestones; [tracker](tracker.md) records status. The preimplementation checkpoint must include canonical amendments, operator decisions, independent review disposition, and a standalone ancestor commit before code changes. Email-first password setup is approved; standalone accepted checkpoints precede implementation.


Approval update: operator explicitly approved email-first signup with password selection after the verification link and requested proceeding. OPEN-P1 is resolved. Implementation and its required standalone checkpoint commit are authorized; production deployment/migration remain deferred. Historical pending-choice statements above describe the preceding review state.

## Implementation checkpoint (2026-11-17)

Email-first signup is approved and implemented after checkpoint `9eb2dfcf0`; nullable identity consumers are governed by reviewed checkpoint `874de621c`. See the current [tracker](tracker.md), [implementation guide](../../oauth_spec.md), and [user help](../../user-guide/sign-in.md). Earlier pending-choice statements describe the superseded review phase. Independent implementation reviews and browser evidence are in artifacts. Production activation, migration, and deployment remain deferred; local review is not rollout clearance.
