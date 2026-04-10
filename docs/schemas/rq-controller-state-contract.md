# RQ Controller State Contract (Draft)
> Proposed additive contract for agent-friendly controller state, parameter metadata, and run orchestration signals.
> **Status:** Draft proposal only; no rq-engine endpoint in this document is implemented yet.
> **See also:** `docs/schemas/rq-engine-agent-api-contract.md`, `docs/schemas/rq-response-contract.md`, `docs/dev-notes/auth-token.spec.md`

## Purpose
- Provide a canonical API for agents to read current run/controller state without scraping HTML or template bootstrap payloads.
- Expose machine-usable schema metadata (types, ranges, units, enums, hints) so agents can validate and assemble requests before submission.
- Expose orchestration metadata (pipeline order, dependencies, readiness, and actionable next steps) so agents can execute full projects deterministically.

## Scope
- Primary surface is run-scoped, read-only endpoints under rq-engine.
- Covers:
  - setup/bootstrap discovery before a run exists,
  - controller discovery and state,
  - controller-level schema and hints,
  - endpoint-level request schema/defaults,
  - pipeline DAG and readiness,
  - output discovery and recovery metadata.
- Endpoint descriptors MAY include non-run-scoped setup operations (for example
  `create`) so agents can reason about end-to-end workflows without
  switching contracts.
- Does not replace existing mutation endpoints.

## Non-Goals
- No immediate runtime behavior changes are made by this document alone.
- No UI rendering prescriptions beyond optional hint metadata.

## Frozen Baseline vs Target Profile
- `Frozen baseline`: current implemented route behavior captured in
  `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  and
  `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`.
- `Target profile`: additive post-cutover behavior described in this contract for
  controller-state endpoints and descriptor/schema hardening.
- If target-profile requirements exceed the frozen baseline, implementation
  packages MUST stage those changes behind the roadmap and preserve
  backward-compatible behavior until cutover package
  `20260410_rq_controller_state_contract_cutover`.

## Proposed Endpoint Surface

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/configs` | List create-time config vocabulary with mod implications and regional applicability. |
| `GET` | `/api/configs/{config}` | Return detailed config metadata for one config ID. |
| `GET` | `/api/endpoints` | List non-run-scoped setup operation descriptors available without a `runid/config` context. |
| `GET` | `/api/endpoints/{operation_id}/schema` | Return request schema + operation descriptor for a specific non-run-scoped setup operation. |
| `GET` | `/api/endpoints/{operation_id}/defaults` | Return deployment-scoped defaults for a specific non-run-scoped setup operation. |
| `GET` | `/api/endpoints/{operation_id}/errors` | Return stable error-code taxonomy and recovery mapping for one non-run-scoped operation. |
| `GET` | `/api/runs/{runid}/{config}/controllers` | List available controllers and capabilities for this run. |
| `GET` | `/api/runs/{runid}/{config}/geospatial-metadata` | Return run-resolved geographic constraints (coverage, station catalogs, scale defaults). |
| `GET` | `/api/runs/{runid}/{config}/controllers/{controller}/state` | Return normalized controller state. |
| `GET` | `/api/runs/{runid}/{config}/controllers/{controller}/schema` | Return controller field schema and constraints. |
| `GET` | `/api/runs/{runid}/{config}/controllers/{controller}/hints` | Return optional field/group hint metadata. |
| `GET` | `/api/runs/{runid}/{config}/controllers/{controller}/templates` | Return named templates plus run-resolved defaults. |
| `GET` | `/api/runs/{runid}/{config}/endpoints` | List operation descriptors for invokable run-scoped actions. |
| `GET` | `/api/runs/{runid}/{config}/endpoints/{operation_id}/schema` | Return request schema + operation descriptor for a specific mutation operation. |
| `GET` | `/api/runs/{runid}/{config}/endpoints/{operation_id}/defaults` | Return run-resolved defaults for a specific operation. |
| `GET` | `/api/runs/{runid}/{config}/endpoints/{operation_id}/errors` | Return stable error-code taxonomy and recovery mapping for one operation. |
| `GET` | `/api/runs/{runid}/{config}/pipeline` | Return config/mod-aware execution DAG and step states. |
| `GET` | `/api/runs/{runid}/{config}/readiness` | Return condensed precondition state and `next_actionable_steps`. |
| `GET` | `/api/runs/{runid}/{config}/outputs` | Return discovered artifacts/exports and producer operations. |

## Setup Bootstrap Discovery Requirements
- Agents MUST be able to discover valid `create` configs without external docs.
- `/api/configs` MUST include, at minimum, per-config:
  - `config_id` (canonical create value)
  - `active_mods`
  - `supported_regions`
  - `required_upload_steps`
  - `recommended_for` (short machine-readable use-case tags)
- `rq_engine_create` schema MUST declare `config` as a field and reference this
  catalog (`catalog_url` or equivalent linkage metadata).
- `rq_engine_create` schema SHOULD include either:
  - an explicit `enum` of currently valid config IDs, or
  - `dynamic_enum_from` linkage to `/api/configs`.
- Bootstrap access policy for `/api/configs` MUST be explicit:
  - preferred: readable without bearer run token (`session_cookie_same_origin`
    or open read mode), because this call often happens before run creation;
  - if deployment requires JWT scope, setup docs/descriptor metadata MUST state
    that a pre-run service/user token is required before discovery.

## Run Geospatial Metadata Requirements
- `/api/runs/{runid}/{config}/geospatial-metadata` SHOULD expose:
  - run bounding geometry/extent,
  - DEM coverage status for the run extent,
  - run-resolved defaults for `map_center`, `map_bounds`, `map_zoom`, `csa`,
    and `mcl`,
  - dynamic catalogs or summaries for region-dependent options (for example
    climate station modes, soil datasets).
- Availability timing MUST be explicit:
  - this endpoint SHOULD be callable immediately after `create`/`fork` and
    before first pipeline mutation;
  - if any fields are unavailable pre-prep, payload SHOULD include
    per-field availability state (`available`, `pending`, `unavailable`) and a
    reason code so agents can fall back deterministically.
- Endpoint schema fields that depend on this metadata MUST indicate that they
  are run-resolved constraints (see `constraint_mode` rules below).

## Auth And Access
- Require run access checks consistent with existing run-scoped rq-engine endpoints.
- Proposed read scope:
  - `rq:read` (new scope for read-only metadata/state endpoints).
- Backward-compatible rollout option:
  - accept `rq:status` until tokens are migrated to `rq:read`.
  - `rq:status` aliasing MUST be limited to the read-only endpoints listed in
    `## Proposed Endpoint Surface` in this document.
  - `rq:status` aliasing MUST NOT authorize mutation, export/download, admin, or
    bootstrap-control surfaces outside this proposed read-only endpoint set.
  - aliasing sunset gate: remove `rq:status` alias only after
    `20260410_rq_controller_state_auth_concurrency` records passing auth-scope
    parity tests for `rq:read` on the affected endpoints.
- Session-token compatibility requirement:
  - existing session-token mint flows that currently issue `rq:status`,
    `rq:enqueue`, and `rq:export` MUST continue to read these endpoints during
    rollout (via `rq:status` alias or by adding `rq:read` at mint time).
- Browser cookie/session behavior remains governed by:
  - `docs/schemas/weppcloud-csrf-contract.md`
  - `docs/schemas/weppcloud-session-contract.md`

### Accepted Auth Modes
- `accepted_auth` values in operation descriptors SHOULD use a stable taxonomy:
  - `bearer_jwt`
  - `rq_token`
  - `session_cookie_same_origin`
  - `captcha`
  - `basic_forward_auth` (for infra-boundary paths only)

## Response And Error Contract
- All keys MUST use `lower_snake_case`.
- Error payload MUST follow `docs/schemas/rq-response-contract.md`.
- Success payloads MUST include:
  - `contract_version`
  - `deployment_revision`
- Run-scoped success payloads MUST include:
  - `run_state_revision`
- Payloads that expose mutable state or schemas MUST include:
  - `state_version` (for state payloads)
  - `schema_version` (for schema payloads)
- Snapshot-producing read endpoints (`controller/state`, `pipeline`, `readiness`,
  `outputs`) MUST include:
  - `updated_at`
  - `etag`
- `deployment_revision` and `run_state_revision` have distinct semantics:
  - `deployment_revision`: deployment/configuration snapshot revision.
  - `run_state_revision`: run-state snapshot revision.
- Non-run-scoped setup endpoints MAY omit `run_state_revision`.
- `run_state_revision` MUST change whenever a mutation or background job changes
  state visible through this contract (for example controller state, pipeline
  status, readiness blockers, defaults, or outputs).
- Clients that compose multiple endpoint reads SHOULD verify
  `deployment_revision` and `run_state_revision` remain stable across those
  reads.

## Orchestration Requirements (Agent-Critical)
- Pipeline endpoint MUST expose:
  - ordered DAG (`depends_on`, `blocks`),
  - step execution state,
  - precondition status,
  - last attempt status and error summary,
  - endpoint/method binding for each step.
- Readiness endpoint MUST expose:
  - cross-controller precondition summary,
  - mod-aware context,
  - deterministic `next_actionable_steps`,
  - explicit invalidation lineage for recently invalidated steps.
- Readiness blockers MUST be join-safe:
  - `blocking_issues[].issue_id` is canonical.
  - `ineligible_operations[].blocked_by_issue_ids[]` MUST reference those
    issue IDs directly.
  - `blocking_issues[].code` is classification metadata only and MUST NOT be
    used as the join key.
- Blocking issues with `severity=error` MUST include `recovery_actions[]`
  entries with concrete `operation_id` and `required_fields` so remediation is
  machine-executable.
- Endpoint schema/default endpoints MUST be operation-centric (not only controller-centric), because endpoint payloads can span multiple controllers.

## Canonical Identifier Model
- `operation_id` is the canonical join key across discovery, pipeline,
  readiness, and OpenAPI.
- `operation_id` MUST match rq-engine OpenAPI operation IDs for implemented
  routes and therefore use the `rq_engine_` prefix.
- For proposed routes that are not yet in OpenAPI, the `operation_id` values in
  this contract are reserved IDs and MUST be used unchanged when those routes
  are implemented.
- Path exceptions (for example `POST /create/` without an `/api` prefix) do not
  change `operation_id` naming requirements.
- `step_id` is a stable workflow-node key in the pipeline DAG.
- A pipeline step MUST carry both:
  - `step_id` (workflow node identity)
  - `operation_id` (invokable operation identity)

## Operation Descriptor Requirements
- Endpoint discovery payloads MUST include executable descriptor details for each
  operation.
- Descriptor shape is endpoint-family specific:
  - endpoint catalog payloads (`/api/endpoints`,
    `/api/runs/{runid}/{config}/endpoints`) MUST inline descriptor fields under
    each `operations[]` entry.
  - endpoint schema/default payloads MUST include an `operation_descriptor`
    object containing the same descriptor field set for the requested
    operation.
- Descriptor field set MUST include:
  - `operation_id`, `method`, `path`
  - `run_scoped` boolean
  - `accepted_auth` modes (for example bearer JWT, session-cookie, CAPTCHA)
  - `auth_requirements` keyed by auth mode for mode-specific requirements (for
    example required scopes for bearer/rq_token modes, same-origin checks for
    session-cookie mode, CAPTCHA challenge requirement)
  - `content_types` and upload `file_fields` (if multipart)
  - conditional field requirements (`required_if`, `available_if`)
  - scope requirements MUST be declared only under `auth_requirements` (do not
    duplicate as top-level `required_scope`)
  - `error_catalog_url` for operation-scoped machine-readable error taxonomy
  - `write_precondition` object for optimistic concurrency policy:
    - `required`
    - `accepted` (`x_run_state_match`, `expected_run_state_revision`)
    - `conflict_status_code`
    - `conflict_error_code`
  - `idempotency_policy` for mutating operations:
    - `supported`
    - `key_locations` (for example `header:Idempotency-Key`)
    - `dedupe_window_seconds`
    - `replay_behavior` (`return_original_success`, `reject_duplicate`)
    - `duplicate_replay_status_code` (required when `replay_behavior=reject_duplicate`)
    - `duplicate_replay_error_code` (required when `replay_behavior=reject_duplicate`)
    - `mismatch_status_code`
    - `mismatch_error_code`
  - `execution_mode` (`sync`, `async`, `sync_redirect`)
  - `returns_job` and `job_key` (if applicable)
  - `success_status_codes`
  - `response_mode` (`json`, `file`, `redirect`, `mixed`)
  - `result_contract` describing required success payload fields and next action
    semantics for the declared execution mode
  - Async `result_contract` MUST include canonical polling status sets:
    - `status_field`
    - `non_terminal_statuses`
    - `terminal_success_statuses`
    - `terminal_failure_statuses`
    - `suggested_poll_interval_seconds`
    - optional `progress_field` when operation reports progress
  - `estimated_duration` for planning/polling ergonomics:
    - `bucket` (`fast`, `medium`, `slow`, `very_slow`)
    - `typical_seconds`
  - `batch_mode_behavior` / `base_project_behavior` when behavior diverges
  - `mutates_controllers` and `invalidates_steps`
- For routes already frozen in
  `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`,
  descriptors MUST preserve checklist semantics for auth mode, required scope,
  execution class, and required success status codes.
- During rollout, mutating-vs-read-only classification remains sourced from the
  frozen checklist artifact until contract cutover package
  `20260410_rq_controller_state_contract_cutover` finalizes descriptor parity
  tests.

## Pipeline Step Identity
- Step IDs are stable contract keys, not display labels.
- The pipeline response is config/mod-aware; absent steps are intentionally
  unavailable for the current run.
- Pipeline step ID vocabulary (comprehensive baseline for DAG-executable
  pipeline nodes):

| Step ID | Canonical Operation ID | Typical Endpoint | Category |
|---|---|---|---|
| `upload-dem` | `rq_engine_upload_dem` | `/api/runs/{runid}/{config}/tasks/upload-dem/` | Watershed prep |
| `fetch-dem-and-build-channels` | `rq_engine_fetch_dem_and_build_channels` | `/api/runs/{runid}/{config}/fetch-dem-and-build-channels` | Watershed prep |
| `set-outlet` | `rq_engine_set_outlet` | `/api/runs/{runid}/{config}/set-outlet` | Watershed prep |
| `build-subcatchments-and-abstract-watershed` | `rq_engine_build_subcatchments_and_abstract_watershed` | `/api/runs/{runid}/{config}/build-subcatchments-and-abstract-watershed` | Watershed prep |
| `build-landuse` | `rq_engine_build_landuse` | `/api/runs/{runid}/{config}/build-landuse` | Core build |
| `build-soils` | `rq_engine_build_soils` | `/api/runs/{runid}/{config}/build-soils` | Core build |
| `build-climate` | `rq_engine_build_climate` | `/api/runs/{runid}/{config}/build-climate` | Core build |
| `prep-wepp-watershed` | `rq_engine_prep_wepp_watershed` | `/api/runs/{runid}/{config}/prep-wepp-watershed` | Core build |
| `run-wepp` | `rq_engine_run_wepp` | `/api/runs/{runid}/{config}/run-wepp` | Core run |
| `run-wepp-watershed` | `rq_engine_run_wepp_watershed` | `/api/runs/{runid}/{config}/run-wepp-watershed` | Core run |
| `upload-cli` | `rq_engine_upload_cli` | `/api/runs/{runid}/{config}/tasks/upload-cli/` | Climate variant |
| `upload-sbs` | `rq_engine_upload_sbs` | `/api/runs/{runid}/{config}/tasks/upload-sbs/` | Disturbed/BAER variant |
| `upload-cover-transform` | `rq_engine_upload_cover_transform` | `/api/runs/{runid}/{config}/tasks/upload-cover-transform` | Disturbed/BAER variant |
| `build-rusle` | `rq_engine_build_rusle` | `/api/runs/{runid}/{config}/build-rusle` | Mod build |
| `build-treatments` | `rq_engine_build_treatments` | `/api/runs/{runid}/{config}/build-treatments` | Mod build |
| `prepare-roads` | `rq_engine_prepare_roads` | `/api/runs/{runid}/{config}/prepare-roads` | Roads build |
| `run-roads` | `rq_engine_run_roads` | `/api/runs/{runid}/{config}/run-roads` | Roads run |
| `run-rhem` | `rq_engine_run_rhem` | `/api/runs/{runid}/{config}/run-rhem` | Mod run |
| `run-swat` | `rq_engine_run_swat` | `/api/runs/{runid}/{config}/run-swat` | Mod run |
| `run-ash` | `rq_engine_run_ash` | `/api/runs/{runid}/{config}/run-ash` | Disturbed/BAER run |
| `run-debris-flow` | `rq_engine_run_debris_flow` | `/api/runs/{runid}/{config}/run-debris-flow` | Disturbed/BAER run |
| `run-omni` | `rq_engine_run_omni` | `/api/runs/{runid}/{config}/run-omni` | OMNI run |
| `run-omni-contrasts` | `rq_engine_run_omni_contrasts` | `/api/runs/{runid}/{config}/run-omni-contrasts` | OMNI run |
| `acquire-openet-ts` | `rq_engine_acquire_openet_ts` | `/api/runs/{runid}/{config}/acquire-openet-ts` | Data acquisition |
| `acquire-rap-ts` | `rq_engine_acquire_rap_ts` | `/api/runs/{runid}/{config}/acquire-rap-ts` | Data acquisition |
| `acquire-polaris` | `rq_engine_acquire_polaris` | `/api/runs/{runid}/{config}/acquire-polaris` | Data acquisition |
| `run-wepp-npprep` | `rq_engine_run_wepp_npprep` | `/api/runs/{runid}/{config}/run-wepp-npprep` | Bootstrap/no-prep run |
| `run-wepp-watershed-noprep` | `rq_engine_run_wepp_watershed_noprep` | `/api/runs/{runid}/{config}/run-wepp-watershed-no-prep` | Bootstrap/no-prep run |
| `run-swat-noprep` | `rq_engine_run_swat_noprep` | `/api/runs/{runid}/{config}/run-swat-noprep` | Bootstrap/no-prep run |

- `pipeline.steps[]` for a specific `runid/config` MUST be a deterministic subset
  of this vocabulary.
- `pipeline.steps[]` MUST NOT include non-pipeline lifecycle/auth/export/report
  operations.
- `step_id` values are authoritative for DAG orchestration.

### Non-Pipeline Run-Scoped Operations (Orchestration-Relevant Subset)

The operation IDs below are a non-exhaustive subset of run-scoped actions
discoverable from `/api/runs/{runid}/{config}/endpoints`. They are listed here
because they are common orchestration-adjacent operations, but they are not
pipeline DAG nodes and MUST NOT appear in `pipeline.steps[]`.

For the exhaustive current run-scoped inventory baseline, use:
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

| Canonical Operation ID | Typical Endpoint | Class |
|---|---|---|
| `rq_engine_update_swat_print_prt` | `/api/runs/{runid}/{config}/swat/print-prt` | Config mutation |
| `rq_engine_update_swat_print_prt_meta` | `/api/runs/{runid}/{config}/swat/print-prt/meta` | Config mutation |
| `rq_engine_run_omni_contrasts_dry_run` | `/api/runs/{runid}/{config}/run-omni-contrasts-dry-run` | Read-only analysis |
| `rq_engine_delete_omni_contrasts` | `/api/runs/{runid}/{config}/delete-omni-contrasts` | Lifecycle mutation |
| `rq_engine_post_dss_export` | `/api/runs/{runid}/{config}/post-dss-export-rq` | Export/data job |
| `rq_engine_export_features_submit` | `/api/runs/{runid}/{config}/export/features` | Export job |
| `rq_engine_fork_project` | `/api/runs/{runid}/{config}/fork` | Run lifecycle |
| `rq_engine_archive_run` | `/api/runs/{runid}/{config}/archive` | Run lifecycle |
| `rq_engine_restore_archive` | `/api/runs/{runid}/{config}/restore-archive` | Run lifecycle |
| `rq_engine_delete_archive` | `/api/runs/{runid}/{config}/delete-archive` | Run lifecycle |
| `rq_engine_bootstrap_enable` | `/api/runs/{runid}/{config}/bootstrap/enable` | Bootstrap lifecycle |
| `rq_engine_bootstrap_checkout` | `/api/runs/{runid}/{config}/bootstrap/checkout` | Bootstrap lifecycle |
| `rq_engine_bootstrap_mint_token` | `/api/runs/{runid}/{config}/bootstrap/mint-token` | Bootstrap lifecycle |
| `rq_engine_issue_session_token` | `/api/runs/{runid}/{config}/session-token` | Session/auth bridge |

- When new agent-facing run-scoped routes are added to the frozen route
  checklist, this section SHOULD be reviewed and updated when needed to keep
  orchestration-relevant subset coverage accurate.

## Step Execution Semantics
- Each pipeline step SHOULD include:
  - `execution_mode`: `sync` or `async`
  - `allow_rerun`: boolean indicating whether rerun is contract-allowed
  - `parallel_group`: optional stable key identifying parallel-safe cohorts
- `status` MUST be one of:
  - `pending`
  - `blocked`
  - `ready`
  - `running`
  - `completed`
  - `failed`
  - `canceled`
  - `skipped`
- Terminal step statuses are:
  - `completed`, `failed`, `canceled`, `skipped`
- For `async` steps in `running` state, payload SHOULD include `active_job_id`.
- For `sync` steps, `active_job_id` MUST be absent.
- If `last_attempt.outcome` is present, it MUST be one of:
  - `finished`
  - `failed`
  - `stopped`
  - `canceled`
- `can_run_now` MUST be true only when `status=ready` and
  `preconditions_met=true`.
- When a previously `completed` step becomes `ready` because of downstream
  invalidation, pipeline/readiness payloads MUST expose the cause via
  `recent_invalidations` and/or per-step `invalidated_by_operation_id`.
- Parallel execution is opt-in only.
- Agents SHOULD treat steps as parallel-safe only when:
  - dependencies are satisfied,
  - no `blocks` edge exists between them,
  - both steps declare the same non-empty `parallel_group`.
- If `parallel_group` is absent, clients SHOULD assume sequential execution for
  safety.
- Clients MUST NOT infer parallel safety from similar dependency graphs alone.

### Pipeline Status Transition Table

| Current | Allowed Next |
|---|---|
| `pending` | `ready`, `blocked`, `skipped` |
| `blocked` | `ready`, `skipped` |
| `ready` | `running`, `skipped` |
| `running` | `completed`, `failed`, `canceled` |
| `failed` | `ready`, `skipped` |
| `canceled` | `ready`, `skipped` |
| `completed` | `ready` (only if invalidated and `allow_rerun=true`) |
| `skipped` | *(terminal; no transitions)* |

## Mutation Result Contract (Normative)

This section specifies target-profile behavior for controller-state cutover.
Until roadmap cutover package `20260410_rq_controller_state_contract_cutover`,
existing frozen routes may return legacy success payload variants documented in
the 2026-02-08 freeze artifacts.

| `execution_mode` | Required Success Fields | Next Action Contract |
|---|---|---|
| `async` | `job_id` or `job_ids`, `status_url`, `message` | Poll `status_url` (or `next_poll_url`) at `suggested_poll_interval_seconds` until `jobstatus.status` is in configured terminal statuses. |
| `sync` | `message` (and optional `result`) | Treat HTTP 2xx as terminal success. |
| `sync_redirect` | `message`, `result.run_context.*`, redirect target (`redirect_url` and/or `Location` header) | Use `result.run_context` as canonical machine source; redirect is optional UX/navigation signal. |

- Operation descriptors MUST include a `result_contract` object that encodes this
  mode-specific behavior without client heuristics.

### Canonical Async Poll Status Values

- `jobstatus.status` success payload values are constrained to:
  - `queued`
  - `started`
  - `deferred`
  - `scheduled`
  - `finished`
  - `failed`
  - `stopped`
  - `canceled`
- Non-terminal statuses:
  - `queued`, `started`, `deferred`, `scheduled`
- Terminal success status:
  - `finished`
- Terminal failure statuses:
  - `failed`, `stopped`, `canceled`
- `jobstatus` SHOULD expose progress for long-running jobs:
  - `progress.completed`
  - `progress.total`
  - `progress.unit`
  - `progress.percent`
  - `progress.updated_at`

### Setup/Fork Run Context Requirements

- Operations that create or fork a run MUST return:
  - `result.run_context.runid`
  - `result.run_context.config`
  - `result.run_context.run_url`
  - `result.run_context.run_api_base_url`
  - `result.run_context.endpoints_url`
  - `result.run_context.pipeline_url`
  - `result.run_context.readiness_url`
  - `result.run_context.outputs_url`

## Controller Registry Payload

```json
{
  "contract_version": "1.0.0-draft",
  "deployment_revision": "2026-04-10.1",
  "run_state_revision": "runstate:abc123:481",
  "runid": "abc123",
  "config": "disturbed9002_wbt",
  "active_mods": ["disturbed", "wepp"],
  "endpoints_url": "/rq-engine/api/runs/abc123/disturbed9002_wbt/endpoints",
  "pipeline_url": "/rq-engine/api/runs/abc123/disturbed9002_wbt/pipeline",
  "readiness_url": "/rq-engine/api/runs/abc123/disturbed9002_wbt/readiness",
  "outputs_url": "/rq-engine/api/runs/abc123/disturbed9002_wbt/outputs",
  "controllers": [
    {
      "name": "roads",
      "enabled": true,
      "state_url": "/rq-engine/api/runs/abc123/disturbed9002_wbt/controllers/roads/state",
      "schema_url": "/rq-engine/api/runs/abc123/disturbed9002_wbt/controllers/roads/schema",
      "hints_url": "/rq-engine/api/runs/abc123/disturbed9002_wbt/controllers/roads/hints",
      "templates_url": "/rq-engine/api/runs/abc123/disturbed9002_wbt/controllers/roads/templates"
    }
  ]
}
```

## Controller State Payload

```json
{
  "contract_version": "1.0.0-draft",
  "deployment_revision": "2026-04-10.1",
  "run_state_revision": "runstate:abc123:481",
  "controller": "roads",
  "state_version": 1,
  "schema_version": 1,
  "controller_version": "2026.04.10",
  "updated_at": "2026-04-10T10:22:31Z",
  "etag": "W/\"roads:abc123:6f58d0\"",
  "fields": {
    "enabled": true,
    "road_width_m": 4.5,
    "slope_range": [0.0, 45.0]
  },
  "warnings": []
}
```

## Controller Schema Payload

- Field constraints MUST declare `constraint_mode`:
  - `static`: invariant constraint bundled with schema version.
  - `run_resolved`: constraint resolved from current run/geography/state and
    therefore tied to `run_state_revision`.
- When `constraint_mode=run_resolved`, field metadata SHOULD include:
  - `constraint_source` (for example `geospatial_metadata`, `controller_state`)
  - `resolved_at` (timestamp used to derive dynamic options)

```json
{
  "contract_version": "1.0.0-draft",
  "deployment_revision": "2026-04-10.1",
  "run_state_revision": "runstate:abc123:481",
  "controller": "climate",
  "schema_version": 1,
  "fields": {
    "climate_mode": {
      "type": "integer",
      "required": true,
      "constraint_mode": "run_resolved",
      "constraint_source": "geospatial_metadata",
      "resolved_at": "2026-04-10T10:22:28Z",
      "enum": [0, 2, 6, 7, 11],
      "enum_labels": {
        "0": "Vanilla (synthetic CLIGEN)",
        "2": "Observed (station file)",
        "6": "Observed Database",
        "7": "Future Database",
        "11": "GridMet+PRISM"
      },
      "enum_available": [0, 6, 11],
      "enum_requires": {
        "2": ["observed_start_year", "observed_end_year"],
        "6": ["observed_start_year", "observed_end_year"],
        "7": ["future_start_year", "future_end_year"]
      }
    },
    "climatestation": {
      "type": "string",
      "required": false,
      "constraint_mode": "run_resolved",
      "constraint_source": "geospatial_metadata",
      "available_if": {
        "field": "climate_mode",
        "op": "in",
        "value": [2, 6]
      }
    }
  }
}
```

## Run-Scoped Endpoint Catalog Payload

```json
{
  "contract_version": "1.0.0-draft",
  "deployment_revision": "2026-04-10.1",
  "run_state_revision": "runstate:abc123:481",
  "operations": [
    {
      "operation_id": "rq_engine_geospatial_metadata",
      "run_scoped": true,
      "method": "GET",
      "path": "/api/runs/{runid}/{config}/geospatial-metadata",
      "accepted_auth": ["bearer_jwt", "session_cookie_same_origin"],
      "auth_requirements": {
        "bearer_jwt": {
          "required_scope": ["rq:read"]
        },
        "session_cookie_same_origin": {
          "same_origin_required": true
        }
      },
      "error_catalog_url": "/rq-engine/api/runs/abc123/disturbed9002_wbt/endpoints/rq_engine_geospatial_metadata/errors",
      "write_precondition": {
        "required": false,
        "accepted": [],
        "conflict_status_code": 409,
        "conflict_error_code": "stale_run_state"
      },
      "idempotency_policy": {
        "supported": false,
        "key_locations": [],
        "dedupe_window_seconds": 0,
        "replay_behavior": "return_original_success",
        "mismatch_status_code": 409,
        "mismatch_error_code": "idempotency_key_conflict"
      },
      "execution_mode": "sync",
      "returns_job": false,
      "job_key": null,
      "content_types": ["application/json"],
      "file_fields": [],
      "success_status_codes": [200],
      "response_mode": "json",
      "result_contract": {
        "kind": "sync_result",
        "required_response_fields": ["dem_coverage", "recommended_defaults"],
        "terminal_signal": "http_status_2xx"
      },
      "estimated_duration": {
        "bucket": "fast",
        "typical_seconds": 1
      },
      "batch_mode_behavior": "n/a",
      "base_project_behavior": "allowed",
      "mutates_controllers": [],
      "invalidates_steps": []
    },
    {
      "operation_id": "rq_engine_build_climate",
      "run_scoped": true,
      "method": "POST",
      "path": "/api/runs/{runid}/{config}/build-climate",
      "accepted_auth": ["bearer_jwt"],
      "auth_requirements": {
        "bearer_jwt": {
          "required_scope": ["rq:enqueue"]
        }
      },
      "error_catalog_url": "/rq-engine/api/runs/abc123/disturbed9002_wbt/endpoints/rq_engine_build_climate/errors",
      "write_precondition": {
        "required": true,
        "accepted": ["x_run_state_match", "expected_run_state_revision"],
        "conflict_status_code": 409,
        "conflict_error_code": "stale_run_state"
      },
      "idempotency_policy": {
        "supported": true,
        "key_locations": ["header:Idempotency-Key"],
        "dedupe_window_seconds": 86400,
        "replay_behavior": "return_original_success",
        "mismatch_status_code": 409,
        "mismatch_error_code": "idempotency_key_conflict"
      },
      "execution_mode": "async",
      "returns_job": true,
      "job_key": "build_climate_rq",
      "content_types": ["application/json", "application/x-www-form-urlencoded"],
      "file_fields": [],
      "success_status_codes": [200],
      "response_mode": "json",
      "result_contract": {
        "kind": "async_job",
        "required_response_fields": ["job_id", "status_url", "message"],
        "next_poll_url_field": "status_url",
        "terminal_signal": "jobstatus.status in terminal_*_statuses",
        "status_field": "status",
        "non_terminal_statuses": ["queued", "started", "deferred", "scheduled"],
        "terminal_success_statuses": ["finished"],
        "terminal_failure_statuses": ["failed", "stopped", "canceled"],
        "suggested_poll_interval_seconds": 5,
        "progress_field": "progress"
      },
      "estimated_duration": {
        "bucket": "medium",
        "typical_seconds": 120
      },
      "batch_mode_behavior": "n/a",
      "base_project_behavior": "allowed",
      "mutates_controllers": ["climate"],
      "invalidates_steps": ["run-wepp", "run-wepp-watershed"]
    },
    {
      "operation_id": "rq_engine_upload_sbs",
      "run_scoped": true,
      "method": "POST",
      "path": "/api/runs/{runid}/{config}/tasks/upload-sbs/",
      "accepted_auth": ["bearer_jwt"],
      "auth_requirements": {
        "bearer_jwt": {
          "required_scope": ["rq:enqueue"]
        }
      },
      "error_catalog_url": "/rq-engine/api/runs/abc123/disturbed9002_wbt/endpoints/rq_engine_upload_sbs/errors",
      "write_precondition": {
        "required": true,
        "accepted": ["x_run_state_match", "expected_run_state_revision"],
        "conflict_status_code": 409,
        "conflict_error_code": "stale_run_state"
      },
      "idempotency_policy": {
        "supported": true,
        "key_locations": ["header:Idempotency-Key"],
        "dedupe_window_seconds": 86400,
        "replay_behavior": "return_original_success",
        "mismatch_status_code": 409,
        "mismatch_error_code": "idempotency_key_conflict"
      },
      "execution_mode": "sync",
      "returns_job": false,
      "job_key": null,
      "content_types": ["multipart/form-data"],
      "file_fields": [
        {
          "name": "input_upload_sbs",
          "required": true,
          "allowed_extensions": [".tif", ".tiff", ".asc"],
          "allowed_media_types": ["image/tiff", "application/x-aaigrid"],
          "max_bytes": 209715200,
          "crs_requirements": {
            "mode": "must_align_with_dem",
            "allow_reprojection": true
          },
          "extent_requirements": {
            "mode": "must_cover_watershed_extent"
          },
          "resolution_requirements": {
            "mode": "within_dem_resolution_tolerance"
          },
          "value_semantics": {
            "classification_type": "burn_severity",
            "allowed_value_map": {
              "0": "unburned",
              "1": "low",
              "2": "moderate",
              "3": "high"
            }
          }
        }
      ],
      "success_status_codes": [200],
      "response_mode": "json",
      "result_contract": {
        "kind": "sync_result",
        "required_response_fields": ["message"],
        "terminal_signal": "http_status_2xx"
      },
      "estimated_duration": {
        "bucket": "fast",
        "typical_seconds": 8
      },
      "batch_mode_behavior": "n/a",
      "base_project_behavior": "allowed",
      "mutates_controllers": ["disturbed", "soils", "landuse"],
      "invalidates_steps": ["build-soils", "build-landuse", "run-wepp", "run-wepp-watershed"]
    },
    {
      "operation_id": "rq_engine_fork_project",
      "run_scoped": true,
      "method": "POST",
      "path": "/api/runs/{runid}/{config}/fork",
      "accepted_auth": ["bearer_jwt", "captcha"],
      "auth_requirements": {
        "bearer_jwt": {
          "required_scope": ["rq:enqueue"]
        },
        "captcha": {
          "challenge_required": true,
          "requires_public_run": true,
          "required_if_no_valid_bearer": true
        }
      },
      "error_catalog_url": "/rq-engine/api/runs/abc123/disturbed9002_wbt/endpoints/rq_engine_fork_project/errors",
      "write_precondition": {
        "required": true,
        "accepted": ["x_run_state_match", "expected_run_state_revision"],
        "conflict_status_code": 409,
        "conflict_error_code": "stale_run_state"
      },
      "idempotency_policy": {
        "supported": true,
        "key_locations": ["header:Idempotency-Key"],
        "dedupe_window_seconds": 86400,
        "replay_behavior": "return_original_success",
        "mismatch_status_code": 409,
        "mismatch_error_code": "idempotency_key_conflict"
      },
      "execution_mode": "async",
      "returns_job": true,
      "job_key": "fork_rq",
      "content_types": ["application/json", "application/x-www-form-urlencoded"],
      "file_fields": [],
      "success_status_codes": [200],
      "response_mode": "json",
      "result_contract": {
        "kind": "async_job",
        "required_response_fields": [
          "job_id",
          "status_url",
          "message",
          "result.run_context.runid",
          "result.run_context.config",
          "result.run_context.run_url",
          "result.run_context.run_api_base_url",
          "result.run_context.endpoints_url",
          "result.run_context.pipeline_url",
          "result.run_context.readiness_url",
          "result.run_context.outputs_url"
        ],
        "next_poll_url_field": "status_url",
        "terminal_signal": "jobstatus.status in terminal_*_statuses",
        "status_field": "status",
        "non_terminal_statuses": ["queued", "started", "deferred", "scheduled"],
        "terminal_success_statuses": ["finished"],
        "terminal_failure_statuses": ["failed", "stopped", "canceled"],
        "suggested_poll_interval_seconds": 4
      },
      "estimated_duration": {
        "bucket": "medium",
        "typical_seconds": 45
      },
      "batch_mode_behavior": "n/a",
      "base_project_behavior": "allowed",
      "mutates_controllers": [],
      "invalidates_steps": []
    },
    {
      "operation_id": "rq_engine_issue_session_token",
      "run_scoped": true,
      "method": "POST",
      "path": "/api/runs/{runid}/{config}/session-token",
      "accepted_auth": ["bearer_jwt", "session_cookie_same_origin"],
      "auth_requirements": {
        "bearer_jwt": {
          "required_scope": ["rq:status"]
        },
        "session_cookie_same_origin": {
          "same_origin_required": true,
          "public_run_fallback": true
        }
      },
      "error_catalog_url": "/rq-engine/api/runs/abc123/disturbed9002_wbt/endpoints/rq_engine_issue_session_token/errors",
      "write_precondition": {
        "required": false,
        "accepted": [],
        "conflict_status_code": 409,
        "conflict_error_code": "stale_run_state"
      },
      "idempotency_policy": {
        "supported": false,
        "key_locations": [],
        "dedupe_window_seconds": 0,
        "replay_behavior": "reject_duplicate",
        "duplicate_replay_status_code": 409,
        "duplicate_replay_error_code": "idempotency_replay_rejected",
        "mismatch_status_code": 409,
        "mismatch_error_code": "idempotency_key_conflict"
      },
      "execution_mode": "sync",
      "returns_job": false,
      "job_key": null,
      "content_types": ["application/json"],
      "file_fields": [],
      "success_status_codes": [200],
      "response_mode": "json",
      "result_contract": {
        "kind": "sync_result",
        "required_response_fields": ["message", "result.token"],
        "terminal_signal": "http_status_2xx"
      },
      "estimated_duration": {
        "bucket": "fast",
        "typical_seconds": 1
      },
      "batch_mode_behavior": "n/a",
      "base_project_behavior": "allowed",
      "mutates_controllers": [],
      "invalidates_steps": []
    }
  ]
}
```

## Setup Endpoint Catalog Payload (Non-Run-Scoped)

```json
{
  "contract_version": "1.0.0-draft",
  "deployment_revision": "2026-04-10.1",
  "operations": [
    {
      "operation_id": "rq_engine_list_configs",
      "run_scoped": false,
      "method": "GET",
      "path": "/api/configs",
      "accepted_auth": ["session_cookie_same_origin", "bearer_jwt"],
      "auth_requirements": {
        "bearer_jwt": {
          "required_scope": ["rq:read"]
        },
        "session_cookie_same_origin": {
          "same_origin_required": true
        }
      },
      "bootstrap_access_note": "Deployments MAY expose this endpoint in open-read mode; if JWT is required, clients need a pre-run token before discovery.",
      "error_catalog_url": "/rq-engine/api/endpoints/rq_engine_list_configs/errors",
      "write_precondition": {
        "required": false,
        "accepted": [],
        "conflict_status_code": 409,
        "conflict_error_code": "stale_run_state"
      },
      "idempotency_policy": {
        "supported": false,
        "key_locations": [],
        "dedupe_window_seconds": 0,
        "replay_behavior": "return_original_success",
        "mismatch_status_code": 409,
        "mismatch_error_code": "idempotency_key_conflict"
      },
      "execution_mode": "sync",
      "returns_job": false,
      "job_key": null,
      "content_types": ["application/json"],
      "file_fields": [],
      "success_status_codes": [200],
      "response_mode": "json",
      "result_contract": {
        "kind": "sync_result",
        "required_response_fields": ["configs"],
        "terminal_signal": "http_status_2xx"
      },
      "estimated_duration": {
        "bucket": "fast",
        "typical_seconds": 1
      },
      "batch_mode_behavior": "n/a",
      "base_project_behavior": "n/a",
      "mutates_controllers": [],
      "invalidates_steps": []
    },
    {
      "operation_id": "rq_engine_create",
      "run_scoped": false,
      "method": "POST",
      "path": "/create/",
      "config_catalog_url": "/rq-engine/api/configs",
      "accepted_auth": ["rq_token", "bearer_jwt", "captcha"],
      "auth_requirements": {
        "rq_token": {
          "required_scope": ["rq:enqueue"]
        },
        "bearer_jwt": {
          "required_scope": ["rq:enqueue"]
        },
        "captcha": {
          "challenge_required": true,
          "required_if_no_authenticated_token": true
        }
      },
      "error_catalog_url": "/rq-engine/api/endpoints/rq_engine_create/errors",
      "write_precondition": {
        "required": false,
        "accepted": [],
        "conflict_status_code": 409,
        "conflict_error_code": "stale_run_state"
      },
      "idempotency_policy": {
        "supported": true,
        "key_locations": ["header:Idempotency-Key", "body:idempotency_key"],
        "dedupe_window_seconds": 86400,
        "replay_behavior": "return_original_success",
        "mismatch_status_code": 409,
        "mismatch_error_code": "idempotency_key_conflict"
      },
      "execution_mode": "sync_redirect",
      "returns_job": false,
      "job_key": null,
      "content_types": ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"],
      "file_fields": [],
      "success_status_codes": [303],
      "response_mode": "redirect",
      "result_contract": {
        "kind": "sync_redirect",
        "required_response_fields": [
          "message",
          "result.run_context.runid",
          "result.run_context.config",
          "result.run_context.run_url",
          "result.run_context.run_api_base_url",
          "result.run_context.endpoints_url",
          "result.run_context.pipeline_url",
          "result.run_context.readiness_url",
          "result.run_context.outputs_url"
        ],
        "location_header_required": true,
        "terminal_signal": "http_status_303"
      },
      "estimated_duration": {
        "bucket": "fast",
        "typical_seconds": 2
      },
      "batch_mode_behavior": "n/a",
      "base_project_behavior": "creates_new_run",
      "mutates_controllers": [],
      "invalidates_steps": []
    }
  ]
}
```

## Endpoint Schema Payload

```json
{
  "contract_version": "1.0.0-draft",
  "deployment_revision": "2026-04-10.1",
  "run_state_revision": "runstate:abc123:481",
  "operation_id": "rq_engine_run_wepp",
  "run_scoped": true,
  "method": "POST",
  "path": "/api/runs/{runid}/{config}/run-wepp",
  "operation_descriptor": {
    "accepted_auth": ["bearer_jwt"],
    "auth_requirements": {
      "bearer_jwt": {
        "required_scope": ["rq:enqueue"]
      }
    },
    "error_catalog_url": "/rq-engine/api/runs/abc123/disturbed9002_wbt/endpoints/rq_engine_run_wepp/errors",
    "write_precondition": {
      "required": true,
      "accepted": ["x_run_state_match", "expected_run_state_revision"],
      "conflict_status_code": 409,
      "conflict_error_code": "stale_run_state"
    },
    "idempotency_policy": {
      "supported": true,
      "key_locations": ["header:Idempotency-Key"],
      "dedupe_window_seconds": 86400,
      "replay_behavior": "return_original_success",
      "mismatch_status_code": 409,
      "mismatch_error_code": "idempotency_key_conflict"
    },
    "execution_mode": "async",
    "returns_job": true,
    "job_key": "run_wepp_rq",
    "content_types": ["application/json", "application/x-www-form-urlencoded"],
    "file_fields": [],
    "success_status_codes": [200],
    "response_mode": "json",
    "result_contract": {
      "kind": "async_job",
      "required_response_fields": ["job_id", "status_url", "message"],
      "next_poll_url_field": "status_url",
      "terminal_signal": "jobstatus.status in terminal_*_statuses",
      "status_field": "status",
      "non_terminal_statuses": ["queued", "started", "deferred", "scheduled"],
      "terminal_success_statuses": ["finished"],
      "terminal_failure_statuses": ["failed", "stopped", "canceled"],
      "suggested_poll_interval_seconds": 5,
      "progress_field": "progress"
    },
    "estimated_duration": {
      "bucket": "slow",
      "typical_seconds": 900
    },
    "batch_mode_behavior": "supports_batch_parent",
    "base_project_behavior": "allowed",
    "mutates_controllers": ["wepp", "soils"],
    "invalidates_steps": ["run-wepp-watershed"]
  },
  "schema_version": 1,
  "request": {
    "type": "object",
    "properties": {
      "clip_soils": {
        "type": "boolean",
        "constraint_mode": "static",
        "source_controller": "soils"
      },
      "clip_soils_depth": {
        "type": "number",
        "minimum": 0.0,
        "constraint_mode": "static",
        "source_controller": "soils"
      },
      "channel_critical_shear": {
        "type": "number",
        "minimum": 0.0,
        "constraint_mode": "run_resolved",
        "constraint_source": "controller_state",
        "source_controller": "wepp"
      },
      "sol_ver": {
        "type": "string",
        "source_controller": "soils",
        "constraint_mode": "run_resolved",
        "constraint_source": "controller_state",
        "enum_available": ["v2006", "v2018"],
        "enum_labels": {
          "v2006": "Legacy disturbed soil defaults",
          "v2018": "Updated disturbed soil defaults"
        },
        "available_if": {
          "field": "context.active_mods",
          "op": "contains",
          "value": "disturbed"
        },
        "required_if": {
          "field": "context.active_mods",
          "op": "contains",
          "value": "disturbed"
        }
      },
      "expected_run_state_revision": {
        "type": "string",
        "description": "Optimistic concurrency precondition when using body mode."
      }
    }
  },
  "responses": {
    "success": {
      "required": ["job_id", "status_url", "message"],
      "example": {
        "job_id": "rq-551",
        "status_url": "/rq-engine/api/jobstatus/rq-551",
        "message": "Job enqueued."
      }
    },
    "conflict": {
      "status_code": 409,
      "error_code": "stale_run_state"
    }
  }
}
```

For upload operations, request schemas SHOULD express conditional rules via
`available_if` and `required_if` predicates on relevant fields.
Upload `file_fields` metadata SHOULD include executable format constraints
(`allowed_extensions`, media types, max size, CRS, extent, resolution, and
value semantics where classification rasters are expected).

## Conditional Constraint Predicate Grammar

- `required_if` and `available_if` predicates MUST use this JSON grammar:
  - leaf predicate:
    - `field`: request field path or context path (for example
      `context.active_mods`)
    - `op`: one of `eq`, `ne`, `in`, `not_in`, `contains`, `gte`, `lte`,
      `exists`
    - `value`: scalar or array for the operator
  - composite predicate:
    - `all`: array of predicates (logical AND)
    - `any`: array of predicates (logical OR)
    - `not`: single predicate
- Unknown operators MUST be rejected as schema errors.
- Context paths MUST be documented by schema payloads (for example
  `context.active_mods`, `context.region`).

## Config Catalog Payload

```json
{
  "contract_version": "1.0.0-draft",
  "deployment_revision": "2026-04-10.1",
  "configs": [
    {
      "config_id": "disturbed9002_wbt",
      "display_name": "Disturbed Watershed (WBT)",
      "active_mods": ["disturbed", "wepp"],
      "supported_regions": ["conus"],
      "required_upload_steps": ["upload-sbs"],
      "recommended_for": ["post_fire", "debris_flow_ready"]
    },
    {
      "config_id": "lt_default_wbt",
      "display_name": "Long-Term Watershed (WBT)",
      "active_mods": ["wepp"],
      "supported_regions": ["conus", "europe"],
      "required_upload_steps": [],
      "recommended_for": ["baseline_watershed"]
    }
  ]
}
```

## Geospatial Metadata Payload

```json
{
  "contract_version": "1.0.0-draft",
  "deployment_revision": "2026-04-10.1",
  "run_state_revision": "runstate:abc123:481",
  "runid": "abc123",
  "config": "disturbed9002_wbt",
  "region": "conus",
  "dem_coverage": {
    "supported": true,
    "source": "3dep",
    "extent_bbox": [-117.34, 45.48, -116.91, 45.81]
  },
  "recommended_defaults": {
    "map_center": [-117.11, 45.64],
    "map_bounds": [-117.34, 45.48, -116.91, 45.81],
    "map_zoom": 11,
    "map_zoom_resolution_m_per_px": 9.6,
    "csa": 10.0,
    "mcl": 45.0
  },
  "dynamic_constraints": {
    "climate_mode": {
      "enum_available": [0, 6, 11]
    },
    "soils_mode": {
      "enum_available": ["ssurgo"]
    },
    "sol_ver": {
      "enum_available": ["v2006", "v2018"]
    }
  },
  "field_availability": {
    "map_center": {
      "state": "available"
    },
    "csa": {
      "state": "available"
    },
    "station_catalog": {
      "state": "pending",
      "reason_code": "awaiting_dem_fetch"
    }
  },
  "computed_at": "2026-04-10T10:22:31Z"
}
```

## Operation Error Catalog Payload

```json
{
  "contract_version": "1.0.0-draft",
  "deployment_revision": "2026-04-10.1",
  "run_state_revision": "runstate:abc123:481",
  "operation_id": "rq_engine_build_climate",
  "errors": [
    {
      "error_code": "missing_station_selection",
      "recoverable": true,
      "http_statuses": [400, 409],
      "recovery_actions": [
        {
          "operation_id": "rq_engine_build_climate",
          "required_fields": ["climatestation"]
        }
      ]
    },
    {
      "error_code": "climate_mode_unavailable_for_region",
      "recoverable": true,
      "http_statuses": [400],
      "recovery_actions": [
        {
          "operation_id": "rq_engine_build_climate",
          "required_fields": ["climate_mode"]
        }
      ]
    }
  ]
}
```

## Mutation Write Preconditions (Optimistic Concurrency)

- Run-scoped mutating operations that can change run/controller state MUST enforce
  `write_precondition` when `write_precondition.required=true`.
- Clients MUST satisfy the precondition by providing one of:
  - `X-Run-State-Match: <run_state_revision>` header (`x_run_state_match`
    mode), or
  - `expected_run_state_revision` request field (`expected_run_state_revision`
    mode).
- `If-Match` is reserved for standard HTTP entity-tag semantics and MUST NOT be
  overloaded with `run_state_revision`.
- If the provided precondition does not match current state, the server MUST
  reject the mutation with HTTP `409` and canonical error payload:

```json
{
  "error": {
    "message": "Run state changed since last read.",
    "code": "stale_run_state",
    "details": "expected=runstate:abc123:481 current=runstate:abc123:489"
  },
  "current_run_state_revision": "runstate:abc123:489"
}
```

## Idempotency And Retry Contract

- Mutating operations MUST declare `idempotency_policy` in their descriptors.
- When `idempotency_policy.supported=true`:
  - clients SHOULD send an idempotency key at one of `key_locations`;
  - when `replay_behavior=return_original_success`, replay with the same key and
    equivalent payload MUST return the original success contract (same canonical
    result shape);
  - when `replay_behavior=reject_duplicate`, replay with the same key and
    equivalent payload MUST return `duplicate_replay_status_code` with
    `duplicate_replay_error_code`;
  - replay with the same key and non-equivalent payload MUST return
    `mismatch_status_code` with `mismatch_error_code`.
- When `idempotency_policy.supported=false`:
  - clients MUST treat transport-level retries as potentially non-idempotent and
    re-read `pipeline`/`readiness` before retrying.

## Operation Defaults Payload

```json
{
  "contract_version": "1.0.0-draft",
  "deployment_revision": "2026-04-10.1",
  "run_state_revision": "runstate:abc123:481",
  "operation_id": "rq_engine_build_climate",
  "resolved_defaults": {
    "climate_mode": 11,
    "observed_start_year": 1990,
    "observed_end_year": 2020
  },
  "defaults_context": {
    "config": "disturbed9002_wbt",
    "active_mods": ["disturbed", "wepp"],
    "region": "conus"
  },
  "computed_at": "2026-04-10T10:22:31Z"
}
```

## Pipeline Payload

```json
{
  "contract_version": "1.0.0-draft",
  "deployment_revision": "2026-04-10.1",
  "run_state_revision": "runstate:abc123:481",
  "updated_at": "2026-04-10T10:22:31Z",
  "etag": "W/\"pipeline:abc123:481\"",
  "runid": "abc123",
  "config": "disturbed9002_wbt",
  "active_mods": ["disturbed", "wepp"],
  "recent_invalidations": [
    {
      "source_operation_id": "rq_engine_upload_sbs",
      "at": "2026-04-10T09:17:11Z",
      "invalidated_steps": ["build-soils", "build-landuse", "run-wepp", "run-wepp-watershed"]
    }
  ],
  "steps": [
    {
      "step_id": "fetch-dem-and-build-channels",
      "operation_id": "rq_engine_fetch_dem_and_build_channels",
      "status": "completed",
      "execution_mode": "async",
      "preconditions_met": true,
      "depends_on": [],
      "blocks": ["set-outlet"],
      "can_run_now": false,
      "allow_rerun": true,
      "parallel_group": "watershed_foundation",
      "endpoint": "/api/runs/{runid}/{config}/fetch-dem-and-build-channels",
      "method": "POST",
      "returns_job": true,
      "success_status_codes": [200],
      "estimated_duration_bucket": "slow",
      "estimated_duration_seconds": 180,
      "suggested_poll_interval_seconds": 5,
      "produces": [
        {
          "type": "controller_state",
          "target": "watershed.has_channels"
        }
      ],
      "last_attempt": {
        "job_id": "rq-111",
        "outcome": "finished",
        "ended_at": "2026-04-10T09:02:14Z",
        "error_code": null,
        "error_message": null,
        "recoverable": null,
        "recovery_hint": null
      }
    },
    {
      "step_id": "upload-sbs",
      "operation_id": "rq_engine_upload_sbs",
      "status": "completed",
      "execution_mode": "sync",
      "preconditions_met": true,
      "depends_on": ["build-subcatchments-and-abstract-watershed"],
      "blocks": ["build-soils"],
      "can_run_now": false,
      "allow_rerun": true,
      "parallel_group": null,
      "endpoint": "/api/runs/{runid}/{config}/tasks/upload-sbs/",
      "method": "POST",
      "returns_job": false,
      "success_status_codes": [200],
      "estimated_duration_bucket": "fast",
      "estimated_duration_seconds": 8,
      "request_content_type": "multipart/form-data",
      "required_fields": ["input_upload_sbs"],
      "produces": [
        {
          "type": "controller_state",
          "target": "mods.disturbed.sbs_uploaded"
        }
      ],
      "last_attempt": {
        "outcome": "finished",
        "ended_at": "2026-04-10T09:17:11Z",
        "error_code": null,
        "error_message": null,
        "recoverable": null,
        "recovery_hint": null
      }
    },
    {
      "step_id": "build-climate",
      "operation_id": "rq_engine_build_climate",
      "status": "running",
      "execution_mode": "async",
      "preconditions_met": true,
      "depends_on": ["build-subcatchments-and-abstract-watershed"],
      "blocks": ["run-wepp"],
      "can_run_now": false,
      "allow_rerun": true,
      "parallel_group": "prep_after_abstraction",
      "endpoint": "/api/runs/{runid}/{config}/build-climate",
      "method": "POST",
      "returns_job": true,
      "success_status_codes": [200],
      "estimated_duration_bucket": "medium",
      "estimated_duration_seconds": 120,
      "suggested_poll_interval_seconds": 5,
      "active_job_id": "rq-223",
      "progress": {
        "completed": 6,
        "total": 12,
        "unit": "subcatchments",
        "percent": 50.0,
        "updated_at": "2026-04-10T10:22:30Z"
      },
      "produces": [
        {
          "type": "controller_state",
          "target": "climate.built"
        }
      ],
      "last_attempt": {
        "job_id": "rq-222",
        "outcome": "failed",
        "ended_at": "2026-04-10T09:21:49Z",
        "error_code": "missing_station_selection",
        "error_message": "Missing station selection for selected climate mode.",
        "recoverable": true,
        "recovery_hint": "Set climatestation or switch to a compatible climate_mode."
      }
    }
  ]
}
```

## Readiness Payload

```json
{
  "contract_version": "1.0.0-draft",
  "deployment_revision": "2026-04-10.1",
  "run_state_revision": "runstate:abc123:481",
  "updated_at": "2026-04-10T10:22:31Z",
  "etag": "W/\"readiness:abc123:481\"",
  "run": {
    "has_dem": true,
    "mods": ["disturbed", "wepp"]
  },
  "watershed": {
    "channels_built": true,
    "outlet_set": true,
    "abstracted": true,
    "num_subcatchments": 42
  },
  "climate": {
    "built": false,
    "mode": null
  },
  "landuse": {
    "built": true,
    "mode": "nlcd"
  },
  "soils": {
    "built": true,
    "mode": "ssurgo"
  },
  "wepp": {
    "hillslopes_run": false,
    "watershed_run": false
  },
  "mods": {
    "disturbed": {
      "enabled": true,
      "sbs_uploaded": true,
      "sol_ver_selected": true
    },
    "features_export": {
      "enabled": false
    }
  },
  "invalidated_steps": [
    {
      "step_id": "build-soils",
      "operation_id": "rq_engine_build_soils",
      "source_operation_id": "rq_engine_upload_sbs",
      "invalidated_at": "2026-04-10T09:17:11Z"
    },
    {
      "step_id": "run-wepp",
      "operation_id": "rq_engine_run_wepp",
      "source_operation_id": "rq_engine_upload_sbs",
      "invalidated_at": "2026-04-10T09:17:11Z"
    }
  ],
  "blocking_issues": [
    {
      "issue_id": "issue_climate_station_missing",
      "code": "climate_station_missing",
      "message": "No climate station selected for the active climate mode.",
      "severity": "error",
      "controller": "climate",
      "field": "climatestation",
      "operation_id": "rq_engine_build_climate",
      "recoverable": true,
      "recovery_hint": "Set climatestation or choose a compatible climate_mode.",
      "recovery_actions": [
        {
          "operation_id": "rq_engine_build_climate",
          "required_fields": ["climatestation"],
          "priority": 1
        },
        {
          "operation_id": "rq_engine_build_climate",
          "required_fields": ["climate_mode"],
          "priority": 2
        }
      ]
    }
  ],
  "ready_operations": [
    {
      "operation_id": "rq_engine_build_soils",
      "step_id": "build-soils",
      "reason": "dependencies_satisfied"
    }
  ],
  "ineligible_operations": [
    {
      "operation_id": "rq_engine_run_wepp",
      "step_id": "run-wepp",
      "blocked_by_issue_ids": ["issue_climate_station_missing"]
    }
  ],
  "next_actionable_steps": [
    {
      "step_id": "build-climate",
      "operation_id": "rq_engine_build_climate",
      "priority": 1,
      "reason": "last_blocking_gap_before_run_wepp",
      "related_issue_ids": ["issue_climate_station_missing"]
    },
    {
      "step_id": "build-soils",
      "operation_id": "rq_engine_build_soils",
      "priority": 2,
      "reason": "invalidated_by_recent_mutation",
      "invalidated_by_operation_id": "rq_engine_upload_sbs"
    }
  ]
}
```

## Outputs Payload

```json
{
  "contract_version": "1.0.0-draft",
  "deployment_revision": "2026-04-10.1",
  "run_state_revision": "runstate:abc123:481",
  "updated_at": "2026-04-10T10:22:31Z",
  "etag": "W/\"outputs:abc123:481\"",
  "artifacts": [
    {
      "id": "features_export_latest",
      "kind": "zip",
      "producer_operation_id": "rq_engine_export_features_submit",
      "producer_step_id": "export-features",
      "producer_job_id": "rq-998",
      "produced_at": "2026-04-10T10:20:02Z",
      "source_run_state_revision": "runstate:abc123:479",
      "expires_at": "2026-04-17T10:20:02Z",
      "content_type": "application/zip",
      "size_bytes": 1834247,
      "sha256": "9c6c8f2de1d0fa4b92d3fa2f60f5f376fa2b36286f7496cff57d4c4555d52d7e",
      "result_source": "jobinfo.result",
      "download_url": "/rq-engine/api/runs/abc123/disturbed9002_wbt/export/features/job/rq-998/download",
      "download_url_params": {
        "runid": "abc123",
        "config": "disturbed9002_wbt",
        "job_id": "rq-998"
      },
      "download_url_template": "/rq-engine/api/runs/{runid}/{config}/export/features/job/{job_id}/download"
    }
  ],
  "exports": [
    {
      "operation_id": "rq_engine_export_geopackage",
      "path": "/api/runs/{runid}/{config}/export/geopackage",
      "response_mode": "file"
    }
  ]
}
```

## Output/Result Discovery Rules
- Pipeline `produces` entries declare post-success state/artifact expectations.
- `outputs` endpoint SHOULD provide the normalized artifact/export index for
  agents that do not want to infer outputs from controller state.
- Artifact entries MUST include concrete retrieval handles (`download_url`,
  `producer_job_id`) when immediately fetchable.
- Downloadable artifact entries MUST include trust/provenance metadata:
  - `produced_at`
  - `source_run_state_revision`
  - `expires_at` (or explicit `null` when non-expiring)
  - `content_type`
  - `size_bytes`
  - `sha256`
- If templated retrieval paths are emitted, artifact entries SHOULD include
  concrete substitution values (`download_url_params`) so clients do not infer
  placeholder bindings.
- `result_source` indicates where a caller should read success artifacts:
  - `controller_state`
  - `jobinfo.result`
  - direct export endpoint response

## Hints And Templates
- Hints payload remains optional UI/agent metadata for labels, grouping, and conditional enablement.
- Templates payload SHOULD include both:
  - static named templates (for reusable profiles),
  - run-resolved defaults (context-aware values).
- Template entries SHOULD be fully machine-actionable and include:
  - applicability (`configs`, `active_mods`, `regions`)
  - `parameters` (complete request payload, not only overrides)
  - `sufficient_without_overrides` (whether direct execution is safe)
  - optional `missing_required_fields` when further input is needed.

```json
{
  "contract_version": "1.0.0-draft",
  "deployment_revision": "2026-04-10.1",
  "run_state_revision": "runstate:abc123:481",
  "controller": "climate",
  "templates": [
    {
      "template_id": "disturbed_conus_default",
      "display_name": "Disturbed CONUS Default",
      "applicability": {
        "configs": ["disturbed9002_wbt"],
        "active_mods": ["disturbed", "wepp"],
        "regions": ["conus"]
      },
      "parameters": {
        "climate_mode": 11,
        "observed_start_year": 1990,
        "observed_end_year": 2020
      },
      "sufficient_without_overrides": true
    },
    {
      "template_id": "observed_station_required",
      "display_name": "Observed Station Climate",
      "applicability": {
        "configs": ["disturbed9002_wbt", "lt_default_wbt"],
        "active_mods": ["wepp"],
        "regions": ["conus"]
      },
      "parameters": {
        "climate_mode": 2,
        "observed_start_year": 1990,
        "observed_end_year": 2020
      },
      "sufficient_without_overrides": false,
      "missing_required_fields": ["climatestation"]
    }
  ],
  "run_resolved_defaults": {
    "climate_mode": 11
  }
}
```

## Caching And Conditional Requests
- Endpoints SHOULD return `ETag`.
- Clients MAY use `If-None-Match`.
- Servers SHOULD return `304` when payloads are unchanged.

## Cross-Endpoint Consistency
- All endpoints in this contract MUST emit the same `deployment_revision` for
  a stable deployment/configuration snapshot.
- Run-scoped endpoints in this contract MUST emit the same
  `run_state_revision` for a stable run-state snapshot.
- Agents performing multi-call planning SHOULD treat either revision changing as
  a stale-read boundary and re-fetch planning surfaces (`pipeline`,
  `readiness`, `outputs`, and operation defaults) before enqueueing the next
  step.

## Compatibility Rules
- Additive fields are allowed in payloads.
- Breaking schema behavior (type changes, field removals, enum narrowing) MUST increment `schema_version`.
- New controllers and steps MAY be added without version changes.

## Security Rules
- Responses MUST NOT include secrets, bearer tokens, CSRF tokens, or internal filesystem paths.
- Responses SHOULD avoid direct PII. If identity context is needed for hints/defaults, use role/capability booleans.

## Suggested Rollout Order
1. Setup bootstrap discovery: `/api/configs`, setup endpoint catalog/schema/defaults.
2. `pipeline` and `readiness` endpoints (orchestration substrate).
3. Endpoint-level schemas/defaults for `build-climate`, `build-landuse`, `build-soils`, `run-wepp`.
4. Upload operation metadata hardening (`upload-dem`, `upload-cli`, `upload-sbs`, `upload-cover-transform`).
5. Controller surfaces for `watershed`, `climate`, `landuse`, `soils`, `wepp`.
6. Operation error taxonomy (`.../endpoints/{operation_id}/errors`).
7. Optional/peripheral controllers (`roads`, `path_ce`, `features_export`).

## ExecPlan Work-Package Roadmap

Implementation of this contract SHOULD be executed as a sequenced set of
work-packages under `docs/work-packages/` (see `docs/work-packages/README.md`).
Each open/in-progress package MUST include:
- `package.md`
- `tracker.md`
- active ExecPlan at `prompts/active/<slug>_execplan.md`
When a package is closed, its active ExecPlan SHOULD be archived to
`prompts/completed/` with an outcome note.

| Order | Proposed Work-Package Folder | Primary Scope | Exit Criteria | Depends On | Progress State |
|---|---|---|---|---|---|
| 1 | `20260410_rq_controller_state_foundation` | Freeze contract join keys and descriptor invariants (`operation_id`, `step_id`, descriptor required fields), plus OpenAPI alignment plan. | Contract sections stabilized; unresolved schema ambiguities closed; implementation checklist accepted. | none | Complete |
| 2 | `20260410_rq_controller_state_setup_discovery` | Implement non-run-scoped setup surfaces: `/api/configs`, `/api/configs/{config}`, `/api/endpoints`, setup schema/defaults/errors endpoints. | Agent can discover valid configs and call `create` without out-of-band docs; setup discovery tests pass. | 1 | Planned |
| 3 | `20260410_rq_controller_state_orchestration_reads` | Implement run-scoped orchestration reads: `/pipeline`, `/readiness`, step state machine fields, invalidation lineage, next-action semantics. | Deterministic readiness->next_actionable_steps loop verified for baseline and disturbed configs. | 1 | Planned |
| 4 | `20260410_rq_controller_state_schema_defaults` | Implement controller and endpoint schema/default surfaces with `constraint_mode`, predicate grammar, and run-resolved defaults. | Schema/default endpoints provide machine-checkable constraints for core build/run operations. | 1, 3 | Planned |
| 5 | `20260410_rq_controller_state_geospatial_uploads` | Implement `/geospatial-metadata` and upload metadata contracts (format/CRS/extent/resolution/value semantics). | Agent can resolve first-step geospatial defaults and validate upload payloads pre-submit. | 2, 4 | Planned |
| 6 | `20260410_rq_controller_state_errors_progress_outputs` | Implement operation error catalogs, async progress signals, and `/outputs` artifact index with trust/provenance metadata. | Agent can recover from cataloged errors, poll with progress, and fetch artifacts from `outputs` only. | 3, 4, 5 | Planned |
| 7 | `20260410_rq_controller_state_auth_concurrency` | Enforce/auth-rollout for `rq:read` aliasing, accepted-auth metadata parity, optimistic concurrency, and idempotency behavior. | Mutation/read preconditions and auth modes match descriptor metadata in tests. | 2, 3, 4, 6 | Planned |
| 8 | `20260410_rq_controller_state_contract_cutover` | Contract freeze and cutover: update inventory/checklist artifacts, OpenAPI contract tests, docs pointers, and rollout notes. | All new endpoints present in frozen inventory/checklist; contract tests green; legacy doc pointers rehomed. | 2, 3, 4, 5, 6, 7 | Planned |

- Progress state vocabulary for this roadmap:
  - `Planned`
  - `In Progress`
  - `Blocked`
  - `Complete`

- `Depends On` values in this table MUST be explicit comma-separated order
  numbers (for example `2, 3, 4`), not numeric ranges.

- For each package, update:
  - `docs/work-packages/<package>/tracker.md`
  - `PROJECT_TRACKER.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/*` when
    endpoint inventory/contract coverage changes.
- Recommended verification gates per package:
  - `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py`
  - focused rq-engine route tests touched by the package
  - `wctl doc-lint --path docs/schemas/rq-controller-state-contract.md`
    (and related schema docs when changed)

## Supported End-to-End Workflows
1. Existing run re-run (`runid/config` already exists).
2. Create/fork plus upload inputs, bootstrapped from non-run-scoped
   `/api/configs` and `/api/endpoints` discovery then continued via run-scoped
   discovery once a `runid/config` is known.
3. Prep/build/run orchestration through pipeline/readiness.
4. Export/download output discovery via `outputs` and export operations.

## Change Management
- When this draft is implemented:
  - add endpoints to `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - add route rows to `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
  - update `docs/schemas/rq-engine-agent-api-contract.md`
  - add OpenAPI/contract tests in `tests/microservices/`
