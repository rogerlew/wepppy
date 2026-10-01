# Implement feature access governance


This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`. Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective current. This plan is the active plan for the feature-access package only; it does not execute or close other active initiatives.

The operator requested a reconciled policy amendment and implementation plan. Those documentation deliverables are prepared. Runtime milestones below are future work: do not execute them before the required contract checkpoint and authority for implementation exist.

## Purpose and outcome


An ordinary authenticated user will be able to become a PowerUser by acknowledging the short training statement and answering the two policy questions. A maintainer will be able to give a named user one internal feature through group membership, recording the reason and times, without giving that user Dev/Admin/Root or requiring multiple reviewers. Anyone inspecting a public project will see its applicable existing non-embargoed feature state/results read-only; actions require separate permission.

OpenET and Batch have separate groups, initially containing only the requesting maintainer. Human Culvert access also becomes group-based, while its existing authorized long-lived service JWT continues to perform its explicitly inventoried operations. Maturity overrides stop promoting Experimental configurations to Preview merely because they use multiple OFEs. Public release of embargoed contrast data and PowerUser suspension/reapplication/permanent revocation are not included.

The target is faithful integration into existing workflows, not a disconnected authorization scaffold. A new model/helper is implemented but not wired until real render, execution, data and identity paths consume it. Closeout requires actual database and generated-output evidence, not only mocked tests or a successful job state.

## Progress


- [x] (2026-10-01 20:47 UTC) Assessed revision `45a39a8337d37c7f7d30087ff4d23c03610072b3`; retained 275 passing baseline tests in the assessment.
- [x] (2026-10-01 20:47 UTC) Recorded operator decisions and prepared FA-01 policy, canonical contract, ADR and shared-contract amendments.
- [x] (2026-10-01 20:47 UTC) Prepared this plan, tracker, surface inventory and pending review gates.
- [x] (2026-10-01 21:05 UTC) Documentation checks passed: 20 Markdown files linted, relative link targets resolved, diff whitespace clean, root AGENTS size 160/160. Spelling previews inspected; unrelated tracker prose retained.
- [x] (2026-10-01 21:13 UTC) Independent prepared-amendment reviews dispatched; four unique findings accepted and corrected in contracts. Both reviewers confirmed the fixes; completed milestone-zero review remains pending; see `artifacts/2026-10-01_contract_reviews.md`.
- [ ] Freeze exact endpoint/artifact matrix and resolve public write authority, anonymous creator compatibility, designated account and Culvert service inventory.
- [ ] Obtain independent contract reviews, disposition findings and record the standalone ancestor checkpoint revision.
- [ ] Implement additive account records, shared evaluator and direct persistence tests.
- [ ] Implement single-maintainer group UI and initial memberships with real readback evidence.
- [ ] Wire protected action/data admission and public inspection, including Culvert compatibility.
- [ ] Implement conservative maturity and PowerUser onboarding after restricted-data gates are ready.
- [ ] Complete real browser/model/artifact acceptance, independent reviews, and an operator-approved rollout plan.

## Surprises & Discoveries


The assessed role model is not linear: Dev does not imply Admin and Admin does not imply Dev. OpenET rendering allows Dev/Root while its execution endpoint requires Admin; Batch uses Admin gates despite Dev registry metadata. Test suites pass because these surfaces are exercised independently.

Profile-issued PowerUser JWTs last 90 days. Existing grouped browse tests allow PowerUser user tokens without a batch identifier claim to read Batch/Culvert fixtures. Adding a Profile button before reconciling grouped reads expands this existing audience.

There is no persisted user group model even though profile token issuance has a `groups` claim hook. Registry caches are process-wide and cannot become mutable membership caches. Culvert returns a separate seven-day batch-scoped browse token; it is not the long-lived submission/polling credential.

The current public-read helper `wepppy/weppcloud/utils/helpers.py:authorize` is not proof of write ownership. Its `require_owner` parameter is reserved rather than an enforced owner-only contract. Public readonly UI alone would leave direct write paths reachable; legitimate anonymous creators also need a defined writer identity before tightening them.

## Decision Log


2026-10-01, operator: use separate public inspection and action permission. Preserve the unanswered embargo exception rather than infer permission to disclose. A publication date does not certify model readiness or automatically change maturity.

2026-10-01, operator: single-maintainer group decisions replace multiple reviewer roles. Reason, actor, person, group scope and timestamps supply accountability. Engineering reviews required by repository standards are separate from this operational UX.

2026-10-01, operator: OpenET/Batch access is only the maintainer initially, enforced through normal feature groups. Preserve Culvert's legitimate service workflow; distinguish it from human membership. No hard-coded account gate or blanket role bypass.

2026-10-01, operator: use the least optimistic accurate maturity, and defer PowerUser suspension, reapplication and permanent revocation. Initial onboarding must not grow into an account-sanctions system.

2026-10-01, plan: use existing database/auth infrastructure and four logical record types. Membership removal affects future admissions; already-admitted jobs may finish. No worker permission rechecks, automatic job cancellation, new services, signing keys, token TTLs or queue topology are planned.

2026-10-01, review disposition: private grouped admission must check live membership for verified human sessions and human-delegated service credentials as well as user tokens. Token-class conversion must preserve provenance; independent Culvert credentials retain their explicit service path. Corrected UI entitlement and acknowledgment timing inconsistencies.

## Outcomes & Retrospective


Planning outcome: the policy and technical documents now have a consistent target, with the existing embargo exception explicit. Documentation received independent prepared-plan review and post-fix confirmation, but is not an accepted implementation checkpoint. No runtime files, users, memberships, credentials or deployment state were changed. The remaining milestone-zero work is concrete identity and boundary verification, not a return to dual-review governance or deferred PowerUser sanctions.

## Context and orientation


Work from `/home/workdir/wepppy` on the current branch; do not create/switch branches. Runtime inside the development container uses `/workdir/wepppy`. The controlling contract is `docs/schemas/feature-access-governance-contract.md`; governance is published at `wepppy/weppcloud/routes/usersum/weppcloud/feature-maturity-and-release-governance.md`, with ADR-0080 recording the amendment. Registry behavior belongs to `wepppy/weppcloud/feature_registry/specification.md`, `schema.py`, `runtime.py`, `feature_registry.yaml` and `config_registry.yaml`.

Accounts live in `wepppy/weppcloud/app.py`, using Flask-Security roles and SQLAlchemy. Migrations are in `wepppy/weppcloud/migrations/versions/`. User/profile routes are in `routes/user.py`; Root administration is in `routes/admin.py`. Proposed group logic belongs in `wepppy/weppcloud/utils/feature_access.py`, with lazy access to account models to avoid importing the Flask app during registry loading.

Run rendering/dynamic sections live in `routes/run_0/run_0_bp.py` and `routes/run_0/templates/runs0_pure.htm`; module mutations in `routes/nodb_api/project_bp.py`. Internal action paths include `routes/nodb_api/path_ce_bp.py`, `routes/nodb_api/omni_bp.py`, `routes/batch_runner/batch_runner_bp.py`, and rq-engine `openet_ts_routes.py`, `omni_routes.py`, `ag_fields_routes.py`, `batch_routes.py`, `upload_batch_runner_routes.py`, `culvert_routes.py`. Generic artifact reads use `wepppy/microservices/browse/`, dedicated download, query-engine, and archive/fork surfaces.

Read nearest AGENTS before implementation, including `wepppy/weppcloud/AGENTS.md`, feature_registry, controllers_js, rq_engine, tests and smoke-test instructions as applicable. Re-read `docs/standards/contract-first-change-standard.md`, the CSRF/session/response contracts and the current deploy entry point before planning any rollout mechanics. Existing closed packages remain evidence, never mutable authority.

## Milestone zero: close the technical contract checkpoint


Use `artifacts/2026-10-01_surface_inventory.md` to trace every public feature read and corresponding mutation, including GET handlers that mutate. Expand it to exact method/path/function entries with principal type, read/write evidence, feature entitlement, request/response expectations and tests. Trace generic files, query datasets, mixed archives, child/fork paths and PATH-CE's consumption of contrasts so the embargo exception cannot be bypassed by an alternate reader. Record how a mixed bundle behaves without denying unrelated public project views; do not invent a filename heuristic from one example.

Resolve the designated maintainer's canonical database account by verified account records/operator input; retain a reference, never a fabricated ID. Inventory the actual Culvert integration's owner, subject, credential identifier/fingerprint, audiences, scopes, expiry, resource claims, client consumers and revocation mechanism without copying a secret JWT. Exercise a non-mutating authenticated compatibility probe where available. The integration may have no human user identity; group changes must not reinterpret it as one.

For public actions, identify and document existing owner/authorized-writer and legitimate anonymous creator evidence. A read-scoped public session does not prove creator authority. If the current system cannot distinguish them, define and ratify the smallest writer-boundary amendment before code, preserving supported anonymous creation. Do not add a service or silently require new login behavior. Record absent/empty/populated/legacy/hostile states independently from role/request combinations. Freeze token-class-aware identity provenance across bearer-to-session conversions; anonymous sessions stay anonymous, and service/MCP subjects or conversion cannot manufacture a human account binding. Inventory any existing explicit delegation, including `routes/user.py:mint_run_token` and `admin-run-token:<user_id>` credentials: protected admission checks the verified originating human's current membership, not a blanket service-class exemption. Include valid human sessions, numeric service subjects matching a member ID, and service-derived role/group-looking claims.

Complete `artifacts/2026-10-01_contract_decision.md`, amending every newly implicated canonical contract. Resolve the existing PowerUser TTL-control OR-versus-ALL role mismatch only under its own cited contract; do not broaden it incidentally. Obtain two independent read-only technical contract reviews, disposition medium/high findings, and commit the checkpoint as a standalone ancestor when commit authority is available. Record its SHA and ancestry. Stop before runtime edits if any of these gates is incomplete. The current user's request is documentation preparation, not a command to proceed through the remaining runtime milestones.

Acceptance is a reviewable, exact matrix with no invented account/service identity, no unresolved public writer boundary, and an accepted ancestor revision. The already-authorized single-maintainer membership workflow does not require a second operational reviewer.

## Milestone one: additive records and shared decisions


Add bounded account models for `FeatureAccessGroup`, `FeatureAccessMembership`, `FeatureAccessEvent` and `OnboardingAcceptance` adjacent to the existing user models, using the repository's SQLAlchemy conventions. Groups use stable keys tied to registry metadata. Enforce unique current group/user membership and unique acceptance for user/statement kind/version. Store optional review/expiration dates; audit events snapshot actor, subject, group/effective scope, action, reason and UTC time. Do not cascade-delete event history on user/group removal. Keep old User IDs, role associations and runs untouched.

Author one additive Alembic migration against the actual current head, not a guessed revision. Validate empty-database and representative legacy upgrade states in an isolated test database. Seed group definitions idempotently; account membership initialization is a separate explicit operation using the verified maintainer ID and a recorded reason. No migration guesses an email or creates credentials. Plan database backup and readback before applying outside isolated tests.

In `utils/feature_access.py`, implement a shared evaluator with verified principal, feature spec, operation (`inspect` or `act`) and run/resource context, returning an explicit decision and reason. Keep framework response conversion at the Flask/FastAPI boundary. Reuse current database access patterns for non-Flask services; do not introduce an authorization HTTP service. Query live memberships when required, and preserve ordinary public read paths that need no membership lookup. Missing group definitions/configuration and database errors must be explicit denials/unavailability, not permissive role fallbacks.

Add registry fields `access_group` and `access_mode` as specified by FA-01. Group-only features are OpenET, Batch and human Culvert; Omni Contrasts, PATH-CE and AgFields permit the preserved Dev/Root path or current group membership. Public inspection is not evaluated by the action gate. PATH-CE actions that consume restricted contrasts need contrast entitlement too, with no automatic membership grant.

Acceptance uses direct real-database tests for atomic membership-plus-event commits, rollback on injected failure, concurrent duplicate adds/removes, preservation of history, expired/review-only memberships and old-token reads of current membership. Unit tests must also prove Root without OpenET/Batch membership is denied and a valid group member still needs run/write/backend/scope permission. This milestone alone does not enable new UI or claim runtime wiring.

## Milestone two: simple group administration and acknowledgment


Add the Root-protected group administration surface in `routes/admin.py` and a matching `templates/user/feature_access.html`, reusing existing Pure form/error patterns. Show group, current members and history; allow add/remove with a required reason and optional review/expiration fields. Registry controls feature mapping; the form cannot invent privileges or edit another role. Root administers membership but receives no implicit group-only action entitlement.

Use the proposed interfaces below as the concrete contract target, and register any necessary adjustment at the checkpoint. Mutation commits group state and its event together. User-facing status/acknowledgment belongs to the Profile surface: users see only their own memberships, can accept the versioned internal statement and see whether actions await acknowledgment. This is not another maintainer review. Legacy operational-role paths stay usable without a new acknowledgment gate.

Initialize OpenET and Batch groups with the verified maintainer as the sole member, retaining audit evidence. Other additions require a named decision rather than a bulk role-to-group migration. No nested groups, delegated administration hierarchy or reviewer queue is included.

Acceptance is a real browser/database round trip: Root adds a named collaborator to one feature group, user acknowledges if required, action entitlement becomes available, and removal changes future admissions while history remains. Non-Root mutation, forged CSRF, unknown group/user, blank reason and cross-account acknowledgment are rejected without partial state. Keyboard navigation and labeled errors must work.

## Milestone three: wire actions, data and public read-only views


Wire the evaluator across the frozen matrix, including run context, dynamic sections and toggles; direct internal acquisition/build/configuration/report paths; Batch management/upload/run; and private grouped browse/download, including private Batch session issuance and live membership checks when human-derived sessions are consumed. A resource-scoped session or broad role is not a group exemption. Test valid member sessions, removed-member stale sessions, Admin/Root sessions without membership and the public Batch exception. Repeat protected Batch admission cases for trusted human-delegated service tokens, including removal with an old token; preserve independent Culvert integration/browse compatibility and unrelated minting behavior. Preserve caller authentication, JWT scopes, run ownership, same-origin/CSRF, readonly and scientific capability checks. Separate public views from action controls without mutating optional NoDb state on read. Match service error envelopes and retain safe denial reasons.

Address OpenET and Batch's hard-coded Admin checks with group-only admission, PATH-CE/AgFields missing feature checks, Omni's hard-coded role checks and the frozen generic data paths. Preserve the currently authorized Culvert submitting service and its seven-day batch artifact credential. Test submit/retry/finalize/poll/cancel/browse/download separately because the credentials and resource scopes differ. Do not grant service rights by inserting a human into a group.

Apply the existing embargo exception to exact artifact/report/query paths registered in milestone zero, including retained/forked data and bundled downloads. Keep normal public non-embargoed views usable. Mutation authorization applies even when an action endpoint uses a misleading safe verb; correct method/CSRF behavior only within the accepted route contract. Already-admitted work may finish; membership changes do not rewrite persisted mod state or cancel jobs.

Acceptance traverses real application boundaries for anonymous public readers, ordinary users, group members/nonmembers, each technical role individually, and the actual class of service token. A public read of never-used optional state creates no files/jobs. Denied direct calls enqueue nothing. A stale user JWT loses protected group access after removal. Private data is unavailable through broad PowerUser claims. Existing authorized service artifact download remains byte-correct.

## Milestone four: conservative maturity and PowerUser onboarding


Implement the bounded multi-OFE rule in registry runtime/schema as needed: Stable/Preview becomes/remains Preview, Experimental/Internal/Deprecated remains declared. Update its tests and user-facing description without changing scientific configuration values. A real loader readback must show both Revegetation MOFE variants remain Experimental.

Add the versioned training statement and two-question form to the Profile page. Use a CSRF-protected authenticated POST that binds to the current account, requires both boolean answers true, records acknowledgment plus automatic approval atomically, and assigns only PowerUser. A current PowerUser or repeated successful request returns the already-approved state without invented historical acceptance or duplicated grants. Preserve unrelated roles and token-mint restrictions.

Do not enable the self-service UI before milestone three proves grouped-data boundaries. Do not add suspension, reinstatement, permanent revocation states or new eligibility questions. Existing role-management controls remain, without claiming that manual removal is a permanent bar to future onboarding.

Acceptance: a normal user can complete onboarding and use a PowerUser workflow, yet cannot execute internal features or inspect private Batch/Culvert data through a freshly minted user token. No/absent answers and forged user/role fields cannot grant privileges. Legacy PowerUsers keep their existing non-internal capabilities. The current scoped token and role tests remain meaningful rather than being replaced with literal assertions of the new implementation.

## Milestone five: complete acceptance and rollout preparation


Run appropriate focused tests while iterating, then the substantive-change Python/frontend gates below once the implementation is stable. Obtain independent correctness/UX and security reviews using repository templates, with direct evidence at database, auth and generated-artifact boundaries. No medium/high findings may remain unresolved at implementation closeout.

Use a production-equivalent test environment and a bounded approved real workflow to demonstrate intent, persisted membership/configuration, prepared inputs, exact executing identity/revision, fresh outputs, report rendering and read-only sharing. Keep API/compute costs within the operator-approved test boundary; fixtures cannot establish live OpenET/service compatibility. Retain browser and artifact evidence without credentials or unnecessary personal data. Confirm archived/restored results preserve the agreed read policy.

Prepare rollout only after inspecting the canonical deploy entry point and nearest operator docs. Stage additive schema before dependent service code; complete private-data enforcement across consumers before opening self-service. Coordinate relevant services so older consumers cannot admit a new group principal under a broad-role fallback. Rollback disables new admissions and preserves membership/event records; it must not restore an overbroad grouped-data path for newly promoted users. Never drop audit tables or rotate tokens as a rollback shortcut.

The current documentation task does not deploy. Record implemented, locally validated, environment validated and deployed separately. Close the package only at its explicitly authorized evidence level, updating tracker and PROJECT_TRACKER while leaving canonical policy outside the package.

## Concrete steps and validation commands


For documentation preparation, run the following from the repository root and expect no documentation errors. Preview spelling changes before applying them.

    wctl doc-lint --path docs/schemas/feature-access-governance-contract.md
    wctl doc-lint --path docs/work-packages/20261001_feature_access_governance
    wctl doc-lint --path wepppy/weppcloud/feature_registry/specification.md
    tools/check_agents_size.sh AGENTS.md

For database work, first inspect the migration graph with the canonical Flask app in an isolated test database. The existing wrapper command is `wctl exec -T weppcloud flask --app wepppy.weppcloud.app db upgrade`; do not run it against the shared/deployed database merely because it appears here. Add actual database upgrade/rollback tests and read back membership/event rows through normal readers.

Existing focused entry points include:

    wctl run-pytest tests/weppcloud/routes/test_feature_registry_runtime.py tests/weppcloud/routes/test_project_bp.py tests/weppcloud/routes/test_run_0_openet_admin_gate.py tests/weppcloud/routes/test_admin_usermod_contract.py tests/weppcloud/routes/test_user_profile_token.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_path_ce_bp.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_batch_runner_create_route.py --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_openet_ts_routes.py tests/microservices/test_rq_engine_omni_routes.py tests/microservices/test_rq_engine_ag_fields_routes.py tests/microservices/test_rq_engine_batch_routes.py tests/microservices/test_rq_engine_upload_batch_runner_routes.py tests/microservices/test_rq_engine_culverts.py tests/microservices/test_browse_auth_routes.py --maxfail=1

Add dedicated evaluator, real database, Profile/group route and public-view tests alongside these modules. Existing tests that mock the permission boundary are not direct conformance evidence. Final code gates are:

    wctl run-pytest tests --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl check-test-stubs

Run affected stubtest modules if public Python surfaces/stubs change. Rebuild controllers with the nearest AGENTS instructions if controller sources change. Run `wctl check-rq-graph` and inspect live job trees only if enqueue wiring changes; no such topology change is planned. Do not rerun the broad suite for this documentation-only preparation.

## Interfaces and dependencies


The proposed web interfaces are `GET /profile` for onboarding/status, `POST /profile/poweruser` for current-user approval, `POST /profile/internal-access/acknowledge` for current-user internal statement acceptance, `GET /admin/feature-access` for Root administration/history, and `POST /admin/feature-access/memberships` for Root add/remove. The membership body has an explicit operation, canonical user ID, group key, nonempty reason and optional review/expiry timestamps. User-facing acceptance endpoints never accept a target account or arbitrary role. Freeze transport encoding and exact success/error payloads in milestone zero under the existing response/CSRF contracts before implementing.

The access module should expose an inspect/action evaluator and transactional membership/onboarding functions; use one result shape containing `allowed`, stable `reason`, and the entitlement basis useful for audit. Raw bearer tokens never enter database events or logs. Static registry loading remains independent of SQLAlchemy; database lookup and framework principal translation occur at request boundaries. Use current service database adapters rather than new network protocols.

## Idempotence, recovery and retained artifacts


Duplicate onboarding/add/remove requests must not create duplicate grants. Database failure rolls back both authorization state and its event. Additive migrations preserve existing account/run/role rows and do not backfill false acknowledgments. Account/group removal retains historical identifiers and scope snapshots. Membership-store failure is explicit; no missing dependency is masked by a permissive fallback.

Retain checkpoint SHA, reviewed surface/state matrices, redacted identity inventory, migration readback, direct denial/no-side-effect evidence, service compatibility, browser screenshots/results and generated-output manifests under this package's artifacts. Record residual scope limits rather than claiming complete parity from a green suite. Reconcile links and living sections after every milestone.

Revision note, 2026-10-01: created for the operator-requested policy amendment and plan. Runtime milestones are deliberately gated on a reviewed ancestor, verified identities and concrete public-writer authority; PowerUser sanctions remain excluded.
