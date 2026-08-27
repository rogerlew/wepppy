# WP12B Endpoint and View Surface Matrix

This matrix is the exact implementation boundary for amendment
`PC-22/WP12B-20260827-1`.

## Builder

- `wepppy/microservices/rq_engine/builder_routes.py`: describe, validate, and
  create routes consume the current graph and stable IDs.
- `wepppy/weppcloud/templates/config_builder.htm` and
  `wepppy/weppcloud/controllers_js/config_builder.js`: render and submit only
  server-described IDs and dependency changes.

## Climate

- `run_0_bp.py` climate catalog context, `controls/climate_pure.htm`, and
  `climate.js`: dataset, station-method, and spatial-method presentation.
- Flask `climate_bp.py`: `query/climate_catalog`, `set_climate_mode`,
  `set_climatestation_mode`, `set_climate_spatialmode`, and station query/set.
- rq-engine `climate_routes.py`: `build-climate` validates the selected dataset
  and methods before mutation/enqueue.
- rq-engine `schema_defaults_routes.py`: climate enum/default/discovery output
  is filtered by the stored graph.

## Landuse

- `run_0_bp.py`, `controls/landuse_pure.htm`, and `landuse.js`: method,
  landcover dataset, mapping, and current-state presentation.
- rq-engine `landuse_routes.py`: `set-landuse-mode`, `set-landuse-db`, and build
  validate stable IDs/runtime mappings before mutation/enqueue.
- rq-engine `schema_defaults_routes.py`: landuse discovery/default output is
  filtered by the stored graph.

## Soil

- `run_0_bp.py`, `controls/soil_pure.htm`, and `soil.js`: builder method and
  current fixed-config dataset presentation.
- Flask `soils_bp.py` `set_soil_mode`: maps the legacy numeric value to a stable
  builder ID and validates before mutation.
- rq-engine `schema_defaults_routes.py`: soil discovery/default output is
  filtered by stored builder capabilities.
- Runtime soil dataset mutation is excluded because no supported run-scoped
  endpoint changes the config-fixed soil provider; Builder selection remains in
  the Builder boundary.

## Watershed and WEPP

- Builder backend/representation/binary controls and builder routes validate
  allowed model tuples for creation.
- `run_0_bp.py` WEPP binary options, `controls/wepp_pure.htm` and its binary
  partial, `wepp.js`, and `wepp_run_payload.py` filter/validate `wepp_bin` from
  the stored run authority rather than the live provider alone.
- rq-engine `schema_defaults_routes.py` and orchestration discovery may report
  only stored backend/representation/binary availability.
- Runtime delineation backend and watershed representation mutation are
  excluded because they are immutable config choices with no supported
  run-scoped selection endpoint.

Workers may consume a validated persisted current value under the compatibility
carveout. They cannot broaden discovery or treat a worker-time provider listing
as run authority. Existing authentication, authorization, CSRF, CAP, and RQ
error contracts remain unchanged for every included endpoint.

## Security and Transport Matrix

- Browser Flask mutations retain session authentication, current run
  authorization, and CSRF validation before capability validation or mutation.
- Browser Flask read routes retain their existing access behavior. In
  particular, `query/climate_catalog` and `query/climatestation` remain
  undecorated GET surfaces; WP12B filters their payloads but does not add an
  authorization boundary.
- Browser rq-engine calls retain signed bearer scope and
  `authorize_run_access`. Private-run wrong-owner, expired, and
  insufficient-scope principals fail before capability disclosure. Existing
  user-token access to public runs remains allowed for both discovery and the
  already-authorized mutation/enqueue surfaces; WP12B does not redefine run
  ownership policy.
- The Config Builder page retains `login_required`; its browser token issuance
  retains authenticated same-origin POST. Builder describe/validate/create
  retain signed `rq:enqueue`; create additionally retains account ownership and
  idempotency. WP12B does not attribute a new CAP check to rq-engine routes.
- Capability validation occurs after authentication/authorization and before
  NoDb mutation or queue enqueue. Validation failures use the canonical
  field-addressable 4xx RQ error payload.

Direct negative tests cover unauthenticated, private-run wrong-owner,
cookie-without-CSRF/CAP where applicable, expired bearer, and insufficient
scope requests at each changed mutation/enqueue boundary and at discovery
boundaries whose existing contract requires those controls. Public-run access
gets positive regression coverage according to the existing Flask/rq-engine
boundary; WP12B adds no public-read or public-mutation denial. Existing route
methods and transport formats remain unchanged: stable catalog IDs remain
strings, while legacy numeric method payloads are mapped to stable IDs before
validation.

| Route/surface | Method/transport | Principal/control order |
| --- | --- | --- |
| `/config-builder/` | GET browser page | existing `login_required` page boundary |
| `/api/auth/rq-engine-token` | POST browser JSON | existing authenticated same-origin token-issuance boundary |
| `/rq-engine/api/project-config/builder` | GET bearer JSON | signed `rq:enqueue`, then registry disclosure |
| `/rq-engine/api/project-config/builder/validate` | POST bearer JSON | signed `rq:enqueue`, then graph validation |
| `/rq-engine/api/project-config/builder/create` | POST bearer JSON | signed `rq:enqueue`, graph/request validation, account ownership, idempotency reservation/replay decision, then write |
| `/runs/<runid>/<config>/query/climate_catalog[/]` | GET JSON | existing undecorated read behavior, then stored graph filtering |
| `/runs/<runid>/<config>/query/climatestation[/]` | GET JSON | existing undecorated read behavior, then current-state response |
| `/runs/<runid>/<config>/tasks/set_climate_mode/` | POST session form/JSON | auth, run authorization, CSRF, stable-ID validation, then NoDb mutation |
| `/runs/<runid>/<config>/tasks/set_climatestation_mode/` | POST session form/JSON | auth, run authorization, CSRF, runtime-to-stable validation, then NoDb mutation |
| `/runs/<runid>/<config>/tasks/set_climatestation/` | POST session form/JSON | auth, run authorization, CSRF, selected-station validation, then NoDb mutation |
| `/runs/<runid>/<config>/tasks/set_climate_spatialmode/` | POST session form/JSON | auth, run authorization, CSRF, runtime-to-stable validation, then NoDb mutation |
| `/rq-engine/api/runs/<runid>/<config>/build-climate` | POST bearer JSON | signed scope, run authorization, graph validation, mutation, then enqueue |
| `/rq-engine/api/runs/<runid>/<config>/set-landuse-mode` | POST bearer JSON | signed scope, run authorization, runtime-to-stable validation, then NoDb mutation |
| `/rq-engine/api/runs/<runid>/<config>/set-landuse-db` | POST bearer JSON | signed scope, run authorization, stable-ID mapping/validation, then NoDb mutation |
| `/rq-engine/api/runs/<runid>/<config>/build-landuse` | POST bearer JSON | signed scope, run authorization, current-state graph validation, then enqueue |
| `/runs/<runid>/<config>/tasks/set_soil_mode/` | POST session form/JSON | auth, run authorization, CSRF, runtime-to-stable validation, then NoDb mutation |
| `/rq-engine/api/runs/<runid>/<config>/prep-wepp-watershed` | POST bearer JSON | signed scope, run authorization, binary stable-ID validation, then mutation/enqueue |
| `/rq-engine/api/runs/<runid>/<config>/run-wepp` | POST bearer JSON | signed scope, run authorization, binary stable-ID validation, then mutation/enqueue |
| `/rq-engine/api/runs/<runid>/<config>/run-wepp-watershed` | POST bearer JSON | signed scope, run authorization, binary stable-ID validation, then mutation/enqueue |
| `/rq-engine/api/runs/<runid>/<config>/controllers/<controller>/schema` | GET bearer JSON | signed scope and run authorization before graph-filtered controller schema disclosure |
| `/rq-engine/api/runs/<runid>/<config>/controllers/<controller>/templates` | GET bearer JSON | signed scope and run authorization before graph-filtered template/default disclosure |
| `/rq-engine/api/runs/<runid>/<config>/endpoints?include_operation_docs=true` | GET bearer JSON | signed scope and run authorization before aggregated graph-filtered operation schema/default disclosure |
| `/rq-engine/api/runs/<runid>/<config>/endpoints/<operation_id>/schema` | GET bearer JSON | signed scope and run authorization before graph-filtered endpoint schema disclosure |
| `/rq-engine/api/runs/<runid>/<config>/endpoints/<operation_id>/defaults` | GET bearer JSON | signed scope and run authorization before graph-filtered defaults disclosure |
| `/rq-engine/api/runs/<runid>/<config>/pipeline` | GET bearer JSON | signed scope and run authorization before graph-filtered orchestration disclosure |
