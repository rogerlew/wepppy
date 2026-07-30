# Add account defaults and fail-closed WBT boundary handling

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current while it
is active.

## Purpose / Big Picture

An authenticated user can open User Preferences from Profile and select
default units plus what happens when a WBT watershed reaches the DEM boundary.
New projects snapshot those defaults. Choosing `Stop with an error` prevents a
clipped WBT watershed from appearing successful and tells the user to select a
different outlet or enlarge the project extent.

## Progress

- [x] (2026-07-30 04:10 UTC) Mapped the current account, Profile, run-scoped
  Unitizer, creation override, WBT edge detector, typed error, configuration,
  and migration surfaces.
- [x] (2026-07-30 04:10 UTC) Scaffolded SURF-14A and recorded the operator's
  UI-label decision and Forest migration authority.
- [ ] Complete two independent checkpoint reviews and disposition all findings.
- [ ] Commit the documentation-only checkpoint before implementation.
- [ ] Implement and test account persistence plus the User Preferences page.
- [ ] Implement and test new-run effective-value resolution and snapshotting.
- [ ] Implement and test WBT boundary warning/error behavior.
- [ ] Complete broad validation, documentation, final reviews, and local E2E.
- [ ] Apply and validate the authorized Forest migration and canary.

## Surprises & Discoveries

- Observation: `Unitizer` preferences are currently run-scoped, not
  account-scoped.
  Evidence: `wepppy/nodb/unitizer.py` persists `unitizer.nodb` under each run.

- Observation: new-project creation already supports an explicit
  `unitizer:is_english` override through the configuration query.
  Evidence: `interfaces.htm` leaves the value blank normally and supplies
  `true`/`false` only after an explicit unit choice; `project_routes.py`
  serializes non-empty overrides before constructing `Ron`.

- Observation: WBT already records hillslope identifiers touching raster edges
  immediately after subcatchment delineation, but does not enforce a policy.
  Evidence: `Watershed.build_subcatchments()` calls
  `identify_edge_hillslopes()`, whose support function reads all four raster
  edges and returns positive identifiers.

- Observation: the rq-engine already handles
  `WatershedBoundaryTouchesEdgeError`.
  Evidence: `watershed_routes.py` has a dedicated exception branch, so this
  package can preserve the typed response contract instead of inventing an
  error envelope.

## Decision Log

- Decision: Use canonical tokens `config|si|english` and
  `config|warn|error`.
  Rationale: short stable values separate storage/API identity from labels and
  admit exact validation.
  Date/Author: 2026-07-30 / requesting operator and Codex.

- Decision: Use `Stop with an error` as the user-visible boundary choice.
  Rationale: the behavior is an intentional typed guard, not an uncontrolled
  crash.
  Date/Author: 2026-07-30 / requesting operator.

- Decision: Use explicit creation input > account preference > project config.
  Rationale: an explicit action for one project must beat an account default;
  a default may override configuration only when the user selected it.
  Date/Author: 2026-07-30 / Codex, derived from the existing creation contract.

- Decision: Apply account preferences only when creating a new project.
  Rationale: existing/shared runs and asynchronous jobs must not depend on
  mutable viewer profile state. Forks preserve the source run.
  Date/Author: 2026-07-30 / requesting operator and Codex.

- Decision: Run the schema migration on Forest only after local tests and final
  reviews.
  Rationale: the operator authorized Forest migration, while staged deployment
  keeps incompatible application/schema states out of the canary environment.
  Date/Author: 2026-07-30 / requesting operator and Codex.

## Outcomes & Retrospective

The package is scaffolded and implementation conformance is pending. Update
this section after each milestone with actual test counts, migration revisions,
E2E evidence, deviations, and remaining rollout work.

## Context and Orientation

The SQLAlchemy `User` model and migrations live under
`wepppy/weppcloud/app.py` and `wepppy/weppcloud/migrations/`. The current
Profile route/template are `wepppy/weppcloud/routes/user.py` and
`wepppy/weppcloud/templates/user/profile.html`. The new page should reuse
`security/_layout.html` and `controls/_pure_macros.html`.

`wepppy/nodb/unitizer.py` reads `[unitizer] is_english` when a new run is
initialized and then persists the resulting category map in `unitizer.nodb`.
`wepppy/microservices/rq_engine/project_routes.py` resolves the authenticated
creator, builds a configuration override string, and initializes `Ron`;
`Ron` constructs Unitizer and Watershed state. That boundary is where account
defaults must be converted into run configuration, before NoDb construction.

`wepppy/nodb/core/watershed.py` reads WBT configuration and owns persisted
Watershed fields. `wepppy/nodb/core/watershed_mixins.py` delineates WBT
subcatchments and calls the edge detector in
`wepppy/topo/watershed_abstraction/support.py`. The policy check belongs
immediately after edge detection and before success timestamping.

## Plan of Work

First finish the contract-first ancestor. Obtain two independent read-only
reviews of `package.md`, the contract decision, ADR-0033, security plan, and
SURF-14A register entry. Resolve all authority, precedence, compatibility,
security, failure-atomicity, migration, and regression findings. Commit only
the documentation checkpoint as a standalone ancestor and record its SHA in
the tracker.

Next add a `UserPreferences` SQLAlchemy model with a one-to-one User
relationship, exact string constraints, timestamps, and cascading foreign key.
Add an Alembic migration that upgrades from the current head and cleanly
downgrades. Implement a small typed preference service that returns defaults
for a missing row, validates exact tokens, performs one atomic upsert/update,
and resolves effective creation overrides without silently swallowing database
errors.

Add login-required GET/POST `/preferences` routes in the existing user
blueprint. Render a server-side form through the existing security/Pure shell
and Pure form macros, add a Profile link, enforce CSRF, display field errors,
and use POST/Redirect/GET on success. Avoid new JavaScript unless direct
evidence proves it necessary.

At the project-creation boundary, resolve the authenticated User once. Preserve
an explicit non-empty `unitizer:is_english` input; otherwise translate
`si`/`english` into the configuration override. Translate a non-`config`
boundary preference into `watershed.wbt:boundary_touch_behavior`. Anonymous
creation uses config. An authenticated database/preference failure must abort
and clean up any newly created empty run directory. Ensure fork/archive
ownership registration cannot apply destination-user defaults to copied run
state.

Add `boundary_touch_behavior = "warn"` to the WBT configuration defaults or
the canonical default-loading path and validate `warn|error` when Watershed
initializes. Persist the effective value with a guarded setter. After WBT edge
identification, publish an actionable warning for `warn`; for `error`, remove
or invalidate canonical ready output as required by actual preflight semantics,
clear stale completion state, and raise
`WatershedBoundaryTouchesEdgeError` with the contract message and deterministic
edge identifiers.

Write model/migration, route/render/security, resolution, NoDb, synthetic
raster, RQ error, and compatibility tests before broad validation. Update the
Profile/User Preferences user guide, Channel Delineation guide, config/developer
documentation, ADR, package records, stubs, and generated artifacts only when
their owning source changes.

After local tests and final reviews pass, restart the local stack and create a
disposable authenticated project for E2E. Confirm saved preferences, effective
run state, config-mode behavior, and the WBT error message without retaining
test credentials.

Finally execute the authorized Forest canary. Record the deployed code
revision, current Alembic head, backup/preflight evidence, and migration SQL
scope. Run the reviewed `flask db upgrade` command inside the Forest
application container, verify the new head/table/constraints, restart only
services that require it, and exercise an authenticated preference save plus
new-project snapshot. Do not migrate production/wepp1.

## Concrete Steps

Run development commands from `/home/workdir/wepppy`:

    wctl doc-lint --path \
      docs/work-packages/20260729_user_preferences_wbt_boundary
    wctl doc-lint --path \
      docs/adrs/ADR-0033-user-defaults-and-wbt-boundary-policy.md

    wctl run-pytest tests/weppcloud/routes/test_user_preferences.py \
      tests/weppcloud/routes/test_user_profile_contract.py \
      tests/microservices/test_rq_engine_project_routes.py \
      tests/nodb/test_unitizer_preferences.py \
      tests/nodb/test_watershed.py \
      tests/microservices/test_rq_engine_watershed_routes.py --maxfail=1

    wctl run-stubtest wepppy.weppcloud.user_preferences
    wctl check-test-stubs
    wctl check-test-isolation
    wctl check-rq-graph
    wctl run-npm lint
    wctl run-npm test
    python3 tools/check_broad_exceptions.py --enforce-changed \
      --base-ref <checkpoint-sha>
    wctl run-pytest tests --maxfail=1
    git diff --check

Before Forest migration, replace placeholders with the actual reviewed compose
files and service names discovered on that host. The canonical container-side
migration form is:

    docker compose <forest compose arguments> exec weppcloud flask db current
    docker compose <forest compose arguments> exec weppcloud flask db upgrade
    docker compose <forest compose arguments> exec weppcloud flask db current

Do not put database passwords, session cookies, JWTs, or preference-form CSRF
tokens into work-package artifacts.

## Validation and Acceptance

The model test must prove one row per user, both check constraints, cascade
delete, missing-row defaults, atomic two-field updates, and migration
upgrade/downgrade/upgrade. Route/render tests must prove login, CSRF, exact
tokens, visible errors, no partial mutation, escaped values, selected state,
Pure macros, prefix-aware Profile navigation, and PRG success.

Creation tests must cover all nine meaningful precedence combinations plus an
explicit unit choice, missing row, anonymous CAP creation, user-token/session
identity, preference lookup failure, existing runs, shared runs, and forks.
The run's persisted Unitizer and Watershed values—not only the configuration
string—are acceptance evidence.

Synthetic rasters must cover every edge, corners, nodata/non-positive edges,
no-edge, multiple deterministic identifiers, `warn`, `error`, invalid config,
stale prior completion state, and rerun recovery. The error case must expose
the contract message through the existing rq-engine error envelope and must
not allow downstream readiness.

Forest acceptance requires the reviewed application revision, one migration
head, the exact new table/constraints, unchanged existing user count, no
required backfill, preference save/reload, one new project with effective
snapshot values, healthy services, and a documented rollback. Production
remains untouched.

## Idempotence and Recovery

Local tests and documentation checks are repeatable. The migration must be
additive and safe to rerun through Alembic head detection. A failed preference
save rolls back its transaction. A failed authenticated preference lookup
cannot leave a registered or usable partial run.

Before Forest apply, capture the current head and confirm a database backup or
approved restore point. If migration apply fails, stop, preserve logs, and do
not repeatedly mutate the database without diagnosing the exact revision. If
the schema succeeds but the application canary fails, roll back application
code first when the additive table is harmless; downgrade the migration only
when the reviewed rollback says it is necessary and no preference rows need
preservation.

## Artifacts and Notes

Keep checkpoint reviews, disposition, final reviews, migration preflight/apply
transcripts with secrets removed, and local/Forest E2E evidence under this
package's `artifacts/` directory. Record exact revisions and test counts in the
tracker and this plan.

## Interfaces and Dependencies

Use existing Flask-SQLAlchemy, Flask-Migrate/Alembic, Flask-Security login,
global CSRF enforcement, PureCSS shell/macros, NoDb locking, RQ response
envelopes, and the owned WBT edge detector. Add no external dependency.

Expose stable Python enums or literal-validated constants for the six tokens
and a typed resolver that accepts an optional explicit unit override, account
preferences, and config values. Keep account persistence independent of
run-scoped Unitizer mutation. Reuse
`WatershedBoundaryTouchesEdgeError`; do not add a generic exception or silent
fallback wrapper.

## Revision Notes

2026-07-30: Initial scaffold records the operator-approved label, typed storage
decision, precedence, reproducibility boundary, WBT policy, contract/review
gates, and scoped Forest migration authority.
