# Deferred retry finite surface matrix

This matrix is the exhaustive SURF-20A implementation boundary. A backend row
is included when a user-facing submission persists an RQ job hint, constructs a
dependent workflow, or scans registries to reject a submission. A frontend row
is included when it disables/rejects submission or polls based on RQ state.
Routes that enqueue fire-and-forget operator maintenance without a controller,
saved hint, dependency graph, or user retry surface are excluded.

## Shared admission invariant

Every included submission uses one common admission service. It acquires an
owner-safe, expiring Redis lock keyed by canonical resource identity and
conflict family; verifies run/batch, operation family, origin, and lineage;
blocks on any queued/started/scheduled associated node; conditionally cancels
the complete deferred subgraph using watched RQ keys; preallocates the
replacement ID; durably saves that exact ID; and finally enqueues using the
preallocated ID. The lock uses an unguessable owner token, compare-and-delete
release, and bounded renewal through the admission transaction. A lock timeout
returns the existing conflict/service-busy response and never mutates a job.

If durable hint save fails, enqueue is never attempted. If enqueue fails, the
preallocated hint resolves as missing and is retryable without another cleanup
step. There is no post-enqueue hint write and no emergency persistence path.

## Backend producers and guards

| Owner | Exact source | Hints/workflow | Conflict family and association |
| --- | --- | --- | --- |
| SURF-02A/B | `wepppy/microservices/rq_engine/batch_routes.py`; `wepppy/rq/batch_rq.py::_active_batch_job_summaries` and new uncapped candidate collector | BatchRunner run/delete hints; registry-scanned child graph | Validated batch name; run and delete are one resource-conflict family and all safely associated deferred nodes from either operation are superseded |
| Culvert batch surface | `wepppy/microservices/rq_engine/culvert_routes.py`; `wepppy/rq/culvert_rq.py`; `wepppy/rq/culvert_rq_pipeline.py`; `wepppy/nodb/culverts_runner.py` | CulvertsRunner batch/retry/finalize hint and child/finalizer graph | Verified culvert batch UUID, `culvert` origin/operation family, and lineage; submit/retry/finalize are one conflict family under an owner-safe batch-UUID lock |
| DOM-02 | `wepppy/weppcloud/routes/nodb_api/project_bp.py::task_set_readonly`; `wepppy/rq/project_rq.py::set_run_readonly_rq` | RedisPrep `set_readonly` hint | Authorized run ID and readonly operation/origin; owner-safe per-run readonly admission lock |
| DOM-05/06/07 | `watershed_routes.py` channel, outlet, subcatchment enqueue paths | RedisPrep hints; subcatchment dependent graph | Run ID, exact watershed operation except subcatchment graph lineage |
| DOM-08A/B/09 | `landuse_routes.py` build/modify paths | RedisPrep hints | Run ID, exact landuse operation/origin |
| DOM-10 | `soils_routes.py` | RedisPrep hint | Run ID, soils operation/origin |
| DOM-11A/B | `climate_routes.py`; `upload_climate_routes.py` | RedisPrep build/upload hints | Run ID; build/upload conflict where they mutate the same climate resource |
| DOM-13C/D | `ag_fields_routes.py`; `wepppy/rq/ag_fields_rq.py` | RedisPrep roots/suite and child graph | Run ID, AgFields operation family, origin, lineage |
| DOM-14A/B/C and DOM-15 | `wepp_routes.py`; WEPP/SWAT no-prep paths in `bootstrap_routes.py`; `swat_routes.py`; `wepppy/rq/wepp_rq.py`; `wepppy/rq/swat_rq.py` | RedisPrep roots and recursive `jobs:*` graphs | Run ID; WEPP family remains mutually exclusive; SWAT exact family; verified origin/lineage |
| DOM-16 | `dss_export_routes.py` | RedisPrep post-DSS hint | Run ID and DSS operation/origin |
| DOM-17 | `treatments_routes.py` | RedisPrep hint | Run ID and Treatments operation/origin |
| DOM-18 | `debris_flow_routes.py` | RedisPrep hint | Run ID and debris-flow operation/origin |
| DOM-19 | `roads_routes.py`; legacy `weppcloud/routes/nodb_api/roads_bp.py`; `wepppy/rq/roads_rq.py` | RedisPrep prepare/run hints | Run ID; prepare/run are one Roads conflict family |
| DOM-20B | `export_routes.py` features/ERMIT paths | RedisPrep export hints | Run ID and exact export operation/origin |
| DOM-21 | `rap_ts_routes.py` | RedisPrep hint | Run ID and RAP operation/origin |
| DOM-22 | `openet_ts_routes.py` | RedisPrep hint | Run ID and OpenET operation/origin |
| DOM-24 | `weppcloud/routes/nodb_api/rangeland_bp.py` | RedisPrep hint | Run ID and Rangeland operation/origin |
| DOM-25A/B | `omni_routes.py`; `wepppy/rq/omni_rq.py` | RedisPrep run/delete hints and dependent graphs | Run ID; scenario/contrast execution uses verified exact graph; contrast run/delete are one resource-conflict family |
| DOM-26 | `rhem_routes.py` | RedisPrep hint | Run ID and RHEM operation/origin |
| DOM-27 | `geneva_routes.py`; legacy `weppcloud/routes/nodb_api/geneva_bp.py` | Geneva active/last job state and dependent panel/batch graph | Run ID, Geneva operation family, origin, lineage |
| DOM-28 | `weppcloud/routes/nodb_api/path_ce_bp.py` | RedisPrep hint | Run ID and Path CE operation/origin |
| DOM-29 | `rusle_routes.py` | RedisPrep hint | Run ID and RUSLE operation/origin |
| DOM-01 | `ash_routes.py` | RedisPrep Ash hint | Run ID and Ash operation/origin |
| DOM-29 | `polaris_routes.py` | RedisPrep POLARIS hint consumed by RUSLE | Run ID and POLARIS operation/origin |
| SURF-03/04 | `fork_archive_routes.py`; `weppcloud/routes/archive_dashboard/archive_dashboard.py` | Fork hint, archive hint/claim, dependent finalizer | Authorized source/destination run identity and `fork-archive` origin. Archive create/restore/delete conflicts are one resource family; fork lineage is separate unless it targets the same locked destination |
| SURF-08 | `migration_routes.py`; `run_sync_routes.py` | RedisPrep migration hint and deferred migration child | Run ID, migration/sync operation family, origin, lineage |
| SURF-18 | `weppcloud/routes/weppcloudr.py` | Parent-owned DEVAL hint and existing job metadata | Run/config, DEVAL operation/origin, lineage |

The following RedisPrep hint writers enqueue independent jobs with no current
dependency edges but still consume the shared admission service so a legacy,
mixed-version, or future deferred receipt cannot be overwritten: `ash_routes`,
`climate_routes`, `debris_flow_routes`, `dss_export_routes`, `export_routes`,
`landuse_routes`, `openet_ts_routes`, `polaris_routes`, `rap_ts_routes`,
`rhem_routes`, `rusle_routes`, `soils_routes`, `treatments_routes`,
`upload_climate_routes`, and the watershed channel/outlet paths. Their tests
prove ordinary queued/started/scheduled protection is unchanged and a synthetic
deferred prior receipt is canceled before replacement.

## Frontend state owners

| Owner | Exact source | Required deferred behavior |
| --- | --- | --- |
| SHR-03A and all `controlBase` consumers | `controllers_js/control_base.js`, its Jest suite, generated `static/js/controllers-gl.js` | Display deferred and job hint, stop polling, enable command |
| DOM-19 | `controllers_js/roads.js` and tests | Reconcile/clear `_activeTaskKey` when authoritative state is deferred; submit normally |
| DOM-13C/D | `controllers_js/ag_fields.js` and tests | Deferred IDs are excluded from `active_job_ids`; actions remain enabled |
| SURF-02A/B | `controllers_js/batch_runner.js` and tests | Deferred batch tree does not retain run/delete UI latch after refresh |
| SURF-08 | `routes/run_0/templates/run_0/rq-migration-status.htm` and inline Jest | Display deferred, stop polling, enable submission |
| SURF-18 | `templates/reports/deval_loading.htm` and inline Jest | Display deferred, stop polling, make refresh/retry action available |
| DOM-20B | `templates/reports/ermit_export_download.htm` and inline Jest | Display deferred, stop polling, permit ordinary export resubmission |
| SURF-03/04 | Archive/fork controller/template active projections and tests | Deferred is not presented as running; server cleanup remains authoritative |
| Culvert batch surface | Culvert batch/retry/finalize client or dashboard state and focused tests | Deferred graph never blocks retry/finalize UI; replacement response becomes the tracked receipt |
| DOM-02 | Project readonly controller/action tests | Deferred readonly receipt does not disable the ordinary readonly submission |

The RQ job dashboard is diagnostic, not a submission controller, and continues
to display deferred as raw nonterminal status. Orchestration/readiness schema
descriptors likewise retain raw RQ classification.
