# Feature access account records

Milestone one implements the FA-01 account substrate and shared evaluator.
It does not wire routes, change current authorization, expose self-service,
initialize maintainer memberships, or deploy a migration. The normative owner is
[FA-01](../schemas/feature-access-governance-contract.md); later milestones wire
its restricted actions, protected data and user interfaces.

## Records and transaction ownership

`utils/feature_access_schema.py` defines four account tables, registered as
`FeatureAccessGroup`, `FeatureAccessMembership`, `FeatureAccessEvent` and
`OnboardingAcceptance` in `wepppy/weppcloud/app.py`. This follows the existing
framework-independent SQL metadata pattern used by the run catalog. Importing
the shared evaluator/store does not import Flask or construct an application.

`FeatureAccessStore` receives the existing account SQLAlchemy engine. Flask
consumers pass `db.engine`; non-Flask consumers use their existing configured
account engine. Do not create a second database or an authorization service.
Each write owns one transaction. A current-user row lock serializes duplicate
membership/acknowledgment writes, including when no membership row exists.
Membership and event insertion commit or roll back together. Reads query current
membership every time; no token group claims or process cache confer membership.

Group administration checks a current active Root account. Membership changes
require a registered group, real user, nonblank reason, and aware timestamps.
A review date alone does not expire access. Identical grants/removals are no-ops;
conflicting active grant metadata requires an explicit remove/add. Expired grants
can be re-granted. Events snapshot actor, subject, group key and ID, feature IDs
and access modes, reason, action, dates and server time. Event and acceptance IDs
are historical snapshots without cascading account/group foreign keys. The
store exposes no event update/delete operation.

The internal-acceptance primitive takes the server-owned statement version and
verified current-user ID; routes must validate the affirmative answer and bind
the current user before calling it. PowerUser role assignment and automatic
approval are still milestone four; no PowerUser acceptance/grant API is exposed
by this stage.

## Decision inputs and limits

`utils/feature_access.py` receives a `VerifiedPrincipal`, `FeatureSpec`, operation
(`inspect` or `act`), `FeatureResourceContext` and store. These are trusted adapter
inputs, never deserialized request/JWT objects. The caller first verifies identity,
expiry/revocation, supported token class, scope and resource binding, then supplies
`existing_access_allowed`. It defaults to false. Human roles must be resolved
through the endpoint's authoritative identity path; integration feature authority
must come from operator registration. A service token class alone confers none.

Non-embargoed inspection returns the existing read decision without a membership
lookup. Private workflow roots require their own read entitlement; contrast-derived
PATH-CE reads set `consumes_contrasts` and require contrast read entitlement.
Actions also enforce readonly/backend/prerequisites. Group-based actions require
the current server-owned internal statement version; legacy Dev/Root paths do
not acquire that requirement. No account is auto-enrolled in a dependency group.

The six governed features require explicit access metadata; omitting both fields
is a configuration error in both the registry loader and direct evaluator inputs,
including contrast dependency specs. Unrelated features retain legacy omission
behavior.

Decisions expose `allowed`, a stable `reason`, and an entitlement `basis`.
Database failures log operator context and return `feature_access_unavailable`;
missing/inactive groups return `feature_access_configuration_error`. Framework
adapters must translate those to explicit errors, never broad-role fallbacks.
Unknown token origins must not be constructed as verified human principals.
Token adapters and endpoint response conversion are later milestone work.

## Migration and operational rollback

Migration `e7a1c9d204bf` follows `d30c91a7b802`. It creates only the four new tables
and six registered group definitions, with no user membership, fabricated legacy
acceptance, role modification or credential creation. `seed_groups` is an
idempotent definition-only operation and does not change existing definitions.
Registry changes to group scope require a separate recorded maintainer decision.

Before applying outside isolated tests, use the canonical deployment workflow,
take and verify a restorable account database backup, confirm the current Alembic
head, retain account/role/run counts, and plan post-upgrade readback of all four
tables, unique constraints and the six empty groups. Then initialize memberships
only through an explicitly authorized, audited operation after resolving the
maintainer's email separately in that deployment. Do not copy numeric user IDs.

Operational rollback disables consumers and retains the additive schema/history.
The migration refuses downgrade because dropping access history would violate
FA-01. Do not use a schema downgrade as an application rollback shortcut.

## Validation

`wctl run-pytest tests/weppcloud/test_feature_access.py` runs real PostgreSQL
transactions inside fresh, randomly named test schemas and cleans them up when each test finishes.
It covers empty/legacy account upgrades, model/migration metadata parity,
constraints, concurrent duplicates, injected audit failure rollback, retention,
expiry, current membership, acknowledgment and evaluator allow/deny boundaries.
No production or shared account schema is migrated by this suite.
