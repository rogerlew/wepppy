# Feature access governance amendment

Status: FA-01 reconciled amendment prepared 2026-10-01; independent milestone-zero correctness/security reviews passed after fixes. Accepted ancestor is recorded in the package tracker; implementation pending.

This document owns the FA-01 feature-access behavior and records the project maintainer's directions following the [implementation assessment](../dev-notes/feature-maturity-governance-implementation-assessment.md). The [governance policy](../../wepppy/weppcloud/routes/usersum/weppcloud/feature-maturity-and-release-governance.md), registry specification, ADR-0001 and auth contracts cross-link this bounded amendment. [ADR-0080](../adrs/ADR-0080-feature-access-governance-amendment.md) preserves its rationale. The [implementation plan](../work-packages/20261001_feature_access_governance/prompts/active/feature_access_governance_execplan.md) may not enter runtime milestones until the contract-first ancestor checkpoint exists. This document does not claim current runtime conformance.

## Decision provenance and scope

Decision venue: user-agent conversation, 2026-10-01. Decision owner: the requesting project maintainer. The agent records the directions and assesses implementation implications; it does not independently grant access or define suspension criteria.

The approved directions concern read-only visibility of limited-access features for users without their entitlement, internal Batch/Culvert access, conservative maturity, single-maintainer group administration and maintainer-only OpenET/Batch operations. PowerUser suspension, reapplication and permanent revocation are explicitly deferred from this scope. Public visibility of publication-embargoed results remains unresolved. No deployment, account mutation, token rotation or feature activation is included in this documentation change.

## Public project visibility and action permissions

Only features with limited access become read-only for callers who lack that feature's entitlement. On a public project, those callers can inspect the feature's existing non-embargoed state/results, but cannot activate, configure, acquire data for, execute, retry, delete or otherwise mutate that restricted feature through UI or direct endpoints. Publicity does not grant restricted-feature entitlement.

**Scope clarification, 2026-10-01:** anonymous project creation and existing anonymous functionality remain unchanged. FA-01 does not introduce a project-wide owner/writer gate, creator credential, legacy ownerless-run migration, recovery process, new login requirement or different ordinary public-editing policy. Existing ordinary project authorization remains the baseline; feature entitlement is an additional check only for a limited-access operation or protected data surface. Existing explicit project `readonly`, run/resource, CAP, scope, CSRF and capability checks still apply where they already apply.

Rationale: the operator requested read-only access to otherwise unavailable features, not read-only public projects. The earlier broad writer/anonymous-creator proposal exceeded that scope and is withdrawn. The absence of historical creator proof is not a blocker for this amendment.

A newly exposed inspect-only restricted-feature view must read retained state/results without initializing the feature, acquiring external data, computing new protected results or enqueuing work. Missing optional feature state is shown as not yet available. Preserve ordinary anonymous page/session/query/cache behavior; do not turn this feature-level read-only rule into a prohibition on all existing request side effects. Capability/backend limits may explain an unavailable action but cannot erase retained readable results.

Reserved exception: ADR-0001's publication embargo remains in force for contrast data, including public projects and derived representations. No release of embargoed results has been authorized. Protected credentials, root-only files and private account/audit data remain excluded from public visibility.

## Batch and Culvert are internal workflows

Batch Runner and Culvert Runner are internal. Their registry entries already say `internal` with reason `compute`; the work is to reconcile actual admission and data-access behavior, not merely relabel the entries.

PowerUser status alone must not confer internal action permissions. Public-project read-only visibility is a separate decision from authority to submit a batch or invoke restricted services. Private grouped data must follow its approved access scope; the current broad privileged-user token path requires reconciliation.

Culvert's existing long-lived integration JWT must be handled as an explicitly authorized service principal. Do not turn it into a human group membership or invalidate it as an incidental part of adding groups. Record the integration's owner, purpose, authorized operations, credential identity and validity/revocation arrangements without recording the secret bearer token.

There are two different credentials in the current design:

- Operation credentials require the scope for each operation. The inspected client credential carries only `culvert:batch:submit`; deployed identity, lifetime and limitations are recorded in the registration section below.
- The API returns a separate seven-day `browse_token` for one batch UUID. It has `token_class=service`, `service_groups=culverts`, a `jti` and a batch-bound `runs` claim. It is not the long-lived submitting credential and does not gain polling rights merely from being returned by submission.

The reconciliation covers submit, retry, finalize, polling, cancellation, browse and download individually. Human group membership does not mint or delegate the submitting service credential. Existing service scopes and resource claims remain independently required. The registration below binds the inspected integration identity and operations; renewal requires an explicit operator-maintained credential record. Do not mint new identities, narrow scopes, rotate credentials or change lifetimes in this package without a separately recorded operator decision.

Sources: [token specification](../dev-notes/auth-token.spec.md), [agent API contract](rq-engine-agent-api-contract.md), [Culvert routes](../../wepppy/microservices/rq_engine/culvert_routes.py), and [browse auth contract](weppcloud-browse-auth-contract.md).

### Culvert client registration and compatibility

The operator identifies `culvert-web-app` at `/workdir/Culvert_web_app` on `wepp2` as the authorized integration; it targets `wepp.cloud`. Current configured operation credential: `sub=culvert-batch-submit-90d`, audience `rq-engine`, service class, `service_groups=culverts`, scope `culvert:batch:submit`, no run claims. Preserve this independently registered service identity without human membership or a new per-batch operation claim. Register the subject/audience/service-group combination through operator-owned configuration tied to this integration key; normal signature, expiry, revocation and operation scopes remain mandatory. Credential renewal/subject changes require explicit registration maintenance, never arbitrary self-registration from JWT fields. Retain existing classless compatibility only for an explicitly registered legacy shape, not every scope-bearing token.

The observed client submits, polls in the server's existing `open` polling mode, and downloads with the returned batch-bound browse token. Its configured operation token does not authorize retry/finalize (`culvert:batch:retry`) or authenticated polling (`rq:status`); group changes do not add those scopes. Keep server retry/finalize/cancel paths compatible with independently authorized credentials that already carry their required scopes. Do not replace open polling globally in this package.

Read-only verification on 2026-10-01 found the configured token signature matches wepp1's rq-engine validation keys but normal validation rejects it as expired (expiry 2026-09-01 20:38:14 UTC). This existing operational problem is separate from group-policy design: never bypass expiry or silently rotate the token. Renewal and a successful live workflow are prerequisites for claiming integration acceptance/rollout, not grounds for broadening the scope of this documentation milestone. Non-secret fingerprints and environment evidence live in the active package; raw credentials never do.

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

Enforce these restrictions through separate feature-specific access groups for OpenET and Batch Runner. Initially, the requesting maintainer's account is the sole member of each group. Authorization checks group membership; they must not special-case the maintainer's user ID or email, or substitute an Admin/Dev/Root role check. The operator identified `rogerlew@gmail.com` on every deployment. Resolve that exact account in each deployment only to initialize these memberships; IDs are environment-specific. Do not hard-code the email or ID in request authorization.

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
| Public ordinary project; anonymous or ungranted viewer | Existing ordinary reads; limited-feature non-embargoed views/results are inspectable | Existing ordinary actions unchanged; deny restricted-feature actions without entitlement |
| Private ordinary project | Existing project read authorization required | Existing project authorization plus feature permission for restricted operations |
| OpenET or Batch human caller | Public inspection as above; private Batch grouped data requires its workflow group | Current corresponding group membership required, including for Admin/Dev/Root |
| Culvert human caller | Private grouped data requires Culvert workflow group; no new anonymous Culvert root is created | Current Culvert group plus applicable existing resource/scope requirements |
| Omni Contrasts | Run access plus Dev/Root legacy entitlement or current contrast group; public embargo exception retained | Same feature entitlement plus existing project/backend/prerequisite constraints |
| PATH-CE / AgFields | Public non-embargoed inspection; private project read access | Dev/Root legacy entitlement or current feature group, plus existing project/capability constraints |
| Authorized Culvert service | Existing batch-bound browse credential remains sufficient for its existing artifact surfaces | Registered integration's existing verified credential and required operation scopes; no human-role requirement |

`batch_runner` and `culvert_runner` groups are workflow scopes. Their private grouped roots are admitted by the corresponding group and checked against the requested workflow/resource identifier, not by the PowerUser role. This does not grant access to unrelated private ordinary runs. Ordinary run children continue to apply their existing owner/resource boundaries. The current Batch public-base-run read exception is preserved; Culvert has no new public-root switch in this increment.

The default legacy operational path for Omni Contrasts, PATH-CE and AgFields is preserved, with additive group access. For OpenET, Batch and human Culvert workflow access, group-only behavior replaces broad role gates. Existing unrelated administrative powers and Root-only sensitive-path checks are unchanged. Group membership cannot override readonly, backend, capability or required token scopes.

Do not strengthen the general `authorize()` helper or create owner proof as part of FA-01. Preserve existing public and anonymous functionality, collaborator management and ordinary fork/archive/export behavior. Add a conditional entitlement check when a shared endpoint actually performs a restricted-feature action, operates on an internal Batch/Culvert workflow resource, or reads/copies embargoed data. Merely having a restricted mod on an ordinary project is not a reason to lock the entire project. Feature groups never confer Root/account administration or unrelated private-run access.

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

Principal resolution is token-class aware. A verified user token identifies its canonical account under the user-token contract. An authenticated session supplies a canonical `user_id` only through a verified human identity binding; session `sub`/`session_id` is never an account ID. Anonymous sessions remain anonymous; existing ordinary actions and public inspection need no new account resolution. Query current membership for protected human operations. JWT `groups` is informational; a stale token cannot retain a removed membership. Do not cache mutable membership in process-wide registry caches. Require existing JWT signature, audience, expiry, revocation, scope and run/session checks first. Do not treat service/MCP `sub` values as database user IDs unless their existing contract explicitly establishes that identity.

For restricted admission, session credentials derived from service/MCP tokens retain verified origin and resource limits; numeric `sub` or conversion to `token_class=session` creates no human group entitlement. Ordinary anonymous/session admission and existing scope bundles/TTLs remain unchanged. New derivatives carry signed `feature_access_principal={version:1,kind:human|integration|anonymous,id:<canonical ID or null>}`, populated only by trusted issuer adapters, never request payloads. This metadata is not a grant: live membership and existing resource/scope checks remain required. A legacy session may establish human origin through its own valid, non-tombstoned SID and live Flask session payload using existing identity resolution. Without that binding, require authenticated refresh/original user credentials for a restricted operation; do not invalidate the token for ordinary functionality. A session ID is never an account ID. Trusted command-bar MCP identities resolve via Flask-Security `fs_uniquifier`; trusted admin-run-token delegation resolves the originating canonical User ID. An independent integration ID must match the operator-owned registration described above. Unknown provenance is denied for restricted admission only.

Token class alone does not establish an independent service principal. Human-delegated credentials, including existing `admin-run-token:<user_id>` service tokens, retain a verified originating human binding and require that account's current membership for group-protected admissions, in addition to their resource/scope checks. Do not infer the binding from an arbitrary subject string; verify it against the inventoried trusted issuance contract. The independent Culvert integration and its returned browse credential keep their separately authorized service path. Inventory every service/MCP delegation and conversion before changing its boundary; no blanket service-class exemption and no new group right follow from conversion. Unrelated run-token minting permissions and TTLs remain unchanged.

Current membership applies to both user tokens and verified human-derived session tokens on private grouped reads and protected actions. Session resource claims are additive, not a membership exemption. Check the private Batch session bridge and consumers; neither an Admin/Root role nor an old session preserves removed group access. Preserve the public Batch read exception and separately authorized service path. Do not add new accepted token classes to existing endpoints.

Removal or expiration affects subsequent protected admissions. Jobs already admitted may finish; this increment neither cancels running/queued jobs nor adds worker-side permission rechecks. Their later reads obey the read policy. New retries, finalizers or submissions are new admissions. Explicit token revocation remains independently effective under current token contracts. No credential TTL changes are part of FA-01.

Membership-store failure returns an explicit unavailable response for an operation requiring membership; it must not grant access by falling back to PowerUser/Admin/Dev. Public non-embargoed inspection that needs no membership decision remains available under its existing read authorization. Preserve normal error envelopes (`rq-response-contract.md`) and existing CSRF/origin protections.

## UI and backend obligations

The Profile page provides the short PowerUser statement, the two yes/no answers, and current status. Submission is authenticated, CSRF-protected and idempotent. It does not allow selecting another account or role. Existing internal-group controls and private grouped-data protections must be ready before this form is enabled for general users.

An administrative group page provides membership add/remove with a required reason, optional review/expiry fields, and history. It does not expose other users' audit notes to public viewers. Users can inspect their own group status and complete the internal acknowledgment without a second maintainer approval.

Restricted-feature renderers and dynamic sections must distinguish readable from actionable state. Disable or omit mutation controls with a clear reason, preserve accessible labels, and enforce the same denial server-side. Disabled JavaScript is presentation, not authorization. Newly exposed inspect-only restricted-feature reads must not initialize their optional controllers or regenerate their protected artifacts; unrelated anonymous functionality is unchanged.

The complete surface inventory must cover direct routes, generic browse/download, query-engine/MCP, exports, archives, forks, child-run URLs, and orchestration reads that contain feature data. A mixed bundle or query must not bypass the retained embargo exception. Preserve existing readable non-embargoed artifacts; do not introduce blanket project denial merely because the project also contains a restricted feature. Use the finite protected-data classification and bundle rules below; no blanket denial applies to ordinary non-protected artifacts.

## Protected-data classification and mixed delivery

The retained embargo follows contrast data, not just the named HTML report. Protected representations are `omni/contrasts.out.parquet`, `omni/README.contrasts.md`, `omni/contrast_id_definitions.psv`, `omni/contrasts/**`, `_pups/omni/contrasts/**` and child-run aliases resolving there; contrast-specific fields in `omni.nodb`, PATH-CE results in `path_ce.nodb`, and structured status/config/dashboard payloads; and PATH-CE outputs derived from contrasts (`path/path_ce_*`, `path/selection.parquet`, `path/hillslope_sdyd.parquet`, `path/untreatable*.parquet`, `path/sweep.parquet`, `path/sweep_manifest.json`, `path/report/**`). Preserve ordinary scenario outputs and non-contrast project data. Trace resolved source identity across aliases/symlinks and derived response composition; copying/renaming does not make protected data public.

For callers lacking contrast entitlement, omit protected entries from navigable catalogs/listings, deny a directly requested protected object, and reject a query that references any protected dataset before execution. Mixed structured responses use explicit projection of non-protected fields; raw mixed NoDb files require entitlement, including `path_ce.nodb`; ordinary config/status projections may omit protected result fields. Deny an indivisible bundle containing protected material with an explicit authorization reason; never return a silently incomplete ZIP. Inspect existing archive membership/source classification before streaming, including HEAD/range and dedicated download. Ordinary bundles without protected material keep their existing admission and content. A fork/export retaining protected data needs its read entitlement and retains the same restriction at its destination; ordinary anonymous forks remain unchanged. Restore cannot shed source classification. No new artifact schema or generalized information-flow service is authorized.

Open job polling retains its existing admission mode and lifecycle/status/progress/queue fields. For unentitled callers, single and batch job-info must project protected contrast/PATH-CE results out of every returned node, including recursive children. For a wholly protected result payload, return `result: null`; mixed results retain only explicitly classified non-protected fields. Do not disclose protected result values through auxiliary metadata, descriptions or errors. Entitled callers retain the existing result shape; ordinary job results and Culvert client polling remain unchanged. The [RQ polling contract](rq-response-contract.md#fa-01-protected-job-results-specified-implementation-pending) owns this response projection.

A generic endpoint needs the additional feature check only for the requested protected operation/resource/data. Shared mutation entry points on `batch;;...`, Culvert child resources and contrast child aliases must enforce their corresponding workflow/contrast entitlement even when reached through bootstrap, generic WEPP execution or cancellation rather than the standalone workflow launcher. Ordinary run execution and incidental invalidation of PATH-CE timestamps/preflight are unaffected. GL dashboard contrast entries require the same read entitlement while ordinary scenario/dashboard content remains available. AgFields inspect-only state uses an observational projection rather than the existing reconciliation write path; authorized action/maintenance behavior is preserved. Entitled contrast-report callers may retain existing report generation; unentitled callers cannot generate or inspect embargoed data. The exact declared paths/handlers and acceptance cases are retained in the reviewed M0 matrix.

## Remaining implementation checkpoint

The current task prepares documentation only. Runtime work requires the bounded restricted-feature surface/state matrix, deployment-specific resolution of `rogerlew@gmail.com`, and the redacted Culvert integration inventory. The operator has excluded a new public-run writer/anonymous-creator boundary. These are explicit milestone-zero inputs, not permission to invent identities or silently alter supported workflows.

Independent correctness and security reviews of the prepared plan and findings disposition are recorded in the [review artifact](../work-packages/20261001_feature_access_governance/artifacts/2026-10-01_contract_reviews.md). The completed milestone-zero matrix passed independent correctness/security review; see the [final disposition](../work-packages/20261001_feature_access_governance/artifacts/2026-10-01_m0_reviews.md). Record the accepted ancestor in the package tracker before runtime work. The operational single-maintainer group decision is distinct from repository engineering reviews. PowerUser suspension, reapplication and permanent revocation do not block this increment. The unanswered proposal to expose embargoed results remains excluded; the existing restriction is retained.

## Proposed FA-01 web transport checkpoint

These routes are the milestone-zero reviewed transport target; no endpoint is implemented by this amendment. Paths are Flask-relative; external requests use the configured site prefix, normally `/weppcloud`. Retain the existing `/profile` and Root administration authentication behavior. New mutation endpoints require authenticated session cookies, standard CSRF validation and `application/json`; they do not accept bearer-token authentication as a substitute for the browser boundary.

| Method / path | Request | Successful response |
| --- | --- | --- |
| GET `/profile` | Existing authenticated profile request | Existing HTML augmented with current-user PowerUser state, current internal statement/version and own group status; no other users' audit reasons |
| POST `/profile/poweruser` | JSON `needs_poweruser: true`, `accepts_training: true`, `statement_version: <currently presented version>` | HTTP 200, `message` and `result` containing `status: granted`, `role_changed` boolean and accepted `statement_version` |
| POST `/profile/internal-access/acknowledge` | JSON `accepts_training: true`, `statement_version: <currently presented internal version>` | HTTP 200, `message` and `result` containing statement kind/version and `changed` boolean |
| GET `/admin/feature-access` | Authenticated Root | HTML group definitions, membership/status and append-only event history; no secret token material |
| POST `/admin/feature-access/memberships` | JSON `operation: add|remove`, canonical integer `user_id`, registered `group_key`, nonblank `reason`; add optionally includes UTC `review_at` / `expires_at` or null | HTTP 200, `message` and `result` containing `user_id`, `group_key`, effective `member` boolean and `changed` boolean |

POST success uses the synchronous `message`/`result` convention in the response contract, not legacy `Content`. Errors use `error.code`, `error.message` and human-readable `error.details`, with no traceback/account-secret disclosure. Unknown fields are rejected, so a client cannot inject actor, target role, approval rule, statement text or user ID into current-user acceptance. JSON booleans are strict; strings and omitted/false answers do not grant access. Statement text/version is server-owned and shown before acceptance.

Stable endpoint errors: 400 `validation_error` for invalid body, fields, answers, identifiers, reason or timestamps; 401 `unauthorized` for absent authentication; 403 `forbidden` for non-Root membership changes; 409 `statement_version_conflict` for a version different from the presented current statement; 503 `feature_access_unavailable` for unavailable required persistence. Existing CSRF middleware errors remain canonical; do not exempt new endpoints. Unknown target users/groups use a Root-only 400 validation response. Every 5xx response includes `error_id`, with server-side traceback/error context tagged by that ID; sanitized client errors do not suppress operator evidence. No partial membership, acceptance, role or audit commit may accompany an error.

Repeated acceptance of the same version does not duplicate its acceptance record. A successful PowerUser request still ensures the role is currently assigned in the same transaction; `role_changed` reflects actual role presence, never merely an old acceptance row. Do not return `status: granted` if the role is absent. This adds no suspension/reinstatement state or durable revocation rule. Existing PowerUsers retain their role without fabricated legacy acceptance; an explicit current acceptance can be recorded without a second role grant. Repeated add with the same effective membership and metadata, or remove of an absent membership, returns `changed: false`. Adding with conflicting metadata to an active membership returns 409 `membership_conflict`; use an explicit reasoned remove/add to replace it. An expired membership may be re-granted by add with a future expiry or no expiry and a new audit event. A review date alone never expires membership. Past expiry on a new/re-granted membership is invalid. Remove accepts no add-only date fields. Membership and event changes remain one transaction.

New endpoints do not mint Culvert integration credentials or add Culvert scopes to general profile tokens. The initial human Culvert operation path uses explicitly operator-issued user credentials with the existing operation scopes and current group membership, with the deployed submit-only service path recorded above. Public inspection requires neither these endpoints nor an internal acknowledgment.
