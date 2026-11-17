# CILogon and account verification tracker

**Updated**: 2026-11-17 (UTC).
**Phase**: implementation and local review; environment acceptance pending.
**Security impact**: high.
**Production**: deployment/migration/credential activation deferred.

## Task board

- [x] Stage inactive wepp1 credentials and retain [receipt](artifacts/20261117_secret_staging.md).
- [x] Approve independent CILogon identity, shared verified Google/GitHub matching, and exact login wording.
- [x] Approve email-first password setup; complete independent contract reviews and checkpoint `9eb2dfcf0`.
- [x] Review nullable-identity consumer compatibility and checkpoint `874de621c`.
- [x] Implement additive migration, provider flow, mailbox lifecycle, responsive account pages, and consumer repairs.
- [x] Dispatch independent implementation reviews and disposition source findings.
- [x] Retain local signed-token/ORM/mail-sink/browser/frontend evidence and user/operator documentation.
- [ ] Complete PostgreSQL/live-provider/SMTP/production-mount acceptance and broader environment-dependent tests before release.

## Current authority and decisions

The [account contract](../../schemas/weppcloud-account-email-verification-contract.md) governs separate CILogon accounts and shared local/Google/GitHub accounts. Email-first signup and password selection after opening the mailbox link are approved; no product decision remains open. Existing local credentials remain usable. No forced legacy reset, account merge, contact-edit workflow, or production activation is authorized.

Consumer findings were resolved using stable IDs: token issuance, Bootstrap authorization, detached role/member access, and owner display now tolerate missing shared login email. CILogon contact email remains informational. See [decision record](artifacts/20261117_contract_decision.md), [migration plan](artifacts/account_migration_plan.md), [implementation guide](../../oauth_spec.md), and [user help](../../user-guide/sign-in.md).

## Reviews and validation

Final focused Python batch: **429 passed**; diagnostic/asset checks: **36 passed**. Frontend: **1,091 Jest tests plus nine Node tests passed**, lint passed. Nine mobile/desktop browser combinations passed. Broader Redis/PostgreSQL suites remain environment-blocked.

[Security review](artifacts/20261117_security_implementation_review.md) and [correctness review](artifacts/20261117_correctness_implementation_review.md) close local source findings. [Validation receipt](artifacts/validation.md) records overlapping test batches, browser evidence, the unavailable Redis/PostgreSQL gates, and production acceptance limits. No deployment readiness is inferred from synthetic tests.

## Handoff boundary

Work remains on `work/cilogon-oidc-scaffold` in `/home/workdir/wepppy-cilogon-oidc`; original checkout WIP is preserved. The operator-approved isolated test container has no published ports or production credentials. Staged wepp1 secrets have not been activated. Future rollout must use the canonical deployment entry point with a coordinated schema/code plan and compatible rollback. No user decision is needed for the dispositioned findings; remaining gates require the appropriate nonproduction environment.
