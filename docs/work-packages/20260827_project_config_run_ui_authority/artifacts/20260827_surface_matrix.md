# WP12D Surface Matrix

This matrix closes the implementation boundary for ratified amendment
`PC-24/WP12D-20260827-3`. Authentication and run access remain before locale or
capability validation. Unlisted operations are unchanged.

## Authority Selection

| Run state | Locale source | Control authority | Registry drift |
| --- | --- | --- | --- |
| Flattened schema-v3 Builder project, exact exposed base and congruent manifest/config locale and selections | flattened project config | validated stored graph | no implicit effect; explicit acknowledged refresh may atomically adopt the current same-locale envelope while preserving selections |
| Flattened schema-v3 preset-source or incongruent project | flattened project config | validated stored graph | unchanged; capability refresh unavailable |
| Flattened schema-v2 project | flattened project config | validated stored graph | unchanged; capability refresh unavailable |
| Legacy shared-preset run | shared defaults plus named `.cfg` | live Builder graph only for one exact exposed base; otherwise existing locale catalog | affects five recognized base profiles by design |
| Legacy project-local config | project-local defaults plus local `.cfg` | same classification as shared legacy, with local precedence | affects five recognized base profiles by design |
| Flattened config with no capability section | frozen config/controller state | existing no-capability behavior; no new locale validation | unchanged; live Builder registry is not consulted |
| Schema-v1 project-owned snapshot | frozen snapshot/controller state | existing schema-v1 behavior; present valid v1 axes still restrict; no new locale validation | unchanged; live Builder registry is not consulted |
| Non-Builder base, overlay composition, or RHEM | effective `.cfg` | existing localized catalog behavior | Builder graph not consulted |
| Legacy project-local chain with locale absent | project-local defaults/config | non-persisting `["us"]` compatibility value, then live Continental-US graph | affects options by design |
| Legacy project-local chain with explicit locale | project-local defaults/config | explicit value; an old Canada `["earth"]` remains Global Earth | classified normally |
| Legacy locale query override | request/config token | none | reject before publication/load |
| Invalid locale composition in a non-flattened legacy run | effective `.cfg` | none | explicit `locale_authority_invalid` |
| Recognized legacy Builder profile with unavailable registry | effective `.cfg` | none | explicit `builder_registry_error` |

## Project Capability Refresh

| State | Preview | Acknowledgment | Apply result |
| --- | --- | --- | --- |
| No graph difference; missing attributes only | existing complete additive preview | not required | merge-only attribute amendment |
| Same-locale graph difference only | complete old/new axes, relations, per-dataset method defaults, revisions, canonical support-state delta, and preserved project selections | exact unchecked warning becomes required | atomic selection-preserving envelope replacement plus manifest discontinuity record |
| Graph and missing-attribute difference | one combined complete preview with preserved project selections | exact acknowledgment required | one atomic selection-preserving envelope replacement and attribute addition transaction |
| Existing project selection is removed or incompatible | unavailable with diagnostic stable IDs | cannot acknowledge | `409 config_update_unavailable`; no substitution, reservation, mutation, or enqueue |
| Locale differs or registry/graph is invalid | unavailable with diagnostic reason | cannot acknowledge | no reservation, mutation, or enqueue |
| Preview/config/manifest/warning revision changes | stale | prior acknowledgment invalid | `409 stale_config_preview` |

Builder creation, legacy live authority, capability-refresh preview, and apply
must call the same public locale-to-graph resolver. Stored authority remains
unchanged until successful apply and page reload.

Refresh adopts current axes, relationships, provider/source revisions, and per-
dataset method defaults while preserving every stored `capability_defaults` value,
`nodb.mods`, and linked `climate.cligen_db`. All must validate against the new
envelope. Current Builder defaults never replace those project selections.
The stored runtime-token list, graph/default locale, manifest Builder locale,
capability profile, and manifest/config selections must be exactly congruent.

Pre-reservation rejection leaves no queue or file side effect. Once apply is
accepted, the job remains observable. Recovery keeps the prior pair if config
replacement did not occur and rolls the complete result pair forward if it did;
the terminal job/UI state reports the recovered pair.

## Navigation Non-Change

| Surface | Required behavior |
| --- | --- |
| Both links in `config_builder.htm` | remain plain `/interfaces/` before and after description or locale changes |
| Flask `GET /interfaces/` | no locale query grammar or filtering; preserve current role-visible curated page |
| Existing create forms | submit only the existing config token and current transport/auth fields |
| Config registry | no locale metadata; preserve visibility/maturity/role/backend ownership |

The Config Builder's own create payload continues to submit its selected
Builder locale ID. The server validates that selection and writes the
corresponding runtime token into the flattened config; this is distinct from
the unchanged established-Interface forms above.

## Run Control Presentation and Submission

| Domain | Presentation consumer | Resolved authority | Submission/discovery surfaces | Exact-current behavior |
| --- | --- | --- | --- | --- |
| Landuse dataset | `run_0_bp.py` -> `landuse_pure.htm` -> `landuse.js` field `landuse_db` | resolved graph `landuse_datasets`; otherwise existing localized catalog | rq-engine `POST set-landuse-db`; rq-engine `POST build-landuse` | all authorized options plus exactly one disabled outside-axis current dataset; ordinary exact-current build allowed |
| Landuse method | same, field `landuse_mode` | selected dataset adjacency intersected with representation adjacency | rq-engine `POST set-landuse-mode`; rq-engine `POST build-landuse` | exact current state remains observable/buildable until authorized recovery |
| Soil builder | `run_0_bp.py` -> `soil_pure.htm` -> `soil.js` field `soil_mode` | selected graph soil dataset adjacency | Flask `POST tasks/set_soil_mode/`; rq-engine `POST build-soils` | exact current mode remains observable/buildable; different unsupported mode fails |
| Climate dataset | `run_0_bp.py` -> `climate_pure.htm` -> `climate.js` fields `climate_catalog_id`/`climate_dataset_choice` | resolved graph `climate_datasets`; otherwise existing localized catalog | Flask `GET query/climate_catalog`; Flask `POST tasks/set_climate_mode/`; rq-engine `POST build-climate` | all authorized options plus exactly one disabled outside-axis current dataset; exact-current build allowed |
| Climate station method | same, field `climatestation_mode` | selected dataset's station-method adjacency | Flask `POST tasks/set_climatestation_mode/`; rq-engine `POST build-climate` | exact current method remains observable/buildable |
| Climate spatial method | same, field `climate_spatialmode` | selected dataset's spatial-method adjacency | Flask `POST tasks/set_climate_spatialmode/`; rq-engine `POST build-climate` | exact current method remains observable/buildable |

RQ discovery in `schema_defaults_routes.py` must use the same resolved authority
for run endpoint schemas/defaults/errors, list-endpoint operation documents, and
capability snapshots. `orchestration_read_routes.py` must use it for pipeline
and readiness. Discovery cannot advertise a value that mutation rejects.

For every row, a different unsupported stable or runtime value fails before
NoDb mutation, timestamp removal, file write, or enqueue. The climate station
identifier, advanced climate toggles, landuse edit/upload operations, soil
`ksflag`, disturbed soil version, reports, and job lifecycle are excluded.

## Stored-State and Locale Precedence

Classify every flattened project before considering non-flattened legacy mode.
Validate a complete stored schema-v2/v3 graph as stored authority. Preserve
flattened no-capability/schema-v1 compatibility without new locale validation
or live-registry consultation. Only for non-flattened legacy mode, resolve
effective `.cfg` locale rather than persisted `Ron._locales` and select a live
Builder graph for an exact one-token exposed base. Never use a shared preset or
live graph for a flattened project.

Within a graph, a current authorized dataset takes precedence over its default;
the default applies only when current state is unset. An outside-authority
current dataset does not suppress authorized recovery choices. No state is
silently substituted or rewritten.

## Error Matrix

| Condition | HTML run page | Flask JSON | rq-engine JSON |
| --- | --- | --- | --- |
| Invalid locale composition in non-flattened legacy mode | 409 diagnostic page, `locale_authority_invalid`, error ID | 409 canonical envelope, diagnostic `details`, `error_id` | 409 canonical RQ envelope, diagnostic `details`, `error_id` |
| Live Builder registry unavailable | 503 diagnostic page, `builder_registry_error`, error ID, `Retry-After: 5` | 503 canonical envelope plus `Retry-After: 5` | 503 canonical RQ envelope plus `Retry-After: 5` |
| Locale-bearing creation/query override | no run page; reject before publication | not applicable | 400 `project_config_validation_failed` canonical envelope |
| Capability refresh acknowledgment missing, false, or wrong revision | not applicable | not applicable | 400 `capability_refresh_acknowledgment_required`; no reservation or enqueue |
| Capability refresh preview/config/manifest/graph drift | not applicable | not applicable | 409 `stale_config_preview`; no mutation or enqueue |
| Preserved project selection removed or incompatible in refreshed envelope | not applicable | not applicable | 409 `config_update_unavailable` with diagnostic stable IDs; no substitution, reservation, mutation, or enqueue |
| Manifest/config locale, capability profile, or selection mismatch; preset source | not applicable | not applicable | 409 `config_update_unavailable` with diagnostics before reservation or mutation |

Authentication, authorization, and run ownership checks retain precedence. The
generic RQ response envelope is unchanged.
