# SURF-14A Contract Decision

**Status**: Original checkpoint accepted at `1b412d61a`; superseding
user-context amendment pending review

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
- `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`;
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
4. Resolve non-Auto units from the authenticated viewing user into a
   request-local presentation overlay without changing durable project units.
5. Resolve WBT boundary behavior from the authenticated initiating user,
   using their preference then the immutable per-run config baseline, and
   carry a deterministic bounded snapshot through the RQ tree without
   persisting account-derived project policy.
6. Add `[watershed.wbt] boundary_touch_behavior = "warn"` with exact
   `warn|error` validation.
7. For WBT edge contact, warn and continue or raise the existing typed edge
   exception with an actionable message and no consumable stale success state.

The operator's 2026-07-29 request approved typed storage, enums, defaults,
failure behavior, and a scoped Forest canary. On 2026-07-30 the operator
demonstrated both WBT transitions, then explicitly corrected the authority and
lifetime: preferences follow the authenticated user rather than the owner;
non-Auto units change that user's view without mutating project units. This
supersedes creation-time account unit snapshotting and the draft owner-only
WBT rule. Neither approval waives a contract, review, acceptance, or Forest
gate.

## Rationale and Rejected Alternatives

Typed PostgreSQL columns were selected because the values are small,
account-scoped, security-sensitive enums. Cookies and local storage cannot
serve RQ workers or multiple browsers. Run NoDb state has the wrong lifetime.
A JSON blob or generic key/value table weakens database validation and makes
contract evolution less visible.

Live profile resolution by an RQ worker is rejected because it makes
execution timing-dependent. Unit preference is intentionally resolved at an
authorized request/view boundary into a nonpersistent presentation object.
WBT boundary behavior is resolved synchronously for the initiating
account-bearing user and then passed as an immutable RQ snapshot.
Non-account-bearing public sessions, service/MCP, direct, and batch paths use
project/config state.

`Warn` as the account default was rejected because it would override a config
set to `error` for every existing user. Account default `config` plus config
default `warn` preserves existing behavior while keeping both layers useful.

`Crash` was rejected as a label. `Stop with an error` accurately describes a
controlled typed job failure.

## Compatibility

The database migration is additive. Existing users have no required row and
resolve to `config`/`config`. Existing projects and persisted Unitizer maps
are unchanged. Account units do not modify creation state. A separate
`_wbt_boundary_touch_config_behavior` records the project baseline; an
account-derived effective choice is execution-only. Archive/restore and fork
copy project state, while each later account-bearing view/submission resolves
that user independently. TOPAZ and DOM-05A conditioning are unchanged.

## Creation and Presentation Compatibility

Account preferences do not parameterize `Ron(...)` or project creation.
Existing explicit `unitizer:is_english` input and selected configuration
continue to determine durable Unitizer state. WBT configuration determines
the durable project baseline. Regular, HUC-fire, anonymous/CAP, service/MCP,
batch, playback, dataset, culvert, internal-child, fork, and archive/restore
creation paths therefore preserve their pre-amendment parameterization.

After ordinary view authorization, an active account-bearing viewer resolves
their Unitizer presentation:

| Viewer preference | Presentation | Durable project mutation |
| --- | --- | --- |
| `config` or missing row | exact project category selections | none |
| `si` | metric defaults for every category | none |
| `english` | US customary defaults for every category | none |
| invalid identity/value or DB failure | sanitized failure | none |
| anonymous/non-account-bearing | exact project category selections | none |

The request-local overlay covers rendered reports/controls, conversion
endpoints, and initial browser preference payload. It never changes cached or
on-disk Unitizer state. Project-specific Unitizer mutation remains an explicit
separate operation.

### Initiating-user WBT delineation matrix

The existing authorization check remains mandatory before preference
resolution. The route snapshots the effective policy before enqueue; the
worker does not query account state.

| Initiator / run | Controlling value | Result |
| --- | --- | --- |
| Active authorized user token or session with numeric `user_id` | initiating user's non-`config` boundary, else immutable config baseline | bounded snapshot enqueued |
| Authorized shared/admin/public-run User | that initiating user's preference | bounded snapshot enqueued |
| Account-bearing inactive/missing User, invalid preference, or baseline failure | none | sanitized `preference_resolution_failed`; no mutation |
| Public session without numeric `user_id` | project policy | no account lookup |
| Service or MCP | persisted run policy | no account lookup |
| Direct/batch worker | persisted run policy | no account lookup |
| Fork/archive/restore | current initiating user's preference | copied project state remains unchanged |

Existing authorization remains authoritative for access. It does not select
the preference account. Account-bearing session means a verified positive
numeric `user_id` claim. The exact private root metadata schema and bounded
child argument are defined in the amendment and canonical RQ contract.
Changing the account after enqueue does not change that job or retry.
Resolution and snapshot validation finish before any NoDb/Redis/queue
mutation. A legacy missing config baseline may then persist only the validated
configuration value under the Watershed lock before any other route mutation.
Child cache invalidation, hydration, snapshot validation, construction of a
nonpersistent execution policy, and only then WBT attempt entry are mandatory.

## Exact WBT State and Asynchronous Transitions

The persisted run field `_wbt_boundary_touch_behavior` remains project policy
and accepts only `warn|error`. Missing legacy state reads as `warn`.
`_wbt_boundary_touch_config_behavior` is the immutable config baseline.
Account-derived effective policy is execution-only and never replaces either
field.

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
dependent abstraction child never runs and becomes `canceled`, and the
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
Both saves and request/job resolution lock the User row before preference
access; existing preference rows are then selected for update. Two concurrent
first saves may race;
the unique-key loser rolls back and performs one bounded select-for-update
retry with the complete form. No field-level merge occurs. Deterministic
create-race and update-serialization tests are required.

## Security and Operations Impact

Security impact is high because the feature adds authenticated database
mutation, CSRF-sensitive form handling, per-user presentation, and an RQ
failure policy. Exact allowlists, atomic transactions, DB constraints,
request-local isolation, escaped rendering, no secret logging, typed errors,
and no silent fallback are mandatory.

The operator authorizes the reviewed additive migration and disposable
authenticated canary on Forest after the contract ancestor, implementation,
local PostgreSQL migration/full-suite validation, and final reviews pass. This
does not authorize production/wepp1 migration.

The repository currently has Alembic heads `7b3c068e7a1d` and
`b7d9c3e2f1a4`. The preference revision must be a merge revision whose
`down_revision` names both heads; no separate empty merge is required.
Because the historical base assumes an existing application `user` table,
fresh validation means a newly created disposable PostgreSQL database
initialized to the representative application schema with the new table
absent and both real parents recorded. It must run graph-level upgrade,
explicit-target downgrade back to both parents, and re-upgrade.

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
checkout to the exact reviewed release SHA and assert the resulting HEAD
equals it. Before apply, record and verify an exact reviewed forward revert
commit as the application rollback target; it must be a commit descendant of
the release commit so rollback itself is a fast-forward. Run Alembic from one
disposable
`weppcloud` container while every long-lived changed-code consumer remains
stopped. Start the four changed services together and then `scheduler` only
after schema, constraints, and unchanged User count verify. The requesting
operator owns restore authorization; Codex may verify the restore point and
must abort rather than initiate a restore without new approval. The canary
uses the requesting operator's authenticated account plus a second existing
operator-designated active test account. Preflight records both numeric User
IDs and each exact prior preference-row state; it must stop for operator
direction rather than create an account or change roles if the second account
is absent. The operator creates one exact disposable run through the ordinary
authenticated path and grants the second account access through the existing
`runs_users` association. Evidence records the generated run and association
identifiers. Cleanup removes only that association and run, restores both
prior preference rows exactly, and deletes a preference row only when it was
absent before the canary. It never deletes a User or alters roles.
Post-cleanup checks prove both Users remain and no unrelated preference or
association changed. Preflight records repository heads, database revisions,
new revision, restore point, both canary identities, prior preference state,
cleanup targets, and restart set.
It aborts on any revision/target mismatch, missing restore point, unexpected
SQL, failed constraint inspection, changed existing-user count, unhealthy
service, or failed canary. After migration, Compose services `weppcloud`,
`rq-engine`, `rq-worker`, and `rq-worker-batch` restart together; `scheduler`
is the only additional service authorized for quiesce/restart and starts
afterwards. The exact commands live in the
ExecPlan and set `FLASK_APP=wepppy.weppcloud.app:app`. On migration failure,
keep all five stopped and do not start new code; preserve logs and await
operator disposition. Application rollback uses the exact preflight-recorded
reviewed forward revert commit and preserves the additive table. Before moving
to rollback code, repeat the same
enqueue stop, queue drain, worker-idle check, graceful worker stop, and
zero-worker registry verification used for apply. Fast-forward to the recorded
rollback commit and assert `git rev-parse HEAD` equals it before restarting the
four changed services together and `scheduler`; never run rollback workers
against new-signature jobs. Destructive downgrade after rows exist requires a
backup and separate operator approval. A post-action dual audit reviews the
redacted transcript before closure.

## Regression Evidence Required

- model constraints, cascade, atomic/concurrent save, and migration
  upgrade/downgrade/upgrade against disposable PostgreSQL;
- actual preference-page/Profile rendering and prefix-aware navigation;
- login, CSRF, exact enum, hostile input, PRG, and no-partial-write routes;
- project creation remains independent of account preferences;
- two-user request-local Unitizer overlays with byte-stable cached/on-disk
  project state across reports, conversions, and browser initialization;
- synthetic WBT no-edge/all-edge/corner/nodata, warn/error, deterministic IDs,
  actionable message, stale-readiness, and rerun recovery;
- initiating-user/shared/admin/session/service fallback, immutable RQ
  snapshot, nonpersistent boundary policy, and canonical error evidence;
- full Python/frontend/docs/stub/graph gates as applicable;
- local E2E and Forest migration/canary artifacts proving two users on one
  unchanged project.

## Operator Approval

The requesting operator explicitly approved `Stop with an error`, requested
the work-package scaffold, granted authority to run the package's reviewed
database migration on Forest, and instructed Codex to execute the original
package. On 2026-07-30 the operator separately corrected the final lifetime:
both preferences track the authenticated user, non-Auto units do not mutate
project units, and WBT uses the initiating user rather than the owner. That
statement supersedes the original creation-time unit delta and owner-only
draft. Approval does not waive contract-first reviews, the standalone
amendment ancestor, tests, post-action audit, or final review gates.

## Original Checkpoint Gate (superseded for preference lifetime and authority)

- [x] Starting revision and normative delta recorded.
- [x] Operator decision and scoped Forest authority recorded.
- [x] Applicable contracts, rationale, compatibility, security, and regression
  plan recorded.
- [x] Independent governance/correctness review passed.
- [x] Independent operations/security review passed.
- [x] Findings disposition complete.
- [x] Documentation-only standalone ancestor committed and recorded as
  `1b412d61a`.

## User-Context Amendment Checkpoint

- [x] Operator's superseding viewing-user/initiating-user decision recorded.
- [ ] Independent governance/correctness review passes.
- [ ] Independent operations/security review passes.
- [ ] User-context findings disposition is complete.
- [ ] Superseding documentation-only standalone ancestor is committed and
  recorded.
