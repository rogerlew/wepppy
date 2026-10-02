# Feature access account records

Milestones one and two implement the FA-01 account substrate, shared evaluator,
Root group administration and Profile acknowledgment. Protected feature endpoint
wiring remains milestone three; PowerUser self-service remains milestone four.
The normative owner is [FA-01](../schemas/feature-access-governance-contract.md).
Production rollout and service-token compatibility still need their later gates.

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
verified current-user ID; the web adapter validates the affirmative answer and binds
the authenticated browser-session user before calling it. PowerUser role assignment and automatic
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

FA-02 target: retained-result inspection returns the existing resource read
decision without a feature-action membership lookup, including contrast/PATH-CE
outputs. Private workflow roots retain their separately specified read scope.
The current `consumes_contrasts` read dependency is superseded: require contrast
action entitlement only when the composed operation actually activates or
executes contrasts, not merely when it reads existing contrast inputs.
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

## Milestone-three integration in progress

The M3 checkpoint adapters resolve active human accounts and current operational
roles from the shared account database. Protected human admissions then read
current group membership and acknowledgment. Signed origin metadata on issued
session, admin delegation and MCP credentials records identity, not entitlement.
Account/configuration failures produce explicit unavailable responses; ordinary
public retained-result inspection must not need a feature-account lookup.

`wepppy/weppcloud/utils/feature_access_integrations.json` is the operator-owned
Culvert registration: exact service subject, audience, token class and service
group. Its returned browse credential carries the signed integration origin.
These checks supplement normal signature, expiry, revocation, scopes and resource
claims. Editing this registration does not renew the expired deployment token.

Restricted controls use the shared decisions, with disabled action fieldsets and
retained views. FA-02 requires removing the checkpoint's feature-derived read filters while retaining action gates. Disabling a restricted mod still requires entitlement
and honors readonly state, but does not require the backend/prerequisites needed
to enable or execute that feature. Newly exposed optional-state GETs are
observational. Existing anonymous ordinary workflows remain in scope for regression.

M3 is not ready for rollout. FA-02 removes the need for a contrast-child lineage
marker and contrast-only SQL/D-Tale read enforcement. Reassess SQL expressions
and cached D-Tale delivery for actual private-resource/containment violations;
public result sharing is intended. No DuckDB upgrade is authorized by FA-02. See the active
[ExecPlan](../work-packages/20261001_feature_access_governance/prompts/active/feature_access_governance_execplan.md)
for decisions, review disposition and remaining acceptance. Do not enable
PowerUser self-service based on the initial route wiring alone.

## Group administration and Profile

Root users reach **Feature groups and decision history** from User Management
or **Manage feature groups and decision history** from Profile. Select a person,
feature group and add/remove decision; supply the purpose and reason. For adds,
review and expiration accept UTC ISO timestamps (for example
`2027-01-01T00:00:00Z`) or blank for no date. Document continuing access in the
reason if both dates are blank. Removal records a new event and retains history;
it does not edit roles, cancel jobs or remove the acknowledgment.

The inventory identifies inactive accounts, expired records and inactive groups.
An inactive account can have a recorded pre-grant, but its effective `member`
response is false. Current membership is not a promise of action admission:
acknowledgment, existing resource permissions and feature requirements still
apply. The current UI describes a separate Omni Contrasts entitlement for PATH-CE
inputs. FA-02 reconciliation must narrow that guidance to operations that actually
activate or execute contrasts; merely reading retained inputs needs no such grant. The page explains this; it never creates a dependency grant.
History is paged in descending event order with **Older decisions** and includes
historical actor/subject IDs, scope, reason and UTC dates.

Profile shows only the current person's memberships and current acknowledgment.
It presents the policy's Internal Collaborator Onboarding text as version
`internal-2026-10-01`. Change the version when the statement changes and retain
historical acceptance rows. Checking the statement and submitting records acceptance
for the current account only. No other person's audit reasons are exposed.
A persistence failure displays a reference ID and explicit unavailable status
without disabling ordinary Profile functions. Existing Dev/Root operational
paths do not acquire an acknowledgment requirement; group-only features do.

The two mutation endpoints accept strict JSON under normal CSRF protection.
`feature_access_web.py` verifies Flask-Security's resolved `session` provenance
and its binding to the cookie's user ID. A stale session plus a valid token is
not sufficient. Errors sanitize persistence details and log an `error_id`.
Mutation responses compute effective membership before transaction commit, so a
failed read rolls back and cannot report an error after saving the decision.

## Explicit maintainer initialization

After an authorized deployment's verified backup and additive migration, run:

```bash
wctl exec -T weppcloud flask --app wepppy.weppcloud.app admin initialize-feature-access \
  --email rogerlew@gmail.com \
  --reason "Initial sole-maintainer access: OpenET API limits and Batch computational limits; continuing access pending an explicit maintainer decision."
```

The command resolves the exact email in the current database and requires an
active Root account. Both OpenET and Batch memberships and their scope/reason
snapshots commit in one transaction. Repeating the same initialization is a
no-op. Existing other members or dated grants cause an explicit conflict rather
than pruning someone or silently renewing a grant. This command never changes
roles, fabricates acknowledgment, or initializes other feature memberships.

Backup validation must include a restore, not just a dump header. A dump scoped
to the `public` schema also needs the installed `pg_trgm` extension to restore
Usersum search indexes; include it explicitly or use the normal full-database
backup. Restore into a disposable database, read back the Alembic revision and
account/role/run counts, then remove only that disposable database. Keep dumps
outside git with restrictive permissions.

## Browser acceptance harness

`tests/weppcloud/feature_access_browser_server.py` runs the complete app on HTTPS
port 8902 in a fresh PostgreSQL schema, with real models, Redis sessions and CSRF.
It initializes fixture maintainer memberships and writes disposable browser
cookies to ignored `docker/secrets/m2-browser.json` (0600). It adds only a
read-only, current-user evaluator probe for the test. It does not exercise model
execution or substitute for milestone-three feature endpoint wiring. Sessions
are provisioned using the documented local test-cookie path; password/CAP login
is outside this acceptance test.

Start the helper:

```bash
wctl exec -T weppcloud python tests/weppcloud/feature_access_browser_server.py
```

Then run the
opt-in `tests/smoke/feature-access.spec.js` via `wctl run-npm test:playwright`, with
`FEATURE_ACCESS_BROWSER=1`, `SMOKE_BASE_URL` pointing to that container's HTTPS
port, the existing `PLAYWRIGHT_BROWSERS_PATH`, and optionally
`FEATURE_ACCESS_EVIDENCE_DIR`. The test covers keyboard submission/error focus,
real grant/acknowledgment/removal, shared-evaluator transitions, retained history
and axe scans. Send SIGTERM to this specific helper process afterward; it removes
its cookies, known Redis sessions and test schema. It never migrates the shared
account schema.

`wctl run-pytest tests/weppcloud/routes/test_feature_access_routes.py` covers
real PostgreSQL and Flask-Security/CSRF route behavior, strict payloads, token
fallback rejection, privacy, effective inactive status and atomic initialization.
