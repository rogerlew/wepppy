# PowerUser discovery and onboarding (PUUX-01)

Status: operator authorized execution 2026-10-13; independent contract reviews passed; implementation pending.

## Discovery and audience

The authenticated Runs page presents a compact Advanced features section after
the header and before the table/map panel when the viewer lacks PowerUser, Admin
and Root. Dev alone does not grant panel access. Test viewer identity, not the
selected catalog owner. The notice survives empty accounts, search and view
changes; it has no alert behavior, modal, dismissal persistence or automatic
grant. Explore PowerUser access links to Profile#poweruser-access-heading.

Describe custom configurations, project troubleshooting and API access without
claiming every viewer lacks them or promising compute allocations. GL Dashboard
remains ordinary project navigation under gl-dashboard-navigation-contract.md;
it is not a PowerUser acquisition benefit.

## Profile and completion

Explain capability examples, compatible-project requirements and separate
internal approval before the unchanged poweruser-2026-10-01 statement and two
required affirmative answers. Enable PowerUser access replaces Request wording;
explain that approval is immediate. POST fields, server-owned account/role,
CSRF, statement version, transaction, idempotence and legacy access follow
feature-access-governance-contract.md and remain unchanged.

Accept client success only for a nonempty message, result.status=granted,
boolean role_changed and matching statement_version. On success remove the
submission controls, present active status and a fixed Profile refresh link,
then reload the server-generated same-origin Profile URL at the PowerUser
heading. Refresh must occur even when the browser already has that fragment.
Do not accept arbitrary return URLs or navigation destinations from the response.
The fresh heading is programmatically focusable and receives focus when its
fragment is targeted. Active Profile provides fixed links to Config Builder,
Runs and a getting-started guide. Existing role holders without a current
acceptance see active access and no action required; no acceptance is invented.
Admin/Root without the literal PowerUser role see that their existing role
already provides these tools, destinations and no acquisition prompt; do not
falsely claim a PowerUser role or recorded acceptance. Dev-only keeps onboarding.

Before refresh, provide a keyboard-usable refresh link as recovery. Invalid or
missing success fields, network errors, invalid CSRF, stale statement or expired
session never present active state; preserve existing server messages where
available and provide a retry/refresh instruction. Re-enable submission on
failure, not after successful grant. Do not alter internal-acknowledgment or
membership-administration completion behavior.

## Internal access

No memberships (including an empty list) shows a concise explanation that
PowerUser does not grant internal permissions. Keep the existing internal
statement and voluntary acknowledgment reachable through a closed Details
section. With memberships present, show the same details open, including
expired/inactive status and the existing acknowledgment action when needed.
PowerUser activation does not satisfy internal acknowledgment or add membership.
Store failure remains an explicit unavailable state, not an empty membership
interpretation. Preserve operational-role exceptions.

## Panel orientation and consistency

Use PowerUser Panel consistently for its trigger, title and help. Both run and
shared report headers apply the existing PowerUser/Admin/Root guard to the
trigger; the modal keeps that guard. Leading panel sections describe inspecting
inputs/outputs and troubleshooting/analysis; place raw NoDb state and logs in
expandable Technical details. Preserve every existing resource condition,
handler, action identifier, project boundary and read-only rule. Clear Locks has
concise caution and existing recovery-help linkage. Getting-started guidance
precedes developer documentation. No new privileged actions or recovery policy.

## Validation and rationale

This reduces hidden discovery, ambiguous approval and dead-end completion while
preserving access boundaries. Verify ordinary zero/populated accounts, legacy
PowerUser, PowerUser/Admin/Root, Dev-only, absent/empty/pending/expired membership,
unavailable store and hostile request states. Verify current-view identity,
keyboard focus after completion, narrow/desktop layouts, unchanged Runs
controls, denied internal actions without membership and real durable grant
readback. Static screenshots and role mocks alone cannot prove the grant path.

Shared presentation authority: docs/ui-docs/controller-contract.md. Permission
and transport authority: docs/schemas/feature-access-governance-contract.md.
Feature registry role/maturity/prerequisite rules are unchanged.
