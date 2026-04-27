# Data Table ID Standardization

> **See also:** [AGENTS.md](../../AGENTS.md) Notes for Next Pass section regarding ID standardization and migrations.

## Why
- Align all parquet assets on numeric join keys (`wepp_id`, `topaz_id`) using nullable `Int32`.  
- Match interchange outputs and simplify analytics/query-engine joins.  
- Preserve GeoJSON/TopoJSON semantics (numeric values) while avoiding duplicate string/int columns.  
- Provide clear migration notes for legacy runs that still emit `"TopazID"`/`"WeppID"` strings.

## Out of Scope
- GeoPackage export rewrite (`gpkg_export.py`). Future work will expose a configurable export pipeline where users choose fields, units, and formats.

## Target Datasets
| Dataset | Writer(s) | Required changes | Key consumers to audit |
| --- | --- | --- | --- |
| `watershed/hillslopes.parquet` | Peridot `abstract_watershed` / `wbt_abstract_watershed` + `peridot_runner.post_abstract_watershed` normalization | Peridot writes base parquet directly; WEPPpy post-step enforces `wepp_id`, `topaz_id` Int32 and drops uppercase legacy variants. Contract now includes additive side-length provenance fields: `length_estimate_mode`, `length_area_over_channel`, `length_edge_median`. | `duckdb_agents.get_watershed_*`, reports (`loss_hill_report`, `average_annuals`), query engine fixtures |
| `watershed/channels.parquet` | same as above | Peridot writes base parquet directly; WEPPpy post-step enforces `wepp_id`, `topaz_id`, `chn_enum` Int32 | hydrology exports, Omni mods, query engine |
| `watershed/flowpaths.parquet` | same as above | Peridot writes flowpaths parquet when enabled; WEPPpy normalizes `topaz_id`, `fp_id` Int32 when present | `Watershed.fps_summary`, consumers of legacy flowpath metadata |
| `ag_fields/sub_fields/*.parquet` | `post_abstract_sub_fields` | emit Int32 ids; normalize `field_flowpaths.parquet` to parent `topaz_id` plus `flowpath_topaz_id` | landuse editing tools, agronomic summaries |
| `landuse/landuse.parquet` | `Landuse.dump_landuse_parquet` | output `topaz_id`, `wepp_id` Int32 | query presets, reports, DuckDB agents, R tooling |
| `soils/soils.parquet` | `Soils.dump_soils_parquet` | same as above | same consumers as landuse |
| RAP/ancillary tables | dataset-specific writers | audit/cast numeric ids | RAP analytics, dashboards |

## Geo/JSON Assets
- `topaz.py`, `wbt_topaz_emulator.py`, `watershed_abstraction.support`: keep property names (`TopazID`, `WeppID`) but guarantee numeric values.
- JS map controllers and R templates already treat values numerically, so no property rename required.

## Compatibility Layer
1. Introduce helpers (likely in `duckdb_agents` or dataframe loaders) that detect legacy uppercase string ids and cast them to new int columns.  
2. During transition, readers prefer lowercase Int32 columns but fall back gracefully.  
3. Add validation to run activation/build steps to confirm new parquet assets comply.

## Peridot Watershed Contract (Current)
- Canonical direct Peridot output behavior is maintained in the
  [Peridot watershed output contract](https://github.com/wepp-in-the-woods/peridot/blob/main/docs/contracts/watershed-output-contract.md).
  This section describes WEPPpy post-processing expectations layered on top of
  direct Peridot CLI outputs.
- Peridot now emits watershed parquet outputs directly (`hillslopes.parquet`, `channels.parquet`, optional `flowpaths.parquet`) and generates `watershed/README.md` with run flags, file manifest, and schema summary.
- `post_abstract_watershed()` is parquet-first for new runs and uses an explicit legacy CSV fallback path only when a required parquet file is missing.
- After WEPPpy post-processing adds canonical derived columns, `post_abstract_watershed()` refreshes `watershed/README.md` manifest/schema sections so documented contract matches final on-disk parquet outputs.
- Legacy migration for historical runs with only `watershed/*.csv` remains supported via `migrate_watershed_outputs()` / `migrate_watersheds()`.
- Side hillslopes (`topaz_id % 10 in {2,3}`) now cap length using `min(area/channel_length, median edge/source length)` and preserve area by recomputing width; hillslope rows expose mode/candidate provenance through additive fields (`length_estimate_mode`, `length_area_over_channel`, `length_edge_median`).
- Length provenance semantics:
  - `length_estimate_mode` is stable and currently emits: `top_edge_median`, `top_representative_flowpath`, `side_edge_median_capped`, `side_area_over_channel`, `side_area_over_channel_no_edge`.
  - `length_area_over_channel` records the side candidate `L_area`; top/source rows emit NaN.
  - `length_edge_median` records the edge/source median candidate when available; unavailable paths emit NaN.

## Testing & Docs
- Update unit/integration tests to assert int32 schemas. Regenerate fixtures referencing legacy casing.  
- Add regression coverage for mixed legacy/new datasets to ensure compatibility layer works.  
- Communicate change in release notes and add migration instructions for historical runs.

## Status Checklist
- [x] Watershed parquet writers updated  
- [x] Watershed migration
- [x] wbt geojson assets
- [x] wbt migration
- [x] Landuse parquet writers updated  
- [x] Landuse migration
- [x] Soils parquet writers updated  
- [x] Soils migration 
- [x] DuckDB/query-engine/report consumers migrated  
- [x] Compatibility helper merged *(schema normalization required; no automatic coercion retained)*  
- [ ] Tests/fixtures refreshed  
- [ ] Documentation + release note published
