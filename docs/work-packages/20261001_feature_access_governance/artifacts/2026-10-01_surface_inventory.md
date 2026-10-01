# FA-01 source and acceptance inventory

Prepared: 2026-10-01 20:47 UTC. Source baseline: `45a39a8337d37c7f7d30087ff4d23c03610072b3`.

The exact current declarations and admission classifications are in [the route inventory](2026-10-01_route_inventory.tsv); [M0 evidence](2026-10-01_milestone_zero.md) freezes the feature-only scope. This overview is not a claim that all ordinary routes change. All paths below are repository-relative.

## Source boundaries

| Boundary | Files/symbols | Required outcome |
| --- | --- | --- |
| Account records | `wepppy/weppcloud/app.py` User/Role and adjacent new records; `migrations/versions/` | Additive upgrade; current membership and retained audit history; no fabricated identity/acceptance |
| PowerUser/profile | `routes/user.py` profile/token paths; `templates/user/profile.html` | Two-question current-user onboarding; atomic role/acceptance; existing token scopes unchanged |
| Group administration | `routes/admin.py`; proposed `templates/user/feature_access.html` | Root administrative boundary; required reason, actor/time, history; no implicit execution grant |
| Registry | `feature_registry/{schema.py,runtime.py,feature_registry.yaml,config_registry.yaml}` | Live group decision separate from immutable metadata; conservative override; no new config/model parameters |
| Run/UI/mod state | `routes/run_0/run_0_bp.py`, `routes/run_0/templates/runs0_pure.htm`, `templates/header/_run_header_fixed.htm`, `routes/nodb_api/project_bp.py`, controller/bootstrap consumers | Public non-embargoed inspection; existing authorization plus restricted-feature entitlement; no mutation on inspect |
| OpenET | rq-engine `openet_ts_routes.py:acquire_openet_ts` and run/mod consumers | Group-only action; one initial member; read existing public results without acquiring API data |
| Omni Contrasts | Flask `routes/nodb_api/omni_bp.py`; rq-engine `omni_routes.py` execute/dry-run/delete; generic data routes | Dev/Root or contrast group; retain public embargo exception across actions and data |
| PATH-CE | `routes/nodb_api/path_ce_bp.py`; `nodb/mods/path_ce/preconditions.py` and controller readers | Inspect without `_ensure_controller` mutation; action group/role plus contrast entitlement; existing scientific preconditions |
| AgFields | rq-engine `ag_fields_routes.py:_authorize` and each upload/build/read/delete consumer | Distinguish action/read operations; no role-only display gate bypass |
| Batch | `routes/batch_runner/batch_runner_bp.py`; rq-engine `batch_routes.py`, `upload_batch_runner_routes.py`; grouped browse/data | Group-only human actions/private grouped data; public-base-read exception; account-only initial membership |
| Culvert | rq-engine `culvert_routes.py`; job/cancel APIs; browse `_download.py` and grouped roots | Human group path plus separately preserved submit/retry/finalize/poll/cancel service path and batch-scoped browse token |
| Generic data | `wepppy/microservices/browse/{auth.py,browse.py,_download.py,dtale.py}`, dedicated download, `_gdalinfo.py`, `wepppy/query_engine/app/` and MCP | Real principal/resource checks; no JWT-group-only admission; no embargo bypass through files/query/download |
| Derived/aggregate data | Fork/archive/export routes, Omni child run resolution, orchestration read routes | Exact inherited-data/bundle disposition; no blanket denial of unrelated public views |
| Common identity/writes | `utils/helpers.py:authorize`, rq-engine `auth.py`, `session_routes.py`, current token validators | Preserve ordinary anonymous behavior; add provenance checks only for restricted admission |

File prefixes in the middle rows are `wepppy/weppcloud/` for Flask and `wepppy/microservices/rq_engine/` for rq-engine unless written fully.

## Known artifact anchors to trace

`omni/contrasts.out.parquet`, contrast documentation/selection artifacts, `_pups/omni/contrasts/`, and PATH-CE's consumption of contrast output establish that the protected report is not the only data surface. Trace the actual writers, catalogs and archive membership to enumerate all representations. These anchors are evidence leads, not a sufficient deny-list. Public ordinary/scenario outputs must remain readable where no embargo applies.

## Valid-state and principal matrix

| State | Observable acceptance |
| --- | --- |
| Feature absent / never used | Public inspection shows no results without creating NoDb/files/jobs; authorized enable follows ordinary workflow |
| Present but empty | Empty read view, no fabricated results; permitted actions usable |
| Populated | Read existing results; restricted actions require existing run authorization and feature entitlement |
| Supported legacy | Existing PowerUser/Dev paths preserved where specified; no invented acknowledgments; current group-only restrictions explicit |
| Malformed group/resource/identity | Bounded explicit error, no grant/no mutation/no secret leakage |
| Membership removed/expired | New protected admission denied even with an old user JWT or human-derived session; already-admitted jobs may finish |
| Review date passed, no expiry | Current membership remains effective pending documented reassessment |
| Database unavailable | Explicit unavailable result where membership is required; no broad-role fallback |
| Public with embargoed artifacts | Non-embargoed views remain readable; protected representations follow retained exception |
| Readonly project / unsupported backend | Read retained permitted results; no action privilege override |

Cross these states with anonymous public visitor, ordinary authenticated nonowner/owner, PowerUser, group member/nonmember, each technical role individually, existing anonymous session, verified Culvert submitting service, returned browse token and wrong-resource/expired/revoked tokens. Root group administration and Root feature execution are separate cases.

Trace private Batch session issuance and every session consumer explicitly. Test Admin/Root without the group, a removed member with an old session, a valid member with a scoped session, and the public Batch exception; resource scope alone is insufficient for private human access.

Trace bearer-to-session identity conversion (`session_routes.py:_identity_from_claims` and its callers). Include a logged-in human session, anonymous public session, service subject numerically equal to a member account ID, and service/MCP-derived sessions with human-looking roles/groups. Preserve authorized service outcomes without treating those credentials as human members.

Trace trusted human-delegated service issuance at `routes/user.py:mint_run_token` (`admin-run-token:<user_id>`) and Batch base-run aliases in browse/download. Test a valid member, Admin/Root nonmember, and removed member using an old delegated token. Require live originating-human membership without changing unrelated mint permissions or treating arbitrary service subjects as human accounts. Independent Culvert service/browse credentials retain their own positive compatibility cases.

## Checkpoint boundary

The operator excluded global writer/creator changes. The canonical access contract and M0 matrix own restricted-resource checks, structured projection, bundle denial, principal adapters and exact new transport. Deployed identity evidence is retained; renewal of the observed expired integration credential and positive live acceptance are later prerequisites. Final independent review and ancestor commit remain.
