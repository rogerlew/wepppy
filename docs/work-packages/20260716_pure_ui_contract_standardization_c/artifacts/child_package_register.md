# Pure UI Contract Child Package Register

**Register version**: 1.4 sequential controller-test execution
**Last updated**: 2026-07-28 UTC
**Authority**: Stable IDs define bounded inventory. They do not require a
registry platform or make shared/governance packages prerequisites for testing
one controller.
**Total**: 76 inventory boundaries: 4 governance, 5 bounded remediations, 39
run-domain, 9 shared-foundation, and 19 non-run/stateful surface packages.
GOV-00 is the existing umbrella at
`docs/work-packages/20260716_pure_ui_contract_standardization_c/`; GOV-00A is the
closed convention child at
`docs/work-packages/20260716_pure_ui_contract_ratification/`; a planned entry
receives a dated directory when it is selected as the next one-at-a-time
package, before tests begin. REM-01 is the operator-authorized
bounded remediation at
`docs/work-packages/20260720_omni_mod_state_sync/`. REM-02 is the
operator-authorized bounded remediation at
`docs/work-packages/20260721_runs_ttl_deletion_catalog/`.
REM-03 and REM-04 are the registered authentication/session and browser-origin
hardening remediations. REM-05 is the operator-authorized Channel Delineation
selector remediation at
`docs/work-packages/20260728_channel_depression_smoothing_fix/`.

## Boundary and Review Rules

Every row is a contractually registered, independently closable boundary. Each
controller package uses the reusable one-controller prompt and an active
ExecPlan. Test/documentation work starts with security impact `none`; re-triage
an actual production patch. One independent correctness review is required for
a production patch. A second review is reserved for high-risk behavior changes,
material shared-producer fan-out, or explicit operator request.

Registration is binding now. `planned` means execution has not started; it does
not mean the contract is optional. Evidence grades such as `unverified`,
`documented`, and `verified` describe implementation conformance only. Removing
or excluding a registered obligation requires explicit operator approval and
review proportional to the change.

Audit-only documentation normally starts with security impact `none`. Before a
discovered remediation is implemented, re-triage immediately. Auth/session/
CSRF/CAP, public routes, uploads/downloads, file/path handling, queue wiring,
worker subprocesses, CI/deployment, secrets, tokens, and external egress are
`high` by default.

Split a registered package before implementation when:

- more than one unrelated high-security remediation is required;
- a shared macro/helper change cannot be covered safely through direct
  consumers;
- baseline and contract work cannot finish within four focused weeks;
- separate route/state owners require independent compatibility decisions; or
- one member cannot reach the same evidence grade as the rest of the package.

An audit may close a contract as `documented` when material evidence is missing,
but it cannot mark that contract `verified`. The package must register the
bounded follow-up needed to obtain the evidence.

## Execution Model

Execute one controller package at a time:

    establish intent
      -> render and trace actual behavior
      -> add focused tests
      -> reproduce mismatch
      -> patch minimally
      -> run existing gates
      -> close and select the next controller

GOV-00A supplies a concise test convention. DOM-01 WATAR/Ash is first because it
has a known historical mismatch. Shared packages are not prerequisites: shared
behavior is tested when a controller exposes it. GOV-01 is a deferred evaluation
that requires measured evidence and explicit operator approval; it is not a
gate for later controller work.

The `Depends on` column records domain/runtime context worth tracing. It does
not require completion of speculative shared or governance tooling before
controller tests can begin.

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

`GOV-00A-M1C` is the separately closable bounded-remediation governance
milestone proposed only for REM-03. It requires its own dual review,
disposition, and standalone ancestor. It borrows no authority from M1A or M1B
and cannot advance the borrowed authentication owners.

`GOV-00A-M1D` is the separately closable bounded-remediation governance
milestone proposed only for REM-04. It requires its own dual review,
disposition, and standalone ancestor. It borrows no authority from earlier
milestones and cannot advance the borrowed browser/session owners.

`GOV-00A-M1E` is the separately closable bounded-remediation governance
milestone proposed only for REM-05. It requires its own dual review,
disposition, and standalone ancestor. It borrows only the finite DOM-05
depression-smoothing propagation boundary and cannot advance DOM-05.

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

Named sets are inventory shorthand only. No machine expansion or dependency
engine is planned. GOV-99 is intentionally absent from all sets.

## Governance Packages

| ID | Package path / proposed slug | Scope | Depends on | Risk / expected security | State |
| --- | --- | --- | --- | --- | --- |
| GOV-00 | Existing `20260716_pure_ui_contract_standardization_c` | Current umbrella: complete population, exclusions, contractual coverage, and frozen execution register | None | High contract risk; docs-only `none` | auditing |
| GOV-00A | Existing `20260716_pure_ui_contract_ratification` | Publish the concise one-controller tests-first convention, simplicity budget, and stop-loss rules | GOV-00 | Docs-only `none` | closed |
| GOV-01 | `pure_ui_contract_maintenance_gate_evaluation` | After at least five controllers, evaluate measured misses, repetition, runtime, false failures, and operator cost; add tooling only with explicit approval | Five completed controller packages and measured need | Risk determined by proposed tooling | deferred; no scaffold |
| GOV-99 | `pure_ui_contract_authority_cutover` | Final coverage audit, stale-link replacement, current AGENTS/README/catalog authority cutover, archived-plan labels, and umbrella closeout | GOV-00, GOV-00A, ALL-DOM, ALL-SHR, ALL-SURF | Medium; docs-only `none` | planned |

## Bounded Remediation Packages

| ID | Dated package | Borrowed owners | Exact defect boundary | Depends on | Security | State |
| --- | --- | --- | --- | --- | --- | --- |
| REM-01 | `20260720_omni_mod_state_sync` | DOM-02, DOM-25A, DOM-25B | Omni Scenarios/Contrasts feature-registry menu availability; Mods checkbox and reason markup; `Ron.mods` enable/disable guards; runs-page section/preflight visibility and metadata; dynamic shared Omni controller remount; Dev/Root gates on contrast run/dry-run/delete plus canonical run access and Dev/Root on the CAP-gated report; focused tests and generated controller bundle only | GOV-00A-M1A | `high`: role-gated dynamic load, persisted mod mutation, contrast actions, and report data | completed / dual-reviewed |
| REM-02 | `20260721_runs_ttl_deletion_catalog` | SURF-06 | Read-only TTL policy/expiry projection for already-authorized catalog rows; one lifecycle table cell; dedicated Usersum documentation and focused catalog/template/doc tests only | GOV-00A-M1B | `high`: authenticated run-metadata presentation; no new access path or mutation | completed / dual-reviewed |
| REM-03 | `20260727_auth_session_persistence_hardening` | SURF-13, SHR-02, SHR-04A | Password-login remember checkbox GET default and POST opt-out; rolling remember-cookie duration/refresh; login/logout cookie boundary; authentication-log redaction and append-only durable diagnostics; focused auth/config/logging tests and documentation only | GOV-00A-M1C | `high`: authentication persistence and credential-adjacent diagnostics | checkpoint review |
| REM-04 | `20260727_web_origin_guard_hardening` | SURF-13, SHR-02, SHR-04A | Existing Flask, rq-engine, and query-engine same-origin guards; reset deletion of configured WEPPcloud session/remember cookies; copied diagnostics report allowlist; focused origin/CSRF/cookie/report tests and documentation only | GOV-00A-M1D | `high`: CSRF-adjacent origin authorization, cookie deletion, and report disclosure | checkpoint review |
| REM-05 | `20260728_channel_depression_smoothing_fix` | DOM-05 | Depression-smoothing selector rendered name, canonical request token, existing worker mutation/persistence, reload hydration, actual-template regression, Usersum note, and production verification only | GOV-00A-M1E | `high`: inherited browser-to-RQ persisted mutation boundary; no new input or queue behavior | checkpoint review |

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

REM-03 excludes OAuth authorization behavior, account/role policy, credential
storage, Redis session lifetime, CSRF policy, CAP verification policy, route
prefixes, RQ behavior, database schemas, and unrelated templates. Its final
evidence is inherited by SURF-13, SHR-02, and SHR-04A without advancing those
owners.

REM-04 excludes new guarded endpoints, authentication and role policy, OAuth
behavior, Caddy configuration, deployment, queue wiring, project data schemas,
model parameterization, diagnostics card presentation, and unrelated UI work.
Its final evidence is inherited by SURF-13, SHR-02, and SHR-04A without
advancing those owners. The register's Diagnostics exclusion remains unchanged:
REM-04 is a defect-scoped exception and does not enroll Diagnostics in the Pure
UI initiative.

REM-05 excludes algorithms, defaults, enum tokens, map behavior, DEM uploads,
route parsing, queue wiring, NoDb schema, authorization, CSRF, and every other
DOM-05 field. Its evidence is inherited by DOM-05 without advancing that owner.

## Domain Amendment Packages

| ID | Dated package | Owner | Exact intended delta | Security | State |
| --- | --- | --- | --- | --- | --- |
| DOM-05A | `20260729_topaz_conditioning_wepppy_integration` | DOM-05 | Add Topaz Conditioning Algorithm/`topaz`, dispatch it to released WBT `TopazConditionDem` width 2, and make it the new-run default only for `disturbed9002_wbt`; preserve legacy tokens, persisted runs, other configs, queue/auth/schema, and downstream flow/channel behavior | `high`: authenticated browser-to-RQ persisted enum and native geospatial worker dispatch | closed locally; ancestor `5754a1e06`; full suite, dual review, and E2E PASS |

DOM-05A is an operator-approved intended behavior amendment, not a conformance
fix and not a reopening of REM-05. Its contract, ADR, dual reviews, security
artifact, and disposition must form a standalone ancestor before source,
template, config, test, generated bundle, or WBT runtime artifacts change.

The exact REM-05 implementation boundary is limited to:

- the `input_wbt_fill_or_breach` macro invocation in
  `wepppy/weppcloud/templates/controls/channel_delineation_pure.htm`;
- actual-template regression coverage in
  `tests/weppcloud/routes/test_pure_controls_render.py`;
- worker non-null/null/failure characterization in
  `tests/rq/test_project_rq_mutation_guards.py`;
- paired channel controller fixtures/assertions only if needed to prove the
  existing canonical request token;
- the Channel Delineation Usersum guide; and
- REM-05/GOV-00A contracts, reviews, trackers, and deployment evidence.

The exact REM-04 implementation boundary is limited to:

- the existing same-origin helpers in
  `wepppy/weppcloud/routes/weppcloud_site.py`,
  `wepppy/microservices/rq_engine/session_routes.py`, and
  `wepppy/query_engine/app/server.py`;
- reset cookie-target construction in
  `wepppy/weppcloud/routes/weppcloud_site.py`;
- copied-report construction in
  `wepppy/weppcloud/static/js/diagnostics/report.js` and structured safe result
  codes in adjacent diagnostics probes only when required;
- focused tests for those exact surfaces; and
- REM-04/GOV-00A contracts, reviews, tracker, and security artifacts.

The exact REM-03 implementation boundary is limited to:

- `wepppy/weppcloud/auth_forms.py`;
- `wepppy/weppcloud/configuration.py`;
- `wepppy/weppcloud/routes/_security/logging.py`;
- host log-rotation configuration limited to the canonical security log;
- focused tests for those surfaces; and
- the REM-03 contract, ADR, incident, operator, and developer documentation.

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
- `wepppy/weppcloud/routes/usersum/{docs_manifest.yaml,nav_tree.yaml}`,
  `wepppy/weppcloud/routes/usersum/usersum.py`, and
  `wepppy/weppcloud/routes/usersum/weppcloud/run-ttl-deletion.md`;
- validation generator `python3 tools/usersum_docs_tool.py build-index --write
  --require-vendor-files`; ignore any dirty
  `wepppy/weppcloud/routes/usersum/generated/docs_index.json` unless separately
  authorized under the root AGENTS instruction;
- `tests/weppcloud/routes/test_user_meta_boundaries.py`,
  `tests/weppcloud/routes/test_user_runs_admin_scope.py`,
  `tests/weppcloud/routes/test_usersum_bp.py`, and
  `tests/weppcloud/test_usersum_template_wiring.py`;
- `tests/weppcloud/utils/test_run_ttl.py` for read-only malformed-payload
  regression evidence; and
- `wepppy/weppcloud/controllers_js/__tests__/runs_lifecycle_template.test.js`
  for executable Runs lifecycle DOM rendering evidence; and
- REM-02/GOV-00A documentation, review, tracker, and security artifacts.

## Run-Domain Packages

These packages account for all 33 production entries in
`routes/run_0/templates/run_page_bootstrap.js.j2::createBootstrapEntries`.
Adjuncts that share one state/route boundary remain parented to the relevant
domain package.

| ID | Package path / proposed slug | Bootstrap/controller scope | Primary source boundary | Depends on | Expected remediation security | State |
| --- | --- | --- | --- | --- | --- | --- |
| DOM-01 | `20260727_watar_ui_contract_pilot` | `ash` | `ash.js`, `ash_pure.htm`, WATAR/ash route, `Ash`, `run_ash_rq` | GOV-00A concise test convention | Test/docs `none`; re-triage actual patch | verified |
| DOM-02 | `20260728_project_shell_ui_contract` | `project` | `project.js`, run header, Project routes, `Ron`, SQL Run, readonly RQ; consumes SHR-05 Unitizer preferences | SHR-01..04B, SHR-05 context | `high`: auth, readonly/public state, mutation/RQ | verified |
| DOM-03 | `20260728_team_collaboration_ui_contract` | `team` | `team.js`, team modal/form, project/team routes, SQL ownership | SHR-01..04B context | `high`: owner/collaborator auth mutations | verified |
| DOM-04A | `20260728_map_orchestration_ui_contract` | `map`: orchestration, center/search/elevation/drilldown and public API | `map_gl.js`, map host, elevation/query routes; consumes SHR-01 `selection_utils.js` | SHR-01..04B context | `low`; `high` if public query routes change | verified |
| DOM-04B | `20260728_map_layers_feature_ui_contract` | `map`: layer/scale/feature UI and model visualization partials | four `map_gl_*` helpers, layer resources, legends/overlays | DOM-04A | `low`; `high` if file/resource routes change | verified |
| DOM-05 | `20260728_channel_delineation_ui_contract` | `channel` | `channel_gl.js`, channel template, watershed routes, DEM upload/build RQ | DOM-04A context | `high`: upload, route, queue/worker | verified |
| DOM-06 | `20260728_outlet_ui_contract` | `outlet` | `outlet_gl.js`, outlet template, watershed route, `set_outlet_rq` | DOM-04A | `high`: route mutation and queue | verified |
| DOM-07 | `20260728_subcatchment_ui_contract` | `subcatchment` | `subcatchments_gl.js`, subcatchments template, abstraction routes/RQ | DOM-04A, DOM-05, DOM-06 | `high`: route mutation and queue/worker | verified |
| DOM-08A | `20260728_landuse_build_ui_contract` | `landuse`: modes, build/upload and reload | landuse controller/base form/routes, `Landuse`, build RQ | SHR-01..04B context | `high`: upload, route, queue/worker | verified |
| DOM-08B | `20260728_landuse_catalog_editor_ui_contract` | `landuse`: user-defined catalog and map editor | user-defined/map templates and catalog/mapping routes | DOM-08A | `high`: file/catalog/mapping mutation | verified |
| DOM-09 | `20260728_landuse_modifier_ui_contract` | `landuseModify` adjunct | `landuse_modify_gl.js`, modify template, map selection and synchronous route mutation | DOM-04A, DOM-08A | `high`: route/state mutation | verified |
| DOM-10 | `20260728_soils_ui_contract` | `soil` | soil controller/template, soils routes, `Soils`, build RQ | SHR-01..04B context | `high`: route, queue/worker | verified |
| DOM-11A | `20260728_climate_catalog_build_ui_contract` | `climate`: catalog/station/mode/build lifecycle | climate controller/base form/routes, `Climate`, build RQ | SHR-01..04B context | `high`: egress, route, queue/worker | verified |
| DOM-11B | `20260728_climate_upload_scaling_ui_contract` | `climate`: upload, scaling, GridMET/MXPT5 and auxiliary modes | upload/aux form sections and route families | DOM-11A | `high`: upload, egress, persisted options | verified |
| DOM-12 | `20260728_observed_ui_contract` | `observed` | observed controller/template/routes, `Observed`, Climate observed state | DOM-11A | `low`: rendered state repair | verified |
| DOM-13A | `20260728_agfields_boundary_schema_ui_contract` | `agFields`: boundary, schema, subfield inventory | AgFields controller/form and boundary/schema/subfield routes/state | DOM-04A, DOM-08A, DOM-10, DOM-11A | `high`: uploads and geospatial files | verified |
| DOM-13B | `20260728_agfields_plant_mapping_ui_contract` | `agFields`: plant database and field/subfield mapping | plant/mapping form sections, routes and persisted state | DOM-13A | `high`: uploads/files and state mutation | verified |
| DOM-13C | `20260728_agfields_wepp_stage_ui_contract` | `agFields`: staged subfield WEPP execution | stages 1-4 UI/routes/state and RQ chain | DOM-13B, DOM-14A | `high`: multi-stage queues/workers | verified |
| DOM-13D | `20260728_agfields_watershed_ui_contract` | `agFields`: watershed schemes, suite jobs, overlays/results/clear | watershed/suite routes, state, artifacts and deletion | DOM-13C, DOM-04B | `high`: queues, artifacts, deletion | verified |
| DOM-14A | `20260728_wepp_core_ui_contract` | `wepp`: core payload, run lifecycle, job hints, base reports | `wepp.js`, base WEPP form/routes, `Wepp`, run/prep RQ | DOM-07, DOM-08A, DOM-10, DOM-11A | `high`: queue/worker and model persistence | verified |
| DOM-14B | `20260728_wepp_advanced_options_ui_contract` | `wepp`: WEPP advanced option partials and parsers | WEPP advanced templates/parsers/routes/state | DOM-14A | `high`: stored model options and queue inputs | verified |
| DOM-14C | `20260728_swat_cover_transform_ui_contract` | `wepp`: SWAT advanced options and cover-transform upload | SWAT partials/routes/state and upload path | DOM-14A, DOM-14B | `high`: upload, queue/worker, stored options | verified |
| DOM-15 | `20260728_bootstrap_control_ui_contract` | `bootstrap` | bootstrap controller/embedded form/routes, enable/checkout/disable RQ | DOM-14A | `high`: admin/auth, git refs/tokens, queues | verified |
| DOM-16 | `20260728_dss_export_ui_contract` | `dssExport` | DSS controller/form/routes, persisted `Wepp` fields, export RQ/zip | DOM-14A | `high`: queue, files, download | verified |
| DOM-17 | `20260728_treatments_ui_contract` | `treatments` | treatments controller/form/routes, `Treatments`, map upload/build RQ | DOM-08A, DOM-10 | `high`: upload, route, queue/worker | verified |
| DOM-18 | `20260728_debris_flow_ui_contract` | `debrisFlow` | debris controller/form/routes, `DebrisFlow`, run RQ | DOM-07, DOM-11A | `high`: role gate, route, queue/worker | verified |
| DOM-19 | `20260728_roads_ui_contract` | `roads`, `roadsMapOverlay` | roads controller/form/overlay/routes, `Roads`, uploads/prepare/run RQ | DOM-04A, DOM-04B, DOM-07 | `high`: upload, files, routes, queues | verified |
| DOM-20A | `20260728_features_export_selection_ui_contract` | `featuresExport`: dynamic catalog, selectors, profiles | controller/form, catalog/planner/service inputs; no NoDb singleton | DOM-04A, DOM-14A | `high` if public/download routes change | verified |
| DOM-20B | `20260728_features_export_execution_ui_contract` | `featuresExport`: enqueue, cache, artifacts, download | export routes/service/cache/RQ/output contracts | DOM-20A | `high`: queue, files, downloads | verified |
| DOM-21 | `20260728_rap_timeseries_ui_contract` | `rapTs` | RAP controller/form/routes, `RAP_TS`, fetch/analyze RQ | DOM-04A | `high`: egress and queue/worker | verified |
| DOM-22 | `20260728_openet_timeseries_ui_contract` | `openetTs` | OpenET controller/form/routes, `OpenET_TS`, external fetch/analyze RQ | DOM-04A | `high`: admin gate, egress, queue/worker | verified |
| DOM-23 | `20260728_disturbed_baer_ui_contract` | `disturbed`, `baer` shared SBS surface | both controllers, one shared template/route/state owner, SBS uploads and invalidation; joint boundary confirmed | DOM-04A, DOM-08A, DOM-10 | `high`: upload/files, route/state mutations | verified |
| DOM-24 | `20260728_rangeland_cover_ui_contract` | `rangelandCover`, `rangelandCoverModify` | controller/form/modifier, rangeland routes/state/build RQ | DOM-04A, DOM-08A | `high`: route/state mutation and queue | verified |
| DOM-25A | `20260728_omni_scenarios_ui_contract` | `omni`: scenarios | Omni controller/scenario form/routes/state, multipart staging/run RQ | DOM-14A, DOM-23 | `high`: upload/files and queue/worker | verified |
| DOM-25B | `20260728_omni_contrasts_ui_contract` | `omni`, `omniContrastOverlays`: contrasts | contrast form/overlay/routes/state/run/delete RQ | DOM-25A, DOM-04A, DOM-04B | `high`: upload/files, delete, queue/worker | verified |
| DOM-26 | `20260728_rhem_ui_contract` | `rhem` | RHEM controller/form/routes, `Rhem`/`RhemPost`, run RQ | DOM-07, DOM-11A | `high`: route and queue/worker | verified |
| DOM-27 | `20260728_geneva_ui_contract` | `geneva` control | Geneva config, task, status/results/frequency-panel, and CN-table route functions/state plus chained RQ; summary query/report functions are SURF-11 consumers of `geneva_bp.py` | DOM-04A, DOM-14A | `high`: route and chained queues/workers | verified |
| DOM-28 | `20260728_pathce_ui_contract` | `pathCe` | PathCE controller/form/Flask route, `PathCostEffective`, run RQ | DOM-04A, DOM-07 | `high`: role gate, route, queue/worker | verified |
| DOM-29 | `20260728_rusle_ui_contract` | `rusle` | RUSLE controller/form/routes, `Rusle`, build RQ | DOM-07, DOM-23 | `high`: routes, queue/worker, generated outputs | verified |

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

| ID | Package path / proposed slug | Scope | Depends on | Risk / expected security | State |
| --- | --- | --- | --- | --- | --- |
| SHR-01 | `pure_ui_dom_form_serialization_contracts` | `dom.js`, `events.js`, `forms.js`, `utils.js`, and authoritative producer ownership of `selection_utils.js`; selector, serialization, selection, submit, absent/disabled semantics | Controller evidence identifying shared work | High / re-triage actual patch | deferred; test when encountered |
| SHR-02 | `pure_ui_transport_session_recorder_contracts` | `http.js`, recorder interceptor, CSRF bootstrap, session heartbeat, canonical request/error transport | Controller evidence identifying shared work | High / re-triage actual patch | deferred; test when encountered |
| SHR-03A | `pure_ui_status_control_contracts` | `status_stream.js`, `control_base.js`, terminal/error mapping, duplicate-load/idempotence behavior | Controller evidence identifying shared work | High / re-triage actual patch | deferred; test when encountered |
| SHR-03B | `pure_ui_bootstrap_observability_contracts` | `bootstrap.js`, `bootstrap_observability.js`, registry/config gates, stale/generated-bundle contract | Controller evidence identifying shared work | High / re-triage actual patch | deferred; test when encountered |
| SHR-04A | `20260728_pure_ui_base_macro_shell_contracts` | `base_pure.htm`, Pure macros, shell ordering, field rendering, tabs and absent-DOM behavior | 105 direct producer/DOM consumer render tests | Test/docs `none`; no production patch | verified |
| SHR-04B | `20260728_pure_ui_modal_details_theme_console_contracts` | `modal.js`, `details_menu.js`, `theme.js`, authoritative `console_utils.js` ownership, console/table macros and duplicate-load behavior | 4 direct Jest + 108 producer/consumer renders | Low / `none`; duplicate-init and table-caller repairs | verified |
| SHR-05 | `20260728_pure_ui_unitizer_preferences_contract` | `unitizer_client.js`, generated map/modal, Project bridge, authenticated backend preferences and persisted round trip | 114 renders + 16 focused Python/Node + 31 Project Jest; selector/event-owner repairs | High / `high`; security review passed | verified |
| SHR-06 | `pure_ui_command_bar_contract` | Command Bar template/JS/routes, chat/token/download/commands/WebSocket/StatusStream | SHR-02, SHR-03A, SHR-03B, SHR-04A, SHR-04B | High / `high` | planned |
| SHR-07 | `20260729_pure_ui_poweruser_panel_contract` | PowerUser panel, web push/service worker, clear-lock and recorder-promotion actions | 187 render/route + 34 focused Jest + 29 retained backend; role/POST/side-effect repairs | High / `high`; security review passed | verified |

## Non-Run and Stateful Surface Packages

| ID | Package path / proposed slug | Scope | Depends on | Risk / expected security | State |
| --- | --- | --- | --- | --- | --- |
| SURF-01 | `20260729_pure_ui_public_creation_cap_contract` | Interfaces/create and regional exact renders plus 7 direct CAP Jest, 147 route/render/CAP, and 11 rq-engine creation tests; no production repair; security review passed | SHR-01, SHR-02, SHR-04A, SHR-04B | High / `high` | verified |
| SURF-02A | `pure_ui_batch_runner_creation_contract` | Batch create/manage templates, bootstrap/controller, schema and persisted run set | SHR-01..04B; `docs/work-packages/20260630_batch_runner_durability/` must be closed and name its verified closeout revision before this unit starts | High / `high` | planned |
| SURF-02B | `pure_ui_batch_runner_execution_contract` | Batch upload, launch, RQ progress/error/completion and durability behavior | SURF-02A, SHR-02, SHR-03A, SHR-03B | High / `high` | planned |
| SURF-03 | `20260729_pure_ui_archive_console_contract` | Exact archive render plus 9 direct client, 166 route/render, and 32 API/RQ tests; sibling-mutation exclusion repaired; security review passed | SHR-02, SHR-03A, SHR-04A, SHR-04B, DOM-02 | High / `high` | verified |
| SURF-04 | `20260729_pure_ui_fork_console_contract` | Exact route/render defaults plus 15 direct client, 168 render/template, and 89 API/cancel/RQ tests; predecessor gap closed; no production repair; security review passed | SURF-01, SHR-02, SHR-03A, SHR-04A, SHR-04B, DOM-02, DOM-03 | High / `high` | verified |
| SURF-05 | `20260729_pure_ui_run_sync_console_contract` | Exact Admin render plus 8 direct client, 166 render/route, and 10 API/RQ tests; duplicate submission repaired; security review passed | SHR-02, SHR-03A, SHR-03B, SHR-04A, SHR-04B | High / `high` | verified |
| SURF-06 | `20260728_pure_ui_runs_catalog_contract` | Runs catalog/users/map/search/sort/page/Admin scope and exact encoded run/config delete enqueue/poll/reload; 65 focused Python + 4 inline Jest; action identity/path/readonly-status repairs; security review passed | SHR-01..04B, DOM-02, DOM-03 | High / `high` | verified |
| SURF-07 | `20260728_pure_ui_rq_job_dashboard_contract` | Job tree/poll/jobinfo/cancel and terminal/error mapping; 268 focused Python + 4 inline Jest; required poll-auth fallback repair; security review passed | SHR-02, SHR-03A, SHR-03B, SHR-04A, SHR-04B | High / `high` | verified |
| SURF-08 | `20260728_pure_ui_run_migration_status_contract` | Migration render/enqueue/poll/worker/reload; 225 focused Python + 7 inline Jest; auth/token-class/lock/persistence/token/archive/readonly repairs; security review passed | SHR-02..04B, SURF-07 | High / `high` | verified |
| SURF-09 | `20260728_pure_ui_readme_editor_contract` | README render/save/preview/raw; 186 focused Python + 7 Jest; authority/path/locking/revision/size/Jinja/client repairs; security review passed | SHR-02, SHR-04A, SHR-04B, DOM-02 | High / `high` | verified |
| SURF-10 | `20260728_pure_ui_disturbed_csv_editor_contract` | Actual render + 4 inline Jest + 195 route/render + 31 lookup tests; optimistic concurrency, variant-confined mutation, recovery, and visible runtime/CDN failure; security review passed; no production repair | DOM-23, SHR-01, SHR-02, SHR-04A, SHR-04B | High / `high` | verified |
| SURF-11 | `20260728_pure_ui_geneva_summary_report_contract` | `query_geneva_summary`, `query_geneva_hru_map_rows`, `query_geneva_hru_map_features`, and `report_geneva_summary` producer ownership in `geneva_bp.py`; interactive map/unitizer contract | 133 render/route + 11 service + 7 focused Jest; lifecycle ownership; security review passed; no production repair | High / `high` | verified |
| SURF-12 | `20260728_pure_ui_report_shell_readonly_contract` | `reports/_base_report.htm`, `_page_container.htm`, and presentation behavior; domain output partials stay parented to domains | 113 direct renders + 124 route tests + 28 Project Jest; no repair | Medium / `low` | verified |
| SURF-13 | `20260728_pure_ui_security_auth_forms_contract` | All security form/email families; 9 direct renders + 2 real auth routes + 85 focused auth + 16 configuration + 2 Jest; security review passed; no production repair | SHR-01, SHR-02, SHR-04A, SHR-04B; REM-03/04 evidence | High / `high`: authentication, session, CSRF and account mutation | verified |
| SURF-14 | `20260728_pure_ui_user_profile_session_contract` | `user/profile.html`; 70 focused Python + actual inline Jest; removed misowned role mutation and repaired prefix-aware password link; security review passed | SURF-13, SHR-01, SHR-02, SHR-04A | High / `high`: identity, token, provider, and session boundary | verified |
| SURF-14A | `20260729_user_preferences_wbt_boundary` | Account User Preferences model/page, new-run Unitizer/WBT default snapshot, and configurable WBT DEM-boundary warn/error behavior | SURF-01, SURF-04, SURF-14, SHR-05, DOM-02, DOM-05, DOM-05A | High / `high`: authenticated mutation, database migration, creation propagation, and RQ failure behavior | implementation complete; focused suites pass; broad validation/final review pending; ancestor `1b412d61a` |
| SURF-15 | `20260728_pure_ui_root_usermod_contract` | 28 focused Python + 4 actual-inline Jest; Root authority, strict validation, self-Root, HTTP error, and visible-feedback repairs; security review passed | SURF-13, SHR-01, SHR-02, SHR-04A | High / `high`: privileged account mutation | verified |
| SURF-16 | `20260728_pure_ui_ermit_export_contract` | `reports/ermit_export_download.htm`, RQ session token, export submit/poll/error, protected download and return navigation | 161 render/Flask + 63 backend + 2 inline Jest; rejected-token retry repair; security review passed | High / `high` | verified |
| SURF-17 | `20260728_pure_ui_rq_info_details_contract` | Admin/Root static RQ snapshot; ordered isolated active panels by queue; 134 focused Python; security review passed | SHR-04A, SURF-07 | High / `high`: privileged operational metadata | verified |
| SURF-18 | `20260728_pure_ui_deval_loading_contract` | DEVAL authorization/CAP, parent-owned PUP tracking, owned-job validation, fail-closed polling, confined worker/artifact, and reload; 157 focused Python + 5 Jest | high security review passed | High / `high`: CAP, queue, job metadata and generated artifact | verified |

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

- a concise intended-versus-observed field/action matrix;
- actual-render evidence for template-defined names, values, and state;
- focused serialization, parser, persistence/reload, and RQ tests only where
  those boundaries apply;
- a failing regression for each confirmed mismatch when practical;
- the smallest compatible production patch for each mismatch;
- focused tests first, then existing applicable broad gates;
- generated-bundle freshness when controller source changes;
- security review only when the actual patch changes an attack surface; and
- one independent correctness review for a production patch.

Test/documentation-only packages do not create hypothetical security artifacts
or dual-review files. A second independent review is reserved for high-risk
behavior changes, material shared-producer fan-out, or explicit operator
request. Record remaining gaps plainly without constructing N/A evidence for
layers that do not apply.

Queue-edge changes additionally require the RQ dependency catalog and
`wctl check-rq-graph`. Parameter/default/formula/unit/fallback changes require
the parameterization ADR gate.

## Estimate and Boundary Preflight

Each controller iteration is expected to fit one focused work package. On the
first day, confirm:

- one controller or inseparable facet;
- actual template and controller sources;
- direct route/state/RQ owners;
- exact focused tests;
- risk-bearing fields/actions; and
- exclusions preventing cleanup or redesign.

Split or narrow the package if one controller contains multiple unrelated
security boundaries or cannot be tested and repaired incrementally. Do not
expand infrastructure to make a broad package appear manageable.

## Capacity and Timeline

The register size does not create an up-front schedule or infrastructure
milestone. Execute one controller at a time and report observed duration after
each package. After five controllers, review mismatches found, runtime, helper
size, false tooling failures, and operator effort. Continue while the loop
provides positive measured value.

GOV-01 remains deferred unless that five-controller evidence demonstrates a
specific miss or repeated burden that existing tests and a small helper cannot
solve. The default is continued controller testing, not platform construction.
