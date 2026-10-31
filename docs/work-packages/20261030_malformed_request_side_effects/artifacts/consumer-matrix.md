# MRS-01 consumer and state coverage matrix

Baseline: `e35d7a3e69497ddfd9709736af50107f56963584`. The discovery tables below
retain baseline classifications; final dispositions follow at the end. **Confirmed defect** below means source tracing plus
the reproduced shared fallback, not a claim that each route was executed.
No consumer is marked verified unaffected merely from static inspection.

## Search boundary and reproducibility

Search `wepppy/microservices/rq_engine`, `wepppy/weppcloud/routes`, their helper,
worker/controller consumers, `controllers_js`, templates, and matching tests.
Exclude bulky run fixtures, generated JS mirrors, third-party code, read-only
polling/lookups and scientific algorithm redesign. Include enabled test-support
creation endpoints because they mutate projects. Preserve all existing auth policy.
The [source inventory](source-inventory.json) lists 429 functions with route
decorators or parsing calls and line numbers, including direct JSON/form parsers.
It is a discovery index, not proof of exhaustive runtime coverage. Follow wrapper
calls and decorators before resolving each record. Search expressions include
`parse_request_payload`, `_normalize_payload_value`, `_normalise_payload_value`,
`get_json`, `request.json/form/body`, `input_payload`, `request_options`,
`reject_unsupported`, `bool(` and optional boolean/numeric coercers.

## Framework and caller profiles

RQ paths below have `/api` prefix and normally `/runs/{runid}/{config}/`.
Flask run paths have `/runs/<runid>/<config>/`; concrete decorator strings and
methods are retained in the source inventory. Shared-parser consumers accept JSON
and forms. `http.js:429–449` supplies JSON/form Content-Type and lets the browser
supply multipart boundaries. `forms.js:197–214` emits checkbox booleans and real
multiselect arrays. RHEM `rhem.js:281–287` submits an object; its form has no stage
flags, so `{}` is an intentional default. No hidden false/checked true same-name
pair was evidenced in scoped RHEM/WEPP/landuse/soil controls.

Transport decisions are in canonical `request-payload-contract.md#transport-acceptance`:
zero bytes and `{}` are distinct from whitespace/null/scalars; empty URL form is
valid; missing/empty Content-Type with nonempty data uses strict JSON compatibility;
unsupported nonempty media fails. These are parser-level rules; required fields
still reject an empty payload. Domain adapters retain explicit list/raw/upload
shapes. The canonical scalar table records null/blank exceptions and aliases.

## RQ consumer groups

| Group / source | Methods and paths | Parser chain / flags / defaults | First business effect; catches | Contract / disposition / evidence target |
| --- | --- | --- | --- | --- |
| RHEM | POST run-rhem | webhook unsupported pre-parser → shared parser; clean/prep/run + hillslope aliases; omitted/null default enabled, blank false | Timestamp clear → enqueue → worker cleanup; route broad catch | Shared contract; **confirmed defect**. Actual HTTP invalid clean, temporary RHEM output sentinels, defaults and false worker boundary |
| WEPP / bootstrap | POST run-wepp, run-wepp-watershed, prep-wepp-watershed, run-wepp-npprep, run-wepp-watershed-no-prep | Shared parser and webhook options; WEPP flags, delete_after_interchange, supplied numeric overrides | Proposed controller saves, timestamps, receipt/hint/reservation, enqueue; broad catches and typed domain errors | WAM-01 + shared; **confirmed defect**. Retain tests/microservices/test_wepp_admission_persistence.py and both route suites, real reload/prepared files |
| Climate, debris, exports, models | POST build-climate, run-debris-flow, post-dss-export-rq, run-swat, acquire-openet-ts, acquire-rap-ts, acquire-polaris, build-rusle | Shared parser; flag/null exceptions in canonical table; RAP raw adapter; DSS invalid mode/order fallback | Controller parse/save or timestamp/enqueue; route broad catches | Shared plus current domain specs; **confirmed defect** for fallback/default and DSS malformed numeric. Route rejection/state tests |
| Landuse / soils build | POST build-landuse, build-soils | input_payload bounded multipart or shared parser; burn aliases/cache clear; mode aliases | Eager controller hydration; accept_input promotion precedes some later mapping/sol_ver validation; broad + SingleInputError catches | Single-user-defined inputs + landuse modification + shared; **confirmed defect**. Real multipart, temp closure, no promotion/deletion/settings save; valid reuse/upload |
| Treatments / Ash | POST build-treatments, run-ash | Shared or indirect payload parsing; required mapping/upload | Treatments mode written before required mapping/file; Ash parse_inputs before mode2 file validation | Shared; **confirmed early-write defect**. Actual required-file/mapping rejection with persisted reload |
| Watershed | POST set-outlet, fetch-dem-and-build-channels, build-subcatchments-and-abstract-watershed | Shared parser; declared optional booleans; silent bad clip/MOFE numeric omission | Parse inputs/save/timestamps/enqueue; broad catches | Shared; **confirmed numeric/default defect**. Every route integration; required-field endpoints still unresolved until exercised |
| Omni | POST run-omni, run-omni-contrasts, dry-run wrappers; delete-omni-contrasts | Shared + raw list adapter; optional output flags; delete uses webhook guard | `_preflight_omni_roots` can recover mixed NoDir roots before parse; mutations/enqueue | Omni thinning/freshness + shared; **confirmed early-recovery/default defect**. Preserve top-level scenario lists and nested data |
| Geneva | Four POST operations in geneva_routes | Shared parser, force_rebuild/rebuild strict supplied bool | Controller/config work/enqueue; broad handlers | Shared; **confirmed shared fallback exposure**, individual required-field paths unresolved. Test explicit null rejection and no initialization |
| Required-field mutations | Landuse mode/db/coverage/mapping/user-defined/modify; agfields schema/build/run/clear; SWAT print/meta; restore/delete archive; run-sync; project create | Shared/wrappers; supported transports and required fields retained; fork strict JSON flag exception | Controller mutations, file writes/delete or enqueue; wrappers vary | Project-owned config, fork, batch and shared; **unresolved per route** except confirmed permissive flag consumers. Empty payload may already fail; test before disposition |
| Body-optional indirect consumers | POST roads prepare/run, export ermit/features, batch run/delete, hello-world, culvert retry/finalize, run-swat-noprep | reject_unsupported only, which swallows malformed JSON or infers absence from Content-Length | Input prep, delete, timestamp or enqueue | Owning domain + shared; **confirmed reachable default defect**. Every exposed path needs rejection evidence; do not alter unrelated Roads behavior/spec |
| Direct fallback | migrate-run; bootstrap checkout; landuse-and-soils | `_safe_json`/direct JSON fallback; migration create_archive flag | Migration reservation/enqueue or checkout mutation; landuse-and-soils requires extent | Shared; **confirmed fallback mechanism**; required-extent path unresolved until actual rejection evidence |
| Direct strict structured APIs | Builder validate/create, project-config update-apply, landuse-map save, agfields rotation-mapping, postfire | Existing JSON schemas / custom json_body | Existing validators then writes; audit wrappers and earlier initialization | Project-owned config/creation policy and domain schemas; **unresolved**, preserve stricter native bool and required fields |
| Direct upload APIs | climate, disturbed, cover transform, huc-fire, batch geojson/SBS, agfields boundaries/plant database, DEM, culvert batch | request.form or specialized bounded upload; callback on culvert | Temporary spooling vs project source promotion/extraction | Existing upload/callback contracts + shared; **unresolved**, test malformed termination, size/duplicate files and closure before labeling unaffected |

## Flask consumer groups

| Group / source | Methods and paths | Parser chain / valid semantics | First business effect; catches | Disposition / evidence target |
| --- | --- | --- | --- | --- |
| project_bp | POST tasks/setname, setscenario, set_public, set_ttl_disabled, set_readonly, mod-state setter; add/remove user | Shared parser; blank name → Untitled, blank scenario retained; explicit state required | Ron hydration before name parse; save/access-state mutation; local add/remove catches + auth decorator | **Confirmed fallback/truthiness defect**. Real blueprint 400 and NoDb/cache follow-up; preserve role/CSRF |
| disturbed_bp | POST set fire-date; CSV editing | Shared parser for date; explicit fire_date:null clears; separate JSON list rows | Disturbed hydration then date clear; local broad catch | **Confirmed date defect**; CSV **unresolved static candidate unaffected** (already rejects malformed before writer), preserve list input |
| path_ce_bp | POST configuration/run | Shared parser; legitimate treatment lists | `_ensure_controller` before parse; execute/save | **Confirmed early-init/default defect**. Never-used optional controller must stay absent on malformed request, valid request initializes |
| roads_bp | POST config/set_params | Shared parser and domain validators | Timestamp clear on empty parsed object | **Confirmed fallback defect**. Test readback/timestamp; no changes to unrelated Roads parameterization |
| geneva_bp | POST config, prepare HRUs, frequency panel, run batch and related helper consumers | `_json_object_payload` direct silent fallback; CSV list editor separate | Controller/enqueue; enabled persisted before config validation | **Confirmed default/partial-save defect**. Validate config before enabled save; legitimate CSV lists preserved |
| watershed_bp | POST tasks/set_terrain_processor_config, run_terrain_processor | Direct get_json bypass + shared fallback; nested config/outlet arrays | Config save and execution | **Confirmed fallback defect**. Validate both nested and flat supported forms |
| interchange_bp / recorder_bp / agent.py | POST interchange migration, recorder/promote, agent/chat | Direct silent JSON `or {}`; recorder events list distinct | Queue migration, draft promotion, session mint/spawn | **Confirmed default defect**. Actual route tests; external queue/spawn controlled, malformed request never calls it |
| bootstrap.py | POST checkout/disable | request.json or {}; disable bool truthiness | Checkout/disable state | **Confirmed null/falsy/flag defect**. Preserve auth and deliberate defaults, reject nonobject JSON |
| soils / climate / wepp / watar | POST ksflag, routine flags, climate adjust/wind toggles, ash wind transport | Shared parser or direct request.json; some boolean_fields missing | Controller save | **Confirmed flag defect**. Explicit false/native+legacy tokens work, containers/text fail before state writes |
| unitizer / omni / observed / rangeland / treatments / batch_runner | Shared parser consumers listed in source inventory | Multivalue forms, nested collections; observed raw CSV trim disabled | Controller or user preference saves, deletes, job work; local and auth broad catches | **Unresolved per route**, audit before closure; shared-parser test alone insufficient |
| Other direct APIs | README save/preview, admin usermod, developer mode, CAPTCHA, command-bar loglevel, user prefs, batch creation | Existing required field/type checks | Varies; some read-only paths excluded | **Unresolved static candidate unaffected**, actual request evidence required |
| Test support | POST /tests/api/create-run | Silent JSON defaults when enabled | New project creation | **Confirmed fallback defect**, included; preserve enablement/auth |
| WATAR contaminant report | POST form submission | Direct form → Ash.parse_cc_inputs | Persist invalid numeric values | **Unresolved adjacent numeric boundary**, classify existing intended valid values before repair |

## State and evidence matrix

| Runtime state | Required outcome | Planned direct evidence |
| --- | --- | --- |
| Absent/never-used optional controller/source | Invalid request cannot initialize; valid request still creates or gives existing required-upload error | PATH CE/Geneva and input-mode fixtures |
| Present-empty configuration/form/default request | Existing intentional defaults and no-op/saves preserved | RHEM {}, empty form, batch/base, zero-byte actual HTTP |
| Populated project/output | Invalid input leaves saved and cached values, sources and output sentinels intact | Real NoDb reload + same-process valid follow-up; RHEM clean sentinel |
| Supported legacy flags/forms/arrays/state | Existing tokens, null/blank policies, aliases and lists work | Framework and route parameterization, no blanket recursive flag coercion |
| Active/busy/replay | WAM-01 conflicts and callback receipt identity remain unchanged | Existing contention/replay suites; inspect prepared input semantics |
| Malformed transport/scalar/domain fields | JSON 400 before first business side effect | Every confirmed route through real exception wrappers |
| Multipart failure/disconnect/cancel | Temporary resources closed; no promotion | Actual bounded parser and controlled stream faults |
| Later valid computation/storage failure | Existing explicit failure/diagnostic behavior; no invented transaction | Existing domain regression suites |

## Baseline evidence (historical)

`reproduce_parsers.py` ran through `wctl exec weppcloud python ...` on 2026-10-30.
`parser-baseline.jsonl` retains ten actual HTTP cases in both frameworks. It uses
probe endpoints invoking production parsers, **not** real business routes, and
performs no destructive/project/queue operations. Independent source reviews
identified the first-effect paths above. Route integration, persistence, upload,
worker and full-suite evidence remains **pending implementation**. No repair,
deployment or production behavior is claimed.

## Final implementation and evidence dispositions

The tables above describe pre-repair findings, not outstanding implementation
work. Exact route paths for the RQ matrix are in [rq-route-coverage.json](rq-route-coverage.json);
Flask paths are retained in `validation/flask-matrix.log`. Tests exercise registered
framework routes and exception wrappers, with controlled auth/read-only and queue
boundaries. These matrix tests prove transport rejection; representative companion
tests prove actual persistence/filesystem noninterference and valid follow-up.

| Discovery group | Final disposition / executable evidence |
| --- | --- |
| RQ shared/default consumers, including RHEM, WEPP, bootstrap, climate, models, watershed, Omni, Geneva, required-field mutations, batch, culvert, Roads and uploads | Repaired; `test_malformed_route_matrix.py` enumerates registered POST routes. Required fields and native strict-schema error codes remain distinct. |
| WAM-01 five admission paths | Preserved; `test_wepp_admission_persistence.py`: 63 pass with disposable Redis, real reload/prepared-input/replay/busy/no-prep assertions. |
| RHEM clean/default execution | Repaired; `test_rq_engine_rhem_routes.py` invalid clean tests use real clean/output sentinels and controlled worker enqueue; valid omitted/null/default/false behavior retained. |
| Landuse/soil input promotion | Repaired; `test_malformed_input_persistence.py`: eight actual multipart/real-controller rejection and valid-follow-up cases; mapping/numeric validation precedes promotion. |
| Treatments/Ash/uploads | Repaired; route tests plus `test_treatments_upload_persistence.py`, upload helpers and disturbed/HUC/batch suites. Real raster/VRT/GeoJSON tests protect old source bytes, relative dependencies, and final metadata paths. |
| Flask project/default/flags, Roads, climate, soils, WEPP, WATAR, unitizer, observed, rangeland, treatments, interchange, Omni | Repaired; registered-route matrix across corresponding blueprint suites; real Ron reload/cache follow-up in `test_project_bp.py`. |
| Optional PATH/Geneva and WATAR numeric fields | Repaired; `test_optional_payload_persistence.py` real absent/populated NoDb tests, byte/reload assertions and valid follow-up; domain suites preserve panel lists and enabled ordering. |
| Flask terrain | Repaired; `test_watershed_terrain_processor_api.py` nested/flat forms, flags and singleton arrays. |
| Agent TTL and batch task directives | Repaired; `test_agent_payload_routes.py` controls token/spawn/publish boundaries; `test_batch_runner_endpoints.py` real BatchRunner persistence/cache rejection and valid follow-up. |
| Recorder, bootstrap, enabled test creation | Repaired; actual registered-route malformed tests in their blueprint suites; recorder form/event and CSRF compatibility tests retained. |
| Postfire specialized API | Verified unaffected for the exercised malformed/schema class: `test_rq_engine_postfire_debris_flow.py::test_invalid_payloads_before_mutation` and `test_model_payload_rejected_before_mutation` cover arrays, duplicates, non-finite values, limits and invalid model selections with absent file/NoDb assertions; included in the passing 4,017-test route run. |
| CSV row editors and strict domain schemas | Preserve explicit list/native schema adapters; domain tests cover rejection before writers. No universal object restriction imposed on legitimate rows/scenario arrays. |
| Cover-transform content | Existing route does not parse CSV content; no confirmed late content-rejection failure. Extension/size/transport boundaries retained; no new CSV rules introduced. |
| Session token and operator token | Repaired actual-body detection without Content-Length; session suite 59 passes and operator-token suite covers stream without length. Specialized token schemas/auth remain unchanged. |
| RQ jobinfo batch | Read-only polling fallback; no mutation/default execution. Excluded after tracing `_safe_json` to `jobinfo_batch`. |
| README, admin role edits, CAPTCHA and command-bar loglevel | Source inspection finds explicit object/required-token/required-level guards before writes. Not classified as confirmed invalid-to-default defects; no blanket “runtime unaffected” claim. |
| User preferences and batch creation forms | Source-guarded required fields: preference choices must belong to both existing enums; batch name/config validate before `_create_batch_project`. Empty parse results do not reach saves/creation. No confirmed default-execution defect; no claim of complete transport conformance for these specialized forms. |
| GL dashboard response JSON | Parses an internal response, not a mutation request; excluded from this request-parser failure class. |
| Read-only views, GETs, path/query-only commands, third-party and scientific validators | Outside this malformed-body-to-business-effect class. Router-class edits on read-only RQ modules only install common typed error translation. |

The source index includes helpers/read-only routes and is deliberately broader than
the confirmed repair set. This is not certification of every numeric/scientific
constraint or arbitrary later computation failure. Unexercised direct APIs remain
unresolved candidates, not verified-unaffected claims; their presence in the index
alone is not evidence of a default-execution defect. Production rollout/observation
is outside this local execution. See [validation](validation.md) for exact gates.
