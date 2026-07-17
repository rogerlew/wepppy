# Pure UI Controller Audit Register

**Status**: Population boundary frozen; included items are contractual and
evidence remains unverified unless stated otherwise
**Last updated**: 2026-07-17 UTC
**Authority**: This file is the coverage/item ledger. Stable execution boundaries
live in `artifacts/child_package_register.md`. The future
`docs/ui-docs/contracts/README.md` is a generated/published reader index, not a
second editable coverage authority. Inclusion in this ledger is a binding
maintenance and ratification obligation, not a suggestion for later discovery.

## Population Rule

An item is in scope when it is a domain controller or state-changing supporting
component rendered by a Pure WEPPcloud run page or Pure standalone console. The
inventory must reconcile all of these evidence sources:

1. modules selected by
   `wepppy/weppcloud/controllers_js/build_controllers_js.py`;
2. runtime bootstrap/registry behavior in `bootstrap.js` and run-page context;
3. templates anywhere under `wepppy/weppcloud/` that import Pure macros or
   inherit a Pure base directly or transitively, including route-local `.html`
   templates, nested advanced options, security/account pages, and modals;
4. standalone Pure route templates and controller bundles;
5. route, NoDb, RQ, and test references reached from each controller.

A helper or read-only partial may share a parent contract instead of receiving
its own domain contract. That decision must appear in this register with a
rationale and parent link. A config-gated controller is not excluded merely
because it is absent from the default run page.

## Contractual Status and Evidence Grade

Coverage obligation and evidence maturity are separate axes:

- `contractual`: the item is unconditionally in scope. Its registered owner must
  maintain and ratify a canonical contract. It cannot be ignored, downgraded to
  optional, or removed without explicit operator approval and dual independent
  review.
- `excluded`: an explicit dual-reviewed decision proves that the surface has no
  independent Pure UI state contract. Excluded surfaces remain listed with
  their parent or rationale.
- `unverified`: the obligation is binding, but endpoint-level metadata,
  generated/runtime evidence, or tests are incomplete.
- `documented`: a canonical normative contract exists, but one or more required
  verification gates remain incomplete.
- `verified`: generated/runtime evidence, tests, named revision, and both
  reviews establish the documented behavior.

Package execution states such as `planned`, `auditing`, and `blocked` live in
the child-package register and trackers. They never weaken `contractual` scope.
An unverified contract is still a contract; the evidence grade only limits what
may be claimed about observed implementation conformance.

## Required Row Data

Every contractual row already records enough identity and ownership to bind the
future work. Before its evidence grade advances to `documented`, record:

- public controller/component name and source module;
- Pure template or rendered host;
- bootstrap/config gates;
- browser/session and rq-engine endpoints;
- NoDb or server mutation owner and RQ worker when applicable;
- frontend/backend tests and known coverage gaps;
- canonical contract path and child-package path;
- source-to-contract manifest key, mapped source globs, and contract test paths;
- security triage, risk tier, status, last verified commit/date;
- parent contract for helpers or an exclusion rationale.

The GOV-00A ratification package standardizes these fields and publishes the
canonical schema. Missing detail is a required-work gap owned by the registered
package, never a reason to treat the row as non-contractual.

## Reconciled Coverage Ledger

Path aliases in the tables are exact: `C/` is
`wepppy/weppcloud/controllers_js/`, `T/` is
`wepppy/weppcloud/templates/controls/`, `R/` is
`wepppy/weppcloud/routes/`, and `J/` is
`wepppy/weppcloud/controllers_js/__tests__/`. Route-family entries are the
finite Python files the child must expand to endpoint-level rows. `No RQ` is an
explicit planning assertion to verify, not permission to omit reload evidence.

### Run bootstrap items

| Key / package | Source and rendered host | Route, state, and RQ boundary | Focused evidence / config / security | Contract scope | Evidence grade |
| --- | --- | --- | --- | --- | --- |
| `project` / DOM-02 | `C/project.js`; run header | `R/nodb_api/project_bp.py`, `Ron`/SQL Run, project RQ | `J/project.test.js`; all runs; high | contractual | unverified |
| `team` / DOM-03 | `C/team.js`; `T/team_pure.htm` | project/team routes, SQL owner/collaborator; no RQ expected | `J/team.test.js`; auth variants; high | contractual | unverified |
| `map` / DOM-04A/04B | `C/map_gl.js` + four `C/map_gl_*` helpers; `T/map_pure_gl.htm` | `R/nodb_api/watershed_bp.py` and public map/query routes; map state; no RQ expected | `J/map_gl.test.js`; layer/config matrix; low, public-route change high | contractual | unverified |
| `channel` / DOM-05 | `C/channel_gl.js`; `T/channel_delineation_pure.htm` | `R/nodb_api/watershed_bp.py`, Watershed; delineation/build RQ | `J/channel_gl.test.js`; DEM modes; high | contractual | unverified |
| `outlet` / DOM-06 | `C/outlet_gl.js`; `T/set_outlet_pure.htm` | `R/nodb_api/watershed_bp.py`, Watershed; outlet RQ | `J/outlet_gl.test.js`; map modes; high | contractual | unverified |
| `subcatchment` / DOM-07 | `C/subcatchments_gl.js`; `T/subcatchments_pure.htm` | `R/nodb_api/watershed_bp.py`, Watershed; abstraction RQ | `J/subcatchments_gl.test.js`; config gates; high | contractual | unverified |
| `landuse` / DOM-08A/08B | `C/landuse.js`; `T/landuse_pure.htm`, `landuse_map.htm`, `landuse_user_defined.htm` | `R/nodb_api/landuse_bp.py`, Landuse; build RQ | `J/landuse.test.js` + two inline suites; modes/catalogs; high | contractual | unverified |
| `landuseModify` / DOM-09 | `C/landuse_modify_gl.js`; `T/modify_landuse.htm` | landuse/watershed routes, Landuse; mutation/build RQ | `J/landuse_modify_gl.test.js`; mod gate; high | contractual | unverified |
| `soil` / DOM-10 | `C/soil.js`; `T/soil_pure.htm` | `R/nodb_api/soils_bp.py`, Soils; build RQ | `J/soil.test.js`; mode/upload matrix; high | contractual | unverified |
| `climate` / DOM-11A/11B | `C/climate.js`; `T/climate_pure.htm` and sections | `R/nodb_api/climate_bp.py`, Climate; build/fetch RQ | `J/climate.test.js`; provider/upload/scaling matrix; high | contractual | unverified |
| `observed` / DOM-12 | `C/observed.js`; `T/observed_pure.htm` | `R/nodb_api/observed_bp.py`, Observed/Climate; fetch/upload path | `J/observed.test.js`; enabled configs; high if mutation | contractual | unverified |
| `agFields` / DOM-13A..13D | `C/ag_fields.js`; `T/ag_fields_pure.htm` | `R/run_0/run_0_bp.py`, AgFields; `wepppy/rq/ag_fields_rq.py` stage/suite chain | `J/ag_fields.test.js`; ag_fields configs/schemes; high | contractual | unverified |
| `wepp` / DOM-14A..14C | `C/wepp.js`; `T/wepp_pure.htm` plus WEPP/SWAT advanced partials | `R/nodb_api/wepp_bp.py`, Wepp/SWAT; WEPP stage pipeline | `J/wepp.test.js`; model/advanced/config matrix; high | contractual | unverified |
| `bootstrap` / DOM-15 | `C/bootstrap_control.js`; `T/bootstrap_pure.htm` | `R/bootstrap.py`, Bootstrap; enable/checkout/disable RQ | `J/bootstrap_control.test.js`; admin/config variants; high | contractual | unverified |
| `dssExport` / DOM-16 | `C/dss_export.js`; `T/dss_export_pure.htm` | `R/run_0/run_0_bp.py`, Wepp export fields; `wepp_rq_dss.py` | `J/dss_export.test.js`; export modes; high | contractual | unverified |
| `treatments` / DOM-17 | `C/treatments.js`; `T/treatments_pure.htm` | `R/nodb_api/treatments_bp.py`, Treatments; upload/build RQ | `J/treatments.test.js`; mod modes; high | contractual | unverified |
| `debrisFlow` / DOM-18 | `C/debris_flow.js`; `T/debris_flow_pure.htm` | `R/nodb_api/debris_flow_bp.py`, DebrisFlow; run RQ | `J/debris_flow.test.js`; role/config gates; high | contractual | unverified |
| `roads` / DOM-19 | `C/roads.js`; `T/roads_pure.htm` | `R/nodb_api/roads_bp.py`, Roads; `wepppy/rq/roads_rq.py` | `J/roads.test.js`; mod/config/upload matrix; high | contractual | unverified |
| `roadsMapOverlay` / DOM-19 | `C/roads_gl.js`; map host/roads report | roads/map routes and Roads artifacts; no independent RQ | `J/roads_gl.test.js`; roads gate; high as DOM-19 adjunct | contractual | unverified |
| `featuresExport` / DOM-20A/20B | `C/features_export.js`; `T/features_export_pure.htm` | `R/run_0/run_0_bp.py`, service/cache; `features_export_rq.py` | `J/features_export.test.js`; catalog/profile/config matrix; high | contractual | unverified |
| `rapTs` / DOM-21 | `C/rap_ts.js`; `T/rap_ts_pure.htm` | `R/run_0/run_0_bp.py`, RAP_TS; fetch/analyze RQ | `J/rap_ts.test.js`; date/config matrix; high | contractual | unverified |
| `openetTs` / DOM-22 | `C/openet_ts.js`; `T/openet_ts_pure.htm` | `R/run_0/run_0_bp.py`, OpenET_TS; fetch/analyze RQ | `J/openet_ts.test.js`; admin/provider gate; high | contractual | unverified |
| `disturbed` / DOM-23 | `C/disturbed.js`; `T/disturbed_sbs_pure.htm` | `R/nodb_api/disturbed_bp.py`, Disturbed; build/invalidation RQ | `J/disturbed.test.js`; disturbed/BAER configs; high | contractual | unverified |
| `baer` / DOM-23 | `C/baer.js`; shared SBS template | disturbed route, Baer/SbsMap; shared build/invalidation | `J/baer.test.js`; BAER gate; high, joint-boundary probe | contractual | unverified |
| `rangelandCover` / DOM-24 | `C/rangeland_cover.js`; `T/rangeland_cover_pure.htm` | `R/nodb_api/rangeland_cover_bp.py`, RangelandCover; build RQ | `J/rangeland_cover.test.js`; gate/modes; high | contractual | unverified |
| `rangelandCoverModify` / DOM-24 | `C/rangeland_cover_modify_gl.js`; `T/modify_rangeland_cover.htm` | rangeland-cover/watershed routes and state; build RQ | `J/rangeland_cover_modify_gl.test.js`; gate; high | contractual | unverified |
| `omni` / DOM-25A/25B | `C/omni.js`; `T/omni_scenarios_pure.htm` | `R/nodb_api/omni_bp.py`, Omni; `wepppy/rq/omni_rq.py` | `J/omni.test.js`; modes/scenario matrix; high | contractual | unverified |
| `omniContrastOverlays` / DOM-25B | `C/omni_contrasts_gl.js`; `T/omni_contrasts_pure.htm` | Omni routes/state/artifacts; contrast run/delete RQ | `J/omni_contrasts_gl.test.js`; contrast modes; high | contractual | unverified |
| `rhem` / DOM-26 | `C/rhem.js`; `T/rhem_pure.htm` | `R/nodb_api/rhem_bp.py`, Rhem/RhemPost; run RQ | `J/rhem.test.js`; gate/config matrix; high | contractual | unverified |
| `geneva` / DOM-27 | `C/geneva.js`; `T/geneva_pure.htm` | `R/nodb_api/geneva_bp.py` config/task/status/results/frequency/CN functions, Geneva; `geneva_rq.py` chain; SURF-11 owns four summary query/report functions | `J/geneva.test.js`; gate/config matrix; high | contractual | unverified |
| `ash` / DOM-01 | `C/ash.js`; `T/ash_pure.htm` | `R/nodb_api/watar_bp.py`, Ash; ash/WEPP RQ | `J/ash.test.js`; WATAR model/mode/files; high | contractual | unverified |
| `pathCe` / DOM-28 | `C/path_ce.js`; `T/path_cost_effective_pure.htm` | `R/nodb_api/path_ce_bp.py`, PathCostEffective; `path_ce_rq.py` | `J/path_ce.test.js`; role/config gates; high | contractual | unverified |
| `rusle` / DOM-29 | `C/rusle.js`; `T/rusle_pure.htm` | `R/run_0/run_0_bp.py`, Rusle; build RQ | `J/rusle.test.js`; gate/mode matrix; high | contractual | unverified |

All 33 rows are `contractual / unverified`. Their future child package and
contract paths, manifest keys/globs, endpoint/function expansion, and verified
revision/date are mandatory ratification evidence; their absence cannot remove
or weaken the contract obligation.

### Bundled shared and standalone items

| Item(s) | Owner | Host/consumer boundary | Focused evidence and security | Contract scope | Evidence grade |
| --- | --- | --- | --- | --- | --- |
| `dom.js`, `events.js`, `forms.js`, `utils.js`, `selection_utils.js` | SHR-01 | all Pure forms; selection consumers DOM-04A/09/24 | `J/dom.test.js`, `events.test.js`, `forms.test.js`, `utils_labels.test.js`, `utils_url_for_run.test.js`; selection gap; low | contractual | unverified |
| `http.js`, `recorder_interceptor.js` | SHR-02 | all HTTP/CSRF/session consumers | `J/http.test.js`, `recorder_interceptor.test.js`, `csrf_bootstrap.test.js`, `session_heartbeat.test.js`; high | contractual | unverified |
| `status_stream.js`, `control_base.js` | SHR-03A | run controllers and stateful consoles | `J/control_base.test.js`; StatusStream gap; high | contractual | unverified |
| `bootstrap.js`, `bootstrap_observability.js` | SHR-03B | run bootstrap and generated bundle | `J/bootstrap.test.js`, `bootstrap_observability.test.js`, `controllers_gl_stale_check.test.js`; high | contractual | unverified |
| Pure bases/macros | SHR-04A | every direct/transitive Pure template | render suite gap; low until behavior change | contractual | unverified |
| `modal.js`, `details_menu.js`, `theme.js`, `console_utils.js` | SHR-04B | run modals, Browse/README hosts, Archive/Fork consoles | theme/modal/details direct gaps; low | contractual | unverified |
| `unitizer_client.js` + generated map | SHR-05 | modal, Project, Geneva report | generated-map/backend round-trip gap; high | contractual | unverified |
| Command Bar scripts/templates | SHR-06 | run and Browse/README hosts | WebSocket/token/command evidence; high | contractual | unverified |
| PowerUser scripts/templates | SHR-07 | privileged run header | role/action/web-push evidence; high | contractual | unverified |
| `batch_runner.js` | SURF-02A | Batch create/manage roots; SURF-02B consumes the producer contract for execution | `J/batch_runner.test.js`; high | contractual | unverified |
| `run_sync_dashboard.js` | SURF-05 | Run Sync root | no direct Jest suite; high | contractual | unverified |
| `geneva_summary_report.js` | SURF-11 | Geneva summary template | `J/geneva_summary_report.test.js`; high if remediation | contractual | unverified |
| `interfaces_captcha.js` | SURF-01 | public create/CAP templates | direct CAPTCHA gap; high | contractual | unverified |

This reconciles all 56 modules selected by `_collect_controller_modules()`: 37
run-support files, 15 shared/global files, and four standalone files.

### Stateful Pure surfaces outside the bundle register

| Surface | Package | Exact host boundary | Security | Contract scope | Evidence grade |
| --- | --- | --- | --- | --- | --- |
| Public creation/CAP | SURF-01 | `templates/interfaces.htm`, `templates/run_0/create_index.htm`, `templates/cap_gate.htm`, `templates/locations/{joh,portland,seattle,spu}/index.htm` | high | contractual | unverified |
| Batch creation/execution | SURF-02A/02B | `R/batch_runner/templates/{create,manage_pure,batch_runner_pure}.htm` | high | contractual | unverified |
| Archive console | SURF-03 | `R/archive_dashboard/templates/rq-archive-dashboard.htm` | high | contractual | unverified |
| Fork console | SURF-04 | `R/fork_console/templates/rq-fork-console.htm` | high | contractual | unverified |
| Run Sync | SURF-05 | `R/run_sync_dashboard/templates/rq-run-sync-dashboard.htm` | high | contractual | unverified |
| Runs catalog | SURF-06 | `templates/user/runs2.html` | high | contractual | unverified |
| RQ job dashboard | SURF-07 | `R/rq/job_dashboard/templates/dashboard_pure.htm` | high | contractual | unverified |
| Run migration status | SURF-08 | `R/run_0/templates/run_0/rq-migration-status.htm` | high | contractual | unverified |
| README editor | SURF-09 | `R/readme_md/templates/{readme_editor,readme_view}.htm` | high | contractual | unverified |
| Disturbed CSV editor | SURF-10 | `T/edit_csv.htm` | high | contractual | unverified |
| Geneva summary | SURF-11 | `templates/reports/geneva/summary.htm`; `R/nodb_api/geneva_bp.py::{query_geneva_summary,query_geneva_hru_map_rows,query_geneva_hru_map_features,report_geneva_summary}` | high if remediated | contractual | unverified |
| Report shell | SURF-12 | `templates/reports/_base_report.htm` and finite domain consumers in child register | low | contractual | unverified |
| Security/auth forms | SURF-13 | `templates/security/*.html` through `_layout.html` | high | contractual | unverified |
| User profile/session | SURF-14 | `templates/user/profile.html` | high | contractual | unverified |
| Root user modification | SURF-15 | `templates/user/usermod.html` | high | contractual | unverified |
| ERMiT export/download | SURF-16 | `templates/reports/ermit_export_download.htm`; `R/nodb_api/wepp_bp.py`; `wepppy/microservices/rq_engine/export_routes.py`; `wepppy/rq/ermit_export_rq.py`; `tests/weppcloud/routes/test_pure_controls_render.py`, `test_wepp_bp.py`, and `tests/microservices/test_rq_engine_export_routes.py` | high | contractual | unverified |
| RQ Info Details | SURF-17 | `R/rq/info_details/templates/info_details.htm`; `R/rq/info_details/routes.py::rq_info_details`; `tests/weppcloud/routes/test_rq_info_details.py` | high: Admin/Root Redis/RQ and submitter metadata | contractual | unverified |
| DEVAL loading | SURF-18 | `templates/reports/deval_loading.htm`; `R/weppcloudr.py::{deval_details,_determine_job,_enqueue_deval_job}`; `wepppy/rq/weppcloudr_rq.py::render_deval_details_rq`; no focused template/poll suite yet | high: CAP, queue, job state and generated report | contractual | unverified |

Direct report-container consumers are itemized rather than hidden under
SURF-12: Ash report pages are DOM-01; `debris_flow.htm` is DOM-18;
`storm_event_analyzer.htm` and WEPP report pages are DOM-14A (with observed data
owned by DOM-12); Geneva summary is SURF-11; RHEM page-container reports are
DOM-26; ERMiT is SURF-16; and DEVAL loading is SURF-18. SURF-12 owns only the
generic `_base_report.htm` and `_page_container.htm` producer behavior.

Diagnostics and GL Dashboard are contractually excluded from this initiative by
dual-reviewed parent/exclusion decisions: they have separate specifications and
architectures and are not run/console controller contracts. UI Showcase is
SHR-04A/04B evidence, not a product contract;
the internal workflow placeholder is parented to its eventual host; vendor code,
passive Browse content, and UserSummary's read-only GET search are host-only,
while their loaded shared scripts remain SHR consumers.

## Audit Matrix Required in Each Canonical Contract

Each child package expands its rows into an exact matrix. At minimum:

| Layer | Required evidence |
| --- | --- |
| Rendered DOM | form id, input id, submitted name, type, default, disabled/hidden behavior, data hooks |
| Controller | selector, hydration source, cached state, serialization method, emitted/consumed events |
| Transport | method, URL, encoding, auth/CSRF/session boundary, canonical keys/types/enums/files |
| Parser | route function, `parse_request_payload` schema/defaults, alias and conflict precedence |
| Mutation | NoDb/server attribute, validation, lock/dump behavior, invalidation and timestamps |
| RQ | enqueue site, worker, dependency/completion/error semantics where applicable |
| Reload | persisted representation, bootstrap seed, old-run compatibility, value round trip |
| Tests | rendered-template assertion, JS payload test, backend parser/mutation test, integration/manual evidence |

## Coverage Rules

- `id` and `name` are separate contract fields. A macro default that makes them
  equal is not evidence that the server expects the same token.
- Public labels, internal enum values, submitted tokens, and persisted values
  must be listed separately.
- Hidden, disabled, unchecked, empty, and absent values must have explicit
  semantics; do not infer them from HTML defaults.
- Legacy aliases must name precedence and deprecation behavior. Silent
  last-write-wins behavior is a defect unless explicitly intended and tested.
- File inputs require extension/size, multipart, temporary storage, and cleanup
  behavior.
- RQ-backed controls require both enqueue and terminal-state evidence.
- A contract is `verified` only at a named commit and with named tests/evidence.
- Every submitted, hydrated, persisted, enum/file, hidden/disabled-sensitive, or
  RQ-controlling value is material/risk-bearing by default. A field, mode, or
  configuration may be excluded only with a written rationale and approval by
  both independent reviewers.
- Verification uses a per-field, per-mode, and per-configuration evidence matrix.
  An untested material variant remains `documented`, not `verified`.
- Each mismatch records observed behavior, normative behavior, authority/
  rationale, discrepancy status, and disposition evidence. A material unresolved
  discrepancy blocks `verified`.

## Reconciliation Checklist

- [x] Capture the bundle module list from `_collect_controller_modules()`.
- [x] Capture all source-declared runtime controller/bootstrap keys and config
  gates; representative rendered-config verification remains package evidence.
- [x] Capture every Pure macro-importing or Pure-base-inheriting template and its
  rendered host.
- [x] Classify route-local Batch Runner, archive dashboard, fork console, and
  run-sync dashboard surfaces as domain contracts or documented exclusions.
- [x] Map each domain controller to route family, mutation owner, RQ family, and
  focused tests; endpoint/function expansion remains package work.
- [x] Mark shared helpers and read-only panels with parent/exclusion rationale.
- [ ] Compare against `control-inventory.md` and archived modernization plans.
- [x] Resolve production GL sources versus retained legacy suites, including the
  `subcatchments_gl.js`/`subcatchment_delineation.js` evidence ambiguity.
- [ ] Expand rendered-template coverage beyond the current small subset in
  `tests/weppcloud/routes/test_pure_controls_render.py`.
- [ ] Add a machine-checkable register representation only after the pilot
  proves which metadata is stable enough to enforce.
- [ ] Add source-to-contract/test mappings and shared-producer consumer fan-out.
- [ ] Prove the change-aware gate fails when a mapped source changes without its
  contract/test or a dual-reviewed no-impact attestation.
- [x] Have both independent reviewers confirm population completeness and the
  two proposed exclusions.
