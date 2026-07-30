# SURF-14A Contract Decision

**Status**: Accepted; dual-reviewed, standalone ancestor commit pending

**Starting implementation revision**:
`715417f7081ea12e168e10426603445ec5140520`

**Decision venue**: Codex API workspace thread, 2026-07-29 21:10 PDT
(2026-07-30 04:10 UTC)

**Participants present**: requesting WEPPcloud operator; Codex

**Stakeholder input relayed**: Mariana requested an actionable error that tells
the user to select another outlet or change the extent rather than silently
accepting a clipped watershed. Mariana was not present in this decision venue.

## Applicable Authority

- `docs/standards/contract-first-change-standard.md`;
- `docs/standards/parameterization-adr-standard.md`;
- `docs/schemas/weppcloud-csrf-contract.md`;
- `docs/schemas/rq-response-contract.md`;
- `docs/schemas/nodb-persistence-concurrency-contract.md`;
- SURF-14 Profile/Session concise intent contract;
- SHR-05 Unitizer Preferences concise intent contract;
- SURF-01 public/authenticated creation contract;
- SURF-04 fork contract;
- DOM-02 Project Shell contract;
- DOM-05 Channel Delineation contract;
- DOM-05A Channel Delineation/Topaz contract;
- the Pure UI child package register's new SURF-14A entry; and
- this package's `package.md` Normative Contract, pending ratification by the
  required checkpoint process.

No existing contract authorizes account preference mutation, creation-time
account defaults, or configurable WBT edge behavior. This is an intended
behavior change, not a conformance fix.

## Exact Normative Delta

1. Add one typed account preference row per User with exact values
   `config|si|english` and `config|warn|error`.
2. Add login/CSRF-protected `/preferences` GET/POST routes and a Profile link,
   using the existing PureCSS account shell and form macros.
3. Use the exact boundary label `Stop with an error`.
4. Resolve new-project values using explicit project input, then account
   preference, then project config, and snapshot the result into run state.
5. Preserve existing runs, shared runs, anonymous creation, and source values
   on forks.
6. Add `[watershed.wbt] boundary_touch_behavior = "warn"` with exact
   `warn|error` validation.
7. For WBT edge contact, warn and continue or raise the existing typed edge
   exception with an actionable message and no consumable stale success state.

The operator's 2026-07-29 request to execute this named package approves this
complete normative delta as documented here, including the typed storage
model, exact enums, precedence, missing-row defaults, snapshot/fork behavior,
`warn` configuration default, WBT failure semantics, and the scoped Forest
migration/canary. The approval does not expand the package or waive any gate.

## Rationale and Rejected Alternatives

Typed PostgreSQL columns were selected because the values are small,
account-scoped, security-sensitive enums. Cookies and local storage cannot
serve RQ workers or multiple browsers. Run NoDb state has the wrong lifetime.
A JSON blob or generic key/value table weakens database validation and makes
contract evolution less visible.

Live profile resolution during every view/job was rejected because it would
make shared and historical runs depend on the current viewer and mutable
account state. Snapshotting during project creation preserves reproducibility.

`Warn` as the account default was rejected because it would override a config
set to `error` for every existing user. Account default `config` plus config
default `warn` preserves existing behavior while keeping both layers useful.

`Crash` was rejected as a label. `Stop with an error` accurately describes a
controlled typed job failure.

## Compatibility

The database migration is additive. Existing users have no required row and
resolve to `config`/`config`. Existing projects and persisted Unitizer maps are
unchanged. A legacy `watershed.nodb` without
`_wbt_boundary_touch_behavior` hydrates to `warn`; that compatibility value is
independent of later account or configuration changes and is copied by
archive/restore and fork operations. New runs persist the resolved value in
`_wbt_boundary_touch_behavior`. Anonymous projects use config. WBT keeps its
current warning behavior unless a config or account preference explicitly
selects `error`. TOPAZ and DOM-05A conditioning are unchanged.

## Exact Creation Resolution and Identity Matrix

Every public, regional, and authenticated create form governed by SURF-01
converges on `POST /create/` in
`wepppy.microservices.rq_engine.project_routes.create`. The authenticated
HUC-fire upload at `POST /huc-fire/tasks/upload-sbs/` is also included. Both
must use the same typed resolver and failure-atomic ownership helper.

Only a `token_class=user` bearer/RQ token or an authenticated cookie session
may resolve account preferences. The resolver binds `sub` only to a numeric
User ID or exact `fs_uniquifier`; it does not fall back to email. Service,
MCP, run-session, unknown, inactive, or conflicting subject/email identities
cannot impersonate an account. Service/MCP creation that the existing route
otherwise authorizes remains config-only and performs no account lookup.
Unknown or inactive `user` identities fail closed. User lookup and preference
snapshot occur in one Flask/database context and return immutable primitives.

Unit resolution for authenticated new runs is:

| Explicit `unitizer:is_english` | Account unit | Effective unit |
| --- | --- | --- |
| exact `true` or `false` | any valid value | explicit bool |
| absent | `si` | false |
| absent | `english` | true |
| absent | `config` or missing row | project configuration |
| any other nonempty explicit value | any | HTTP 400 `invalid_unitizer_override`; no run |
| absent | invalid persisted value / lookup failure | HTTP 500 `preference_resolution_failed`; no run |

Boundary resolution for authenticated new runs is independent:

| Account boundary | Effective boundary |
| --- | --- |
| `warn` | warn |
| `error` | error |
| `config` or missing row | project configuration |
| invalid persisted value / lookup failure | HTTP 500 `preference_resolution_failed`; no run |

Tests cover the Cartesian product of all successful authenticated unit rows
and all successful boundary rows, plus each failure row. Identity/operation
behavior is:

| Identity / operation | Account lookup | Resolution |
| --- | --- | --- |
| Anonymous/CAP new run | none | valid explicit unit or project config; boundary config |
| Authorized service/MCP new run | none | valid explicit unit or project config; boundary config |
| Unknown/inactive authenticated User | required and fails | canonical 5xx; no run |
| Existing/shared run | none | persisted state |
| Fork/archive restore | none | copied source state |

Payload values override same-named query values under the existing creation
merge contract. Preference-derived overrides may add only
`unitizer:is_english` and
`watershed.wbt:boundary_touch_behavior`. A resolved authenticated identity
whose active User row cannot be found returns a generic 5xx with code
`preference_resolution_failed` and an `error_id`. A database or preference
failure uses the same response. DB details, paths, query text, and stack traces
remain server-side, and no run directory is created.

Authenticated creation is successful only after filesystem/`Ron`
initialization and atomic `Run` plus `runs_users` owner association succeed.
No authenticated `303` or HUC-fire success may reference an ownerless run.
Failure compensates by rolling back both SQL records and removing only the
newly created, validated run directory; cleanup failure is logged with the
same `error_id` and still fails closed.

The other in-repository `Ron(...)` constructors are explicitly excluded:
batch `_base` and child copies use batch configuration; profile playback,
dataset tooling, test-support, and culvert fixtures are non-user production
tools; `land_and_soil_rq` initializes an internal child run. None resolves
viewer account defaults. Fork/archive operations copy source state and never
invoke this resolver.

## Exact WBT State and Asynchronous Transitions

The persisted run field is `_wbt_boundary_touch_behavior`; its public property
accepts only `warn|error`. Missing legacy state reads and then persists as
`warn` on the next Watershed mutation.

At every WBT worker/direct/batch subcatchment attempt, the
`build_subcatchments` and `abstract_watershed` RedisPrep timestamps are
cleared, the previous canonical WBT `subwta.tif` is removed, prior abstraction
outputs remain non-ready, and the prior edge-ID set is replaced. Conditioning,
flow-direction, channel, and prior derived abstraction files may remain on
disk, but downstream preflight must reject them while either completion
timestamp is absent.

After edge detection, sorted unique positive identifiers are persisted. In
`warn` mode, `subwta.tif` remains canonical, the Watershed logger records the
exact warning plus edge IDs, and the RQ worker publishes it on
`<runid>:subcatchment_delineation`. The warning text is the user-visible
contract message followed by ` Edge hillslope IDs: [1, 2].`, where bracketed
values are sorted unique base-10 integers separated by comma-space. The status
event is exactly
`rq:<job_id> WARNING build_subcatchments_rq(<runid>) <warning text>`.
The build timestamp is written only after success. In `error` mode,
`subwta.tif` is deleted, both timestamps remain absent, edge IDs remain
diagnostic state, no completion trigger is published, and
`WatershedBoundaryTouchesEdgeError` is raised with the contract message. A
later successful rerun replaces the edge IDs, recreates `subwta.tif`, writes
the build timestamp, and permits abstraction to restore its timestamp.

For the normal two-child RQ tree, the subcatchment child becomes `failed`, the
dependent abstraction child never runs and becomes `stopped`, and the
aggregate root reports `failed` after no descendant remains active.
`GET /rq-engine/api/jobstatus/<job_id>` retains its canonical status-only
payload. `GET /rq-engine/api/jobinfo/<root-or-child-job-id>` returns HTTP 200
with the canonical fields plus:

```json
{
  "status": "failed",
  "exc_info": null,
  "error": {
    "code": "watershed_boundary_touches_dem_edge",
    "message": "The delineated watershed reaches the DEM boundary and may be clipped. Select a different outlet or enlarge the project extent, then delineate again.",
    "details": {"edge_hillslope_ids": [1, 2]}
  },
  "error_id": "<uuid>"
}
```

The root surfaces the failed descendant's same `error` and `error_id`.
Because polling is open by default, no raw traceback, path, or exception
representation is returned or retained for this expected controlled failure;
RQ job traceback fields are overwritten with the sanitized message.
Diagnostics are the structured server log keyed by `error_id` and the existing
Admin/Root `/weppcloud/rq/info-details` job identity/status page. The structured
log contains run ID and sorted edge IDs but no secret or traceback. Host log
access requires authenticated SSH plus Docker permission and is not an HTTP
API. Tests prove exact endpoint payloads, terminal aggregation, no abstraction,
redaction, and successful retry. Any dependency-wiring change triggers catalog
regeneration, `wctl check-rq-graph`, and live-tree evidence.

## Concurrent Preference Writes

The page is a complete-form, whole-record last-committed-write-wins contract.
`user_id` is the primary/unique key and both columns update in one transaction.
Existing rows are selected for update. Two concurrent first saves may race;
the unique-key loser rolls back and performs one bounded select-for-update
retry with the complete form. No field-level merge occurs. Deterministic
create-race and update-serialization tests are required.

## Security and Operations Impact

Security impact is high because the feature adds authenticated database
mutation, CSRF-sensitive form handling, account-to-run propagation, and an RQ
failure policy. Exact allowlists, atomic transactions, DB constraints,
failure-atomic project creation, escaped rendering, no secret logging, typed
errors, and no silent fallback are mandatory.

The operator authorizes the reviewed additive migration and disposable
authenticated canary on Forest after the contract ancestor, implementation,
local PostgreSQL migration/full-suite validation, and final reviews pass. This
does not authorize production/wepp1 migration.

The repository currently has Alembic heads `7b3c068e7a1d` and
`b7d9c3e2f1a4`. The preference revision must be a merge revision whose
`down_revision` names both heads; no separate empty merge is required.
Validation covers fresh upgrade and a database already at both heads through
upgrade/downgrade/upgrade.

The migration names its four constraints `pk_user_preferences`,
`fk_user_preferences_user_id_user`, `ck_user_preferences_unit_system`, and
`ck_user_preferences_wbt_boundary_touch_behavior`; Forest verifies all four
before application startup.

Forest is SSH target `forest`, repository `/home/workdir/wepppy`, Compose
project `docker`, Compose file `docker/docker-compose.dev.yml`, and PostgreSQL
database `wepppy`. Its current repository and database revisions are both
`7b3c068e7a1d` plus `b7d9c3e2f1a4`; the
`wepppy-postgres-backup` container was healthy at checkpoint discovery. The
latest successful observed restore artifact was
`/backups/weppcloud-20260730-013013.dump`; a later 03:09 UTC attempt failed
while PostgreSQL was unavailable. Forest apply therefore requires a newly
successful backup made after final preflight, not reliance on the older dump.

Forest uses a contained schema-first rollout despite the bind-mounted source
tree. First create and validate a fresh custom-format backup. Then stop enqueue
surfaces `weppcloud`, `rq-engine`, and `scheduler`; prove default/batch queues
have zero queued/executing jobs and every registered worker is idle; stop
`rq-worker` and `rq-worker-batch` with a 30-minute graceful timeout; and verify
the post-stop registries remain empty. Only then fast-forward the clean Forest
checkout to the exact reviewed release SHA. Run Alembic from one disposable
`weppcloud` container while every long-lived changed-code consumer remains
stopped. Start the four changed services together and then `scheduler` only
after schema, constraints, and unchanged User count verify. The requesting
operator owns restore authorization; Codex may verify the restore point and
must abort rather than initiate a restore without new approval. The canary uses
the requesting operator's authenticated account, records its generated run ID,
and deletes only that exact disposable run plus the temporary preference row
after evidence is captured. Preflight records repository heads, database
revisions, new revision, restore point, canary identity, cleanup target, and
restart set.
It aborts on any revision/target mismatch, missing restore point, unexpected
SQL, failed constraint inspection, changed existing-user count, unhealthy
service, or failed canary. After migration, Compose services `weppcloud`,
`rq-engine`, `rq-worker`, and `rq-worker-batch` restart together; `scheduler`
is the only additional service authorized for quiesce/restart and starts
afterward. The exact commands live in the
ExecPlan and set `FLASK_APP=wepppy.weppcloud.app:app`. On migration failure,
keep all five stopped and do not start new code; preserve logs and await
operator disposition. Application rollback uses a reviewed revert commit and
preserves the additive table. Destructive downgrade after rows exist requires
a backup and separate operator approval. A post-action dual audit reviews the
redacted transcript before closure.

## Regression Evidence Required

- model constraints, cascade, atomic/concurrent save, and migration
  upgrade/downgrade/upgrade against disposable PostgreSQL;
- actual preference-page/Profile rendering and prefix-aware navigation;
- login, CSRF, exact enum, hostile input, PRG, and no-partial-write routes;
- complete precedence, explicit input, anonymous, identity failure, existing,
  shared, and fork creation matrices;
- persisted Unitizer and Watershed snapshot evidence;
- synthetic WBT no-edge/all-edge/corner/nodata, warn/error, deterministic IDs,
  actionable message, stale-readiness, and rerun recovery;
- canonical rq-engine error-envelope evidence;
- full Python/frontend/docs/stub/graph gates as applicable;
- local E2E and Forest migration/canary artifacts.

## Operator Approval

The requesting operator explicitly approved `Stop with an error`, requested
the work-package scaffold, granted authority to run the package's reviewed
database migration on Forest, and then instructed Codex to execute this named
package. That execution instruction approves the complete Exact Normative
Delta and contained disposable Forest canary recorded above. Approval does not
waive contract-first reviews, the standalone ancestor, tests, post-action
audit, or final review gates.

## Checkpoint Gate

- [x] Starting revision and normative delta recorded.
- [x] Operator decision and scoped Forest authority recorded.
- [x] Applicable contracts, rationale, compatibility, security, and regression
  plan recorded.
- [x] Independent governance/correctness review passed.
- [x] Independent operations/security review passed.
- [x] Findings disposition complete.
- [x] Documentation-only standalone ancestor committed and recorded as
  `1b412d61a`.
