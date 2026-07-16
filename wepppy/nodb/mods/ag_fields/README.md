# AgFields NoDb Mod (`wepppy.nodb.mods.ag_fields`)

> Manages agricultural field boundary ingestion, sub-field abstraction (Peridot), and per-sub-field WEPP runs for WEPPcloud projects.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb locking/caching conventions and test guidance.

## Overview

This module provides the `AgFields` NoDb controller, which coordinates an “ag fields” workflow inside a WEPPcloud run working directory (`wd`). At a high level it:

- Normalizes and validates a user-supplied field boundary GeoJSON into a canonical location.
- Extracts tabular attributes (crop rotation schedule columns, IDs, etc.) into a Parquet “rotation schedule” for fast access.
- Rasterizes the field boundary polygons onto the project DEM grid for downstream tools.
- Runs Peridot “sub-field” abstraction (intersecting fields with hydrologic subwatersheds and generating representative slope files).
- Builds multi-year WEPP management files from crop rotation schedules and runs a WEPP hillslope simulation per sub-field.
- Runs field-aware, direct-outlet, or connectivity-aware mixed watershed routing
  below independently composable scheme roots with source/closure manifests.

The controller is stateful and persisted as `ag_fields.nodb` at the root of the working directory.

## Workflow

Typical sequence (some steps are optional depending on the UI/route calling into this module):

1. **Ingest boundaries**: `AgFields.validate_field_boundary_geojson(...)`
2. **Confirm the boundary schema atomically**: `AgFields.confirm_schema("field_id", "Crop{}")`
4. **Rasterize boundaries**: `AgFields.rasterize_field_boundaries_geojson()`
5. **Abstract sub-fields (Peridot)**: `AgFields.periodot_abstract_sub_fields(...)`
6. **Polygonize sub-fields**: `AgFields.polygonize_sub_fields()`
7. **Provide crop→management mapping**: call `AgFields.write_rotation_lookup(rows)` (and optionally populate `ag_fields/plant_files/` via `handle_plant_file_db_upload`)
8. **Run WEPP and publish interchange per sub-field**: use the Stage 4 RQ
   endpoint, which selects the persisted `AgFields.wepp_bin`, calls
   `AgFields.run_wepp_ag_fields()`, and then publishes the six native
   interchange datasets before marking the stage complete. Direct controller
   callers receive raw outputs only and must explicitly invoke
   `run_wepp_ag_fields_interchange(...)`.
9. **Run an isolated watershed scheme**: call
   `AgFields.run_watershed_integration(scheme="concept_1" | "concept_2" |
   "hybrid")` after Stage 4 is current. An omitted scheme remains Concept 2.
   Automatic concurrency is capped at 16; explicit `max_workers` must be 1-16.

## Inputs and outputs

### Required inputs (in or relative to `wd`)

- Field boundary GeoJSON (user-supplied) containing:
  - a `field_id` attribute column (required by validation)
  - crop rotation columns covering the observed climate year range (column names addressed via `rotation_accessor`)
- `ag_fields/rotation_lookup.tsv`: crop name → management source mapping (see format below)
- Existing watershed/climate context produced by the normal WEPPcloud workflow (e.g., `dem`, `wepp/runs`, and the `Watershed`, `Climate`, `Landuse` NoDb controllers)

### Key generated artifacts

| Path (relative to `wd`) | Produced by | Purpose |
|---|---|---|
| `ag_fields/fields.WGS.geojson` | `validate_field_boundary_geojson` | Canonical boundary GeoJSON for downstream tooling and UI overlays |
| `ag_fields/rotation_schedule.parquet` | `validate_field_boundary_geojson` | Field attribute table extracted from the GeoJSON (used to read crop columns per year) |
| `ag_fields/field_boundaries.tif` | `rasterize_field_boundaries_geojson` | Field ID raster aligned to the project DEM grid |
| `ag_fields/sub_fields/fields.parquet` | `periodot_abstract_sub_fields` | Sub-field metadata (field/topaz/wepp/sub_field IDs, geometry stats, etc.) |
| `ag_fields/sub_fields/field_flowpaths.parquet` | `periodot_abstract_sub_fields` | Sub-field flowpath metadata with parent `topaz_id`, canonical `flowpath_topaz_id`, and `fp_id` |
| `ag_fields/sub_fields/sub_field_id_map.tif` | Peridot | Sub-field ID raster (intersection of hydrology + fields) |
| `ag_fields/sub_fields/sub_fields.geojson` | `polygonize_sub_fields` | Polygonized sub-fields with `field_id`, `topaz_id`, `wepp_id`, `sub_field_id` |
| `wepp/ag_fields/runs/p<sub_field_id>.*` | `run_wepp_ag_fields` | Per-sub-field WEPP inputs (`.run`, `.man`, `.slp`) |
| `wepp/ag_fields/output/H<sub_field_id>.*.dat` | WEPP | Per-sub-field WEPP outputs (loss, plot, soil, water balance, etc.) |
| `wepp/ag_fields/output/interchange/H.{pass,ebe,element,loss,soil,wat}.parquet` | Stage 4 RQ native interchange | Failure-atomic six-file bundle keyed by real `field_id` and `sub_field_id`; sub-fields do not have their own TOPAZ/parent-WEPP identity |
| `wepp/ag_fields/output/interchange/interchange_version.json` | Stage 4 RQ native interchange | Last-written completion manifest with dataset kind, AgFields schema version, mapping hash, row counts, and row groups |
| `wepp/ag_fields/watershed/runs/` | Historical Concept 2 run | Preserved unscoped parent and watershed run files |
| `wepp/ag_fields/watershed/output/` | Historical Concept 2 run | Preserved unscoped parent PASS, watershed output, and interchange |
| `wepp/ag_fields/watershed/manifest/` | Historical Concept 2 run | Preserved unscoped source, closure, summary, and evaluation evidence |
| `wepp/ag_fields/watershed/concept-1/` | Concept 1 integrator | Field-aware OFE runs, watershed output, plan/routing manifests, and interchange |
| `wepp/ag_fields/watershed/concept-2/` | Current Concept 2 integrator | Current direct-outlet source/closure manifests and isolated watershed output |
| `wepp/ag_fields/watershed/hybrid/` | Hybrid integrator | Peridot branch detail, residual OFE inputs, weighted connected-source closure, and watershed output |

## Quick start / examples

### Python (controller-driven workflow)

```python
from wepppy.nodb.mods.ag_fields import AgFields

wd = "/wc1/runs/co/copacetic-note"
ag = AgFields.getInstance(wd)

# 1) Normalize + validate boundaries (copies into wd/ag_fields/fields.WGS.geojson)
ag.validate_field_boundary_geojson("inputs/field_boundaries.geojson")

# 2) Validate both schema choices before either value is persisted
ag.confirm_schema("field_id", "Crop{}")

# 4) Create wd/ag_fields/field_boundaries.tif aligned to the project DEM
ag.rasterize_field_boundaries_geojson()

# 5) Abstract sub-fields with Peridot (requires the normal WEPPcloud watershed inputs)
ag.periodot_abstract_sub_fields(sub_field_min_area_threshold_m2=0.0, verbose=True)
ag.polygonize_sub_fields()

# 6) Provide crop->management mapping and run WEPP per sub-field
# - Write wd/ag_fields/rotation_lookup.tsv from structured rows (see below).
#   ag.write_rotation_lookup(rows)
# - Optionally populate wd/ag_fields/plant_files/ with:
#   ag.handle_plant_file_db_upload("plant_db.zip")
ag.wepp_bin = "wepp_260714"
ag.run_wepp_ag_fields()

# 7) Run one routing scheme (omitting scheme selects concept_2)
summary = ag.run_watershed_integration(scheme="concept_1", max_workers=8)
print(summary["scheme"], summary["parent_count"])
```

### `rotation_lookup.tsv` format

`CropRotationManager` reads `wd/ag_fields/rotation_lookup.tsv`. It must have three tab-delimited columns:

1. `crop_name`: string matching values found in the rotation schedule columns
2. `database`: `weppcloud` or `plant_file_db`
3. `rotation_id`:
   - for `weppcloud`: a management ID (must parse as an integer)
   - for `plant_file_db`: a `.man` filename present under `wd/ag_fields/plant_files/` (spaces are normalized to underscores)

Example:

```tsv
crop_name	database	rotation_id
Corn	plant_file_db	corn_spring_NT.man
Forest	weppcloud	42
```

`write_rotation_lookup()` preserves this three-column schema, permits intentionally unmapped rows by omitting them from the TSV, validates every mapped row before replacement, and returns structured `ok`/`unmapped` results. Any invalid mapped row raises `RotationLookupValidationError` and leaves the prior file unchanged. `validate_rotation_lookup()` returns the same per-crop result structure and does not print.

### Multi-year management synthesis

AgFields builds one source-management entry per observed crop year and composes
them with `ManagementRotationSynth(..., mode="stack-and-merge")`. Some uploaded
plant managements encode a crop as two one-year rotations: a setup year followed
by the retained crop year. The synthesizer normalizes those rotations, removes
the setup year as a separate simulation year, and combines its distinct surface
operations with the preceding crop year. When setup and crop years already
reference the same surface sequence, that sequence is retained as-is; spring and
fall operations are therefore not duplicated or reordered.

Plant, operation, initial-condition, contour, and drainage definitions are
shared when their complete model structure is identical. Scenario names are
reference keys and may differ after segment prefixing, so they do not make two
otherwise identical definitions distinct. All explicit scenario references,
including the residue-addition plant index (`iresad`), are remapped to the
retained definition. Unreferenced definitions are omitted after the final
management graph is assembled. Surface and yearly scenarios remain isolated by
simulation year because a later setup-year merge may mutate one of them.

The resulting crop order, number of simulation years, operation dates, and
referenced model values are unchanged. Production synthesis fails before writing
when more than 32 distinct referenced yearly scenarios remain, matching the
expanded WEPP hillslope input limit and avoiding a misleading zero-return-code
run without a success marker. The independent Concept 1 planner remains limited
to 20 OFEs.

### Concept 1 management-capacity census

`management_corpus` is a server-independent diagnostic CLI for an accepted
Concept 1 or hybrid `ofe_plan.parquet`. It composes the exact deduplicated
management graph for each parent without applying the production yearly-scenario
write ceiling, serializes and reparses every result, and records bounded-section
metrics plus source and generated-file SHA-256 hashes. This inventory exception
does not decide the production writer or WEPP executable limit.

```bash
python3 -m wepppy.nodb.mods.ag_fields.management_corpus \
  --ofe-plan /tmp/agfields-concept1-census/ofe_plan.parquet \
  --parent-runs /wc1/runs/<prefix>/<runid>/wepp/runs \
  --subfield-runs /wc1/runs/<prefix>/<runid>/wepp/ag_fields/runs \
  --output-dir /tmp/agfields-concept1-management-corpus
```

To materialize and execute every parent in an accepted plan against an explicit
hillslope binary, also provide the matching parent summary and simulation length:

```bash
python3 -m wepppy.nodb.mods.ag_fields.corpus_execution \
  --ofe-plan /tmp/agfields-concept1-census-v8/ofe_plan.parquet \
  --parent-summary /tmp/agfields-concept1-census-v8/parent_summary.parquet \
  --parent-runs /wc1/runs/sa/sacral-self-discipline/wepp/runs \
  --subfield-runs /wc1/runs/sa/sacral-self-discipline/wepp/ag_fields/runs \
  --output-dir /tmp/agfields-concept1-parent-corpus \
  --wepp-bin /path/to/wepp_hill \
  --sim-years 17
```

The command writes complete generated inputs, PASS-focused WEPP outputs,
`execution_results.parquet`, `execution_summary.json`, and logs only for failed
parents. It refuses a non-empty output directory and classifies materialization,
invalid-input, invalid-producer, non-finite PASS, timeout, signal,
missing-output, and numerical-fault failures without mutating the source project.

The output directory contains `management_corpus.parquet` (one metric row per
parent), `management_sources.parquet` (one hashed source row per OFE),
`management_corpus_summary.json` (maxima and distributions), and reparsed files
under `managements/`. Use `--workers` to override the default of up to eight
independent parent-management processes.

### Plant management archives

`handle_plant_file_db_upload()` accepts a ZIP already staged under `ag_fields/`. Member paths are checked, `.man` matching is case-insensitive, final extensions are normalized to lowercase, and spaces become underscores. Same-named re-uploads replace deterministically; only distinct colliding names within one archive receive `_1`, `_2`, and so on. Unreadable 2017.1 files raise `PlantFileProcessingError` naming the member, while regular invalid files remain visible in the persisted inventory with their parse reason. Use `get_plant_file_inventory()` to read provenance and `delete_plant_file()` to remove a basename.

Jim-interface archives can contain applied-residue plant placeholders with a
nonpositive maximum canopy height. During ingestion, a plant with `hmax <= 0`
is normalized to `0.00001 m` only when parsed references prove it is used by a
residue-addition operation and is not used as an active yearly or initial plant.
This is the minimum positive value retained by the management serializer; no
other plant or operation field changes. Preserved 2017.1 sources remain
unchanged, raw 98.4 header notes are retained, and each inventory file reports
an additive `normalizations` list with the original and final values. See
`docs/adrs/ADR-0016-agfields-applied-residue-hmax-floor.md`.

## HTTP and RQ surface

`wepppy.microservices.rq_engine.ag_fields_routes` exposes the staged workflow under `/api/runs/{runid}/{config}/agfields/`. The surface includes boundary upload, atomic schema confirmation, build-subfields enqueue, plant ZIP enqueue/inventory/delete, mapping read/save, management options, sub-field WEPP enqueue, scheme-aware watershed enqueue/clear, Stage 4 artifact clear, overlay serving, and state hydration. Read routes require `rq:status`; mutations require `rq:enqueue`; all routes authorize access to the requested run. Watershed mutations accept `concept_1`, `concept_2`, `hybrid`, or request-only `all`; omission remains Concept 2.

RQ entrypoints live in `wepppy.rq.ag_fields_rq`. Job hints use `agfields_build_subfields`, `agfields_plantdb`, `agfields_run_wepp`, the three scheme-specific watershed keys, and additive Run All parent key `agfields_run_watershed_suite`. The historical `agfields_run_watershed` hint remains a Concept 2 alias. A single scheme remains one direct job. `all` returns one suite parent as `job_id` plus the unchanged scheme-child `job_ids` mapping. The route atomically registers the complete planned tree on the parent; dispatch and cancellation share a lock. The parent records Concept 1, Concept 2, and hybrid under ordered `jobs:*` metadata with serial allow-failure dependencies, so later comparisons execute after an earlier failure without overlapping full-watershed memory peaks. A fourth registered finalizer depends on all three scheme IDs with `allow_failure=True`; Batch Runner-style release guards prevent already-failed dependencies from stranding later schemes or finalization. Only the finalizer emits the suite terminal trigger. Workers publish scheme-aware phase/result/failure payloads to `{runid}:ag_fields`, clear only the `ag_fields.nodb` cache before mutable hydration, and return JSON-serializable results.

Preflight completion uses additive `TaskEnum.run_ag_fields` (🌽) and checklist key
`ag_fields`. Serialized submissions and synchronous input/artifact mutations
clear the timestamp; the Stage 4 worker clears it again on start and stamps it
only after every sub-field WEPP run and the six-file interchange publication
succeed. The controller persists a separate interchange source signature, and
rq-engine reports Stage 4 complete only when the raw-run signature, interchange
signature, current workflow signature, source mapping hash, and last-written
manifest agree. `preflight2` additionally requires that completion be newer
than parent WEPP, watershed abstraction, landuse, soils, and climate.

Stage 5 intentionally does not add or overload a global `TaskEnum`: its completion,
failure, source signature, and terminal summary live in additive AgFields state.
Submitting or clearing Stage 5 does not invalidate the successful Stage 4 preflight
timestamp. Every AgFields job still shares the same per-run submit lock and live
job admission check.

Current state is an additive mapping keyed by `concept_1`, `concept_2`, and
`hybrid`. `get_watershed_integration_states()` hydrates all three independently;
clear operations accept the same exact identifier and remove only its fixed
scheme root. Historical singular state and the unscoped Concept 2 tree remain
read-only legacy evidence.

Each attempt builds in a server-named staging directory beside the fixed scheme
root and publishes only after the terminal manifest is durable. A failed retry
leaves the prior completed tree in place, persists
`manifest/last_attempt_failure.json`, and records
`error.preserved_previous_result` in scheme state. Scheme-scoped clear also
removes abandoned attempt/previous directories for that exact slug.

Concept 2 v1 derives parent and retained areas from the exactly aligned
`subwta.tif` and `sub_field_id_map.tif` grid, materializes legacy parent PASS files
from current prepared inputs inside the isolated tree, verifies climate content,
and delegates weighted serialization/closure to the owned native
`combine_weighted_hillslope_pass_files` API. Historical NoDb payloads default to
`not_run` without a migration write. Clearing rejects path escapes and symlinked
roots and never addresses baseline or independent sub-field artifacts.

> Scientific limitation: field water and sediment are injected at the parent
> outlet; downslope buffer, trapping, and runon effects are not represented.

AgFields mutations are single-flight per run. A short Redis submit lock closes enqueue races, live RQ status prevents overlapping build/plant/WEPP jobs, and synchronous boundary/schema/mapping/delete/clear routes return `agfields_job_active` while a job is queued or running. Successful boundary ingestion also retains the source basename for reload-safe UI reporting while continuing to store geometry under the canonical `fields.WGS.geojson` artifact name.

The state snapshot reports build provenance rather than asking clients to infer
it. Re-upload clears the schema selections; sub-fields are stale until
polygonization records the current boundary/schema signature; WEPP runs are
stale when either that signature or `rotation_lookup.tsv` changes. Starting a
raw run invalidates the interchange completion marker, so an interchange
failure cannot leave Stage 4 or the Stage 5 prerequisite falsely complete.
Historical runs without both signatures are conservatively incomplete until
rebuilt. Readiness covers observed climate year bounds, `dem/wbt/flovec.tif`,
and the parent `wepp/runs/p<wepp_id>.sol`/`.cli` pairs. `wepp.wepp_bin` hydrates
the Stage 4 executable selector and is persisted in `ag_fields.nodb` when the
queued run starts.

## Integration points

- **NoDb controllers**: uses `Climate`, `Landuse`, and `Watershed` (`wepppy.nodb.core`) for observed year range, landuse mapping, and Topaz/WEPP translator behavior.
- **Topography / Peridot**: calls `wepppy.topo.peridot.peridot_runner.run_peridot_wbt_sub_fields_abstraction` and `post_abstract_sub_fields`.
- **WEPP execution**: writes per-sub-field `.run` files using `run_templates/sub_field.template` and runs hillslopes via `wepp_runner.wepp_runner.run_hillslope`.
- **Optional catalog refresh**: best-effort calls into `wepppy.query_engine.update_catalog_entry` when available.
- **UI/analysis tooling**: the canonical `ag_fields/fields.WGS.geojson` and generated Parquet outputs are used by run explorers (for example, the embedded D-Tale service can register AgFields overlays when the module is importable).

## Developer notes

- **Locking**: `AgFields` is a `NoDbBase` controller; mutations are expected to occur under the NoDb lock. Many public methods acquire the lock internally (via `with self.locked():`) and persist on success.
- **GeoJSON requirements**:
  - must include a `field_id` column (validation fails otherwise)
  - preferably uses the exact projected UTM CRS of the project DEM so rasterization preserves project-grid precision
  - unlabeled coordinates matching the project UTM grid are recognized even when the GeoJSON driver defaults them to WGS84
  - WGS84 longitude/latitude and correctly declared alternate projected CRSs are reprojected to the DEM CRS; ambiguous projected coordinates are rejected rather than guessed
  - features must overlap the project DEM extent, or rasterization fails fast
- **Legacy artifact name**: `fields.WGS.geojson` is the established canonical basename, but boundary ingestion preserves the uploaded coordinate values until rasterization; the basename does not guarantee WGS84 coordinates.
- **Peridot prerequisites**: Peridot’s sub-field abstraction asserts `wd/dem/wbt/flovec.tif` and `wd/ag_fields/field_boundaries.tif` exist.
- **Sub-field flowpath schema**: Peridot writes `field_flowpaths.csv` with parent `topaz_id` and flowpath-record `flowpath_topaz_id`. WEPPpy normalizes that table to `ag_fields/sub_fields/field_flowpaths.parquet` and keeps compatibility for historical CSVs where pandas read the old duplicate header as `topaz_id.1`.
- **WEPP executable**: `[ag_fields] bin` supplies the new-project default independently of `[wepp] bin`; `ag-fields.cfg` uses `wepp_260714`, whose synchronized hillslope management capacity is 32. Historical NoDb payloads without `_wepp_bin` fall back to the parent Wepp controller until the user selects an AgFields executable.
- **Concurrency**: `run_wepp_ag_fields()` runs sub-fields in a `ThreadPoolExecutor`. The UI uses automatic sizing; API callers may still pass `max_workers`.

## Further reading

- `wepppy/weppcloud/routes/usersum/weppcloud/ag_field-mod.md` (WEPPcloud-focused notes and example run layouts)
- `wepppy/topo/peridot/peridot_runner.py` (Peridot sub-field abstraction details)
