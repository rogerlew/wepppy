# Milestone-two acceptance and local initialization

Recorded during October 1 (Pacific) / October 2, 2026 (UTC), against milestone-one
ancestor `62ce1af3f` plus the M2 working changes. Production was not modified.

## Implemented boundary

Root can inspect registered groups, current membership records and paged retained
history, and record a reasoned add/remove with optional UTC review/expiration.
Profile shows only the signed-in person's memberships and the policy's internal
statement (`internal-2026-10-01`), with idempotent acknowledgment. Unknown fields,
invalid types/dates, cross-account acknowledgment, non-Root writes, missing or
forged CSRF, and token substitution for browser sessions are rejected. Inactive
accounts may receive recorded pre-grants but remain ineffective.

Group administration reuses User Management's Pure panels/tables and Preferences'
form macros/status patterns. It explains PATH-CE's separate contrast dependency.
No role assignment, model execution, queue wiring or protected artifact/action
endpoint was changed. Those consumers remain M3; PowerUser self-service is M4.

## Database and transport evidence

- Focused PostgreSQL store/evaluator + route suite: **75 passed**, including
  transaction rollback, concurrency, effective inactive status, six token-fallback
  rejections and failure of the second initializer event rolling back both groups.
- Final route/usermod/Profile regression after transport import cleanup:
  **73 passed**, 10 warnings in 67.56 seconds.
- Existing focused store/usermod/Profile regression: **76 passed** before the
  final review fixes; the later focused results above establish their coverage.
- Store and web modules pass stubtest; test-stub guard passes. Standard frontend
  lint plus explicit standalone `feature_access.js` lint pass; Jest passes
  **112 suites / 919 tests**.
- Broad Python suite: **10,198 passed, 126 skipped, 4,010 warnings in 2,535.69
  seconds (42:15)**. No failures.

Full-suite timing note: the broad run began before the final qualified Flask
imports/export list cleanup. The final transport is independently covered by
73 route tests and web stubtest; this cleanup does not change behavior.

## Real browser/database round trip

The complete Flask app ran in the existing development container under its normal
UID/dependencies, with actual account models in an isolated PostgreSQL schema,
HTTPS, Flask-Security/Redis sessions, CSRF middleware, real templates and scripts.
The existing documented test-cookie provisioning path established the two
synthetic users' sessions; this is post-login acceptance, not a password/CAP test.
No auth, database or response mock was used for the workflow. The test-only
current-user probe calls the shared evaluator; it does not claim M3 action wiring.

Playwright: **1 passed in 8.8 seconds**. Root grants AgFields to the ordinary
collaborator; the collaborator acknowledges on Profile; Root removes membership.
Evaluator transitions are denied (no group), denied (acknowledgment missing),
allowed, denied (removed). Both reasoned events remain visible after removal.
The sole OpenET/Batch fixture memberships are initialized separately by the real
CLI. No WEPP job or paid API call is part of M2 acceptance.

Keyboard navigation/submission and focus on a labeled error were exercised.
An initial axe pass found two navigation links below 4.5:1 contrast on the page
background; replacing them with standard secondary buttons fixed the issue.
Final WCAG 2 A/AA and 2.1 AA scans report zero violations on both pages. This is
bounded automated/manual keyboard evidence, not a product-wide conformance claim.

Retained evidence:

- [Round-trip observations](m2-browser/roundtrip.json)
- [Admin screenshot](m2-browser/admin-granted.png) and [axe result](m2-browser/admin-granted-axe.json)
- [Profile screenshot](m2-browser/profile-pending.png) and [axe result](m2-browser/profile-pending-axe.json)

The helper was stopped after acceptance; its test schema, known Redis sessions
and ignored mode-0600 cookie file were removed. No credential appears in retained
evidence. The opt-in test is skipped unless its isolated server is requested.

## Local shared database initialization

This was the authorized M2 initialization in local development only, not a
production deployment. Read-only preflight found `public` at Alembic
`d30c91a7b802`, no feature-access tables, and one exact designated active Root
account, `rogerlew@gmail.com` (local ID 1). Baseline counts: 10 users, 5 roles,
11 role associations and 466 runs.

Before migration, a custom-format backup of `public` plus `pg_trgm` was written
with restrictive permissions through the existing postgres-backup service:

- Host path: `.docker-data/postgres-backups/feature-access-m2-20261001-with-extension.dump`
- SHA-256: `4eebc2fcc7bd786c6757c74755917f5dddd1737d9e4e9d4c7e8c5e766504df83`

An actual restore into disposable database `feature_access_m2_restore_20261001`
succeeded with `--exit-on-error`; the restored Alembic revision and all four
counts matched the baseline. The disposable database was removed afterward.
An initial schema-only restore correctly exposed missing `pg_trgm` operator
classes, so the validated archive explicitly includes that extension. The
existing backup credential file was database-scoped; a restricted temporary file
supported the disposable restore and was removed. No credential was printed.

The canonical Flask migration command upgraded only to `e7a1c9d204bf`. Readback
confirmed six empty definitions, then the explicit initializer resolved the
local email and atomically created the sole OpenET and Batch memberships. Reason:
“Initial sole-maintainer access: OpenET API limits and Batch computational limits;
continuing access pending an explicit maintainer decision.”

[Post-initialization readback](2026-10-01_m2_local_readback.json) proves exactly
two memberships and two add events, both with actor/subject ID 1 and their scope
snapshots, no acceptance rows, and unchanged account/role/run counts. The other
four groups remain empty. No service was restarted and no user's statement was
accepted on their behalf. Normal application activation and production migration
remain separate rollout work; initialized records alone do not enforce M3 gates.

## Independent findings disposition

[Correctness review](2026-10-01_m2_correctness_review.md) closed three Medium
findings: the initial unacknowledged Profile render, PATH-CE dependency guidance,
and inactive-account effective status. [Security review](2026-10-01_m2_security_review.md)
closed one Medium token-fallback finding and one Low authentication-error
correlation finding. Both reviewers confirmed zero unresolved High/Medium/Low
findings against the final bounded implementation and browser evidence.

Broad-exception enforcement passed with no added broad catches. New untracked
modules received direct AST inspection because the inventory uses git-tracked
files; no bare or broad handlers were found. Observe-only quality
telemetry ran with explicit `/tmp` output paths (radon unavailable); it does not
gate acceptance. Documentation lint passed for the 16-file package and all four
other changed documentation targets; relative links, exact statement/policy text
and whitespace checks passed. Spelling previews retained the axe product name
and unrelated existing tracker prose.

## Remaining scope

M3 wires restricted feature actions/data and public read-only views across the
frozen surface inventory. M4 adds conservative maturity and PowerUser onboarding.
Production initialization must repeat identity verification, backup/restore and
readback per deployment. Culvert's expired configured credential remains a later
operator-renewal/live-acceptance dependency; it was not changed here.
