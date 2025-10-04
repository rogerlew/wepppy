# Sub-Fields Abstraction Utility (WBT) — Specification & Implementation Plan

## Background
- WEPPcloud's AgFields workflow needs slope profiles for agricultural sub-fields that sit within existing WEPP watershed delineations.
- Current peridot tools (`abstract_watershed`, `wbt_abstract_watershed`) generate hillslope abstractions per TOPAZ/WBT subcatchment, but they do not split those subcatchments by management field boundaries.
- The Hangman "dumbfounded-patentee" run (located at `/wc1/runs/du/dumbfounded-patentee/`) already prepares `ag_fields/field_boundaries.tif` and relies on Whitebox Tools data (`dem/wbt/*`). Step 3 of its dev notes explicitly calls for a peridot program to abstract sub field hillslopes.
- We want to phase out TOPAZ-specific functionality; the new tool will be WBT-only and should encourage users to adopt the Whitebox backend.

## Objectives
1. Provide a CLI binary within peridot (e.g. `sub_fields_abstraction`) that consumes a WEPPcloud run directory built with the WBT backend.
2. Derive "sub-fields" by intersecting the Whitebox `subwta.tif` (hillslope IDs) with the rasterised field-boundary map from `ag_fields/field_boundaries.tif`.
   - Treat the field ID as the major key and the subcatchment ID as the minor key.
   - Ignore channel cells (TOPAZ IDs ending with `4`).
   - Optionally filter out very small sub-fields by area threshold (m²).
3. For every sub-field, compute representative flowpaths and slope profiles:
   - Reuse peridot's existing flowpath walkers and slope aggregation logic where possible.
   - Output WEPP-ready `.slp` files plus subflow files to mirror the existing `flowpaths` outputs in the projects `ag_fields/slope_files` directory.
4. Emit metadata CSVs that mirror the current hillslope/flowpath tables but prepend a `field_id` column (and expose the parent `subwta_id`).

Non-goals/requirements:
- No channel abstraction or channel metadata generation.
- No support for legacy TOPAZ rasters or `.ARC` formats.
- No updates (yet) to the Python `AgFields` module; this spec focuses on the peridot side.
- No persisted intersection raster; the subwta/field boundary intersection is derived on-the-fly similar to the existing `mofe_map` workflow.

## Inputs & Preconditions
- Working directory (`wd`) supplied on the CLI must contain at minimum:
  - `dem/wbt/subwta.tif`, `relief.tif`, `flovec.tif`, `fvslop.tif`, `taspec.tif`, `netw.tsv`.
  - `ag_fields/field_boundaries.tif` rasterised on the same grid as `subwta.tif` (same extents, resolution, projection).
- Field IDs stored in `field_boundaries.tif` are positive integers. Zero or nodata values indicate no field and are skipped.
- Whitebox D8 directions remain encoded as in existing `wbt_abstract_watershed`; we keep using `remap_whitebox_d8_to_topaz` to align with TOPAZ directions before walking flowpaths.

## Outputs
- Directory structure rooted at `ag_fields/sub_fields/` (created / refreshed each run):
  - `lookups/sub_fields.csv` – mapping of `sub_field_id,field_id,subwta_id,area_m2,pixel_count`.
  - `slope_files/field_{field_id}_{subwta_id}.slp` – representative slope profiles per sub-field (no zero padding required).
  - `slope_files/flowpaths/field_{field_id}_{subwta_id}.slps` – optional subpath profiles concatenated to optimize inode count when requested.
  - `metadata/sub_fields.csv` – columns `[field_id, subwta_id, sub_field_id, slope_scalar, length, width, direction, aspect, area, elevation, centroid_px, centroid_py, centroid_lon, centroid_lat]`.
  - `metadata/sub_field_flowpaths.csv` – same schema as the current flowpath metadata with `field_id` and `sub_field_id` inserted ahead of `topaz_id/fp_id` (we keep `subwta_id` for traceability).

Existing `ag_fields/slope_files/` can contain other artifacts later; keeping sub-field outputs in a dedicated subtree avoids collisions.

## High-Level Algorithm
1. **Setup**
   - `env::set_current_dir(wd)` (mirrors existing binaries).
   - Build/clean `ag_fields/sub_fields/` output directories. Avoid deleting unrelated `plant_files` etc.
2. **Load rasters**
   - Read `subwta.tif`, `relief.tif`, `flovec.tif`, `fvslop.tif`, `taspec.tif` as before (with `Raster::<i32>` / `<f64>`).
   - Read and validate `field_boundaries.tif` (as `Raster::<i32>`).
   - Assert matching `width`, `height`, `geo_transform`, and optional `proj4`; abort with descriptive error if mismatched.
3. **Build sub-field index**
   - Traverse all pixels once, skipping when:
     - `field_id <= 0` or equals the raster's `no_data`.
     - `subwta_id % 10 == 4` (channel).
   - For remaining pixels, create key `(field_id, subwta_id)`.
   - Maintain `HashMap<(i32, i32), Vec<usize>>` (or `HashMap<(i32, i32), SubFieldAccumulator>`) capturing pixel indices and counts. No persistent raster is produced.
   - Compute pixel count and area (`count * cellsize²`) per combination.
   - Filter combos below `sub_field_min_area_threshold_m2` threshold (configurable CLI option; default 0 -> keep all). Drop them from maps and zero out those pixels in the output raster.
   - Assign each remaining combo a new contiguous `sub_field_id` (1..N). Update the raster data map accordingly.
4. **Generate flowpaths per sub-field**
   - For each retained `(field_id, subwta_id)` combination:
     - Store its `HashSet<usize>` for O(1) membership tests.
     - Walk flowpaths restricted to that mask: adapt `walk_flowpaths`/`walk_flowpath` to accept a closure or optional mask so that flow directions stop when the next cell is outside the mask even if it shares the same `subwta_id`.
     - Aggregate slopes via a new `FlowpathCollection::abstract_subfield(...)` helper (can reuse large parts of `abstract_subcatchment` but takes precomputed mask + parent channel information to compute width/direction).
     - Capture the resulting representative `FlowPath` plus underlying `FlowpathCollection` of subflows for metadata export.
   - Use `rayon` to parallelise across sub-fields (bounded by CLI `--ncpu` similar to existing binaries).
5. **Write artifacts**
   - `csv::Writer` for lookup & metadata tables (ASCII output to remain WEPP-compatible).
   - Use existing `FlowPath::_write_slp` machinery for slope files; provide custom wrappers that accept a desired filename stem instead of hardcoding `hill_<topaz_id>.slp`.
   - Flowpath `.slp` files are optional but required per request (“we do need to create the flowpath files”). Mirror `write_subflow_slps`, but prefix filenames with `sub_field_...` and include `field_id`.
   - Ensure directories exist before writing (use `std::fs::create_dir_all`).
6. **Return**
   - Bubble up IO errors to CLI; log summary counts (`#sub_fields retained`, thresholds, output paths).

## CLI Definition
Add a new binary `src/bin/sub_fields_abstraction.rs` registered in `Cargo.toml`. Proposed Clap options:

| Flag | Default | Description |
|------|---------|-------------|
| `path_to_wd` (positional) | — | WEPPcloud run directory root. |
| `--ncpu/-n` | `4` | Rayon thread pool size. |
| `--max-points/-m` | `99` | Max polyline vertices per slope profile. |
| `--clip-hillslopes` | `false` | Whether to apply length clipping. |
| `--clip-hillslope-length` | `300.0` | Maximum hillslope length when clipping enabled. |
| `--sub-field-min-area-threshold-m2` | `0.0` | Drop sub-fields smaller than this area. |
| `--field-raster` | `ag_fields/field_boundaries.tif` | Override path to the rasterised field IDs. |
| `--output-dir` | `ag_fields/sub_fields` | Allow alternate destination (optional; default keeps convention). |

All other behaviour mirrors `wbt_abstract_watershed` (e.g., thread pool initialisation).

## Implementation Details
### 1. Data Structures
- `SubFieldKey { field_id: i32, subwta_id: i32 }` – helper struct with `Eq/Hash` for map keys.
- `SubFieldRecord` containing:
  - `id: i32` (sequential sub_field_id),
  - `key: SubFieldKey`,
  - `indices: HashSet<usize>`,
  - `flowpaths: FlowpathCollection` (raw per-pixel flowpaths),
  - `summary: FlowPath` (representative hillslope),
  - `area_m2: f64`.
- `SubFieldOutputs` struct to stage final data before writing (filenames, metadata rows).

### 2. Raster masking utilities
- Introduce helper `build_sub_field_masks(field_raster, subwta_raster, min_area_m2) -> (Vec<SubFieldRecord>, LookupRows)` inside `watershed_abstraction.rs` or a new module (e.g., `sub_fields.rs`).
- The helper returns deduplicated records ready for flowpath generation.

### 3. Flowpath walkers
- Add masked variants:
  - `walk_flowpaths_masked(topaz_id, mask: &HashSet<usize>, subwta, relief, flovec, fvslop, taspec)` -> `FlowpathCollection`.
  - `walk_flowpath_masked` modifies the main loop to break when `!mask.contains(&next_indx)` even if the raw `subwta` matches.
- Reuse existing logic for slope/elevation interpolation, ensuring `indices_hash` initialised with mask membership to avoid infinite loops.

### 4. Sub-field abstraction
- Create `FlowpathCollection::abstract_subfield(mask_indices, field_id, subwta, taspec, channels)` by adapting `abstract_subcatchment`:
  - Compute area using `mask_indices.len()` not `subwta.indices_of`.
  - Keep original `topaz_id` for orientation decisions.
  - When referencing channels, look up `channels.get_fp_by_topaz_id(chn_id)` exactly as before; we still rely on the parent channel width.
  - Weighted slope aggregation, aspect, centroid logic can be reused (with centroid derived from `subwta.centroid_of(&mask_indices)` since it only needs the indices themselves).
  - Set `FlowPath.fp_id` to the assigned `sub_field_id` (or maintain `field_id`) so file naming stays unique.

### 5. Output writers
- Implement dedicated writers instead of reusing `write_slps` to control filenames and metadata order:
  - `write_sub_field_slps(sub_fields: &[SubFieldRecord], out_dir, max_points, clip_hillslopes, clip_length)` – uses `FlowPath::write_slp` with filenames `sub_field_{field}_{subwta}.slp`.
  - `write_sub_field_flowpath_slps` – iterate over each `FlowpathCollection` subflow and output `sub_field_{field}_{subwta}_fp_{fpid}.slp`.
  - `write_sub_field_metadata` and `write_sub_field_flowpath_metadata` to produce the CSVs with the augmented headers.
- Ensure ASCII encoding (Rust `csv` already writes UTF-8; values are numeric so ASCII-safe).

### 6. CLI binary wiring
- New binary mirrors the structure of `abstract_watershed.rs`:
  1. Parse options via Clap derive.
  2. Build global Rayon thread pool.
  3. Call `wbt_sub_fields_abstraction(...)` with parsed arguments.
  4. Handle errors by printing to `stderr` and returning non-zero exit codes (Clap default behaviour under `anyhow::Result` or manual `Result`).

### 7. Cargo updates
- Add to `[ [bin] ]` section in `Cargo.toml`:
  ```toml
  [[bin]]
  name = "sub_fields_abstraction"
  path = "src/bin/sub_fields_abstraction.rs"
  ```
- Ensure existing features (`bindgen`) continue to gate GDAL dependencies as before.

## Error Handling & Logging
- Validate mandatory files upfront; provide actionable error messages (missing field raster, mismatched dimensions, etc.).
- Report when combinations are dropped due to area threshold; include counts + threshold in summary logging (`println!` or `log::info!`).
- Guard against empty results (if no sub-fields survive filtering, exit gracefully with message and still emit empty lookup/metadata files for consistency).

## Performance Considerations
- Hashing `indices` per sub-field can be memory intensive; convert `Vec<usize>` to `HashSet<usize>` lazily (only before flowpath walking) and free when finished (records can drop the set once flowpaths are computed).
- Use `rayon` for per sub-field processing; number of sub-fields per watershed is expected to be manageable (fields << total pixels).
- Reuse computed `FlowpathCollection` for channel network (`walk_channels`) once; no need to recompute per sub-field.

## Testing Strategy
- **Unit tests** (Rust):
  - Verify `build_sub_field_masks` correctly filters channels, honours area thresholds, and assigns sequential IDs.
  - Validate `walk_flowpath_masked` stops at field boundaries via synthetic 5x5 raster fixtures.
- **Integration test**:
  - Prepare a small WBT fixture under `tests/fixtures/sub_fields/` with:
    - `dem/wbt` rasters trimmed to 20x20.
    - `ag_fields/field_boundaries.tif` with two fields overlapping two subcatchments.
  - Run the new binary with `Command::new` in a test, then assert on output files, metadata rows, and count of slope files.
- **Manual validation** (documented in dev-notes): run against `/wc1/runs/du/dumbfounded-patentee/` and confirm outputs integrate with `AgFields` workflow.

## Open Questions / Follow-ups
1. Confirm desired naming scheme for slope files with stakeholders (`sub_field_{field}_{subwta}.slp` vs. zero padded).
2. Should we emit GeoJSON copies for GIS inspection? (Not part of initial scope but easy to add later.)
3. Determine default `min_area_m2`; spec uses 0 but we may want a sensible positive default once requirements solidify.
4. Future work: extend `AgFields` Python to invoke this binary and consume the outputs.
