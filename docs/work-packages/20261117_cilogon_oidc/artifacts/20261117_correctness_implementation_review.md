# Independent correctness and compatibility review

Reviewed: 2026-11-17 20:27 UTC. Reviewer: `account_contract_correctness`.

Candidate: uncommitted implementation on contract checkpoint
`874de621ce1aa4237b975ca2095dd4e259f58263`. This review covers source and test
readback; it does not authorize production migration, deployment, or credential
activation. No production files were edited by this reviewer.

## Disposition

No remaining source findings in the reviewed account, OIDC, migration, profile,
token, Bootstrap, and run-owner display changes. Previously reported source
findings are closed by the repairs below. Source acceptance is distinct from
the outstanding production-equivalent validation gates.

The implementation follows the accepted email-first signup contract, keeps
CILogon accounts independent of shared login email, preserves existing local
credentials, and uses provider-established email ownership only for first-time
Google/GitHub shared-account matching. No product decision remains pending in
this review.

## Findings closed by source readback

| ID | Prior concern | Repair and regression evidence inspected |
| --- | --- | --- |
| COR-01 | New shared users could receive unusable framework recovery links instead of first-password setup. | `account_security.forgot_password` dispatches `none`/`pending` records to mailbox-bound setup and established local credentials to framework reset. Lifecycle tests cover the new recovery path and blocked framework bypasses. |
| COR-02 | Personal/run token issuance rejected users without login email. | `routes/user.py` retains ID and role authorization and omits the optional email claim. NULL-email token tests cover this behavior. |
| COR-03 | Bootstrap resolved identity through email, breaking independent CILogon accounts. | New signed tokens carry validated positive `user_id`; ID resolution is authoritative and legacy email-only tokens remain supported. Tests cover missing email, invalid present IDs, inactive users, and current run access. |
| COR-04 | The RQ mint adapter supplied session-token `sub` as the user ID and could leak a raw validation exception as HTTP 500. | `rq_engine/bootstrap_routes.py` prefers present `user_id`; `mint_bootstrap_token_operation` validates it before minting and raises `BootstrapOperationError`. Actual FastAPI route tests cover session subject plus ID, numeric legacy subject, invalid present ID, and service subject. |
| COR-05 | Detached ORM results could lose roles or deny run collaborators by comparing Python object identity. | Bootstrap resolvers eagerly load roles/run users and compare membership by database user ID. The real-ORM lifecycle test covers owner, CILogon collaborator, Admin, and removed membership. The integrator reports it passed in the final focused batch below. |
| COR-06 | NULL owner email could raise during RQ authorization, and an email-based role mutation could target no user. | RQ owner checks tolerate NULL email; the WEPPcloudR role assignment passes the current User object. Stable ID checks remain in place. |
| COR-07 | Model-created databases lacked the normalized-email uniqueness protection added by migration. | `User.__table_args__` and Alembic both declare the normalized unique index. Tests cover duplicate rejection and preservation of IDs, hashes, roles, and run membership. |
| COR-08 | The token controls could overflow the mobile profile. | `static/css/account.css` wraps the token row and removes its restrictive minimum width. Retained layout results show document width equals viewport at 320, 375, and 1280 pixels. The reviewer inspected `profile-shared-375.png`. |
| COR-09 | CILogon-owned runs appeared anonymous because their login email is NULL. | `app.Run.owner`, `routes/user._owner_email_map`, and `run_catalog/reader.collect` now use `User <id>` for an existing owner without a login email. Existing ownerless fallbacks remain unchanged; contact email is never an identity substitute. The real account/run model and route-mapping regression test passed in the integrator's final focused batch. PostgreSQL catalog execution remains a separate gate below. |

Also inspected the final Google/CILogon signed-claims validation and UserInfo
subject binding, strict GitHub verified-email selection, provider-error log
sanitation, last-provider password proof, and the no-local-password constraint
on CILogon accounts. Signed-token tests use actual Authlib signature validation
with mocked provider transport; they are not live-provider acceptance evidence.

## Evidence limits and release gates

- The integrator reports the final isolated focused batch completed with
  **429 passed, 30 warnings in 32.47 seconds**, including the real owner-display
  test, Bootstrap adapter and detached-ORM tests, account lifecycle, signed
  OIDC, and remember/session regression checks. This supersedes the earlier
  partial counts. This reviewer inspected source and tests but did not
  independently execute the batch. PostgreSQL catalog and Redis-dependent
  broad suites remained unavailable; no full-suite pass is claimed.
- `ui-layout-results.json` and screenshots establish responsive rendering of
  retained fixture pages. They do not establish authenticated browser action,
  CAPTCHA, real mail delivery, or live OIDC redirect/cookie behavior.
- Migration tests exercise disposable SQLite data. PostgreSQL normalized-index
  behavior, concurrent registration/link uniqueness, send reservation locking,
  simultaneous token redemption, and populated-database compatibility require
  production-equivalent evidence before rollout.
- The integrator attempted the PostgreSQL catalog tests, but the isolated
  container had no PostgreSQL service. The catalog owner-label repair is closed
  by source readback only; real catalog query/readback remains an explicit
  environment gate and must not be reported as passed.
- Real CILogon callback/issuer/claims, Google/GitHub provider behavior, external
  prefix and cookie handling, SMTP delivery, and protected-project access across
  the deployed process boundaries remain live integration gates. Do not infer
  them from mocked transport or SQLite success.
- Preserve the coordinated migration/compatible-code rollback gate. Old code
  must not run over new CILogon or pending-credential records. The additive
  migration downgrade guard is useful protection, not proof of rollout parity.
- Grandfathered unverified local passwords remain usable by explicit operator
  choice. Ordinary mailbox verification does not replace those passwords or
  revoke their sessions; the profile accurately directs deliberate recovery
  when the owner needs to secure that credential.

Canonical authority: `docs/schemas/weppcloud-account-email-verification-contract.md`,
especially Account lifecycle, Mailbox proof, Migration and compatibility, and
Nullable identity consumer compatibility; plus the amended auth-token,
Bootstrap, session, CSRF, and safe-traceback contracts.
