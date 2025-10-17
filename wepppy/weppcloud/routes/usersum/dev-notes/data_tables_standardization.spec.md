# Data Table ID Standardization

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
| `watershed/hillslopes.parquet` | `peridot_runner.post_abstract_watershed`, WBT runner | write `wepp_id`, `topaz_id` (Int32); drop uppercase string variants | `duckdb_agents.get_watershed_*`, reports (`loss_hill_report`, `average_annuals`), query engine fixtures |
| `watershed/channels.parquet` | same as above | ensure `wepp_id`, `topaz_id`, `chn_enum` Int32 | hydrology exports, Omni mods, query engine |
| `watershed/flowpaths.parquet` | same as above | cast `topaz_id`, `fp_id` to Int32 | `Watershed.fps_summary`, consumers of flowpath metadata |
| `ag_fields/sub_fields/*.parquet` | `post_abstract_sub_fields` | emit Int32 ids | landuse editing tools, agronomic summaries |
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
