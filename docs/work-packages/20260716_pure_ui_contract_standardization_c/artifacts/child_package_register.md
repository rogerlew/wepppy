# Pure UI Contract Child Package Register

**Register version**: 1.2 contractual baseline
**Last updated**: 2026-07-21 UTC
**Authority**: Stable IDs define package boundaries; dated package directories
are created only when work starts.
**Total**: 73 execution units: 4 governance, 2 bounded remediations, 39
run-domain, 9 shared-foundation, and 19 non-run/stateful surface packages.
GOV-00 is the existing umbrella at
`docs/work-packages/20260716_pure_ui_contract_standardization_c/`; GOV-00A is the
active ratification child at
`docs/work-packages/20260716_pure_ui_contract_ratification/`; the remaining 69
receive dated directories only when started. REM-01 is the operator-authorized
bounded remediation at
`docs/work-packages/20260720_omni_mod_state_sync/`. REM-02 is the
operator-authorized bounded remediation at
`docs/work-packages/20260721_runs_ttl_deletion_catalog/`.

## Boundary and Review Rules

Every row is a contractually registered, independently closable boundary. Each
package must use the reusable child-package prompt, create an active ExecPlan,
repeat security triage, retain two raw/verbatim independent reviews, and record
a separate primary-agent disposition with post-fix confirmation.

Registration is binding now. `planned` means execution has not started; it does
not mean the contract is optional. Evidence grades such as `unverified`,
`documented`, and `verified` describe implementation conformance only. Removing
or excluding a registered obligation requires explicit operator approval and
dual independent review.

Audit-only documentation normally starts with security impact `none`. Before a
discovered remediation is implemented, re-triage immediately. Auth/session/
CSRF/CAP, public routes, uploads/downloads, file/path handling, queue wiring,
worker subprocesses, CI/deployment, secrets, tokens, and external egress are
`high` by default.

Split a registered package before implementation when:

- more than one unrelated high-security remediation is required;
- a shared macro/helper change fans out beyond the package's mapped consumers;
- baseline and contract work cannot finish within four focused weeks;
- separate route/state owners require independent compatibility decisions; or
- one member cannot reach the same evidence grade as the rest of the package.

An audit may close a contract as `documented` when material evidence is missing,
but it cannot mark that contract `verified`. The package must register the
bounded follow-up needed to obtain the evidence.

## Dependency Spine

The required control-plane order is:

    GOV-00 population and register
      -> GOV-00A contractual standard ratification
      -> SHR-01 through SHR-04B shared foundations
      -> DOM-01 WATAR pilot
      -> GOV-01 change-aware maintenance gate
      -> remaining domain/shared/surface packages
      -> GOV-99 authority cutover and closeout

Read-only reconnaissance may run ahead. The WATAR contract is not marked
`verified` until SHR-01 through SHR-04B are complete and their conclusions are
exercised by the pilot. Later implementation packages do not bypass the
standard, WATAR pilot, maintenance gate, or applicable shared foundations.
Every row after GOV-01 therefore inherits GOV-00, GOV-00A, GOV-01, and its applicable
shared-foundation dependencies; row-level dependencies name additional ordering
constraints. GOV-00A, SHR-01 through SHR-04B, and DOM-01 are the deliberate
pre-GOV-01 ratification/foundation/pilot exceptions shown explicitly.

REM-01 is a second, defect-scoped pre-GOV-01 exception authorized on 2026-07-20
under `docs/standards/contract-first-change-standard.md` section "Bounded
Cross-Owner Remediation." It borrows only the registered source and behavior
listed below. It does not execute or advance DOM-02, DOM-25A, or DOM-25B and
does not waive their dependencies for any other work.

`GOV-00A-M1A` is the separately closable bounded-remediation governance
milestone. Its accepted standalone ancestor is sufficient only for REM-01; the
remaining GOV-00A deliverables stay open.

`GOV-00A-M1B` is the separately closable bounded-remediation governance
milestone proposed only for REM-02. It requires its own dual review, disposition,
and standalone ancestor. It borrows no authority from M1A, and it cannot advance
SURF-06 or any other package.

Dependency shorthand expands exactly as follows:

- `SHR-01..04B` = SHR-01, SHR-02, SHR-03A, SHR-03B, SHR-04A, SHR-04B.
- `SHR-02..04B` = SHR-02, SHR-03A, SHR-03B, SHR-04A, SHR-04B.
- `ALL-DOM` = DOM-01, DOM-02, DOM-03, DOM-04A, DOM-04B, DOM-05, DOM-06,
  DOM-07, DOM-08A, DOM-08B, DOM-09, DOM-10, DOM-11A, DOM-11B, DOM-12,
  DOM-13A, DOM-13B, DOM-13C, DOM-13D, DOM-14A, DOM-14B, DOM-14C, DOM-15,
  DOM-16, DOM-17, DOM-18, DOM-19, DOM-20A, DOM-20B, DOM-21, DOM-22,
  DOM-23, DOM-24, DOM-25A, DOM-25B, DOM-26, DOM-27, DOM-28, DOM-29.
- `ALL-SHR` = SHR-01, SHR-02, SHR-03A, SHR-03B, SHR-04A, SHR-04B,
  SHR-05, SHR-06, SHR-07.
- `ALL-SURF` = SURF-01, SURF-02A, SURF-02B, SURF-03, SURF-04, SURF-05,
  SURF-06, SURF-07, SURF-08, SURF-09, SURF-10, SURF-11, SURF-12, SURF-13,
  SURF-14, SURF-15, SURF-16, SURF-17, SURF-18.

Named sets are register metadata and must be expanded to concrete edges by the
GOV-01 machine-readable manifest. GOV-99 is intentionally absent from all sets.

## Governance Packages

| ID | Proposed slug | Scope | Depends on | Risk / expected security | State |
| --- | --- | --- | --- | --- | --- |
| GOV-00 | Existing `20260716_pure_ui_contract_standardization_c` | Current umbrella: complete population, exclusions, contractual coverage, and frozen execution register | None | High contract risk; docs-only `none` | auditing |
| GOV-00A | Existing `20260716_pure_ui_contract_ratification` | Ratify canonical schema, contractual/evidence axes, contract-first authority, compatibility policy, contract template, and derived reader-index rules | GOV-00 | High contract risk; docs-only `none` | auditing |
| GOV-01 | `pure_ui_contract_maintenance_gate` | Source/contract/test manifest; full and change-aware checks; shared fan-out; reviewed no-impact attestations | GOV-00A, SHR-01..04B, DOM-01 | High regression risk; `low` unless CI/permissions change | planned |
| GOV-99 | `pure_ui_contract_authority_cutover` | Final coverage audit, stale-link replacement, current AGENTS/README/catalog authority cutover, archived-plan labels, and umbrella closeout | GOV-00, GOV-00A, GOV-01, ALL-DOM, ALL-SHR, ALL-SURF | Medium; docs-only `none` | planned |

## Bounded Remediation Packages

| ID | Dated package | Borrowed owners | Exact defect boundary | Depends on | Security | State |
| --- | --- | --- | --- | --- | --- | --- |
| REM-01 | `20260720_omni_mod_state_sync` | DOM-02, DOM-25A, DOM-25B | Omni Scenarios/Contrasts feature-registry menu availability; Mods checkbox and reason markup; `Ron.mods` enable/disable guards; runs-page section/preflight visibility and metadata; dynamic shared Omni controller remount; Dev/Root gates on contrast run/dry-run/delete plus canonical run access and Dev/Root on the CAP-gated report; focused tests and generated controller bundle only | GOV-00A-M1A | `high`: role-gated dynamic load, persisted mod mutation, contrast actions, and report data | completed / dual-reviewed |
| REM-02 | `20260721_runs_ttl_deletion_catalog` | SURF-06 | Read-only TTL policy/expiry projection for already-authorized catalog rows; one lifecycle table cell; dedicated Usersum documentation and focused catalog/template/doc tests only | GOV-00A-M1B | `high`: authenticated run-metadata presentation; no new access path or mutation | ratification in progress |

REM-01 excludes Omni scenario/contrast payload shapes, uploads, queue wiring or
execution semantics, artifacts, report content/formatting, overlays, deletion
semantics beyond the contrast endpoint's authorization gate, model parameters,
and all non-Omni Project shell behavior. Its final evidence is inherited as an input to the
later DOM-02, DOM-25A, and DOM-25B audits without changing their planned state.

REM-02 excludes TTL duration/calculation, access touching, policy toggling, GC,
run deletion, database/schema changes, catalog filtering/sorting, maps, delete
or poll controls, all permission/CSRF/RQ behavior, and deployment. Its final
evidence is inherited by SURF-06 without advancing the owner beyond this finite
presentation defect.

The exact REM-01 source boundary is limited to:

- `wepppy/weppcloud/feature_registry/{schema.py,runtime.py,feature_registry.yaml,specification.md}`;
- `wepppy/weppcloud/routes/nodb_api/project_bp.py` and
  `wepppy/weppcloud/routes/run_0/run_0_bp.py`;
- only the Dev/Root authorization boundary of
  `wepppy/microservices/rq_engine/omni_routes.py` contrast run, dry-run, and
  delete entry points; and only canonical run access plus Dev/Root
  authorization in the CAP-gated
  `wepppy/weppcloud/routes/nodb_api/omni_bp.py` contrast-report entry point;
- `wepppy/weppcloud/templates/header/_run_header_fixed.htm`,
  `wepppy/weppcloud/routes/run_0/templates/{runs0_pure.htm,run_page_bootstrap.js.j2}`;
- `wepppy/weppcloud/controllers_js/project.js` and the generated
  `wepppy/weppcloud/static/js/controllers-gl.js`;
- focused registry, project-route, run-render, Project-controller,
  `tests/microservices/test_rq_engine_omni_routes.py`, and
  `tests/weppcloud/routes/test_omni_bp_routes.py` tests named by the REM-01
  ExecPlan; and
- REM-01/GOV-00A documentation, review, tracker, and security artifacts.

The exact REM-02 source boundary is limited to:

- `wepppy/weppcloud/routes/user.py` and
  `wepppy/weppcloud/templates/user/runs2.html`;
- the read-only `read_ttl_state` consumption boundary in
  `wepppy/weppcloud/utils/run_ttl.py` (without modifying TTL policy logic);
- `wepppy/weppcloud/routes/usersum/docs_manifest.yaml`,
  `wepppy/weppcloud/routes/usersum/usersum.py`, and
  `wepppy/weppcloud/routes/usersum/weppcloud/run-ttl-deletion.md`;
- validation generator `python3 tools/usersum_docs_tool.py build-index --write
  --require-vendor-files`; ignore any dirty
  `wepppy/weppcloud/routes/usersum/generated/docs_index.json` unless separately
  authorized under the root AGENTS instruction;
- `tests/weppcloud/routes/test_user_meta_boundaries.py`,
  `tests/weppcloud/routes/test_user_runs_admin_scope.py`,
  `tests/weppcloud/routes/test_usersum_bp.py`, and
  `tests/weppcloud/test_usersum_template_wiring.py`; and
- REM-02/GOV-00A documentation, review, tracker, and security artifacts.

## Run-Domain Packages

These packages account for all 33 production entries in
`routes/run_0/templates/run_page_bootstrap.js.j2::createBootstrapEntries`.
Adjuncts that share one state/route boundary remain parented to the relevant
domain package.

| ID | Proposed slug | Bootstrap/controller scope | Primary source boundary | Depends on | Expected remediation security | State |
| --- | --- | --- | --- | --- | --- | --- |
| DOM-01 | `watar_ui_contract_pilot` | `ash` | `ash.js`, `ash_pure.htm`, WATAR/ash route, `Ash`, `run_ash_rq` | GOV-00A, SHR-01..04B | `high`: uploads, route, queue, persisted parameters | planned |
| DOM-02 | `project_shell_ui_contract` | `project` | `project.js`, run header, Project routes, `Ron`, SQL Run, readonly RQ; consumes SHR-05 Unitizer preferences | GOV-01, SHR-01..04B, SHR-05 | `high`: auth, readonly/public state, mutation/RQ | planned |
| DOM-03 | `team_collaboration_ui_contract` | `team` | `team.js`, team modal/form, project/team routes, SQL ownership | GOV-01, SHR-01..04B | `high`: owner/collaborator auth mutations | planned |
| DOM-04A | `map_orchestration_ui_contract` | `map`: orchestration, center/search/elevation/drilldown and public API | `map_gl.js`, map host, elevation/query routes; consumes SHR-01 `selection_utils.js` | GOV-01, SHR-01..04B | `low`; `high` if public query routes change | planned |
| DOM-04B | `map_layers_feature_ui_contract` | `map`: layer/scale/feature UI and model visualization partials | four `map_gl_*` helpers, layer resources, legends/overlays | DOM-04A | `low`; `high` if file/resource routes change | planned |
| DOM-05 | `channel_delineation_ui_contract` | `channel` | `channel_gl.js`, channel template, watershed routes, DEM upload/build RQ | DOM-04A | `high`: upload, route, queue/worker | planned |
| DOM-06 | `outlet_ui_contract` | `outlet` | `outlet_gl.js`, outlet template, watershed route, `set_outlet_rq` | DOM-04A | `high`: route mutation and queue | planned |
| DOM-07 | `subcatchment_ui_contract` | `subcatchment` | `subcatchments_gl.js`, subcatchments template, abstraction routes/RQ | DOM-04A, DOM-05, DOM-06 | `high`: route mutation and queue/worker | planned |
| DOM-08A | `landuse_build_ui_contract` | `landuse`: modes, catalog, build/upload and reload | landuse controller/base form/routes, `Landuse`, build RQ | GOV-01, SHR-01..04B | `high`: upload, route, queue/worker | planned |
| DOM-08B | `landuse_catalog_editor_ui_contract` | `landuse`: user-defined catalog and map editor | user-defined/map templates and catalog/mapping routes | DOM-08A | `high`: file/catalog/mapping mutation | planned |
| DOM-09 | `landuse_modifier_ui_contract` | `landuseModify` adjunct | `landuse_modify_gl.js`, modify template, map selection and route mutation | DOM-04A, DOM-08A | `high`: route/state mutation | planned |
| DOM-10 | `soils_ui_contract` | `soil` | soil controller/template, soils routes, `Soils`, build RQ | GOV-01, SHR-01..04B | `high`: uploads/files, route, queue/worker | planned |
| DOM-11A | `climate_catalog_build_ui_contract` | `climate`: catalog/station/mode/build lifecycle | climate controller/base form/routes, `Climate`, build RQ | GOV-01, SHR-01..04B | `high`: egress, route, queue/worker | planned |
| DOM-11B | `climate_upload_scaling_ui_contract` | `climate`: upload, scaling, GridMET/MXPT5 and auxiliary modes | upload/aux form sections and route families | DOM-11A | `high`: upload, egress, persisted options | planned |
| DOM-12 | `observed_ui_contract` | `observed` | observed controller/template/routes, `Observed`, Climate observed state | DOM-11A | `high` if upload/public route changes; otherwise `low` | planned |
| DOM-13A | `agfields_boundary_schema_ui_contract` | `agFields`: boundary, schema, subfield inventory | AgFields controller/form and boundary/schema/subfield routes/state | DOM-04A, DOM-08A, DOM-10, DOM-11A | `high`: uploads and geospatial files | planned |
| DOM-13B | `agfields_plant_mapping_ui_contract` | `agFields`: plant database and field/subfield mapping | plant/mapping form sections, routes and persisted state | DOM-13A | `high`: uploads/files and state mutation | planned |
| DOM-13C | `agfields_wepp_stage_ui_contract` | `agFields`: staged subfield WEPP execution | stages 1-4 UI/routes/state and RQ chain | DOM-13B, DOM-14A | `high`: multi-stage queues/workers | planned |
| DOM-13D | `agfields_watershed_ui_contract` | `agFields`: watershed schemes, suite jobs, overlays/results/clear | watershed/suite routes, state, artifacts and deletion | DOM-13C, DOM-04B | `high`: queues, artifacts, deletion | planned |
| DOM-14A | `wepp_core_ui_contract` | `wepp`: core payload, run lifecycle, job hints, base reports | `wepp.js`, base WEPP form/routes, `Wepp`, run/prep RQ | DOM-07, DOM-08A, DOM-10, DOM-11A | `high`: queue/worker and model persistence | planned |
| DOM-14B | `wepp_advanced_options_ui_contract` | `wepp`: WEPP advanced option partials and parsers | WEPP advanced templates/parsers/routes/state | DOM-14A | `high`: stored model options and queue inputs | planned |
| DOM-14C | `swat_cover_transform_ui_contract` | `wepp`: SWAT advanced options and cover-transform upload | SWAT partials/routes/state and upload path | DOM-14A, DOM-14B | `high`: upload, queue/worker, stored options | planned |
| DOM-15 | `bootstrap_control_ui_contract` | `bootstrap` | bootstrap controller/embedded form/routes, enable/checkout/disable RQ | DOM-14A | `high`: admin/auth, git refs/tokens, queues | planned |
| DOM-16 | `dss_export_ui_contract` | `dssExport` | DSS controller/form/routes, persisted `Wepp` fields, export RQ/zip | DOM-14A | `high`: queue, files, download | planned |
| DOM-17 | `treatments_ui_contract` | `treatments` | treatments controller/form/routes, `Treatments`, map upload/build RQ | DOM-08A, DOM-10 | `high`: upload, route, queue/worker | planned |
| DOM-18 | `debris_flow_ui_contract` | `debrisFlow` | debris controller/form/routes, `DebrisFlow`, run RQ | DOM-07, DOM-11A | `high`: role gate, route, queue/worker | planned |
| DOM-19 | `roads_ui_contract` | `roads`, `roadsMapOverlay` | roads controller/form/overlay/routes, `Roads`, uploads/prepare/run RQ | DOM-04A, DOM-04B, DOM-07 | `high`: upload, files, routes, queues | planned |
| DOM-20A | `features_export_selection_ui_contract` | `featuresExport`: dynamic catalog, selectors, profiles | controller/form, catalog/planner/service inputs; no NoDb singleton | DOM-04A, DOM-14A | `high` if public/download routes change | planned |
| DOM-20B | `features_export_execution_ui_contract` | `featuresExport`: enqueue, cache, artifacts, download | export routes/service/cache/RQ/output contracts | DOM-20A | `high`: queue, files, downloads | planned |
| DOM-21 | `rap_timeseries_ui_contract` | `rapTs` | RAP controller/form/routes, `RAP_TS`, fetch/analyze RQ | DOM-04A | `high`: egress and queue/worker | planned |
| DOM-22 | `openet_timeseries_ui_contract` | `openetTs` | OpenET controller/form/routes, `OpenET_TS`, external fetch/analyze RQ | DOM-04A | `high`: admin gate, egress, queue/worker | planned |
| DOM-23 | `disturbed_baer_ui_contract` | `disturbed`, `baer` shared SBS surface | both controllers, one shared template/route/state owner, SBS uploads and invalidation; boundary probe must confirm joint closure | DOM-04A, DOM-08A, DOM-10 | `high`: upload/files, route/state mutations | planned |
| DOM-24 | `rangeland_cover_ui_contract` | `rangelandCover`, `rangelandCoverModify` | controller/form/modifier, rangeland routes/state/build RQ | DOM-04A, DOM-08A | `high`: route/state mutation and queue | planned |
| DOM-25A | `omni_scenarios_ui_contract` | `omni`: scenarios | Omni controller/scenario form/routes/state, multipart staging/run RQ | DOM-14A, DOM-23 | `high`: upload/files and queue/worker | planned |
| DOM-25B | `omni_contrasts_ui_contract` | `omni`, `omniContrastOverlays`: contrasts | contrast form/overlay/routes/state/run/delete RQ | DOM-25A, DOM-04A, DOM-04B | `high`: upload/files, delete, queue/worker | planned |
| DOM-26 | `rhem_ui_contract` | `rhem` | RHEM controller/form/routes, `Rhem`/`RhemPost`, run RQ | DOM-07, DOM-11A | `high`: route and queue/worker | planned |
| DOM-27 | `geneva_ui_contract` | `geneva` control | Geneva config, task, status/results/frequency-panel, and CN-table route functions/state plus chained RQ; summary query/report functions are SURF-11 consumers of `geneva_bp.py` | DOM-04A, DOM-14A | `high`: route and chained queues/workers | planned |
| DOM-28 | `pathce_ui_contract` | `pathCe` | PathCE controller/form/Flask route, `PathCostEffective`, run RQ | DOM-04A, DOM-07 | `high`: role gate, route, queue/worker | planned |
| DOM-29 | `rusle_ui_contract` | `rusle` | RUSLE controller/form/routes, `Rusle`, build RQ | DOM-07, DOM-23 | `high`: routes, queue/worker, generated outputs | planned |

The 33 bootstrap keys have exactly one primary package owner. Facet packages may
share source or state, but they cannot claim a second primary bootstrap owner.

| Bootstrap key | Primary owner | Facet package(s) |
| --- | --- | --- |
| `project` | DOM-02 | None |
| `team` | DOM-03 | None |
| `map` | DOM-04A | DOM-04B |
| `channel` | DOM-05 | None |
| `outlet` | DOM-06 | None |
| `subcatchment` | DOM-07 | None |
| `landuse` | DOM-08A | DOM-08B |
| `landuseModify` | DOM-09 | None |
| `soil` | DOM-10 | None |
| `climate` | DOM-11A | DOM-11B |
| `observed` | DOM-12 | None |
| `agFields` | DOM-13A | DOM-13B, DOM-13C, DOM-13D |
| `wepp` | DOM-14A | DOM-14B, DOM-14C |
| `bootstrap` | DOM-15 | None |
| `dssExport` | DOM-16 | None |
| `treatments` | DOM-17 | None |
| `debrisFlow` | DOM-18 | None |
| `roads` | DOM-19 | None |
| `roadsMapOverlay` | DOM-19 | None |
| `featuresExport` | DOM-20A | DOM-20B |
| `rapTs` | DOM-21 | None |
| `openetTs` | DOM-22 | None |
| `disturbed` | DOM-23 | None |
| `baer` | DOM-23 | None |
| `rangelandCover` | DOM-24 | None |
| `rangelandCoverModify` | DOM-24 | None |
| `omni` | DOM-25A | DOM-25B |
| `omniContrastOverlays` | DOM-25B | None |
| `rhem` | DOM-26 | None |
| `geneva` | DOM-27 | SURF-11 report consumer |
| `ash` | DOM-01 | None |
| `pathCe` | DOM-28 | None |
| `rusle` | DOM-29 | None |

Shared-state pairings are intentional: Disturbed/BAER, Rangeland plus modifier,
Roads plus overlay, and Omni plus contrast overlay. AgFields, WEPP, Map,
Landuse, Climate, Features Export, and Omni are split where one package would
exceed the evidence/review boundary.

## Shared-Foundation Packages

| ID | Proposed slug | Scope | Depends on | Risk / expected security | State |
| --- | --- | --- | --- | --- | --- |
| SHR-01 | `pure_ui_dom_form_serialization_contracts` | `dom.js`, `events.js`, `forms.js`, `utils.js`, and authoritative producer ownership of `selection_utils.js`; selector, serialization, selection, submit, absent/disabled semantics | GOV-00A | High / `low` | planned |
| SHR-02 | `pure_ui_transport_session_recorder_contracts` | `http.js`, recorder interceptor, CSRF bootstrap, session heartbeat, canonical request/error transport | SHR-01 | High / `high` | planned |
| SHR-03A | `pure_ui_status_control_contracts` | `status_stream.js`, `control_base.js`, terminal/error mapping, duplicate-load/idempotence behavior | SHR-01, SHR-02 | High / `high` | planned |
| SHR-03B | `pure_ui_bootstrap_observability_contracts` | `bootstrap.js`, `bootstrap_observability.js`, registry/config gates, stale/generated-bundle contract | SHR-01, SHR-02, SHR-03A | High / `high` | planned |
| SHR-04A | `pure_ui_base_macro_shell_contracts` | `base_pure.htm`, Pure macros, shell ordering, field rendering, tabs and absent-DOM behavior | SHR-01 | High / `low` | planned |
| SHR-04B | `pure_ui_modal_details_theme_console_contracts` | `modal.js`, `details_menu.js`, `theme.js`, authoritative `console_utils.js` ownership, console/table macros and duplicate-load behavior | SHR-01, SHR-04A | High / `low` | planned |
| SHR-05 | `pure_ui_unitizer_preferences_contract` | `unitizer_client.js`, generated map/modal, Project bridge, authenticated backend preferences and persisted round trip | SHR-01, SHR-02, SHR-04A, SHR-04B | High / `high`; ADR if conversion/default behavior changes | planned |
| SHR-06 | `pure_ui_command_bar_contract` | Command Bar template/JS/routes, chat/token/download/commands/WebSocket/StatusStream | SHR-02, SHR-03A, SHR-03B, SHR-04A, SHR-04B | High / `high` | planned |
| SHR-07 | `pure_ui_poweruser_panel_contract` | PowerUser panel, web push/service worker, clear-lock and recorder-promotion actions | SHR-02, SHR-04A, SHR-04B, DOM-02 | High / `high` | planned |

## Non-Run and Stateful Surface Packages

| ID | Proposed slug | Scope | Depends on | Risk / expected security | State |
| --- | --- | --- | --- | --- | --- |
| SURF-01 | `pure_ui_public_creation_cap_contract` | Interfaces/create and `locations/{joh,portland,seattle,spu}/index.htm` forms, `interfaces_captcha.js`, CAP widgets and duplicate-handler safeguards | SHR-01, SHR-02, SHR-04A, SHR-04B | High / `high` | planned |
| SURF-02A | `pure_ui_batch_runner_creation_contract` | Batch create/manage templates, bootstrap/controller, schema and persisted run set | SHR-01..04B; `docs/work-packages/20260630_batch_runner_durability/` must be closed and name its verified closeout revision before this unit starts | High / `high` | planned |
| SURF-02B | `pure_ui_batch_runner_execution_contract` | Batch upload, launch, RQ progress/error/completion and durability behavior | SURF-02A, SHR-02, SHR-03A, SHR-03B | High / `high` | planned |
| SURF-03 | `pure_ui_archive_console_contract` | Archive console/list/create/restore/delete; consumes SHR-04B `console_utils.js` and SHR-03A StatusStream | SHR-02, SHR-03A, SHR-04A, SHR-04B, DOM-02 | High / `high` | planned |
| SURF-04 | `pure_ui_fork_console_contract` | Fork console CAP/session/localStorage recovery/cancel/copy ownership; consumes SHR-04B `console_utils.js` | SURF-01, SHR-02, SHR-03A, SHR-04A, SHR-04B, DOM-02, DOM-03 | High / `high` | planned |
| SURF-05 | `pure_ui_run_sync_console_contract` | Run Sync host/root/token/options/status/RQ lifecycle | SHR-02, SHR-03A, SHR-03B, SHR-04A, SHR-04B | High / `high` | planned |
| SURF-06 | `pure_ui_runs_catalog_contract` | Runs catalog/users/map/delete/poll controls and persistence/permission behavior | SHR-01..04B, DOM-02, DOM-03 | High / `high` | planned |
| SURF-07 | `pure_ui_rq_job_dashboard_contract` | Minted token, job tree/poll/jobinfo/cancel and terminal/error mapping | SHR-02, SHR-03A, SHR-03B, SHR-04A, SHR-04B | High / `high` | planned |
| SURF-08 | `pure_ui_run_migration_status_contract` | Old-run migration mutation, retry/skip and terminal state | SHR-02..04B, SURF-07 | High / `high` | planned |
| SURF-09 | `pure_ui_readme_editor_contract` | README save/preview/raw, auth/path/CSRF, tab lock/concurrency, safe markdown rendering | SHR-02, SHR-04A, SHR-04B, DOM-02 | High / `high` | planned |
| SURF-10 | `pure_ui_disturbed_csv_editor_contract` | Edit CSV optimistic concurrency, disturbed lookup mutation, runtime/CDN failure | DOM-23, SHR-01, SHR-02, SHR-04A, SHR-04B | High / `high` | planned |
| SURF-11 | `pure_ui_geneva_summary_report_contract` | `query_geneva_summary`, `query_geneva_hru_map_rows`, `query_geneva_hru_map_features`, and `report_geneva_summary` producer ownership in `geneva_bp.py`; interactive map/unitizer contract | DOM-27, SHR-05 | High / `high` if route/auth/query behavior is remediated | planned |
| SURF-12 | `pure_ui_report_shell_readonly_contract` | `reports/_base_report.htm`, `_page_container.htm`, and presentation behavior; domain output partials stay parented to domains | SHR-04A, SHR-04B; DOM-01, DOM-11A, DOM-12, DOM-14A, DOM-18, DOM-26, DOM-27 | Medium / `low` | planned |
| SURF-13 | `pure_ui_security_auth_forms_contract` | Inherited `security/_layout.html` family: login, registration, confirmation, password reset/change, magic login and account-exit flows | SHR-01, SHR-02, SHR-04A, SHR-04B | High / `high`: authentication, session, CSRF and account mutation | planned |
| SURF-14 | `pure_ui_user_profile_session_contract` | `user/profile.html`, profile mutation, session reset and browser storage behavior | SURF-13, SHR-01, SHR-02, SHR-04A | High / `high`: identity and session mutation | planned |
| SURF-15 | `pure_ui_root_usermod_contract` | `user/usermod.html`, root-admin user lookup and role/account mutation | SURF-13, SHR-01, SHR-02, SHR-04A | High / `high`: privileged account mutation | planned |
| SURF-16 | `pure_ui_ermit_export_contract` | `reports/ermit_export_download.htm`, RQ session token, export submit/poll/error, protected download and return navigation | SHR-02, SHR-03A, SHR-04A, DOM-14A | High / `high`: authentication, queue and protected artifact download | planned |
| SURF-17 | `pure_ui_rq_info_details_contract` | `routes/rq/info_details/templates/info_details.htm`, Admin/Root Redis/RQ recent/active/failed job and submitter-state presentation | SHR-04A, SURF-07 | High / `high`: privileged operational metadata | planned |
| SURF-18 | `pure_ui_deval_loading_contract` | `reports/deval_loading.htm`, CAP-gated enqueue/cache decision, job tracking/poll/backoff/error/refresh and generated report handoff | SHR-03A, SHR-04A, DOM-14A, SURF-07 | High / `high`: CAP, queue, job metadata and generated artifact | planned |

## Complete 56-Module Reconciliation

`build_controllers_js.py::_collect_controller_modules()` currently selects 56
files. Their allocation is:

- 37 run-page support files: 33 primary bootstrap controller modules plus the
  four Map helper modules. They are owned by DOM packages above.
- 4 standalone/non-run modules: `batch_runner.js` (producer SURF-02A; consumer
  SURF-02B),
  `run_sync_dashboard.js` (SURF-05), `geneva_summary_report.js` (SURF-11), and
  `interfaces_captcha.js` (SURF-01).
- 15 shared/global modules: DOM/events/forms/HTTP/recorder/utils/modal/unitizer/
  StatusStream/controlBase/bootstrap/observability/details/selection/theme. They
  are owned by SHR packages. SHR-01 is the sole producer owner for
  `selection_utils.js`; DOM-04A, DOM-09, and DOM-24 are consumers only.

Production evidence must use GL implementations (`channel_gl.js`,
`subcatchments_gl.js`, `outlet_gl.js`, `landuse_modify_gl.js`, and
`rangeland_cover_modify_gl.js`). Retained legacy sources/tests are historical
evidence, not proof of the generated production bundle.

## Parent and Exclusion Decisions

| Surface/module | Decision | Rationale |
| --- | --- | --- |
| Team and Disturbed modals | Parent DOM-03 and DOM-23 | Same state/route boundary as domain controller |
| Unitizer modal and backend preference routes | Parent SHR-05 | Independent authenticated preference/persistence boundary; DOM-02 is a consumer |
| Run header Project mutations | Parent DOM-02 | Project-owned state; generic navigation remains SHR-04A/04B |
| WEPP advanced partials | Parent DOM-14B | Submitted through WEPP state/route boundary |
| SWAT and cover-transform partials | Parent DOM-14C | Distinct upload and execution inputs justify a separate facet |
| Roads/Omni map overlays | Parent DOM-19/DOM-25B | Read domain artifacts and share domain lifecycle |
| Domain report panels | Parent domain package | Output/readiness belongs to producing controller |
| Geneva interactive summary | SURF-11 | Stateful report controller has independent query/map/unitizer contract |
| ERMiT export/download report | SURF-16 | Stateful authenticated RQ and protected-download lifecycle is not a read-only report shell |
| UI Showcase | Evidence for SHR-04A/04B, not a product contract | Test/demo surface |
| Diagnostics | Excluded from this initiative | Governed by existing diagnostics specifications/work prompts; no bundled run/console controller |
| GL Dashboard | Excluded from this initiative | Separate architecture/specification and test system; not a controllers-gl run/console contract |
| Browse and UserSummary markdown/search pages | Excluded except Command Bar host behavior | Read-only content/GET-search surfaces have no independent Pure controller state; any loaded shared script remains a listed SHR consumer |
| Vendor assets (`marked.js`, QR library) | Host-only contract | Vendored internals are not WEPPcloud authority |

All exclusions must be confirmed in GOV-00 by both independent reviewers.

## Known Baseline Gaps and Hazards

- Many Jest suites hand-author DOM, so they cannot prove Jinja/macro output.
- Rendered field matrices are visibly incomplete for numerous domain controls.
- Archive and Fork templates can load bundled and standalone StatusStream code;
  base Pure pages can similarly load Theme twice. Idempotence must be proved.
- Public CAP pages combine bundle-side and inline CAP behavior, risking duplicate
  handlers/submission.
- Direct JS coverage is absent or indirect for modal, details menu, CAPTCHA,
  theme, run-sync, and selection utilities.
- Large inline scripts in runs catalog, RQ dashboard, migration status, and README
  editor lack proportionate controller tests.
- Current documentation still labels the 2025 migration inventory complete/
  authoritative and links current readers to missing or archived plans.

## Per-Package Acceptance

Every registered package must provide, where applicable:

- exact controller/template/route/state/test matrix;
- per-field, per-mode, and per-configuration evidence matrix;
- rendered page DOM and actual serialized request evidence;
- server normalization and persistence/reload or explicit statelessness proof;
- RQ enqueue plus terminal/error evidence;
- observed/normative discrepancy ledger and compatibility decisions;
- source/contract/test manifest updates and change-aware gate results;
- targeted frontend/backend tests, generated-bundle stale check where relevant,
  and live dev/job-tree evidence for stateful or RQ packages;
- formal security artifact when remediation crosses a high-security boundary;
- two raw independent reviews, primary disposition, and post-fix confirmation.

An inapplicable acceptance item requires a written `N/A` rationale confirmed by
both reviewers; silence does not count. Governance packages substitute
deterministic inventory/count fixtures, manifest-schema and negative-gate tests,
documentation/link/lifecycle checks, and dual review for runtime DOM/RQ evidence.
An operator-accepted residual risk is recorded with owner, rationale, and date;
it is not relabeled as a resolved review finding.

Queue-edge changes additionally require the RQ dependency catalog and
`wctl check-rq-graph`. Parameter/default/formula/unit/fallback changes require
the parameterization ADR gate.

## Estimate and Boundary Preflight

Unless listed below, a row is estimated at 1-3 focused weeks. This default plus
the exception table gives every registered ID an explicit estimate; estimates
are planning ranges, not deadlines.

| IDs | Estimate | Required first-day boundary probe |
| --- | --- | --- |
| GOV-00 | 2-4 weeks | Freeze deterministic coverage ledger and exclusions |
| GOV-00A | 2-4 weeks | Ratify binding status/evidence semantics, contract-first authority, and canonical contract schema |
| GOV-01 | 2-4 weeks | Prove manifest schema and one negative source-drift fixture |
| GOV-99 | 2-3 weeks | Freeze finite dependency and authority-cutover checklist |
| DOM-04A, DOM-08A, DOM-11A, DOM-13A, DOM-13C, DOM-13D, DOM-14A, DOM-14B, DOM-14C, DOM-23, DOM-25A, DOM-25B | 2-4 weeks | Confirm one route/state owner and that every member can reach one evidence grade |
| SHR-01, SHR-02, SHR-03A, SHR-03B, SHR-04A, SHR-04B | 2-4 weeks | Freeze producer/consumer fan-out before editing shared code or macros |
| SURF-02A, SURF-02B, SURF-06, SURF-12, SURF-13 | 2-4 weeks | Confirm finite surface/template/route list and one security boundary |
| All other registered IDs | 1-3 weeks | Confirm source matrix, state owner, discrepancy authority and acceptance evidence |

The probe exits only when the matrix fits within four weeks, has one accountable
state boundary, and has one authority for each discrepancy. Otherwise the
package is split in this register and reviewed before implementation.

## Capacity and Timeline

This register is deliberately finer than the original waves because independent
upload, queue, auth, and persistence boundaries should not share one regression
review. At 72 execution units, even an uninterrupted one-week-per-unit sequence
has a theoretical serial floor above 18 months once foundation and review gates
are included. A truthful serial planning range is 24-36 months. After GOV-00,
GOV-00A, SHR-01 through SHR-04B, DOM-01, and GOV-01, separately authorized isolated
worktrees with at most two disjoint writers have a theoretical floor near 10
months and a more credible range of 12-20 months. Current staffing and competing
work are not assumed in either range.

The first milestone is limited to GOV-00, GOV-00A, SHR-01 through SHR-04B,
DOM-01, and GOV-01. Its likely duration is 18-32 serial weeks, or 14-22 weeks
only when authorized disjoint documentation/evidence work can proceed
concurrently. It is not the timeline for the full initiative.
