# Implement feature access governance


This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`. Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective current. This plan is the active plan for the feature-access package only; it does not execute or close other active initiatives.

The operator requested the amendment and plan, then authorized committing review fixes and executing milestone zero. Review fixes were committed as `36f35b6f0`; milestone-zero source investigation is recorded in `artifacts/2026-10-01_milestone_zero.md`. The accepted ancestor is recorded below, and the operator authorized milestone one (committed as `62ce1af3f`) milestone two (committed as `c19fefcc6`) and now milestone three. Milestones four and five remain future work.

## Purpose and outcome


An ordinary authenticated user will be able to become a PowerUser by acknowledging the short training statement and answering the two policy questions. A maintainer will be able to give a named user one internal feature through group membership, recording the reason and times, without giving that user Dev/Admin/Root or requiring multiple reviewers. Users lacking a limited feature's action entitlement can inspect shared retained state/results read-only, including contrasts and derived PATH-CE outputs under FA-02. Anonymous creation and ordinary functionality remain unchanged; no global public-writer gate is introduced.

OpenET and Batch have separate groups, initially containing only the requesting maintainer. Human Culvert access also becomes group-based, while its existing authorized long-lived service JWT continues to perform its explicitly inventoried operations. Maturity overrides stop promoting Experimental configurations to Preview merely because they use multiple OFEs. Permitted users may share generated results broadly under normal resource-sharing rules. Feature operation remains restricted; PowerUser suspension/reapplication/permanent revocation are not included.

The target is faithful integration into existing workflows, not a disconnected authorization scaffold. A new model/helper is implemented but not wired until real render, execution, data and identity paths consume it. Closeout requires actual database and generated-output evidence, not only mocked tests or a successful job state.

## Progress

- [x] (2026-10-02 UTC) Milestone three complete locally at candidate `23c2f27fe`: shared principal adapters, restricted action/data wiring, read-only views, regression and independent review.
- [x] (2026-10-02 UTC) Added live identity/group adapters and initial direct action, grouped delivery, catalog, export and recursive polling enforcement. Isolated PostgreSQL plus signed OpenET route admission proves acknowledgment and old-token removal before mutations.
- [x] Operator resolved the sharing policy: internal/embargo restricts feature operation; permitted users may share outputs broadly. Fork classification/refusal is no longer required for a result embargo.
- [x] Prepare FA-02 canonical amendments and independent reviews; all contract findings independently closed, documentation/links/whitespace checks passed.
- [x] Commit standalone FA-02 checkpoint `102c81066` before runtime edits.
- [x] Reconcile FA-02 shared reads, remove feature-derived file/result classification and ancestry gates, preserve action/private checks; independent bounded review findings closed.
- [x] Reproduce S04/S08 on disposable synthetic private files; both remain real private-resource defects.
- [x] Commit reviewed FA-02 sharing reconciliation as `5d4f199e6`.
- [x] (2026-10-02 UTC) Remediate S04 by binding only admitted catalog sources into DuckDB and disabling external access before caller expressions execute; retained private-file canary denied.
- [x] Remediate S08 with per-dataset visibility metadata and scoped downstream admission while retaining anonymous public D-Tale; retained anonymous canary denied.
- [x] Obtain independent correctness/security disposition of S04/S08 containment; PRC01–PRC10 and PRS-01–PRS-04 closed with zero unresolved findings.
- [x] Complete the stable affected microservice/query/WEPPcloud regression: 3,468 passed, 2 skipped.
- [x] Complete full-repository regression (10,246 passed, 126 skipped, 12 subtests passed) and M3 private-resource service/browser acceptance against the exact candidate revision; production remains unchanged.

- [x] (2026-10-02 UTC) Milestone-two account UI, acknowledgment and atomic initializer implemented; focused PostgreSQL/browser acceptance and independent reviews pass.
- [x] (2026-10-02 UTC) Local shared database backed up, test-restored, migrated and initialized for the verified sole maintainer; production unchanged.
- [x] (2026-10-02 UTC) Full Python regression: 10,198 passed, 126 skipped; milestone-two validation and handoff complete.

- [x] (2026-10-01) Milestone one complete: additive records/migration, shared decisions, PostgreSQL acceptance and independent reviews.


- [x] (2026-10-01 20:47 UTC) Assessed revision `45a39a8337d37c7f7d30087ff4d23c03610072b3`; retained 275 passing baseline tests in the assessment.
- [x] (2026-10-01 20:47 UTC) Recorded operator decisions and prepared FA-01 policy, canonical contract, ADR and shared-contract amendments.
- [x] (2026-10-01 20:47 UTC) Prepared this plan, tracker, surface inventory and pending review gates.
- [x] (2026-10-01 21:05 UTC) Documentation checks passed: 20 Markdown files linted, relative link targets resolved, diff whitespace clean, root AGENTS size 160/160. Spelling previews inspected; unrelated tracker prose retained.
- [x] (2026-10-01 21:13 UTC) Independent prepared-amendment reviews dispatched; four unique findings accepted and corrected in contracts. Both reviewers confirmed the fixes; completed milestone-zero review remains pending; see `artifacts/2026-10-01_contract_reviews.md`.
- [x] (2026-10-01) Committed review disposition `36f35b6f0`; traced 239 route declarations, credential paths, missing anonymous creator proof and artifact side effects. Bounded source/transport review fixes independently confirmed.
- [x] (2026-10-01) Operator clarified feature-only read-only scope, designated rogerlew@gmail.com and wepp2 Culvert client; verified local/production account and redacted credential metadata.
- [x] (2026-10-01) Prepared bounded route/data/principal/transport matrix; expired configured Culvert token recorded as later live-acceptance dependency.
- [x] (2026-10-01) Independent correctness/security reviews accepted the narrowed matrix after fixes; zero unresolved High/Medium findings, recorded in `artifacts/2026-10-01_m0_reviews.md`.
- [x] (2026-10-01) Accepted standalone contract ancestor: `d3639f970669411e9c0f5bf8e80898645c947559`; M0 complete.
- [x] (2026-10-01) Implemented additive account records/migration, shared evaluator and direct PostgreSQL persistence tests; final account/registry run passed 180 cases.
- [x] Implement single-maintainer group UI and local initial memberships with real readback evidence.
- [x] Wire protected action/data admission and public inspection, preserving the inventoried Culvert credential contract and recording its expired deployed credential as a rollout dependency.
- [x] (2026-10-02 UTC) Implement conservative multi-OFE maturity and atomic, current-user PowerUser onboarding after M3 private boundaries; isolated browser/token acceptance passes.
- [x] (2026-10-02 UTC) Complete M4 focused/frontend/full regression: 275 focused tests; 112 Jest suites / 919 tests; full repository 10,267 passed with 126 skipped.
- [ ] Complete real browser/model/artifact acceptance, independent reviews, and an operator-approved rollout plan.

## Surprises & Discoveries

Historical M3 discovery under FA-01 (reassess under FA-02): checking declared query datasets does not constrain file reads inside SQL expressions. Installed DuckDB 1.1.1 rejects `allowed_paths`; disabling external access also prevents ordinary prebound Parquet views from scanning. No dependency was changed. D-Tale's launch guard does not protect its separately served cached datasets; the existing in-process service needs a live downstream admission design and service/browser acceptance. Contrast-child forks lose their protected path and lack durable archive-surviving lineage; FA-01 currently forbids a new artifact schema. FA-02 removes the feature-derived result embargo and therefore the fork-lineage requirement. SQL/D-Tale access to genuinely private resources still requires reassessment; do not retain contrast-only mitigations or declare actual privacy defects fixed by changing policy.

S04 containment prototype: DuckDB 1.1.1 can query a registered
`pyarrow.dataset.Dataset` after `enable_external_access=false`, while a direct
`read_parquet('/private/path')` fails with `PermissionException`. This preserves
lazy Arrow scanning of admitted Parquet sources and closes expression-level file
access without parsing away legitimate scalar subqueries. Spatial sources need
a trusted `pyogrio.read_arrow` adapter because DuckDB external access is disabled
before caller SQL; its GeoArrow metadata must be converted to ordinary WKB and
wrapped with `ST_GeomFromWKB`.

S08 uses the existing D-Tale internal secret for a 60-second launch ticket and
one-hour viewer cookie, while the existing Redis and Postgres secrets support
live revocation/session and group-membership checks. Viewer identity belongs to
each opaque capability rather than shared dataset metadata. Upstream D-Tale
stores tables and GeoJSON in process-global registries and reuses numeric derived
IDs, so the integration guards lookup/list, structured merge references,
derivative propagation, cleanup/ID reuse and uploaded-overlay provenance. This
preserves authorized private maps and anonymous public tables without a universal
D-Tale login.

Production-equivalent M3 acceptance exposed three integration gaps hidden by
mocked boundaries. The shared UI token issuer used Flask-Security's opaque
`fs_uniquifier` as `sub`, while the trusted principal adapter requires the
numeric account ID. Browse and Query Engine did not receive all existing
database/token secrets needed by their newly wired live checks. Finally, a
clean private-only D-Tale process could not use upstream `build_main_url()`
before setting its capability cookie because the guarded key list was correctly
empty. The exact candidate now uses numeric user subjects, explicit
Redis/Postgres startup dependencies and required existing secrets, and a
verified/double-quoted private dataset redirect.

The full-suite gate also exposed a test-isolation defect rather than a runtime
authorization failure. `rq_engine.auth` captures its Redis constructor at import
time, before the session Redis stub is installed during full collection. The M1
signed-token test patched the module attribute but not that captured constructor,
so its fork-preparation check contacted real Redis and failed authentication.
The test now replaces the captured constructor explicitly; the all-collection
reproduction and complete suite pass without changing production behavior.

Milestone two: a stale Flask-Security session can fall through to token authentication; session presence alone is insufficient. The adapter verifies resolved session provenance and identity binding. Inactive pre-grants need effective status read inside the write transaction. Axe identified two low-contrast navigation links, fixed by existing button styles. A `public`-only backup omits `pg_trgm`; test restore caught missing Usersum index operators, and an archive explicitly including the extension restored successfully. The web module uses qualified Flask imports so stubtest does not inspect context-bound proxies.

Milestone one: the run catalog already uses shared SQL metadata without constructing Flask, so the new account records follow that precedent. Database waits can cross an expiry boundary; admission uses PostgreSQL wall-clock time and grants sample UTC after row locks. The autouse test-secret fixture clears deployed password-file settings, so isolated PostgreSQL tests capture the configured URI before that fixture, as existing catalog tests do.


The assessed role model is not linear: Dev does not imply Admin and Admin does not imply Dev. OpenET rendering allows Dev/Root while its execution endpoint requires Admin; Batch uses Admin gates despite Dev registry metadata. Test suites pass because these surfaces are exercised independently.

Profile-issued PowerUser JWTs last 90 days. Existing grouped browse tests allow PowerUser user tokens without a batch identifier claim to read Batch/Culvert fixtures. Adding a Profile button before reconciling grouped reads expands this existing audience.

There is no persisted user group model even though profile token issuance has a `groups` claim hook. Registry caches are process-wide and cannot become mutable membership caches. Culvert returns a separate seven-day batch-scoped browse token; it is not the long-lived submission/polling credential.

Source investigation found no durable anonymous creator proof, but the operator explicitly rejected a new public-writer/creator boundary: only limited-feature access changes. Preserve anonymous creation and functionality. Account identity is deployment-specific (local 1, production 12 for the designated email). Culvert's configured submit-only token signature matches production but expired September 1; do not rotate or bypass expiry as part of governance implementation.

## Decision Log

2026-10-02 UTC, M3 service acceptance: user JWT `sub` is the positive numeric
account ID used by the live account principal adapter; `fs_uniquifier` remains a
session identity and is not an authorization subject. Browse, D-Tale and Query
Engine mount the existing Postgres secret and retain Redis startup ordering;
Query Engine also mounts the existing WEPP verification secret for its
browser-facing routes while MCP signing remains separate. A private D-Tale
launch constructs only the already-verified dataset main path using D-Tale's
own quoting after signed-ticket and live-capability checks. No new secret,
service or trust class is introduced.

2026-10-02 UTC, S04 implementation: replace generated filesystem table
functions with opaque registered source relations carried in `QueryPlan`.
Resolve and authorize exact catalog paths before execution, register Parquet as
lazy Arrow datasets and supported vector files as trusted Arrow/WKB sources,
then disable DuckDB autoload/autoinstall and all external access before executing
the generated statement. Reject `ST_Transform` in caller SQL because PROJ reads
`+nadgrids` paths outside DuckDB's external-access switch. Preserve ordinary SQL
expressions and scalar subqueries over registered relations. No DuckDB upgrade,
new dependency or service topology is introduced.

2026-10-02 UTC, S08 implementation: trusted browse admission sends the current
resource-public bit to the existing authenticated D-Tale loader. Fail closed
when the field is absent. Public datasets keep their current anonymous viewer
behavior. Private datasets use capabilities signed by the already-shared
internal token, are hidden from name/enumeration access, and propagate scope to
derived IDs. Each capability retains its own verified principal, rechecks JWT or
session expiry/revocation and current run/group authorization on every request,
and is removed on expiry or dataset discard. Retain private map support behind
the same live viewer capability by filtering D-Tale's process-global GeoJSON
lookup/list boundary, including public-to-private transitions. Mount the existing
Postgres secret in D-Tale so current group membership can be evaluated;
the existing Redis secret supports token/session revocation checks. The one-hour
viewer TTL is an upper bound and requires relaunch after expiry.

2026-10-02 UTC, FA-02: the operator clarified that internal/embargo status prevents unauthorized feature use, while permitted users may share results broadly. Amend canonical policy/ADRs and consumer contracts before code. Retire feature-only result classification, copied-output embargo, contrast selectors/report read gates and polling redaction. Preserve restricted actions, private project/grouped-resource boundaries and sensitive files. Reading existing contrast inputs does not require permission to execute contrasts; invoking that dependency does. The earlier fork and DuckDB questions are superseded insofar as they sought to enforce a result embargo. No dependency upgrade or universal D-Tale login requirement is authorized.

2026-10-02 UTC, M3 review disposition in progress: preserve legacy `?pup=` classification, classify effective catalog filesystem sources and raw mixed catalog/ZIP representations, and project propagated child errors without breaking missing-job children. Resolve membership from current account records, never from broad JWT roles. Keep the fork marker/refusal choice and dependency evaluation pending explicit operator answers; do not interpret a generic continuation as either decision.

2026-10-02 UTC, milestone-three compatibility plan: preserve ordinary anonymous workflows and existing scopes, token lifetimes, run authorization and job topology. Add signed origin metadata only at trusted issuers; read current account/group state for protected admissions. Wire finite artifact classification before self-service onboarding. Validate denied requests before writes/enqueues and retained public views without optional NoDb initialization. No account/data migration, production activation or credential renewal is included.

2026-10-02 UTC, milestone four: treat the existing `multi-ofe-is-preview` rule
as a Preview ceiling rather than a universal replacement. Publish the policy's
PowerUser statement as `poweruser-2026-10-01`; bind approval to the current
active session account and server-owned PowerUser role/rule. Existing
PowerUsers retain their role without fabricated acceptance. No sanctions state,
internal membership, scope expansion, migration or deployment is included.

2026-10-02 UTC, milestone two: publish the policy's unchanged internal onboarding text as `internal-2026-10-01`; use existing Pure forms/tables and explicit read errors. Record inactive-account pre-grants without effective entitlement. Both initial groups and events share a transaction, and initialization refuses conflicting decisions. Apply the accepted migration and audited initial memberships to local development after verified restore/readback; do not restart services or alter production. Group-based acknowledgment remains a personal action, not fabricated by initialization.

2026-10-01, milestone two compatibility plan: add session/CSRF-protected administration and current-user acknowledgment without changing role assignment, ordinary project behavior, or protected feature endpoints. Reuse User Management tables, Preferences Pure form macros and inline status patterns. Validate real PostgreSQL transactions, browser rendering and evaluator transitions in isolated schemas; production migration/initialization remains a rollout operation with backup/readback, not an implicit deployment.

2026-10-01, milestone-one implementation: use one additive migration after actual head `d30c91a7b802`, initialize only six group definitions, and keep membership initialization separate. Root-checked membership writes own a transaction and lock the subject account row; events snapshot feature IDs/access modes and retain identifiers without cascading deletion. Operational downgrade refuses to drop audit history; rollback disables consumers.


2026-10-01, operator: use separate public inspection and action permission. Preserve the unanswered embargo exception rather than infer permission to disclose. A publication date does not certify model readiness or automatically change maturity.

2026-10-01, operator: single-maintainer group decisions replace multiple reviewer roles. Reason, actor, person, group scope and timestamps supply accountability. Engineering reviews required by repository standards are separate from this operational UX.

2026-10-01, operator: OpenET/Batch access is only the maintainer initially, enforced through normal feature groups. Preserve Culvert's legitimate service workflow; distinguish it from human membership. No hard-coded account gate or blanket role bypass.

2026-10-01, operator: use the least optimistic accurate maturity, and defer PowerUser suspension, reapplication and permanent revocation. Initial onboarding must not grow into an account-sanctions system.

2026-10-01, plan: use existing database/auth infrastructure and four logical record types. Membership removal affects future admissions; already-admitted jobs may finish. No worker permission rechecks, automatic job cancellation, new services, signing keys, token TTLs or queue topology are planned.

2026-10-01, review disposition: private grouped admission must check live membership for verified human sessions and human-delegated service credentials as well as user tokens. Token-class conversion must preserve provenance; independent Culvert credentials retain their explicit service path. Corrected UI entitlement and acknowledgment timing inconsistencies.

2026-10-01, operator clarification: only limited-access features become read-only for unentitled users. Ordinary anonymous behavior stays unchanged; earlier writer/creator proposals are withdrawn. The designated account is rogerlew@gmail.com, resolved per deployment; Culvert client is on wepp2.

## Outcomes & Retrospective

M3 is complete locally at runtime candidate `23c2f27fe`; its service dependency
and numeric-subject checkpoint is `03fc3eae6`. FA-02 shared-result
reconciliation is committed as `5d4f199e6` against reviewed standalone contract
ancestor `102c81066`. The final stable affected microservice/query/WEPPcloud
suite passed 3,468 cases with 2 skips. Frontend lint and all 112 Jest suites /
919 tests passed; Compose rendering, test-stub checks and broad-exception
enforcement passed. The final full Python suite passed 10,246 tests with 126
skipped and 12 subtests passed in 2,668.41 seconds (44:28).

The [service/browser acceptance](../../artifacts/2026-10-02_m3_service_browser_acceptance.md)
exercised the exact candidate through Caddy with production service processes,
identities, mounts, Redis and PostgreSQL. It proved private D-Tale admission,
immediate membership revocation/restoration, anonymous public-table continuity,
declared Query Engine reads and denial of undeclared external sources. Synthetic
fixtures were removed and the designated account remained the sole active Batch
member. The [final correctness and security reviews](../../artifacts/2026-10-02_m3_final_reviews.md)
report zero unresolved High, Medium or Low findings. The historical
[interim M3 security review](../../artifacts/2026-10-02_m3_security_review.md)
is superseded for the final candidate by that review record.

The full-repository regression result is recorded in the acceptance artifact
and tracker. No production activation, credential renewal or dependency upgrade
occurred. The deployed Culvert credential remains expired, so renewal and a
positive live compatibility run are rollout gates rather than M3 source gaps.
Milestone four is next.

Milestone two: Root management/history, own Profile status and versioned acknowledgment, strict session/CSRF mutations, and the atomic sole-maintainer initializer are implemented. PostgreSQL acceptance passed 75 cases; final route regressions passed 73. Full-app browser acceptance passed with real sessions/database, evaluator denied/denied/allowed/denied transitions, retained events, keyboard/error focus and zero axe violations. Both independent reviews have zero unresolved findings. Local migration/initialization readback shows two memberships, two audit events, zero acceptances and unchanged legacy counts. Frontend lint and 112 Jest suites/919 tests pass; store/web stubtest and stub checks pass. Broad Python regression passed: 10,198 passed, 126 skipped in 2,535.69 seconds; final qualified-import/export cleanup also passed the 73-case route rerun and web stubtest. See [M2 acceptance](../../artifacts/2026-10-01_m2_acceptance.md); M3 enforcement and production rollout remain future work.

Milestone-one implementation: four account models, definition-only additive migration after `d30c91a7b802`, live membership store with atomic retained events, explicit shared decisions and required six-feature metadata are implemented. Independent correctness/security reviews closed three Medium findings (dependency error propagation, expiry after waits, omitted metadata role fallback). The final focused account/registry suite passed 180 cases; the full Python suite passed (10,149 passed, 126 skipped). It started before the final metadata guard; the final guard is covered by the 180-case rerun. All three new modules passed stubtest, and stub/doc/link/whitespace checks passed. No routes/UI, shared schema, maintainer memberships or credentials were changed.


Milestone-zero outcome: bounded source, transport, identity and deployed credential evidence are prepared. Final narrowed-scope reviews passed after fixes; accepted ancestor `d3639f970669411e9c0f5bf8e80898645c947559` closes milestone zero. The existing expired Culvert credential prevents positive live integration acceptance until operator renewal; it does not justify new auth policy, token rotation or wider scope. At milestone zero, runtime files, accounts, memberships and credentials remained unchanged.

## Context and orientation


Work from `/home/workdir/wepppy` on the current branch; do not create/switch branches. Runtime inside the development container uses `/workdir/wepppy`. The controlling contract is `docs/schemas/feature-access-governance-contract.md`; governance is published at `wepppy/weppcloud/routes/usersum/weppcloud/feature-maturity-and-release-governance.md`, with ADR-0080 recording the amendment. Registry behavior belongs to `wepppy/weppcloud/feature_registry/specification.md`, `schema.py`, `runtime.py`, `feature_registry.yaml` and `config_registry.yaml`.

Accounts live in `wepppy/weppcloud/app.py`, using Flask-Security roles and SQLAlchemy. Migrations are in `wepppy/weppcloud/migrations/versions/`. User/profile routes are in `routes/user.py`; Root administration is in `routes/admin.py`. Proposed group logic belongs in `wepppy/weppcloud/utils/feature_access.py`, with lazy access to account models to avoid importing the Flask app during registry loading.

Run rendering/dynamic sections live in `routes/run_0/run_0_bp.py` and `routes/run_0/templates/runs0_pure.htm`; module mutations in `routes/nodb_api/project_bp.py`. Internal action paths include `routes/nodb_api/path_ce_bp.py`, `routes/nodb_api/omni_bp.py`, `routes/batch_runner/batch_runner_bp.py`, and rq-engine `openet_ts_routes.py`, `omni_routes.py`, `ag_fields_routes.py`, `batch_routes.py`, `upload_batch_runner_routes.py`, `culvert_routes.py`. Generic artifact reads use `wepppy/microservices/browse/`, dedicated download, query-engine, and archive/fork surfaces.

Read nearest AGENTS before implementation, including `wepppy/weppcloud/AGENTS.md`, feature_registry, controllers_js, rq_engine, tests and smoke-test instructions as applicable. Re-read `docs/standards/contract-first-change-standard.md`, the CSRF/session/response contracts and the current deploy entry point before planning any rollout mechanics. Existing closed packages remain evidence, never mutable authority.

## Milestone zero: close the technical contract checkpoint

Historical M0 scope (FA-02 supersedes its feature-derived read restrictions): use the declarations and admission classifications in `artifacts/2026-10-01_route_inventory.tsv`, the resource/data matrix in `artifacts/2026-10-01_milestone_zero.md`, and `artifacts/2026-10-01_credential_matrix.md`. Scope is limited-feature admission and protected data: preserve ordinary anonymous creation, editing, session flows and model work. Do not add a general writer/owner gate, creator credential or legacy-recovery process. Existing project readonly and narrower authenticated-only contracts remain as they are.

The operator specified `rogerlew@gmail.com` on every deployment. Read-only lookup verified local ID 1 and wepp1 ID 12, both active; use per-deployment lookup only for seeding, never request authorization. The Culvert client is `/workdir/Culvert_web_app` on wepp2. Its configured submit-only service credential has no run claims; actual wepp1 validation verified its signature and rejected its September 1 expiry. Preserve independent service admission, existing open polling and returned seven-day batch browse tokens. No renewal is authorized. A successful live compatibility run is a later prerequisite after the operator repairs the expired credential; the documented expiration is not a reason to bypass validation or block this design checkpoint.

Freeze feature-only principal provenance and legacy handling, exact Profile/admin transport, mixed-result projection and protected bundle denial in the canonical FA-01 contract. Shared endpoints gain conditional checks only for a protected workflow/contrast child resource, an internal feature action or embargoed data. Public base reads and ordinary non-protected aliases remain unchanged. Preserve ordinary query/cache behavior and incidental invalidation of feature timestamps; inspect-only restricted feature views must not execute that feature or regenerate protected results.

The canonical query owner is `wepppy/query_engine/README.md`; protected polling projection belongs in `docs/schemas/rq-response-contract.md`. Include synthetic contrast/PATH-CE result allow/deny cases for single/batch/recursive job-info while preserving lifecycle/queue and ordinary Culvert polling.

Reconcile all affected canonical contracts and record the operator clarification and read-only production evidence in the checkpoint. Keep the unrelated PowerUser TTL-control OR-versus-ALL mismatch separate. Obtain two independent read-only reviews of the narrowed matrix, disposition medium/high findings and commit the accepted checkpoint as a standalone ancestor; record its SHA. The milestone-zero step included no runtime edits or deployment; the operator subsequently authorized milestone one. Acceptance is the reviewed bounded matrix and committed ancestor, with the expired-credential limitation explicitly carried into implementation/rollout gates.
## Milestone one: additive records and shared decisions


Add bounded account models for `FeatureAccessGroup`, `FeatureAccessMembership`, `FeatureAccessEvent` and `OnboardingAcceptance` adjacent to the existing user models, using the repository's SQLAlchemy conventions. Groups use stable keys tied to registry metadata. Enforce unique current group/user membership and unique acceptance for user/statement kind/version. Store optional review/expiration dates; audit events snapshot actor, subject, group/effective scope, action, reason and UTC time. Do not cascade-delete event history on user/group removal. Keep old User IDs, role associations and runs untouched.

Author one additive Alembic migration against the actual current head, not a guessed revision. Validate empty-database and representative legacy upgrade states in an isolated test database. Seed group definitions idempotently; account membership initialization is a separate explicit operation using the verified maintainer ID and a recorded reason. No migration guesses an email or creates credentials. Plan database backup and readback before applying outside isolated tests.

In `utils/feature_access.py`, implement a shared evaluator with verified principal, feature spec, operation (`inspect` or `act`) and run/resource context, returning an explicit decision and reason. Keep framework response conversion at the Flask/FastAPI boundary. Reuse current database access patterns for non-Flask services; do not introduce an authorization HTTP service. Query live memberships when required, and preserve ordinary public read paths that need no membership lookup. Missing group definitions/configuration and database errors must be explicit denials/unavailability, not permissive role fallbacks.

Add registry fields `access_group` and `access_mode` as specified by FA-01. Group-only features are OpenET, Batch and human Culvert; Omni Contrasts, PATH-CE and AgFields permit the preserved Dev/Root path or current group membership. Public inspection is not evaluated by the action gate. Historical M1 enforced contrast entitlement for PATH-CE inputs. FA-02 supersedes that read dependency: actual composed contrast execution needs contrast action entitlement; consuming retained inputs does not. No automatic membership grant is introduced.

Acceptance uses direct real-database tests for atomic membership-plus-event commits, rollback on injected failure, concurrent duplicate adds/removes, preservation of history, expired/review-only memberships and old-token reads of current membership. Unit tests must also prove Root without OpenET/Batch membership is denied and a valid group member still needs existing run/backend/scope permission. This milestone alone does not enable new UI or claim runtime wiring.

## Milestone two: simple group administration and acknowledgment


Add the Root-protected group administration surface in `routes/admin.py` and a matching `templates/user/feature_access.html`, reusing existing Pure form/error patterns. Show group, current members and history; allow add/remove with a required reason and optional review/expiration fields. Registry controls feature mapping; the form cannot invent privileges or edit another role. Root administers membership but receives no implicit group-only action entitlement.

Use the proposed interfaces below as the concrete contract target, and register any necessary adjustment at the checkpoint. Mutation commits group state and its event together. User-facing status/acknowledgment belongs to the Profile surface: users see only their own memberships, can accept the versioned internal statement and see whether actions await acknowledgment. This is not another maintainer review. Legacy operational-role paths stay usable without a new acknowledgment gate.

Initialize OpenET and Batch groups with the verified maintainer as the sole member, retaining audit evidence. Other additions require a named decision rather than a bulk role-to-group migration. No nested groups, delegated administration hierarchy or reviewer queue is included.

Acceptance is a real browser/database round trip: Root adds a named collaborator to one feature group, user acknowledges if required, action entitlement becomes available, and removal changes future admissions while history remains. Non-Root mutation, forged CSRF, unknown group/user, blank reason and cross-account acknowledgment are rejected without partial state. Keyboard navigation and labeled errors must work.

## Milestone three: wire actions, data and public read-only views

M3 began at checkpoint `458557219`; FA-02 was then reconciled through the [contract checkpoint](../../artifacts/2026-10-02_fa02_sharing_checkpoint.md), and the completed runtime candidate is `23c2f27fe`. FA-02 supersedes contrast/PATH-CE read restrictions in the historical M0 matrix, not the entire action or private-resource inventory. Preserve the previous review as a record of its assessed policy.

Keep current group checks on OpenET/Batch/human Culvert actions and legacy Dev/Root-or-group checks on Omni Contrasts/PATH-CE/AgFields actions. Keep current identity/provenance, acknowledgment, resource scopes, readonly, backend, scientific capability, CSRF and service-integration checks. Private Batch/Culvert reads still follow the existing workflow and resource scope, including old human-derived tokens; public Batch reads remain available. Ordinary anonymous creation/modeling/session behavior is unchanged.

Remove feature-derived read gates across shared evaluator/adapters, public run sections, contrast selectors/dashboard/report reads, generic browse/download/GDAL/D-Tale launch, query catalogs/datasets, export/archive/fork/restore, raw catalog/state files and job-result projection. Retained-result queries, formatting and packaging are shareable under existing endpoint/resource requirements. An endpoint that executes restricted science still needs action entitlement even if named report/export or using GET. Trace PATH-CE's actual execution dependency; reading existing contrast inputs alone does not require contrast action permission. Do not deny ordinary baseline actions merely because the run is a contrast child or was forked from one.

No contrast-lineage marker, blanket contrast-child fork rejection or universal D-Tale login requirement is needed. Reassess SQL-expression reads and cached D-Tale access for actual private-resource or sensitive-file violations; public shared results are expected. Record separate residual findings with concrete evidence and a bounded remediation plan. Do not silently expand scope into a DuckDB upgrade, new credentials or service topology.

Acceptance covers public retained contrast/PATH-CE results and ordinary outputs for anonymous readers where the existing endpoint permits them, authenticated nonmembers and removed members; byte-correct downloads/ZIPs and retained fork/archive/restore results; ordinary query expressions/catalogs and recursive polling shapes; and successful authorized actions. Denied restricted actions enqueue or mutate nothing. Private-resource denial, existing transport requirements, scopes, service credentials and shared-result visibility must all survive removal/expiry of action membership. Inspect-only optional-state views initialize no restricted controller or analysis. Final correctness/security reviews and production-equivalent browser/service acceptance are still required.

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

Run affected stubtest modules if public Python surfaces/stubs change. Rebuild controllers with the nearest AGENTS instructions if controller sources change. Run `wctl check-rq-graph` and inspect live job trees only if enqueue wiring changes; no such topology change is planned. The original documentation-only preparation did not require the broad suite; authorized runtime milestones use the implementation gates above.

## Interfaces and dependencies


The proposed web interfaces are `GET /profile` for onboarding/status, `POST /profile/poweruser` for current-user approval, `POST /profile/internal-access/acknowledge` for current-user internal statement acceptance, `GET /admin/feature-access` for Root administration/history, and `POST /admin/feature-access/memberships` for Root add/remove. The membership body has an explicit operation, canonical user ID, group key, nonempty reason and optional review/expiry timestamps. User-facing acceptance endpoints never accept a target account or arbitrary role. Freeze transport encoding and exact success/error payloads in milestone zero under the existing response/CSRF contracts before implementing.

The access module should expose an inspect/action evaluator and transactional membership/onboarding functions; use one result shape containing `allowed`, stable `reason`, and the entitlement basis useful for audit. Raw bearer tokens never enter database events or logs. Static registry loading remains independent of SQLAlchemy; database lookup and framework principal translation occur at request boundaries. Use current service database adapters rather than new network protocols.

## Idempotence, recovery and retained artifacts


Duplicate onboarding/add/remove requests must not create duplicate grants. Database failure rolls back both authorization state and its event. Additive migrations preserve existing account/run/role rows and do not backfill false acknowledgments. Account/group removal retains historical identifiers and scope snapshots. Membership-store failure is explicit; no missing dependency is masked by a permissive fallback.

Retain checkpoint SHA, reviewed surface/state matrices, redacted identity inventory, migration readback, direct denial/no-side-effect evidence, service compatibility, browser screenshots/results and generated-output manifests under this package's artifacts. Record residual scope limits rather than claiming complete parity from a green suite. Reconcile links and living sections after every milestone.

Revision note, 2026-10-01: created for the operator-requested policy amendment and plan. Runtime milestones are deliberately gated on a reviewed ancestor, verified identities and the feature-only scope boundary; PowerUser sanctions remain excluded.

Revision note, 2026-10-01 scope correction: removed the broader creator/writer proposal after explicit operator clarification; recorded deployment-specific account identity and the expired submit-only Culvert credential without changing it.

Revision note, 2026-10-01: operator authorized milestone one. Reuse the existing framework-independent SQL metadata pattern, with account ORM models registered in app.py; validate in isolated PostgreSQL schemas before any shared deployment migration. Milestones two through five were future work at that checkpoint.

Milestone-one handoff, 2026-10-01: implementation and validation are complete; the operator authorized committing this milestone. Both independent reviewers confirmed all findings closed. The package remains open and unwired; milestone two is the next implementation step.


Milestone-two handoff, 2026-10-02 UTC: implementation, focused/browser/database gates, independent reviews and broad Python regression are complete. Local initialization is verified after backup restore; production is unchanged. The operator authorized committing the completed milestone. Milestone three is the next implementation step.

Milestone-four implementation, 2026-10-02 UTC: the conservative maturity
ceiling and PowerUser Profile flow are implemented. Real PostgreSQL transport
tests prove atomic/idempotent role plus acceptance writes, strict current-user
payloads and rollback. The isolated full-app browser promoted an ordinary user,
minted a fresh token and confirmed private Batch remained denied with zero axe
violations. Production is unchanged; M5 final review and rollout preparation
remain open.

Milestone-four validation, 2026-10-02 UTC: final focused tests passed 275 cases;
the isolated browser passed with zero axe violations and token-free retained
evidence; frontend passed 112 suites / 919 tests. The full repository passed
10,267 tests with 126 skipped in 46:34. A first broad attempt encountered one
unrelated retained NoDb lock after 3,608 passes; its exact parameter passed in
isolation and the full rerun passed without recurrence. M4 is complete locally.

2026-10-02 implementation update: recorded FA-02 ancestor `102c81066`; removing feature-result classification, projection and inherited contrast gates. PATH-CE consumes retained contrasts without executing them, so its own action gate suffices. Private-resource findings and acceptance remain open.

2026-10-02 milestone-three handoff: sharing reconciliation and private-resource
containment passed bounded and final independent correctness/security review.
The exact-candidate service/browser run exercised live revocation through the
production processes and blocked both retained private canaries while preserving
public anonymous viewing. See `artifacts/2026-10-02_m3_service_browser_acceptance.md`
and `artifacts/2026-10-02_m3_final_reviews.md`. This closes local M3; it does not
authorize production rollout. Milestone five remains next.
