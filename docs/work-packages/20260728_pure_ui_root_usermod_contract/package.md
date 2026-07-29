# SURF-15 Pure UI Root User Modification Contract

**Status**: Verified
**Package ID**: SURF-15
**Security impact**: `high`
**Dedicated security review**: required

## Purpose

Verify the privileged user-management surface from actual rendering through
same-origin role mutation and persisted reload. A Root operator can inspect
escaped account metadata and explicitly grant or revoke only the registered
operational roles without allowing an Admin, malformed request, or client-side
control bypass to widen authority.

## Concise Intent Contract

The user-management page and mutation endpoint are Root-only. The page renders
all users as escaped read-only identity and login metadata, with checked state
for the existing PowerUser, Admin, Dev, and Root roles. An empty user set has a
clear table state.

Each role checkbox submits the target user ID, one allowlisted role, and a
literal boolean state by same-origin JSON POST with CSRF. A successful
mutation persists through the existing Flask-Security datastore and is visible
on reload. A failed request restores the checkbox and presents a visible,
escaped status without logging user data or treating a transport failure as
success.

The server validates the JSON object, target identity, allowlisted role, and
boolean state. It rejects redundant changes and must not permit the acting Root
to remove their own Root role; the disabled self-Root checkbox is presentation
of that server-enforced invariant, not its enforcement.

## Scope

- `wepppy/weppcloud/templates/user/usermod.html`;
- `wepppy/weppcloud/routes/admin.py::{usermod,task_usermod}`;
- `wepppy/weppcloud/_context_processors.py::_get_all_users`;
- Flask-Security role persistence and reload behavior;
- Root navigation links as consumers; and
- direct render, actual-inline-client, route, CSRF, persistence, hostile-value,
  and security evidence.

## Exclusions

This package adds no role, account activation/deactivation, account deletion,
password reset, provider mutation, session revocation, bulk mutation, search,
pagination, or audit-log system. SURF-14 remains the read-only profile owner.

## Acceptance

Actual rendering proves Root, empty, hostile, selected, and self-Root-disabled
states. The real inline client proves exact endpoint/payload/CSRF behavior and
failure rollback with visible status. Real route tests prove Root-only GET and
POST, CSRF-before-role enforcement, strict request validation, self-Root
protection, persistence, and reload. Any mismatch receives a failing
regression before the smallest contract-compatible repair. Focused and broad
validation, dedicated security review, documentation lint, a separate commit,
and a clean worktree are required.

## Outcome

SURF-15 verified the Root user-management contract and required four related
production repairs: the GET now requires Root rather than both Admin and Root;
the POST strictly validates JSON and boolean state; the acting Root cannot
remove their own Root role; and the inline client provides text-only visible
success/error feedback without logging user data.

Direct render/route tests cover Root/Admin authority, all users, empty and
hostile metadata, checked/disabled role states, CSRF ordering, validation,
grant/revoke persistence, redundant changes, and reload. Four actual-inline
Jest cases cover exact same-origin CSRF JSON, success, response failures,
invalid JSON, transport failure, rollback, and disabled-state preservation.
Focused Python passed 28 tests, full frontend passed 97 suites/699 tests, and
broad Python passed 5,534 tests with 58 skips. Security review passed with no
unresolved findings.
