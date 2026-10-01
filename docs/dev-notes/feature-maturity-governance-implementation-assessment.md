# Feature maturity governance implementation assessment

Date: 2026-10-01

Assessed revision: `45a39a8337d37c7f7d30087ff4d23c03610072b3`

Status: Assessment complete; implementation recommendations updated for operator direction on 2026-10-01.

The [feature access governance amendment](../schemas/feature-access-governance-contract.md) records the subsequent operator decisions and rationale. The inventory below describes the assessed implementation and ratified policy; the delivery recommendations now target public read-only feature views, single-maintainer group administration, conservative maturity, internal Batch/Culvert workflows and maintainer-only OpenET/Batch actions. Cross-contract reconciliation is prepared in FA-01; the reviewed technical checkpoint and implementation remain pending. See the [implementation work package](../work-packages/20261001_feature_access_governance/package.md) and its active plan.

## Conclusion

WEPPcloud implements a useful maturity registry and coarse role gates, but not the access-governance lifecycle in the [ratified policy][policy]. PowerUser self-service and scoped collaborator groups are missing. Closing those two UI gaps alone would leave inconsistent execution permissions, absent membership audit records, and undefined group-removal behavior.

Before enabling self-service, resolve the existing PowerUser user-token access to grouped batch/culvert data. The current helper and fixture tests allow that access without per-group membership or an identifier claim. This is a concrete dependency of the self-service change, not merely a future group-management enhancement.

The implementation should retain the registry as the owner of feature/config metadata, use the existing account database for reviewed access and onboarding records, and apply one feature-access decision across the UI and the corresponding execution/data boundaries. Group membership must not imply Dev/Admin/Root membership or ownership of unrelated runs.

This assessment changes no production behavior or canonical contract. It records source-confirmed gaps, local test evidence, policy conflicts, and proposed implementation sequencing. It does not establish production exploitability, deployment state, scientific validity, accessibility conformance, or award/legal compliance. No production accounts, grants, jobs, or run artifacts were modified.

## Evidence and current inventory

The assessment covered the full policy, registry specification/schema/runtime/YAML, account models and migrations, profile and Root role management, feature toggling/rendering, the six internal feature entry points, project creation, token issuance and consumption, and representative data-access paths. Negative findings about missing models/workflows are based on repository searches and the inspected implementation; external manual access records were not available.

Loading the real registries in the development container produced:

| Registry | Effective inventory |
| --- | --- |
| Features | 18: 2 stable, 8 preview, 2 experimental, 6 internal |
| Configs | 16: 4 stable, 7 preview, 2 experimental, 3 deprecated |
| PowerUser-gated registry features | `debris_flow`, `roads` |
| Internal features | `openet_ts`, `omni_contrasts`, `path_ce`, `culvert_runner`, `batch_runner`, `ag_fields` |
| Internal configs | None currently; schema supports internal metadata with `min_role: dev` |

All current config entries have `min_role: user`. Effective config maturity differs from YAML for `reveg-mofe` and `reveg-10m-mofe`: the `multi-ofe-is-preview` override makes both Preview although their entries say Experimental.

The role model is not a linear hierarchy. Actual `user_meets_min_role()` results are:

| User's only role | `poweruser` gate | `dev` gate | `admin` gate | `root` gate |
| --- | --- | --- | --- | --- |
| User | Deny | Deny | Deny | Deny |
| PowerUser | Allow | Deny | Deny | Deny |
| Dev | Allow | Allow | Deny | Deny |
| Admin | Allow | Deny | Allow | Deny |
| Root | Allow | Allow | Allow | Allow |

`min_role: user` is an audience floor, not a login requirement. Authentication, project creation restrictions, and run access are separate boundaries. Multi-role users can obscure discrepancies that single-role tests expose.

## Policy coverage

Priority meanings: P0 = resolve before opening new access paths; P1 = required for the first complete governed-access release; P2 = subsequent governance/evidence improvements, unless a specific feature's acceptance depends on them.

| Policy obligation | Implementation assessment | Required work |
| --- | --- | --- |
| Registry owns maturity, visibility and release metadata | Partial. Shared schema/runtime and major menu/render/toggle consumers exist; endpoint-specific roles remain. | P0: register and reconcile execution/read surfaces for each feature. |
| Public visibility and action permissions | Existing policy/spec conflict and OpenET UI/execution mismatch. | Operator direction: public-project feature views are read-only for callers without action permission; embargoed-output exception remains unresolved. |
| Least optimistic accurate maturity | Multi-OFE override can raise Experimental to Preview. | Operator direction: preserve the least optimistic accurate label; no automatic Experimental-to-Preview promotion. |
| Stable/preview/experimental/deprecated definitions and caveats | Shared user guide, badges, feature documentation, and deprecated replacements exist. No general evidence gate for promotions. | P2: maintainer release checklist with validation, limitations, support and replacement evidence. |
| PowerUser request and concise training | Missing self-service form/route, versioned acknowledgment and decision record. | P1: two-question automatic onboarding as requested by the operator. |
| PowerUser does not grant internal access | Registry implements this separation. Direct endpoint enforcement is incomplete. | P0: preserve separation at every registered action/read boundary. |
| Scoped Internal Collaborator access | Missing. User has global roles and run associations, no collaborator groups or feature grants. | P1: groups, bounded memberships, reviewed scopes and grant evaluation. |
| Purpose-based external access | Policy exists; no scoped grant workflow found. | P1: maintainer can add a named person to a bounded group with a reason; a request form is optional. |
| Access decision authority | No structured scoped-access administration exists. | Operator direction: one authorized maintainer records group membership decisions. |
| Dual-role review by internal reason | Required by the ratified text, not implemented. | Operator rejected this requirement for staffing reasons; reconcile policy to single-maintainer auditable decisions. |
| Decision reasons, scope and onboarding version | Root mutation commits a role change without the policy's structured provenance. | P1: atomic access/decision persistence and audit records for approval, denial, deferral and narrowing. |
| Review, expiry, renewal and revocation | No feature-grant lifecycle exists. Role assignments have no expiry/review metadata. | P1: distinguish review dates from expiration, enforce grant expiry, retain renewal/revocation history. |
| Embargo date and bounded renewal | Schema validates date/reason pairing; ADR-0001 supplies dates. No date-driven review workflow found. | P1: due-review reporting and explicit renewal/reclassification; do not auto-promote scientific maturity. |
| Restriction reasons visible to users | Reasons/dates exist in YAML but are not included in general menu presentation; ordinary denial is often only `Not Authorized`. | P1: explain restrictions and the request pathway on an approved informational surface. |
| Access records retrievable and retained | Repository ADRs support release history; no first-class collaborator access ledger/export exists. | P1: retrievable decisions and a defined retention owner/process; assess external records before migration. |
| Sponsor-neutral fairness and bounded authority | Policy and ADRs supply rules; no structured conflict/escalation or comparative decision view found. | P1: decision fields and reviewer guidance; P2: periodic audit. Human accountability remains necessary. |
| Accessibility by maturity | UI accessibility work and public statement exist; registry has no linked per-feature conformance evidence. | P1: validate new onboarding/review flows; P2: map existing maturity states to retained evidence. |
| Version, maturity and limitations at time of use | Current labels and some configuration provenance exist. No general maturity-at-execution record found in inspected export/config code. | P2: define a small release/provenance record for outputs where needed; do not infer past status from today's registry. |
| Publication consultation, credit and no retroactive veto | Documented human process; no feature-specific acknowledgment record. | P1: versioned onboarding and grant expectations. Avoid inventing publication approval rights. |
| Operational restrictions distinct from scientific maturity | Internal reason enums exist; access checks and operational controls are not consistently connected. | P1: preserve backend, quota, service-scope and run checks alongside grants. |

## Confirmed implementation gaps

### PowerUser is currently a Root-managed role

[User and Role models][models] provide the existing role relationship. [Root administration][admin] exposes `/usermod` and `POST /tasks/usermod/`, both Root-only. The latter accepts `PowerUser`, `Admin`, `Dev`, or `Root`, changes the association and commits. It has no fields for training acceptance, policy version, decision reason, approval rule, or review date.

[Profile routes][user] and [the profile template][profile] display roles and provide preferences, identity-provider management and token minting. They provide no PowerUser application. The account migration inventory contains no onboarding/access-request tables.

The policy permits automatic or manual approval; the operator's request for self-promotion selects the automatic path as the proposed implementation target. The UI should use the existing profile page, display the training statement (at most 200 words), and ask exactly the two policy questions. Two affirmative answers should atomically create the versioned acceptance/automatic decision and add PowerUser to the current authenticated user. Do not add affiliation, research plans or discretionary eligibility criteria to this path.

Repeated submission should return the already-approved state without duplicate grants. Existing PowerUsers should remain usable; label their provenance as legacy rather than fabricating a training acceptance. The operator explicitly deferred PowerUser suspension, reapplication and permanent revocation on 2026-10-01. Do not add sanction states or reinstatement flows, and do not make those decisions prerequisites for this increment. Preserve existing administrative role controls; durable suspension/permanent-revocation enforcement against future self-service requests is not claimed. Scoped group membership removal and existing token revocation remain separate.

### PowerUser exposes more than two feature toggles

Self-promotion exposes the existing PowerUser surface, including:

| Capability | Source and implications |
| --- | --- |
| Roads and legacy Debris Flow controls | [Feature YAML][features]; Roads is Experimental and WBT-only, Debris Flow Stable. |
| Profile user-token minting | [user.py][user], `mint_profile_token`: 90-day tokens, rq-engine/query-engine audiences, read/query/status/enqueue/export scopes. Run/resource authorization still applies. |
| Clear NoDb locks/cache | [project_bp.py][project], `clear_locks` / `clear_nodb_cache`: accepts PowerUser, Admin or Root plus run access. |
| Command-bar operational actions | [command_bar.py][commandbar], `_PRIVILEGED_ROLES`: PowerUser, Admin or Root, with run authorization. |
| Config Builder cell-size override | [builder_routes.py][builder], `_OVERRIDE_ROLES`: PowerUser, Admin or Root. |
| Recorder draft promotion | [recorder_bp.py][recorder]: requires literal PowerUser and additional feature conditions. |
| Grouped browse user-token eligibility | [browse/auth.py][browse], `GROUP_USER_TOKEN_ALLOWED_ROLES`; this is not collaborator group membership. |

Run-token minting remains Admin/Root-only. Do not accidentally extend it when adding self-service.

**P0 before self-service: grouped data access is broader than scoped membership.** In `browse/auth.py`, `_require_identifier_claim()` returns immediately for user tokens; `authorize_group_request()` then checks the privileged role and root-only path restrictions without looking up ownership or collaborator membership. Batch/culvert browse handlers pass that authorization context through to the reader. Existing `test_group_user_token_with_privileged_role_is_allowed` and `test_culvert_download_allows_user_token_with_privileged_role` deliberately allow a PowerUser user token without a `runs` claim to read fixture data. Thus self-service PowerUser would also open this existing grouped-data audience. Actual production data exposure was not tested.

The [browse auth contract][browsecontract] says grouped routes must authorize against an identifier claim, but the user-token branch skips that check. Reconcile both this contract discrepancy and the intended legacy privileged-user audience before enabling self-service. Do not silently remove current user access or assume that new collaborator groups automatically constrain these routes.

There is an additional existing mismatch: the header exposes the TTL toggle to PowerUser/Admin/Root using OR, but `task_set_ttl_disabled` uses `roles_required('Admin', 'Root', 'PowerUser')`, which requires all three. This was confirmed against the installed Flask-Security decorator documentation. A PowerUser-only account cannot use that visible control. Reconcile the exact intended TTL audience in its existing contract before changing it.

### No persisted collaborator group or grant model exists

`User.roles` and `User.runs` cannot represent “this person can use PATH-CE for project X until date Y.” No Group, Membership, FeatureAccessRequest, reviewer decision, or scoped grant model was found in the account models/migrations.

`_current_user_groups()` in [user.py][user] reads `getattr(current_user, 'groups', None)` for token claims, but `User` defines no such relationship. This is a claim hook, not an implemented group-management system. Browse “groups” and service-token `service_groups` refer to other authorization concepts and must not be repurposed as collaborator membership.

[Registry schema][schema] requires `min_role: dev` for every internal entry, and [runtime authorization][runtime] accepts only Dev/Root for that gate. Adding a database group without changing the schema/authorization contract and all consumers would leave collaborators blocked. Replacing `dev` globally with `poweruser` would grant every self-promoted account internal access and violate the policy.

### Internal access checks differ by surface

| Feature | Registry/UI | Backend evidence | Assessment |
| --- | --- | --- | --- |
| `openet_ts` | Internal/API constrained; Dev/Root | [openet_ts_routes.py][openet], `acquire_openet_ts`: JWT + run access + literal Admin | Confirmed parity defect. Dev-only/Root-only can see the feature but fail execution; Admin-only has the converse role eligibility. |
| `omni_contrasts` | Internal/embargo to 2027-05-22; Dev/Root; menu visible disabled to users | [omni_bp.py][omniweb] report reads registry role; [omni_routes.py][omnirq] hard-codes Dev/Root for execute, dry-run and delete | Existing direct controls are protected, but a new group grant would not work until both paths share the decision. |
| `path_ce` | Internal/beta; Dev/Root; WBT | [path_ce_bp.py][pathce]: enable uses `set_project_mod_state`; config/status/results/run routes use run authorization without the registry role check | Confirmed missing feature check. An already-enabled run's execution/read permissions are not bounded by the menu gate. Other preconditions still apply; no live unauthorized execution attempted. |
| `ag_fields` | Internal/beta; Dev/Root | [ag_fields_routes.py][agfields], `_authorize`: JWT scope + run access, without feature role/grant check | Confirmed missing feature check across the helper's upload/build/read/delete consumers. No live unauthorized job attempted. |
| `batch_runner` | Internal/compute; Dev/Root; excluded from Mods menu | [batch_runner_bp.py][batchweb] and [batch_routes.py][batchrq]/[upload_batch_runner_routes.py][batchupload] use Admin | Confirmed divergence. The registry does not control standalone admission. Root is not automatically Admin in these checks. Flask also has `BATCH_RUNNER_ENABLED` and `BATCH_RUNNER_SKIP_AUTH` switches; live settings were not inspected. |
| `culvert_runner` | Internal/compute; Dev/Root; excluded from Mods menu | [culvert_routes.py][culvert] uses `culvert:batch:submit`/`retry` token scopes and service identity | Separate supported service boundary. Decide how human collaborator grants compose with it; do not remove service-token restrictions. |

Feature access is additive to run ownership/publicity, token scopes, readonly state, backend compatibility, prerequisites and capability exclusions. [General run authorization][helpers] allows public runs and does not itself enforce feature maturity. A run that retains an internal mod, or a user who knows a direct endpoint, must therefore be included in the access matrix.

Generic browse/download, query-engine, archive/fork, child-run and orchestration-status surfaces need an explicit policy disposition. Searches found no general feature-registry enforcement in browse/query-engine. This is not evidence that all paths are publicly exposed: those services have their own run/token checks. It does show that protecting a menu/report URL cannot by itself establish embargo protection for underlying files or queries. Define which operations remain available for already-produced results after grant expiry; preserve the policy's prohibition on a retroactive publication veto.

### Config launch policy is not a general feature entitlement gate

[Interfaces rendering][interfaces] filters config cards using registry roles. [Project creation][creation] authenticates the caller and applies creation/preset policies but does not consult registry `min_role`. [Preset resolution][preset] accepts preset metadata, not a user principal. All currently registered configs are user-level, so this is a readiness gap for future restricted configs, not evidence of an active internal-config bypass.

Both named presets and project-owned Builder configs need an explicit disposition before adding restricted configs. Keep locale/capability authority with the project-config subsystem; do not put it into access groups or infer entitlement from a filename.

### Review and audit requirements have no application lifecycle

There are no persisted reviewer delegations, pending review queues, reason-dependent approvals, named-user onboarding acknowledgments, expiring grants, or decision exports in the inspected account implementation. Release ADRs are valuable but do not establish who currently has access to a feature or why.

The original policy requires multiple reviewer roles and permits one person to hold them. The operator has now rejected the multi-role workflow altogether: implement a single authorized maintainer recording the person, group, reason and timestamps. Amend the ratified text before runtime implementation; do not encode two attestations by the same person as a substitute.

Token role checks generally consume issued claims. The system has token/session revocation machinery, and the session bridge can reload database roles when minting, but neither implements a current feature-grant lookup. Putting collaborator scopes into a long-lived JWT alone would leave access until token expiry. Approval, revocation and expiry need a defined propagation contract across web and API processes.

## Conflicts and decisions to settle before implementation

1. **Public read-only views.** Operator direction: public projects expose feature views read-only to users without action permission. Reconcile Policy 2, the registry and [ADR-0001][embargo]; whether this includes publication-embargoed results remains unresolved.
2. **Maturity overrides.** Resolved direction: choose the least optimistic accurate maturity. Amend the current universal Preview override to preserve Experimental status unless separately promoted on evidence; never erase Internal/Deprecated meaning with an automatic override.
3. **PowerUser capability set.** Confirm self-service includes the current capabilities listed above, explicitly resolve grouped batch/culvert data access before launch, and resolve the TTL mismatch. PowerUser suspension, reapplication and permanent revocation are explicitly out of scope, not launch prerequisites. Do not introduce new restrictions or remove existing privileges as an incidental onboarding change.
4. **Technical-role compatibility.** OpenET and Batch actions use separate feature-specific access groups, each initially containing only the requesting maintainer. Broad Admin/Dev/Root membership alone must not admit others. Resolve the canonical account identity to initialize membership; enforce access through the groups rather than hard-coded account checks. Preserve unrelated technical privileges.
5. **Auditable group administration.** Resolved direction: one authorized maintainer adds/removes a named person for a reason. Record actor, subject, group, effective scope and timestamps; retain change history. Scope changes also need an attributable decision. No dual-reviewer workflow or mandatory reviewer queue.
6. **Review versus expiry.** A review date requests reassessment; an expiration date ends authorization. Define timezone/boundary behavior and treatment of running/queued work. Beta accessibility exceptions may be indefinite under the policy; that does not imply indefinite collaborator grants.
7. **Embargo expiration.** ADR-0001 requires review by 2027-02-22 and reassessment on 2027-05-22. A date does not establish Preview/Stable readiness. Record renewal or a new maturity/internal reason, with transparent overdue status; do not silently keep an expired publication reason forever.
8. **Dependency access.** ADR-0001 states PATH-CE depends on Omni Contrasts, but PATH-CE has an empty registry prerequisite list and consumes contrast outputs. Define bounded dependency grants or denial without auto-granting all internal features or silently activating mods.
9. **Results and sharing.** Decide execute/read/export/fork/archive behavior for internal data on public/shared runs, after grant revocation, and for queued jobs. Run ownership and feature permission remain distinct. Service/MCP identities need explicit scopes rather than fabricated human membership.
10. **Accessibility and disclosure.** The policy does not explicitly list Experimental in its conformance table; the public statement limits the validated theme set. Clarify coverage and retained evidence without claiming conformance from a maturity label. Define where a user can read a restriction reason and request access without exposing private collaborator records.

These are contract decisions, not reasons to delay the assessment or silently redesign the policy. The [contract-first standard][contractfirst] requires reconciled canonical contracts and the accepted ancestor checkpoint before intended UI/auth behavior changes.

## Proposed implementation shape

### Reuse the existing account database

Use additive SQLAlchemy/Alembic changes in the existing account database. No new identity provider, authorization service, queue, datastore, or dependency is warranted by the current evidence.

The minimum logical records are:

| Record | Purpose |
| --- | --- |
| Versioned onboarding acceptance | User id, statement/version, accepted time; PowerUser request/automatic decision metadata as required by policy. |
| Collaborator group and membership | Stable group identity, named member, authorized purpose/scope, validity/review state; membership changes linked to decisions. |
| Optional access request | Requester, typed feature/config/workflow scope, optional project/run constraint, reason code, purpose, sponsor contact only when applicable, training version and decision state. |
| Maintainer decision | Authorized actor, affected user/group/scope, action, reason and timestamp; one decision, not multiple reviewer roles. |
| Effective grant and audit events | Approved subject/scope, validity interval, review date, originating request/decisions, changes, revocation/renewal; retrievable history. |

This is a logical model, not a requirement for a table per row. Keep feature and config scopes distinct even when IDs match. Prefer simple group composition and bounded grants; no nested group hierarchy or generic policy language is needed. An individual request may be fulfilled through a narrowly scoped group membership, provided its named-user decision and onboarding remain auditable.

A grant's effective scope must be no broader than the approved group scope, member scope and time interval. Adding features to an existing group must not silently widen prior approvals. Adding a member must record the authorized maintainer's decision. Revocation removes authorization while preserving the historical decision record.

### One decision reused by actual consumers

Define a shared feature-access evaluator accepting a verified principal, typed resource, action and optional run context. Its result should include allow/deny, a stable user-facing reason and decision provenance useful for audit. Keep the human membership lookup separate from static registry loading: the registry's process-wide `lru_cache` must not cache mutable grants.

For internal access, evaluate the explicitly preserved operational access path or a current approved grant. OpenET/Batch actions are specifically restricted to the designated maintainer account; do not infer that grant from broad role membership. In either case, independently enforce the existing run, scope, backend, capability and action constraints. A group grant is not an ownership bypass, a backend override or a right to administer other users.

Wire this decision into header options, run sections, `/view/mod`, `set_mod`, each registered action/report/data endpoint and any restricted config creation path. Retain the current service-specific authorization where additive. Human grant revocation must be checked using current server-side state at protected API admission, not trusted indefinitely from a JWT snapshot. Reuse existing database access mechanisms; measure any need for caching before introducing it.

Define queued/running-job semantics before worker changes. Admission-time authorization, execution-time rechecks and cancellation are distinct behaviors. Do not cancel running work or alter job dependencies implicitly. If queue wiring changes are necessary, apply the RQ graph and live-tree validation requirements.

### Small user and maintainer flows

Use the Profile page for PowerUser training/request and current access status. Use an approved informational feature-access page for restriction reasons, available request scopes and request status. A user should see their own grants, purpose, expiration/review date, and how to request renewal; they should not see other collaborators' PII or internal reviewer notes.

Provide a simple maintainer group-management page: select person and group, enter reason, save the decision and timestamp. Support removal and inspection of history. A mandatory reviewer queue, dual approval and separate reviewer roles are outside the directed scope.

Review dashboards and exportable records can begin as ordinary database queries and operator procedures. Enforce actual expiration during authorization so access does not depend on a reminder job. Notifications or scheduled automation can be considered later if ordinary operations prove insufficient.

## Delivery order and acceptance

### Phase 1 Contract reconciliation and endpoint inventory

Create a scoped implementation work package and active ExecPlan. Preserve this assessment as evidence. Inventory every action and read surface for all six internal features, including standalone/service entry points and derived data. Resolve the ten decisions above; amend the policy, registry specification, affected domain contracts, auth/token and browse contracts as applicable. Keep implementation conformance pending until tested.

Record compatibility, additive schema migration, maintainer administration authority, retained role privileges and the exact read/revocation boundary. Obtain the required independent contract reviews and commit the standalone checkpoint before runtime edits. The implementation has high security impact and needs independent correctness and security review artifacts.

Acceptance: an ordinary user, PowerUser, scoped collaborator, access administrator and each technical role have an unambiguous action/read matrix. No unresolved conflict is hidden by tests that merely copy current behavior. If the grouped-data decision requires scoped grants, implement that prerequisite from Phases 3–4 before enabling Phase 2 self-service; phase numbering is not authorization to expose the existing broad audience.

### Phase 2 PowerUser self-service

Implement the versioned statement, two-question Profile form, CSRF-protected mutation, atomic approval/role assignment and status display. Reuse Flask-Security and the account database. Preserve existing roles and explicitly handle legacy users, duplicate submissions and failed transactions. PowerUser suspension, reapplication and permanent revocation workflows are deferred; no implementation or acceptance gate for them belongs in this phase.

Acceptance: a logged-in ordinary user answers both questions yes and can immediately use an appropriate PowerUser feature; missing/no answers do not grant access; an unauthenticated or forged-CSRF request fails; no caller can choose another user or role. The resulting audit record identifies the statement version and automatic approval rule. An internal feature remains denied. Verify the newly available token/operational controls against the agreed matrix.

### Phase 3 Scoped groups and reviewed internal access

Add groups, memberships, maintainer decisions and grants with named-user onboarding, renewal/revocation, audit export and applicable review dates. Keep a request form optional. Adopt additive migrations; do not manufacture historical approvals or silently alter unrelated technical privileges. Initialize OpenET/Batch action grants only for the designated maintainer.

Acceptance: the maintainer adds an external user to one feature group with a reason, and the audit history identifies both people, scope and timestamp. That user gains the permitted actions without technical roles; other internal actions remain denied. Removal and scope changes are auditable. Public-project read-only visibility remains separate. OpenET/Batch actions remain restricted to the designated maintainer.

### Phase 4 Enforce parity across UI and execution

Apply the evaluator across all inventoried surfaces. Resolve the OpenET/Batch role conflicts, PATH-CE/AgFields missing checks, hard-coded Omni checks and scoped dependency behavior. Include hidden, already-enabled, shared/public, forked and child-run cases. Exercise service identities separately. Add config-launch enforcement before the first internal config is introduced.

Acceptance: an approved collaborator can render, configure, execute and inspect the granted workflow end to end; an unapproved caller cannot perform protected actions through direct endpoints but can inspect public-project read-only views under the agreed embargo rule. Removing membership or expiring the grant has the specified effect even with a previously issued token. Authorization and required denial tests use actual persistence/evaluator boundaries, not mocked role checks alone. Preserve accepted historical-result access and ongoing-job semantics.

### Phase 5 Release evidence and operational acceptance

Add the agreed restriction explanations, review/embargo procedures, promotion checklist, accessibility evidence mapping and any bounded output provenance changes. Test a real approved workflow under production-equivalent identities, database schema, configuration and token boundaries. For generated outputs, inspect actual prepared inputs, fresh output content and the user-facing result; job success alone is insufficient.

Acceptance: maintainers can answer who has access, to what, why, under whose authority and until when; users can understand their access and request review. Retain browser keyboard/accessibility checks, real database round trips, expiry/revocation evidence and feature output evidence. Local test success is not deployment acceptance.

## Regression and migration plan

Use the real role matrix above plus User+grant, PowerUser+grant, unauthorized group member, expired/revoked membership, access-administrator-only and service/MCP identities. Separately cover absent optional state, empty state, valid populated state, supported legacy state, malformed/hostile state and concurrent submissions/reviews.

Required cases include missing/recorded maintainer decisions, unauthorized membership edits, changed group scope, replayed onboarding, old training version, forged subject/scope, stale token, group removal, applicable grant expiry at the boundary, no database connectivity, public readonly views, incompatible backend, missing dependencies, cross-project access, maintainer-only OpenET/Batch actions and active internal mods retained from an earlier grant. Select explicit failure behavior for the new authorization-store boundary without masking errors as a public grant.

Migrations must be additive, preserve existing user IDs and roles, and retain history. Validate upgrades with legacy users and an empty grants table before enabling the UI. Rollout order is database support, all authorization consumers, then access-management UI. A partially upgraded service must not silently interpret a scoped collaborator as Dev. Define rollback to disable new admissions while retaining decision records; never roll back by broadening roles or silently dropping audit data.

For future runtime work, use focused tests first, then `wctl run-pytest tests --maxfail=1`, applicable frontend lint/tests, CSRF/auth regressions and real database/browser acceptance. Current tests cover registry and role behavior but do not cover a group lifecycle that does not yet exist. Tests that currently assert hard-coded roles or universal Preview overrides must be reconciled with the approved contract rather than mechanically retained or deleted.

## Validation performed for this assessment

Real registry loading in the running development container validated the current YAML/config paths and produced the inventory and role matrix above. Installed Flask-Security documentation confirmed ALL semantics for `roles_required` and ANY semantics for `roles_accepted`.

The following existing focused suite passed **268 tests**, with 10 dependency/deprecation warnings, in 27.33 seconds:

```bash
wctl run-pytest \
  tests/weppcloud/routes/test_feature_registry_runtime.py \
  tests/weppcloud/routes/test_admin_usermod_contract.py \
  tests/weppcloud/routes/test_user_profile_contract.py \
  tests/weppcloud/routes/test_user_profile_token.py \
  tests/weppcloud/routes/test_run_0_openet_admin_gate.py \
  tests/weppcloud/routes/test_weppcloud_site_interfaces_route.py \
  tests/microservices/test_rq_engine_openet_ts_routes.py --maxfail=1
```

These tests establish the current tested behavior, not compliance with the ratified policy. In particular, OpenET rendering tests allow Dev, while its rq-engine tests separately require Admin and mock authorization in the enqueue case. No test traverses that complete user journey in this selection.

A follow-up selection confirmed the grouped-data behavior: **7 passed**, 83 deselected, 6 dependency/deprecation warnings, in 0.70 seconds. The accepted PowerUser cases use signed user tokens without a group identifier claim and read temporary fixture data, including a culvert download. Combined assessment total: **275 passing tests**.

```bash
wctl run-pytest tests/microservices/test_browse_auth_routes.py \
  -k 'group_user_token or culvert_download_allows_user_token or group_service_token_missing_identifier' \
  --maxfail=1
```

No full test sweep, live unauthorized execution, new migrations, production database inspection, or live accessibility audit was performed. Remaining operational evidence includes existing off-repository access decisions, actual multi-role account distributions, deployment revisions, group administration authority, and workflow-specific scientific/accessibility evidence.

[policy]: ../../wepppy/weppcloud/routes/usersum/weppcloud/feature-maturity-and-release-governance.md
[models]: ../../wepppy/weppcloud/app.py
[admin]: ../../wepppy/weppcloud/routes/admin.py
[user]: ../../wepppy/weppcloud/routes/user.py
[profile]: ../../wepppy/weppcloud/templates/user/profile.html
[schema]: ../../wepppy/weppcloud/feature_registry/schema.py
[runtime]: ../../wepppy/weppcloud/feature_registry/runtime.py
[features]: ../../wepppy/weppcloud/feature_registry/feature_registry.yaml
[project]: ../../wepppy/weppcloud/routes/nodb_api/project_bp.py
[commandbar]: ../../wepppy/weppcloud/routes/command_bar/command_bar.py
[builder]: ../../wepppy/microservices/rq_engine/builder_routes.py
[recorder]: ../../wepppy/weppcloud/routes/recorder_bp.py
[browse]: ../../wepppy/microservices/browse/auth.py
[browsecontract]: ../schemas/weppcloud-browse-auth-contract.md
[openet]: ../../wepppy/microservices/rq_engine/openet_ts_routes.py
[omniweb]: ../../wepppy/weppcloud/routes/nodb_api/omni_bp.py
[omnirq]: ../../wepppy/microservices/rq_engine/omni_routes.py
[pathce]: ../../wepppy/weppcloud/routes/nodb_api/path_ce_bp.py
[agfields]: ../../wepppy/microservices/rq_engine/ag_fields_routes.py
[batchweb]: ../../wepppy/weppcloud/routes/batch_runner/batch_runner_bp.py
[batchrq]: ../../wepppy/microservices/rq_engine/batch_routes.py
[batchupload]: ../../wepppy/microservices/rq_engine/upload_batch_runner_routes.py
[culvert]: ../../wepppy/microservices/rq_engine/culvert_routes.py
[helpers]: ../../wepppy/weppcloud/utils/helpers.py
[interfaces]: ../../wepppy/weppcloud/routes/weppcloud_site.py
[creation]: ../../wepppy/microservices/rq_engine/project_routes.py
[preset]: ../../wepppy/nodb/project_config_snapshot.py
[embargo]: ../adrs/ADR-0001-time-limited-publication-embargo-for-omni-contrasts.md
[contractfirst]: ../standards/contract-first-change-standard.md
