# MRS-01 consumer and state coverage matrix

Baseline: `e35d7a3e69497ddfd9709736af50107f56963584`. All runtime repair
coverage remains pending. **Confirmed defect** below means source tracing plus
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

## Current evidence and limits

`reproduce_parsers.py` ran through `wctl exec weppcloud python ...` on 2026-10-30.
`parser-baseline.jsonl` retains ten actual HTTP cases in both frameworks. It uses
probe endpoints invoking production parsers, **not** real business routes, and
performs no destructive/project/queue operations. Independent source reviews
identified the first-effect paths above. Route integration, persistence, upload,
worker and full-suite evidence remains **pending implementation**. No repair,
deployment or production behavior is claimed.
