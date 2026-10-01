# Feature access governance amendment

Status: FA-01 reconciled amendment prepared 2026-10-01; independent technical reviews and ancestor checkpoint pending. Implementation pending.

This document owns the FA-01 feature-access behavior and records the project maintainer's directions following the [implementation assessment](../dev-notes/feature-maturity-governance-implementation-assessment.md). The [governance policy](../../wepppy/weppcloud/routes/usersum/weppcloud/feature-maturity-and-release-governance.md), registry specification, ADR-0001 and auth contracts cross-link this bounded amendment. [ADR-0080](../adrs/ADR-0080-feature-access-governance-amendment.md) preserves its rationale. The [implementation plan](../work-packages/20261001_feature_access_governance/prompts/active/feature_access_governance_execplan.md) may not enter runtime milestones until the contract-first ancestor checkpoint exists. This document does not claim current runtime conformance.

## Decision provenance and scope

Decision venue: user-agent conversation, 2026-10-01. Decision owner: the requesting project maintainer. The agent records the directions and assesses implementation implications; it does not independently grant access or define suspension criteria.

The approved directions concern public-project read-only visibility, internal Batch/Culvert access, conservative maturity, single-maintainer group administration and maintainer-only OpenET/Batch operations. PowerUser suspension, reapplication and permanent revocation are explicitly deferred from this scope. Public visibility of publication-embargoed results remains unresolved. No deployment, account mutation, token rotation or feature activation is included in this documentation change.

## Public project visibility and action permissions

The default for a public project is that all users can inspect its feature views in read-only mode. A viewer without action authorization must not be able to activate, configure, execute, retry or otherwise mutate a feature through the UI or a direct endpoint. Publishing a project does not grant operational access to its internal features.

Model read permission separately from action permission. Read-only views should present existing project state and results without initiating computation or external API acquisition. This direction is broader than displaying a disabled feature name in a menu. It does not require creating missing feature state while rendering a public project.

Rationale: public projects should be inspectable and understandable even when a viewer cannot run the same workflow. A single visibility/enablement role gate cannot express this behavior.

Reserved exception: ADR-0001's restriction on publication-embargoed contrast data remains in force on public projects. The operator has not yet answered whether public sharing should override it. FA-01 preserves that restriction rather than treating silence as permission to publish; a later explicit decision can amend it. This retained exception makes the public-read default implementable without releasing embargoed data.

Public inspection covers the feature state and already-produced results applicable to that project. Missing optional state renders an empty/not-yet-run view without controller creation or jobs. Capability/backend limits may explain why an action is unavailable but must not erase retained readable results. Project-wide readonly still disables mutations even for a group member. Protected credentials, root-only files and private account/audit data are never made public by this rule.

## Batch and Culvert are internal workflows

Batch Runner and Culvert Runner are internal. Their registry entries already say `internal` with reason `compute`; the work is to reconcile actual admission and data-access behavior, not merely relabel the entries.

PowerUser status alone must not confer internal action permissions. Public-project read-only visibility is a separate decision from authority to submit a batch or invoke restricted services. Private grouped data must follow its approved access scope; the current broad privileged-user token path requires reconciliation.

Culvert's existing long-lived integration JWT must be handled as an explicitly authorized service principal. Do not turn it into a human group membership or invalidate it as an incidental part of adding groups. Record the integration's owner, purpose, authorized operations, credential identity and validity/revocation arrangements without recording the secret bearer token.

There are two different credentials in the current design:

- The submitting integration JWT carries scopes such as `culvert:batch:submit`, `culvert:batch:retry` and, when provided, `rq:status`. Its actual deployed lifetime, principal and scope set have not been inspected in this assessment.
- The API returns a separate seven-day `browse_token` for one batch UUID. It has `token_class=service`, `service_groups=culverts`, a `jti` and a batch-bound `runs` claim. It is not the long-lived submitting credential and does not gain polling rights merely from being returned by submission.

The reconciliation covers submit, retry, finalize, polling, cancellation, browse and download individually. Human group membership does not mint or delegate the submitting service credential. Existing service scopes and resource claims remain independently required. The pre-implementation inventory must bind the currently authorized integration's verified subject/credential identity and operations to an operator-owned service-access record. Do not mint new identities, narrow scopes, rotate credentials or change lifetimes in this package without a separately recorded operator decision.

Sources: [token specification](../dev-notes/auth-token.spec.md), [agent API contract](rq-engine-agent-api-contract.md), [Culvert routes](../../wepppy/microservices/rq_engine/culvert_routes.py), and [browse auth contract](weppcloud-browse-auth-contract.md).

## Maturity remains conservative

Choose the least optimistic accurate maturity supported by evidence. The multi-OFE override must not raise an Experimental configuration to Preview merely because it uses multiple OFEs. In particular, the declared Experimental status of `reveg-mofe` and `reveg-10m-mofe` must be preserved unless separately promoted on evidence.

Rationale: representation choices do not establish scientific readiness. This is not permission to rank all five labels numerically: Internal is an access/release state, and Deprecated is a lifecycle state. An override must not erase either restriction or lifecycle information by applying a universal Preview label.

Implementation must amend the registry override specification and its tests before or with the approved implementation sequence; do not change scientific model parameters as part of this labeling correction.

## One maintainer administers auditable groups

Replace the dual-reviewer workflow with a single authorized maintainer's group membership decision. The intended operation is simple: add or remove a named person from a bounded group, record the reason, and retain who performed the change and when.

The minimum audit event identifies the acting maintainer, affected user, group, effective feature/action scope, action, reason and timestamp. Preserve addition, removal and scope-change history. Keep any applicable review or expiration information, but do not invent a mandatory default lifetime merely to populate a field.

Membership does not grant Dev, Admin, Root or unrelated private-project access. The group defines the bounded capability; existing run and service checks still apply. Changes to group scope also require an attributable reason and timestamp because they change members' effective access.

Use one explicit administrative decision rather than two reviewer roles, two role-specific attestations, a mandatory reviewer queue or a new approval hierarchy. A web request form may be added if it helps actual users, but is not a prerequisite for the maintainer to record a grant. Existing onboarding and record-retention obligations must be reconciled without reintroducing dual approval.

Rationale: the project does not have staffing for a multi-role review process. The required control is attributable, reasoned, retrievable access history with bounded grants.

## OpenET and Batch operations remain maintainer-only

OpenET actions remain limited to the requesting project maintainer because of API constraints. Batch Runner actions remain limited to that same maintainer because of computational limits. These are specific-person restrictions, not a grant to every Admin, Dev or Root account and not an open collaborator cohort.

Enforce these restrictions through separate feature-specific access groups for OpenET and Batch Runner. Initially, the requesting maintainer's account is the sole member of each group. Authorization checks group membership; they must not special-case the maintainer's user ID or email, or substitute an Admin/Dev/Root role check. Resolve the canonical account identity only to initialize these memberships; do not invent a database ID.

Public read-only feature views do not authorize OpenET acquisition or Batch creation/execution. Membership additions, removals and group-scope changes use the same reason-and-timestamp audit trail as other internal feature groups. This group-based restriction was explicitly confirmed by the operator on 2026-10-01: the initial audience is one person, while the enforcement mechanism remains ordinary scoped group membership.

Future expansion requires an explicit recorded access decision. No automatic expansion results from PowerUser self-promotion or a broad technical role. Emergency/maintenance exceptions, if needed, must be explicitly reconciled with existing operator access rather than silently assumed.

## Deferred PowerUser lifecycle

The ratified policy contains broad grounds: protecting reliability, storage, compute capacity and scientific integrity; prior misuse or unresolved compliance concerns; and consequences for failing agreed consultation expectations. It does not specify concrete suspension criteria, decision evidence, notice, duration, reinstatement or the interaction with automatic PowerUser reapplication.

The operator explicitly deferred PowerUser suspension, reapplication and permanent revocation on 2026-10-01. These are not prerequisites or acceptance conditions for the current self-service and group-access work. Do not add suspension states, reinstatement flows, permanent-ban flags or new denial criteria in this scope.

Current PowerUser scope is initial onboarding, versioned acknowledgment, automatic approval and idempotent handling of duplicate submissions or users who already hold the role. Duplicate submission is not a reinstatement workflow. Preserve existing administrative role controls; this increment does not promise durable suspension or permanent revocation enforcement against future self-service requests.

Rationale: deliver the requested onboarding and auditable group access without expanding into an unagreed account-sanctions lifecycle. Scoped group membership removal and its audit history remain in scope; existing token revocation mechanisms and the Culvert credential reconciliation are separate from the deferred PowerUser lifecycle.

## Authorization composition

The implementation must expose separate decisions for `inspect`, `act` and `manage_membership`. An action includes a semantic mutation regardless of HTTP verb: module enable/disable, configuration writes, acquisition, upload, execution, retry, finalization, cancellation, deletion, or generation of an export. Reading an existing result is inspection; requesting a new result is an action.

| Surface/principal | Inspection | Actions |
| --- | --- | --- |
| Public ordinary project; anonymous or ungranted viewer | Allow existing non-embargoed feature views/results under existing read transport protections | Publicity alone never authorizes actions |
| Private ordinary project | Existing project read authorization required | Existing project write authorization plus feature permission required |
| OpenET or Batch human caller | Public inspection as above; private Batch grouped data requires its workflow group | Current corresponding group membership required, including for Admin/Dev/Root |
| Culvert human caller | Private grouped data requires Culvert workflow group; no new anonymous Culvert root is created | Current Culvert group plus applicable existing resource/scope requirements |
| Omni Contrasts | Run access plus Dev/Root legacy entitlement or current contrast group; public embargo exception retained | Same feature entitlement plus project write/backend/prerequisite constraints |
| PATH-CE / AgFields | Public non-embargoed inspection; private project read access | Dev/Root legacy entitlement or current feature group, plus project write/capability constraints |
| Authorized Culvert service | Existing batch-bound browse credential remains sufficient for its existing artifact surfaces | Registered integration's existing verified credential and required operation scopes; no human-role requirement |

`batch_runner` and `culvert_runner` groups are workflow scopes. Their private grouped roots are admitted by the corresponding group and checked against the requested workflow/resource identifier, not by the PowerUser role. This does not grant access to unrelated private ordinary runs. Ordinary run children continue to apply their existing owner/resource boundaries. The current Batch public-base-run read exception is preserved; Culvert has no new public-root switch in this increment.

The default legacy operational path for Omni Contrasts, PATH-CE and AgFields is preserved, with additive group access. For OpenET, Batch and human Culvert workflow access, group-only behavior replaces broad role gates. Existing unrelated administrative powers and Root-only sensitive-path checks are unchanged. Group membership cannot override readonly, backend, capability or required token scopes.

Public-run mutation authorization must distinguish a project owner/authorized writer from a viewer. The existing `authorize()` public-read result cannot be reused as proof of write authority. Before runtime edits, the surface inventory must register how existing authenticated ownership, administrative write authority, and legitimate anonymous creator sessions are proven. Preserve supported anonymous creation workflows; do not equate a read-scoped token for a public run with creator authority. Where current infrastructure cannot distinguish them, record the exact missing authority contract and resolve it at the checkpoint rather than silently locking out creators or opening writes.

PATH-CE actions that consume embargoed contrast results also require contrast entitlement under ADR-0001. A PATH-CE group does not silently add the user to the contrast group. Group administration must explain this dependency and permit the maintainer to record the necessary memberships with their reasons. No model runs or dependencies are auto-enabled by a membership change.

## Registry representation

Retain `min_role` as the legacy role audience for compatibility. Add internal-feature metadata `access_group` (stable group key) and `access_mode` (`role_or_group` or `group_only`). Omission preserves the existing role behavior for entries outside the changed internal inventory. Reject unsupported modes, empty group keys, and group mode without an explicit group key. The static registry loader does not query the account database.

Initial mapping: `openet_ts`, `batch_runner`, and `culvert_runner` use matching group keys and `group_only`; `omni_contrasts`, `path_ce`, and `ag_fields` use matching group keys and `role_or_group`. Initially only the designated maintainer belongs to OpenET and Batch groups. Other memberships require an explicit recorded decision; do not infer membership from role, project affiliation or JWT `groups` claims. The existing Culvert service integration is admitted separately.

An internal feature still declares `min_role: dev` for its legacy metadata, but this field does not bypass `group_only`. `menu_min_role` governs disabled name discovery only and does not authorize actions or embargoed data. Public inspection uses this contract rather than the legacy menu/action audience. Registry order, labels, backend ownership and locale/capability contracts stay unchanged.

For the existing `multi-ofe-is-preview` rule, the effective result is Preview for declared Stable or Preview configurations. Declared Experimental, Internal and Deprecated remain unchanged. This finite rule preserves the caution introduced by multiple OFEs without treating maturity/access states as a numeric ranking. No config or model parameter changes are included.

## Account records and atomicity

Use the existing SQLAlchemy account database and Alembic migrations. The initial logical records are groups, current memberships, append-only access events, and versioned onboarding acceptances. No multi-stage request/reviewer model or new service is required.

Groups have a stable key matching registry metadata, a label and an active state. Membership identifies group and canonical user ID, has a unique current `(group_id, user_id)` association, and can carry optional review/expiration dates. The event history records every add/remove/change with actor, affected user, group, effective feature scope, reason and server UTC time. A membership with a review date alone stays effective until changed; an actual expiration ends admission at that instant. No automatic lifetime is imposed.

Persist membership changes and their audit event in one transaction. Reject blank reasons and unknown users/groups; an already-satisfied add/remove is an explicit idempotent no-op, not a second grant. Preserve actor/subject identifiers and event scope snapshots even if a user/group is later removed; do not cascade-delete history. Apply existing award-related retention obligations through the maintainer's retention process, not a new fixed cleanup timer.

Onboarding acceptance identifies user, statement kind/version and accepted UTC time. PowerUser acceptance and role assignment are one transaction, including the automatic decision/rule and approval time. The two required boolean answers must both be true; user ID, target role and approval rule are server-owned. Legacy PowerUsers keep access with legacy provenance rather than fabricated training. Group membership may be assigned before the user acknowledges the internal statement; group-based protected actions require that acknowledgment. Preserved legacy operational-role paths do not acquire a new onboarding gate.

The initial group-administration UI reuses the existing Root administrative trust boundary. An administrator may manage groups without thereby receiving group-protected execution access. Introducing delegated group administrators is outside this increment. Mapping groups to features is registry-controlled; a UI cannot create arbitrary capabilities by naming a group. Group definition/scope changes must be accompanied by a recorded maintainer decision.

## Tokens and admission timing

Resolve a verified user/session principal to the canonical database user ID, then query current membership for protected operations. JWT `groups` is informational; a stale token cannot retain a removed membership. Do not cache mutable membership in process-wide registry caches. Require existing JWT signature, audience, expiry, revocation, scope and run/session checks first. Do not treat service/MCP `sub` values as database user IDs unless their existing contract explicitly establishes that identity.

Removal or expiration affects subsequent protected admissions. Jobs already admitted may finish; this increment neither cancels running/queued jobs nor adds worker-side permission rechecks. Their later reads obey the read policy. New retries, finalizers or submissions are new admissions. Explicit token revocation remains independently effective under current token contracts. No credential TTL changes are part of FA-01.

Membership-store failure returns an explicit unavailable response for an operation requiring membership; it must not grant access by falling back to PowerUser/Admin/Dev. Public non-embargoed inspection that needs no membership decision remains available under its existing read authorization. Preserve normal error envelopes (`rq-response-contract.md`) and existing CSRF/origin protections.

## UI and backend obligations

The Profile page provides the short PowerUser statement, the two yes/no answers, and current status. Submission is authenticated, CSRF-protected and idempotent. It does not allow selecting another account or role. Existing internal-group controls and private grouped-data protections must be ready before this form is enabled for general users.

An administrative group page provides membership add/remove with a required reason, optional review/expiry fields, and history. It does not expose other users' audit notes to public viewers. Users can inspect their own group status and complete the internal acknowledgment without a second maintainer approval.

Public project renderers and dynamic sections must distinguish readable from actionable state. Disable or omit mutation controls with a clear reason, preserve accessible labels, and enforce the same denial server-side. Disabled JavaScript is presentation, not authorization. Inspect-only reads must not call helpers that initialize optional controllers or regenerate artifacts.

The complete surface inventory must cover direct routes, generic browse/download, query-engine/MCP, exports, archives, forks, child-run URLs, and orchestration reads that contain feature data. A mixed bundle or query must not bypass the retained embargo exception. Preserve existing readable non-embargoed artifacts; do not introduce blanket project denial merely because the project also contains a restricted feature. Exact artifact boundaries and supported partial-read behavior require retained source evidence and contract review before implementation.

## Remaining implementation checkpoint

The current task prepares documentation only. Runtime work requires an exact surface/state matrix, canonical maintainer identity for group initialization, a redacted Culvert integration inventory, and resolution of the public-run writer/anonymous-creator boundary. These are explicit milestone-zero inputs, not permission to invent identities or silently alter supported workflows.

Independent correctness and governance/security contract reviews, findings disposition and the standalone contract ancestor commit are still required. The operational single-maintainer group decision is distinct from repository engineering reviews. PowerUser suspension, reapplication and permanent revocation do not block this increment. The unanswered proposal to expose embargoed results remains excluded; the existing restriction is retained.
