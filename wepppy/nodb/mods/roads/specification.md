# Roads NoDb Inslope Integration Specification

Status: Implemented (Phase 2 Step-2)  
Last Updated: 2026-03-27  
Scope: `Inslope_bd` and `Inslope_rd` road designs for the first WEPPcloud Roads NoDb integration.
Canonical cross-route `output_scope` contract: `docs/schemas/output-scope-contract.md`.

## Goal

Implement a repeatable pipeline that:

1. Converts road linework into monotonic segments.
2. Preserves original feature properties and adds segment metadata.
3. Tags each segment with channel and receiving-hillslope Topaz IDs near its low point.
4. Runs road-segment WEPP hillslopes and injects their effects into watershed routing via pass-file combination.

This phase targets only inslope bare-ditch and inslope rocked-ditch designs.

## WEPPcloud User Story (Phase 1)

1. User runs WEPP normally (existing WEPPcloud workflow).
2. User enables `Roads` from the `Mods` dropdown; this instantiates a Roads controller for the run.
3. User uploads a roads GeoJSON with road segment paths.
4. User reviews/edits Roads run settings (surface/traffic defaults, soil texture, rock fragment percent, climate years, optional overrides).
5. User clicks `Run WEPPcloud Roads`.
6. System executes Roads pipeline:
   - monotonic segmentation and lowpoint attribution,
   - segment-to-hillslope/channel mapping,
   - single-OFE road segment WEPP runs,
   - pass-file combination against mapped hillslopes,
   - watershed rerun with combined pass files.
7. User sees Roads run status and Roads-vs-baseline diagnostics/reports.

## Roads NoDb Controller Integration (Phase 1 In Scope)

Roads is in-scope as a first-class NoDb controller for this phase.

Implementation targets:

- Controller: `wepppy/nodb/mods/roads/roads.py`
- Module package: `wepppy/nodb/mods/roads/`
- WEPPcloud routes: `wepppy/weppcloud/routes/nodb_api/roads_bp.py`
- UI controls/report templates:
  - `wepppy/weppcloud/templates/controls/roads_pure.htm`
  - `wepppy/weppcloud/templates/reports/roads/*.htm`

Controller type:

- `class Roads(NoDbBase)` with run-scoped persisted state (`roads.nodb`).

Run precondition:

- Baseline WEPP hillslope and watershed outputs exist for the run (`wepp/output/H*.pass.dat`, `wepp/runs/pw0.run`).

Activation and backend guard:

- `Roads` is enabled/disabled through the canonical project mod endpoint (`/tasks/set_mod`).
- Roads requires WBT delineation backend (`watershed.delineation_backend_is_wbt == True`).
- Attempting to enable Roads on non-WBT runs must return an explicit error (same pattern as existing backend-gated modules).
- Roads execution and preflight completion are WEPP-dependent; no Roads run is considered complete before WEPP completion.

## Roads Controller State Contract

Minimum persisted state fields:

- `enabled`: bool
- `uploaded_geojson_relpath`: str | null
- `uploaded_geojson_sha256`: str | null
- `discovered_attribute_catalog`: dict | null (top-level feature-property field catalog for current upload)
- `roads_params`: dict
- `last_prepare_summary`: dict | null
- `last_run_summary`: dict | null
- `status`: one of `idle|prepared|running|completed|failed`
- `errors`: list[str]
- `timestamps`: dict

Roads artifacts (run-relative):

- `wepp/roads/segments/*`
- `wepp/roads/runs/*`
- `wepp/roads/output/*`
- `wepp/roads/output/interchange/*` (regenerated report resources)

## Roads(NoDbBase) Implementation Blueprint

Implemented class contract (`wepppy/nodb/mods/roads/roads.py`):

- `class Roads(NoDbBase)`
- `filename = "roads.nodb"`
- Persist all state in a run-local controller file (`<wd>/roads.nodb`) using standard NoDb locking semantics.

Controller responsibilities:

- maintain roads enablement/config state for the run.
- validate and stage uploaded roads GeoJSON.
- execute deterministic segment preparation (`monotonic_segments` + lowpoint/channel/hillslope attribution).
- orchestrate segment WEPP runs and watershed-injection rerun.
- expose status and summarized diagnostics for UI/report endpoints.

Suggested public controller surface (phase 1):

- `set_enabled(enabled: bool) -> None`
- `set_params(payload: dict) -> dict` (normalized params)
- `set_uploaded_geojson(src_path: str) -> dict` (saved path + checksum metadata)
- `prepare_segments() -> dict` (writes `wepp/roads/segments/*`, updates `last_prepare_summary`)
- `run_roads_wepp() -> dict` (writes `wepp/roads/{runs,output}/*`, updates `last_run_summary`)
- `query_status() -> dict`
- `query_summary() -> dict`

State machine contract:

- `idle` -> `prepared` -> `running` -> `completed`
- any execution error transitions to `failed` and appends diagnostic messages in `errors`.
- successful parameter or upload changes after `prepared/completed` clear stale run summaries and return to `idle`.

Collaborators and dependencies:

- Segment utility: `wepppy/nodb/mods/roads/monotonic_segments.py`
- WEPP run context: `wepppy.nodb.core.wepp.Wepp`
- Topaz translator: `wepppy.wepp.out.top_summary.WeppTopTranslator`
- Watershed rerun builder: `wepp_runner.wepp_runner.make_watershed_omni_contrasts_run`
- RQ workers (new): `wepppy/rq/roads_rq.py` with separate prepare/run entrypoints.

## UI and Registration Touchpoints

Roads integration must include all of the following registration updates:

- Add Roads to project mod display map:
  - `wepppy/weppcloud/routes/nodb_api/project_bp.py` (`MOD_DISPLAY_NAMES`).
- Enforce Roads WBT backend guard in project mod toggle path:
  - `wepppy/weppcloud/routes/nodb_api/project_bp.py` (`set_project_mod_state`).
- Add Roads to header `Mods` dropdown options:
  - `wepppy/weppcloud/templates/header/_run_header_fixed.htm` (`header_mod_options`).
- Add Roads control metadata in run-0 mod registry, ordered immediately after Debris Flow:
  - `wepppy/weppcloud/routes/run_0/run_0_bp.py` (`MOD_UI_DEFINITIONS`).
- Add Roads nav item and content section in run page template, ordered after Debris Flow:
  - `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`.
- Register Roads TOC/preflight emoji mapping:
  - `wepppy/weppcloud/routes/run_0/run_0_bp.py` (`TOC_TASK_ANCHOR_TO_TASK`, anchor `#roads`).
- Register Roads preflight checklist selector mapping:
  - `wepppy/weppcloud/static/js/preflight.js` (`getSelectorForKey`).
- Register Roads blueprint exports/imports:
  - `wepppy/weppcloud/routes/nodb_api/__init__.py`
  - `wepppy/weppcloud/routes/__init__.py`

## Roads API/UI Workflow Contract

Expected route family (patterned after existing NoDb `api/tasks/query/report` routes):

- `POST /runs/<runid>/<config>/tasks/set_mod` with payload `{"mod":"roads","enabled":true|false}` (canonical mod enable path)
- `POST /runs/<runid>/<config>/tasks/roads/upload_geojson`
- `POST /runs/<runid>/<config>/tasks/roads/set_params`
- `GET /runs/<runid>/<config>/api/roads/config`
- `POST /runs/<runid>/<config>/api/roads/config`
- `GET /runs/<runid>/<config>/api/roads/status`
- `GET /runs/<runid>/<config>/api/roads/results`
- `POST /runs/<runid>/<config>/tasks/roads/prepare_segments`
- `POST /runs/<runid>/<config>/tasks/roads/run`
- `GET /runs/<runid>/<config>/query/roads`
- `GET /runs/<runid>/<config>/query/roads/summary`
- `GET /runs/<runid>/<config>/report/roads/summary`
- `GET /runs/<runid>/<config>/report/roads/results`

UI control requirement:

- Add a `Run WEPPcloud Roads` action in Roads controls once baseline WEPP exists and a roads GeoJSON is uploaded.
- Roads control appears in the run page immediately after Debris Flow in both TOC and content stack.

Execution mode:

- Queue-backed task execution (RQ) for `prepare_segments` and `run` to avoid request blocking.
- RQ payload contract:
  - `run_roads_prepare_rq(runid: str)` executes only prepare stage.
  - `run_roads_rq(runid: str)` executes full run stage from latest prepared segments.
  - both jobs persist status transitions in `roads.nodb`.

## Roads Report Resource Regeneration Contract (Implemented)

At the end of `run_roads_wepp()`, Roads executes `_regenerate_roads_report_resources()` and stores the result under `last_run_summary["roads_report_resources"]`.

Behavioral contract:

- Regeneration is roads-scoped only:
  - writes under `wepp/roads/output/interchange/*`,
  - never mutates baseline `wepp/output/*`.
- Regeneration refreshes query-engine catalog registration for roads outputs.
- Regeneration fails explicitly when required resources are missing (no silent fallback wrappers).
- Output scope is explicit and fixed in this payload:
  - `output_scope = "roads"`.

Persisted `roads_report_resources` fields:

- `status` (`"ready"` on success)
- `output_scope` (`"roads"`)
- `roads_output_relpath`
- `interchange_relpath`
- `required_relpaths`
- `missing_relpaths`
- `roads_segment_loss_summary_relpath` (`null` for single-storm runs)
- `generated_at`

Required resource sets:

- Non-single-storm:
  - `H.pass.parquet`
  - `H.wat.parquet`
  - `loss_pw0.out.parquet`
  - `loss_pw0.hill.parquet`
  - `loss_pw0.chn.parquet`
  - `ebe_pw0.parquet`
  - `totalwatsed3.parquet`
  - `README.md`
  - `roads_segment_loss_summary.parquet`
  - optional `chnwb.parquet` only when source `chnwb.txt(.gz)` exists.
- Single-storm:
  - `H.pass.parquet`
  - `ebe_pw0.parquet`
  - `README.md`

Run Results link gating:

- `report/roads/results` shows only report links whose required roads resources are present.
- Non-single-storm-only links (for example return periods, yearly/avg water balance, streamflow, watershed loss summary) are hidden when required resources are absent.

Road segment loss summary artifact:

- File: `wepp/roads/output/interchange/roads_segment_loss_summary.parquet`.
- Built from `roads.segment.pass.manifest.json` + `loss_pw0.hill.parquet`.
- Join precedence:
  - first `target_hillslope_wepp_id`,
  - fallback `segment_run_id`.
- Includes diagnostics columns:
  - `loss_match_key`
  - `loss_row_missing`.
- No on-disk CSV is written; CSV is served on demand via download conversion (`?as_csv=1`).

## Roads API Payload and Validation Contract

`upload_geojson` request contract:

- Accept multipart upload (`file`) with `.geojson` extension.
- Require GeoJSON `FeatureCollection` with `LineString`/`MultiLineString` geometries.
- Reject non-line geometries and invalid JSON with explicit error responses.

`upload_geojson` validation rules:

- max upload size (phase-1 default): `50 MB`.
- reject empty feature sets.
- require readable CRS context (`input_crs` param + optional GeoJSON `crs.properties.name`).
- prepare stage uses configured `input_crs` for coordinate transforms during segmentation/attribution.
- persist source checksum (`sha256`) and normalized ingest summary.

`set_params` request contract:

- Accept JSON object only.
- validate enums/ranges for:
  - `soil_texture_default`, `surface_default`, `traffic_default`,
  - `rfg_pct_default`, `road_width_m_default`,
  - optional `attribute_field_map` values:
    - `design`
    - `surface`
    - `traffic`
  - attribute discovery limit params:
    - `attribute_discovery_profile_feature_limit`
    - `attribute_discovery_value_preview_limit`
    - `attribute_discovery_value_max_chars`.

### Attribute Discovery and Mapping Contract

- Upload-time discovery scans top-level `feature.properties` keys and persists:
  - `field_names`
  - `field_profiles` (`non_empty_count`, `distinct_non_empty_count`, `sample_values`)
  - profile scope metadata (`field_count`, `total_feature_count`, `profiled_feature_count`, `profile_truncated`)
  - discovery-limit metadata (`discovery_limits`).
- On each upload:
  - stale mapping selections are reset,
  - best-effort remap discovery is attempted by exact field-name match.
- Mapping is used in both prepare and run stages:
  - prepare-stage design eligibility respects configured `attribute_field_map.design`,
  - run-stage design/surface/traffic resolution respects configured mapping fields.
- Surface and traffic fallback values are explicit params:
  - `surface_default` must resolve to `gravel` or `paved`,
  - `traffic_default` must resolve to `high`, `low`, or `none`.
- Surface and traffic resolution order depends on mapping state:
  - when mapped field is set: mapped field -> configured default value,
  - when mapped field is unset: legacy keys -> configured default value.
- Missing custom mapped fields warn and fallback to configured defaults (no hard fail). Warning summaries are persisted in prepare/run summaries.
- Discovery and mapping scope is top-level `feature.properties` only for this phase (nested paths out of scope).

Common API error messages (current behavior):

- `"Roads module is not enabled for this run."`
- `"Roads requires WBT delineation backend."`
- `"Provide multipart \`file\` for Roads upload."`
- `"Roads upload must be a .geojson file."`
- `"Roads GeoJSON must be a FeatureCollection."`
- `"Roads GeoJSON supports only LineString or MultiLineString geometries."`
- `"Roads upload exceeds max_upload_mb limit (... MB)."`
- parameter-validation messages from `set_params` (for example numeric/range/enum validation failures).

## TaskEnum and Preflight Contract

`TaskEnum` updates (`wepppy/nodb/redis_prep.py`):

- add `run_roads = "run_roads"`.
- label: `Run Roads`.
- emoji: `🚗`.

Run page TOC/preflight mapping updates:

- add `#roads -> TaskEnum.run_roads` in `TOC_TASK_ANCHOR_TO_TASK` (`run_0_bp.py`).
- add selector mapping `"roads": 'a[href="#roads"]'` in `weppcloud/static/js/preflight.js`.

Preflight service checklist updates (`services/preflight2/internal/checklist/checklist.go`):

- add checklist key `roads` (default `false`).
- compute `roads` completion as WEPP-dependent:
  - `check["roads"] = safeGT(prep["timestamps:run_roads"], runWepp)`.
  - if `runWepp` is missing, `roads` remains `false`.

Lock UI mapping update:

- `"roads.nodb"` is mapped in `preflight.js` to the Roads run lock indicator.

## Feasibility Assessment

## What Already Works

- `wepppy.nodb.mods.roads.monotonic_segments` already:
  - splits non-monotonic road paths by DEM profile.
  - defaults to `0.5 m` tolerance.
  - preserves source properties.
  - assigns unique `segment_id`.
  - emits segment low-point point features.
  - sets `topaz_id_chn_lowpoint` and `topaz_id_hill_lowpoint` for eligible inslope designs.
- Existing watershed runs consume `H*.pass.dat` entries from `pw0.run`, so swapping selected hillslope pass files is operationally feasible.
- `wepp_runner.make_watershed_omni_contrasts_run(...)` already supports per-hillslope pass path substitution.
- `wepppyo3` already has high-performance hillslope pass parsing (`hillslope_pass_to_columns`), which is a good base for a pass combiner.

## What Changed In Implementation

- Segment eligibility/attribution is implemented for both:
  - `Inslope_bd`
  - `Inslope_rd`
- Receiving hillslope attribution is implemented as `topaz_id_hill_lowpoint` with suffix invariant (`1|2|3`) enforced by utility behavior/tests.
- Segment execution is implemented under `wepp/roads/segments/` and `wepp/roads/{runs,output}/`.
- Pass combination is implemented through `wepppyo3.wepp_interchange.combine_hillslope_pass_files(..., strategy="phase1")`.

## Technical Risk and Mitigation

- Risk: pass-file fields like hydrograph-shape terms (`tcs`, `oalpha`) are not strictly additive.
- Mitigation: phase 1 treats pass combination as a calibrated approximation and validates against targeted full reruns where available.
- Risk: ambiguous lowpoint neighbors (multiple channel/hillslope candidates).
- Mitigation: deterministic neighbor-order and tie-break rules (defined below).

## Legacy WEPP:Road Alignment

The legacy WEPP:Road implementation (`/workdir/fswepp2/api/wepproad.py`) uses a 3-OFE hillslope (road/fill/buffer), not MOFE.  
This Roads NoDb phase intentionally simplifies inslope runs to a single OFE hillslope representation, with road OFE parameterization borrowed from legacy road templates.

Implication: this is an approximation relative to full WEPP:Road 3-OFE physics; acceptable for phase 1 if validated against known scenarios.

## Single-OFE Parameterization (Greenfield, Legacy-Derived)

This section defines the required parameterization contract for `Inslope_bd` and `Inslope_rd` in WEPPcloud Roads.

Source rationale:

- `wepproad.py` design/surface/traffic logic (`/workdir/fswepp2/api/wepproad.py`)
- legacy soil template semantics and comments (`/workdir/fswepp2/api/db/wepproad/soils/*.sol`)
- legacy UI label shows `inveg` as `Insloped, vegetated or rocked ditch` (parity outputs under `/workdir/fswepp2/parity-runs/wepproad/`)

## Design Mapping

- `Inslope_bd` -> legacy `inbare` semantics.
- `Inslope_rd` -> legacy `inveg` semantics (`vegetated or rocked ditch` bucket in legacy WEPP:Road).

Only these two designs are in scope for phase 1.

## Surface Mapping

Target surface domain:

- `gravel`
- `paved`

Default normalization from incoming road properties (case-insensitive):

- `Dirt`, `Gravel`, `Graveled`, `Native`, `Unpaved` -> `gravel`
- `Paved`, `Asphalt`, `Concrete` -> `paved`

If no recognized surface value exists, use controller default (phase-1 default: `gravel`) and log a warning.

This legacy lookup applies when `attribute_field_map.surface` is unset. When a surface mapping is set, runtime order is mapped field -> `surface_default`.

## Traffic Mapping

Target traffic domain:

- `high`
- `low`
- `none`

Resolution order:

1. explicit per-segment `TRAFFIC` property (if present/valid),
2. mapped from `CONDITION` (phase-1 default mapping):
   - `Impassable` -> `none`
   - `Year round` -> `high`
   - `New2011` -> `low`
3. controller default (phase-1 default: `low`).

This legacy order applies when `attribute_field_map.traffic` is unset. When a traffic mapping is set, runtime order is mapped field -> `traffic_default`.

## Soil Template Selection

Use legacy naming convention:

- `3{surf_code}{texture}{tau_c}.sol`

Where:

- `surf_code = "g"` for `gravel`, `"p"` for `paved`
- `texture in {"clay","silt","sand","loam"}`
- `tau_c` selection:
  - default `2`
  - `Inslope_rd` (`inveg`) -> `10`
  - `Inslope_bd` (`inbare`) with `paved` surface -> `1`

Resulting design/surface combinations:

- `Inslope_bd` + `gravel` -> `tau_c = 2`
- `Inslope_bd` + `paved` -> `tau_c = 1`
- `Inslope_rd` + `gravel` -> `tau_c = 10`
- `Inslope_rd` + `paved` -> `tau_c = 10`

## Soil Parameter Adjustments

Apply legacy WEPP:Road adjustments to selected template:

- `rfg_pct` handling:
  - write segment/default `ubr` value.
  - set `urr_ref = 65` for `gravel`; `95` for `paved`.
  - set `ufr_ref = (ubr + 65) / 2` for both `gravel` and `paved`.
- traffic effect on detachability/interrill:
  - for `traffic != high` (`low` or `none`), divide first-layer `Ki` and `Kr` by `4`.

## Management File Selection

Use legacy management files:

- base: `3inslope.man` for both `Inslope_bd` and `Inslope_rd`
- if `traffic == none`: `3inslopen.man`

(`traffic == low` uses `3inslope.man`; only soil `Ki/Kr` is reduced as above.)

## Legacy Parameterization Matrix (Phase 1)

The following matrix is the greenfield single-OFE mapping contract to legacy WEPP:Road semantics.

| Design | Surface | Traffic | Soil Template Rule | `tau_c` | Management | Ki/Kr Factor (layer 1) | `urr_ref` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Inslope_bd` | `gravel` | `high` | `3g{texture}2.sol` | `2` | `3inslope.man` | `1.0` | `65` |
| `Inslope_bd` | `gravel` | `low` | `3g{texture}2.sol` | `2` | `3inslope.man` | `0.25` | `65` |
| `Inslope_bd` | `gravel` | `none` | `3g{texture}2.sol` | `2` | `3inslopen.man` | `0.25` | `65` |
| `Inslope_bd` | `paved` | `high` | `3p{texture}1.sol` | `1` | `3inslope.man` | `1.0` | `95` |
| `Inslope_bd` | `paved` | `low` | `3p{texture}1.sol` | `1` | `3inslope.man` | `0.25` | `95` |
| `Inslope_bd` | `paved` | `none` | `3p{texture}1.sol` | `1` | `3inslopen.man` | `0.25` | `95` |
| `Inslope_rd` | `gravel` | `high` | `3g{texture}10.sol` | `10` | `3inslope.man` | `1.0` | `65` |
| `Inslope_rd` | `gravel` | `low` | `3g{texture}10.sol` | `10` | `3inslope.man` | `0.25` | `65` |
| `Inslope_rd` | `gravel` | `none` | `3g{texture}10.sol` | `10` | `3inslopen.man` | `0.25` | `65` |
| `Inslope_rd` | `paved` | `high` | `3p{texture}10.sol` | `10` | `3inslope.man` | `1.0` | `95` |
| `Inslope_rd` | `paved` | `low` | `3p{texture}10.sol` | `10` | `3inslope.man` | `0.25` | `95` |
| `Inslope_rd` | `paved` | `none` | `3p{texture}10.sol` | `10` | `3inslopen.man` | `0.25` | `95` |

## Single-OFE Slope File Contract

Road segment slope file generation is greenfield single-OFE:

- one OFE only (`n_ofe = 1`)
- profile width:
  - per-segment `WIDTH_M` override when available, else controller default (phase-1 default: `4.0 m`)
- profile length:
  - segment geometry length in meters
- slope:
  - segment grade from oriented high-to-low endpoints over segment length,
  - clamped to safe bounds (`0.1%` to `40%`) using legacy WEPP:Road road-slope validation bounds.

The segment geometry must be oriented downslope before slope-file emission.

## Run-Level Parameter Defaults

Controller-level defaults (editable in Roads UI/API):

- `soil_texture_default`: one of `clay|silt|sand|loam`
- `rfg_pct_default`: `20`
- `surface_default`: `gravel`
- `traffic_default`: `low`
- `road_width_m_default`: `4.0`
- `trace_max_steps`: `20000`
- `input_years`: inherit baseline WEPP climate years unless explicitly overridden
- `wepp_bin`: inherit baseline run setting unless explicitly overridden

Per-segment property overrides are supported for:

- design
- surface
- traffic
- soil texture
- rock fragment percent
- road width

## WEPP Run Assembly Contract

For each selected segment, Roads must generate a standalone WEPP hillslope contributor run with:

- climate: inherit baseline run climate station/files and simulation year span unless explicitly overridden in Roads params.
- slope file: generated from monotonic, downslope-oriented segment profile (see monotonicity requirement below).
- soil file: selected and adjusted using the legacy-derived rules in this specification.
- management file: selected from `3inslope.man` or `3inslopen.man`.
- run metadata:
  - deterministic run key based on `segment_id`,
  - preserved provenance fields (`segment_id`, source feature ID if available, `topaz_id_chn_lowpoint`, `topaz_id_hill_lowpoint`).

Contributor variants:

- channel-associated segments: one-OFE road contributor (phase-1 behavior retained).
- non-channel routed segments: two-OFE routed contributor (`road OFE + buffer OFE`), where:
  - road OFE uses the existing inslope road parameterization,
  - buffer OFE uses trace-derived `path_length_m` and slope statistics.

Required output for each successful segment run:

- segment pass file under `wepp/roads/output/`.
- per-segment execution record in `last_run_summary` with status and diagnostics.

## Segment Utility Requirements

Module: `wepppy/nodb/mods/roads/monotonic_segments.py`

## Design Filter

Define inslope eligibility with case-insensitive comparison:

- `design.lower() in {"inslope_bd", "inslope_rd"}`

Only eligible designs receive channel/hillslope lowpoint attribution. All segments retain `topaz_id_chn_lowpoint` and `topaz_id_hill_lowpoint` properties; default value is `null`.

## Output Feature Contract

Each output segment feature must preserve all source properties and include:

- `segment_id`: globally unique string per output file (`roads-seg-######`).
- `topaz_id_chn_lowpoint`: `int | null`.
- `topaz_id_hill_lowpoint`: `int | null`.
- `_roads_low_point_x`: low point x in source CRS.
- `_roads_low_point_y`: low point y in source CRS.
- `_roads_low_point_elevation_m`: sampled DEM elevation.
- `_roads_lowpoint_decision`: prepare-stage classification label.
- `_roads_routing_eligibility`: one of `channel_associated`, `non_channel_routable`, `non_routable`, `design_not_eligible`, `missing_channel_lookup_rasters`.
- `_roads_non_channel_routable`: bool flag for run-stage trace eligibility.
- `_roads_lowpoint_row`, `_roads_lowpoint_col`: lowpoint seed cell used for run-stage trace calls.
- `_roads_lowpoint_topaz_id`, `_roads_lowpoint_topaz_suffix`, `_roads_lowpoint_is_hillslope_pixel`: lowpoint `subwta` diagnostics.

Companion low-point point features must carry the same properties as their segment, plus:

- `_roads_feature_type = "segment_low_point"`

## Channel Lowpoint Rule

For eligible designs:

1. Compute lowpoint raster cell from segment lowpoint coordinate.
2. Search `[self + 8 neighbors]` for channel mask cells (`netful > 0`).
3. If found, set `topaz_id_chn_lowpoint` to that cell’s `subwta` Topaz ID.
4. If none found, set `null`.

Determinism: preserve fixed offset order so repeated runs produce identical IDs.

## Non-Channel Routable Rule (Step-2)

For eligible designs where channel-neighbor search fails:

1. Inspect `subwta` at the low-point cell.
2. If low-point `subwta` suffix is `1`, `2`, or `3`, mark segment as non-channel routable:
   - `_roads_lowpoint_decision = "non_channel_hillslope_routable"`
   - `_roads_routing_eligibility = "non_channel_routable"`
   - `_roads_non_channel_routable = true`
3. Otherwise mark non-routable:
   - `_roads_lowpoint_decision = "no_channel_pixel_near_lowpoint"`
   - `_roads_routing_eligibility = "non_routable"`
   - `_roads_non_channel_routable = false`

## Hillslope Lowpoint Rule

For eligible designs with non-null `topaz_id_chn_lowpoint`:

1. Let `chn = topaz_id_chn_lowpoint` (must end in `4`).
2. Candidate receiving hillslopes are:
   - `chn - 3` (suffix `1`, center)
   - `chn - 2` (suffix `2`, right)
   - `chn - 1` (suffix `3`, left)
3. Sample `subwta` in a local neighborhood around the segment lowpoint cell.
4. Select the first candidate present by deterministic priority:
   - nearest cell distance to lowpoint center.
   - then candidate priority `center (chn-3)`, `right (chn-2)`, `left (chn-1)`.
   - then numeric ascending as final tie-break.
5. Set `topaz_id_hill_lowpoint` to selected candidate; else `null`.

Required invariant:

- If `topaz_id_hill_lowpoint` is not null, it must end in `1`, `2`, or `3`.

## `wepp/roads` Layout and Execution Contract

Run-root-relative directories:

- `wepp/roads/segments/`
- `wepp/roads/runs/`
- `wepp/roads/output/`

Primary artifacts:

- `wepp/roads/segments/roads.inslope.monotonic.geojson`
- `wepp/roads/segments/roads.inslope.low_points.geojson`
- `wepp/roads/segments/roads.inslope.summary.json`
- `wepp/roads/segments/roads.segment.pass.manifest.json`
- `wepp/roads/runs/*.run` (segment and watershed runs)
- `wepp/roads/output/H<segment_or_target>.pass.dat`
- `wepp/roads/output/interchange/*`
  - includes `roads_segment_loss_summary.parquet` and regenerated report resources
- `wepp/roads/roads.log`

Layout rationale:

- Roads is an in-run mod, not a child-run clone; storing outputs under `wepp/roads/*` aligns with existing mod layouts (for example `wepp/ag_fields/*`) and avoids unnecessary `_pups/*` coupling.
- Keeping Roads pass files in `wepp/roads/output/` allows a single watershed `pw0.run` in `wepp/roads/runs/` to reference one directory (`../output/`) for both unchanged and roads-adjusted hillslopes.

## Segment Selection for WEPP Runs

Operational filter for inslope step-2:

- `DESIGN` in `{Inslope_bd, Inslope_rd}`
- channel-associated execution path:
  - `topaz_id_chn_lowpoint` is not null,
  - `topaz_id_hill_lowpoint` is not null.
- non-channel routed execution path:
  - `_roads_non_channel_routable == true` (prepare-stage metadata),
  - run-stage trace reaches channel,
  - traced receiving hillslope resolves to `subwta` suffix `1|2|3`,
  - traced receiving hillslope maps through `top2wepp`.

Non-selected segments are recorded but not executed.

## Road Slope File Monotonicity Requirement

Road segment WEPP slope files must be monotonic in elevation for each simulated segment.

Required behavior:

- Before writing each segment `.slp`, verify the sampled profile is monotonic (within tolerance) in the direction used for WEPP routing.
- If the segment geometry direction is opposite of the desired downslope routing direction, reverse coordinates before writing the slope file.
- If a segment cannot be represented as monotonic after segmentation/tolerance rules, skip execution and report it in diagnostics.

Rationale:

- WEPP hillslope routing assumes a consistent flow direction along profile length; non-monotonic segment slope files can produce unstable or nonphysical runoff routing behavior.

## Hillslope Mapping Requirement

Each executed segment must map to a watershed hillslope WEPP ID using the run translator (`WeppTopTranslator.top2wepp`).

Contract:

- segment -> `topaz_id_hill_lowpoint` -> `wepp_id`
- if no mapping exists, segment is skipped and reported in summary diagnostics.

## Watershed-Routing Injection Strategy

## Phase 1 Strategy (Pass Combination + Watershed Rerun)

1. Copy baseline `wepp/runs` to `wepp/roads/runs`.
2. Generate and run segment-level WEPP hillslope runs under `wepp/roads/`.
3. For each target hillslope WEPP ID, combine:
   - baseline hillslope pass (`H<wepp_id>.pass.dat`)
   - all mapped road-segment pass files
4. Stage `wepp/roads/output/` with one pass file per watershed hillslope:
   - for untouched hillslopes, stage baseline pass from `wepp/output/H<wepp_id>.pass.dat` (symlink preferred, copy acceptable when symlink is unavailable),
   - for roads-targeted hillslopes, write combined pass as `wepp/roads/output/H<wepp_id>.pass.dat`.
5. Build watershed run in `wepp/roads/runs/pw0.run` using `make_watershed_omni_contrasts_run` with per-hillslope pass paths rooted at `../output/H<wepp_id>`.
6. Run watershed from `wepp/roads/runs/pw0.run`.

This preserves routing dynamics in WEPP watershed execution while injecting road effects.

## Pass Combiner Specification (`wepppyo3`)

Preferred module location: `wepppyo3/wepp_interchange`.

Recommended API direction:

- `combine_hillslope_pass_files(base_pass, road_passes, out_pass, *, strategy="phase1")`

Minimum behavior:

1. Parse pass files to structured columns (existing parser).
2. Align rows by simulation day key:
   - primary: `year` + `julian`
   - fallback: `sim_day_index`
3. Resolve day-level event kind by precedence across contributors:
   - `EVENT` > `SUBEVENT` > `NO EVENT`
4. Additive volume/mass fields (sum across base + roads):
   - `runvol`, `sbrunv`, `drrunv`, `gwbfv`, `gwdsv`, `tdet`, `tdep`.
5. Depth fields (`runoff`, `sbrunf`, `drainq`) must be explicitly handled:
   - if contributing area metadata is available, recompute from combined volumes.
   - otherwise, sum same-unit depth terms when all contributors are directly comparable.
   - if neither rule can be applied, set deterministic fallback (`0`) and emit diagnostic metadata.
6. Concentration fields:
   - derive per-class mass `mass_i = sedcon_i * runvol`.
   - sum masses.
   - recompute `sedcon_i = total_mass_i / total_runvol` when `total_runvol > 0`, else `0`.
7. Hydrograph-shape fields (`dur`, `tcs`, `oalpha`) and peak (`peakro`) in phase 1:
   - `dur`: `max(dur_i)` across aligned source events.
   - `tcs`: `max(tcs_i)` across aligned source events.
   - `peakro`: combine with SCS-triangular superposition (WEPP-like `wshscs` behavior), not simple sum.
   - `oalpha`: back-calculate from combined fields:
     - if `runvol_comb > 0`: `oalpha_comb = max(tcs_comb / 24, peakro_comb * 3600 * tcs_comb / runvol_comb)`.
     - else: `oalpha_comb = 0`.
8. Day-kind handling:
   - resolved `EVENT`: apply full merge behavior above.
   - resolved `SUBEVENT`: combine subsurface/tile/baseflow terms; set `dur`, `tcs`, `oalpha`, `peakro` to `0`.
   - resolved `NO EVENT`: keep day as `NO EVENT` with zero flow fields.
9. Serialize a valid WEPP hillslope pass file.

Notes:

- This is an approximation. A later phase can introduce a physics-aware hydrograph merge.
- Build combiner tests against parser round-trip and synthetic multi-source events.
- `oalpha` is intentionally not capped to `1.0` in phase 1 to mirror current WEPP pass-writing behavior in `wshpas.for` (the upper-bound clamp is commented out there).
- Rationale for phase-1 hydrograph-shape rules is based on WEPP internals in `/workdir/wepp-forest`:
  - hillslope pass writes `tcs/oalpha` (`wshpas.for`) and watershed reads `htcs/halpha` (`wshred.for`);
  - channel duration merge is max (`wshcqi.for`);
  - channel `tc` follows longest/max path logic (`wshtc.for`);
  - channel `alpha` merge uses max contributor alpha (`wshpek.for`);
  - multi-contributor peak merge uses SCS-triangular superposition (`wshscs.for`, called by `wshpek.for`);
  - left/right/top channel contributors are treated as upstream inflow in aggregation logic (`wshcqi.for`, `wshchr.for`).

## Validation and Acceptance Criteria

## Utility Tests

- Existing monotonic split tests remain green.
- Coverage includes tests for:
  - `Inslope_rd` channel attribution parity with `Inslope_bd`.
  - `topaz_id_hill_lowpoint` assignment and suffix invariant.
  - deterministic tie-break behavior.
  - null behavior when no nearby channel/hillslope exists.

## Integration Checks

- Segment pipeline writes expected artifacts under `wepp/roads/segments/`.
- Segment-to-hillslope mapping summary includes counts:
  - eligible
  - mapped
  - skipped (no channel, no hillslope, no translator map)
- Watershed rerun succeeds using combined pass files.
- Compare baseline vs roads-injected watershed outputs (mass/flow deltas) for sanity bounds.
- Queue wiring governance checks pass for new Roads jobs:
  - update `wepppy/rq/job-dependencies-catalog.md`,
  - run `wctl check-rq-graph` (and regenerate graph if drift is reported).

## Implementation Milestones (Completed)

1. Finalized segment utility behavior for both inslope designs (`Inslope_bd`, `Inslope_rd`), including channel/hillslope lowpoint attribution and deterministic IDs.
2. Completed unit/integration coverage for `monotonic_segments` outputs and invariants.
3. Implemented `Roads(NoDbBase)` controller (`roads.py`) with persisted state contract and status lifecycle.
4. Implemented Roads API/UI scaffolding:
   - blueprint routes in `roads_bp.py`,
   - Roads controls panel with upload/config/run actions,
   - summary + run-results report endpoints/templates.
5. Added RQ workers for `prepare_segments` and `run` orchestration.
6. Implemented single-OFE segment WEPP run assembly under `wepp/roads/{runs,output}/` using this parameterization contract.
7. Integrated pass combiner in `wepppyo3`, then wired watershed rerun assembly with `make_watershed_omni_contrasts_run`.
8. Added diagnostics/reporting, roads-scoped report-resource regeneration, and end-to-end validation on fixture runs.

## Non-Goals (Phase 1)

- Non-inslope designs (`Outslope_*`, etc.).
- Exact replication of legacy 3-OFE WEPP:Road behavior.
- Full WEPP:Road 3-OFE decomposition (road/fill/buffer) inside Roads phase 1.
- Advanced physics-based hydrograph merge beyond the documented phase-1 approximation.

## Future Concept Draft: `Outslope_unrutted` MOFE Hillslope Replacement

Status: concept draft only (not implemented in phase 1).

This concept treats Roads as an enhanced scenario model, not a baseline-vs-roads delta workflow.

### Intent

- model `Outslope_unrutted` with a multi-OFE profile that preserves explicit road, fill, and buffer behavior.
- replace targeted receiving hillslope pass files with synthetic roads-aware pass files.
- avoid additive double counting by replacing (not adding to) the targeted hillslope response.

### Flow Regime and Routing Semantics (Concept Draft)

Design-regime mapping:

- `outslope unrutted`: sheet-flow abstraction.
- `outslope rutted`: point-source abstraction for water/sediment discharge from road low point.
- `inslope bare ditch` and `inslope rocky ditch`: point-source abstraction for water/sediment discharge from road low point.

Physical assumptions:

- inslope point-source cases assume ditch/culvert bypass of fill-slope dynamics.
- outslope rutted assumes no culvert bypass; concentrated flow can erode across fill slope before entering downslope buffer.

Current implementation boundary (phase 2 step-2):

- only inslope designs are implemented.
- channel-associated low points keep the phase-1 behavior (`topaz_id_chn_lowpoint` + `topaz_id_hill_lowpoint` prepare mapping).
- non-channel low points are now routable when the low-point `subwta` suffix is `1|2|3`; run-stage tracing routes those segments to channel and executes routed contributors as `road OFE + buffer OFE`.
- routed contributors are merged through the existing pass-combine flow using traced receiving-hillslope attribution.

Implemented step-2 non-channel low-point path:

1. If low point is not channel-associated, evaluate low-point cell in `subwta`.
2. If `subwta` value is a hillslope pixel (`int` value ending in `1|2|3`), mark segment as non-channel routable in prepare outputs.
3. During run, trace routable low points to channel via `wepppyo3.roads_flowpath.trace_downslope_flowpath(...)`.
4. If trace reaches channel, build routed contributor profile as `road OFE + flowpath buffer OFE`:
   - road OFE from existing inslope segment parameterization,
   - buffer OFE from trace path length/slope.
5. Resolve receiving hillslope from traced pre-channel cell (`subwta` suffix `1|2|3`) and merge resulting contributor pass into mapped hillslope output.
6. If trace does not reach channel, skip contributor generation and persist explicit diagnostics in run summary/logs.

### High-Fidelity Concept (Top-Level)

1. Identify outsloped road discharge strips and trace downslope delivery paths to the channel network.
2. Partition traced strips by receiving WEPP hillslope ID so each contributor maps deterministically.
3. For each affected strip, build a roads-aware MOFE profile with ordering:
   - upslope hillslope segment -> road -> fill -> downslope buffer segment.
4. For each affected receiving hillslope, represent unaffected remainder area with non-road hillslope contributor profile(s).
5. Run WEPP for all contributors, then assemble one synthetic `H<wepp_id>.pass.dat` per affected hillslope by contributor aggregation.
6. Stage synthetic hillslope pass files as replacements for affected hillslopes; keep baseline pass files for untouched hillslopes.
7. Run watershed routing once using the full set of staged pass files.

### Fidelity Invariants

- **Replacement semantics**: targeted hillslope response is replaced, not incrementally added.
- **Area conservation**: affected-strip plus unaffected remainder area equals original hillslope area.
- **Buffer preservation**: final downslope buffer OFE remains explicit in the roads-aware contributor profile.
- **Topology preservation**: watershed structure remains unchanged (`left/right/top` hillslope-channel linkage stays canonical).
- **Road geometry parity**: `Outslope_unrutted` road OFE parameterization follows legacy outslope geometry intent (including area-preserving transform behavior).

### Deferred Details (To Be Specified Later)

- exact strip delineation and flowpath tracing rules.
- hillslope-boundary splitting when a traced strip crosses multiple hillslopes.
- contributor aggregation math for hydrograph-shape terms in replacement mode.
- parameter defaults and per-segment overrides for outsloped designs.
- handling for segments that terminate on channels vs within hillslope interiors.

## Point-Source Flowpath Trace Contract in Rust

Status: step-1 substrate implemented (2026-03-27).

### Direction

- keep the point-source routing engine in Rust (no pure-Python reimplementation).
- keep one shared implementation in `peridot` and expose it through both CLI and `wepppyo3`.

### Implemented Step-1 Surfaces

- `peridot` core API:
  - `roads_trace::trace_downslope_flowpath(...) -> TraceDownslopeResult`
- `peridot` CLI wrapper:
  - `trace_downslope_flowpath --subwta --flovec --relief --seed-row --seed-col [--channel] [--max-steps] [--out-json]`
- `wepppyo3` runtime API:
  - `wepppyo3.roads_flowpath.trace_downslope_flowpath(subwta_path, flovec_path, relief_path, seed_row, seed_col, channel_path=None, max_steps=20000) -> dict`

### Implemented v1 Trace Result Contract

Returned fields (CLI JSON and `wepppyo3` dict keys):

- `seed_row`, `seed_col`, `seed_topaz_id`
- `reaches_channel`
- `channel_row`, `channel_col`, `channel_topaz_id`
- `termination_reason`
- `rows`, `cols`, `indices`
- `distance_m`, `elevation_m`, `segment_slope`
- `path_length_m`, `drop_m`, `mean_slope`, `max_slope`

Termination labels:

- `hit_channel`
- `invalid_flow_direction`
- `loop_detected`
- `raster_edge`
- `max_steps_exceeded`

Channel-detection rule in v1:

- when `channel_path/channel_mask` is provided, channel is `mask > 0`.
- when channel mask is absent, channel is inferred from `SUBWTA` suffix `4` (`topaz_id % 10 == 4`).

v1 integration constraints:

- `subwta`, `flovec`, `relief`, and optional channel-mask rasters must share identical raster shape (`width`/`height`); shape mismatches fail explicitly.
- seed inputs are raster cell coordinates (`seed_row`, `seed_col`, 0-based), not projected/map coordinates.
- v1 does not perform raster reprojection/resampling inside trace execution; callers are responsible for providing aligned rasters.
- CLI and `wepppyo3` wrappers are contract-bound to the shared `peridot` core API (validated by parity tests).

### Ordered Follow-On Plan

1. Implement `outslope_rutted` point-source routing for both channel-associated and non-channel low points, including explicit fill OFE handling.
2. Implement `outslope_unrutted` as MOFE hillslope replacement (`hill -> road -> fill -> hill`) with replacement semantics (no double counting).
