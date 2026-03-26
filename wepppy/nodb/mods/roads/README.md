# Roads NoDb Controller

> Converts uploaded road linework into Roads-scoped WEPP runs by segmenting inslope roads, mapping them to receiving hillslopes/channels, and regenerating Roads results and reports.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb controller conventions and [specification.md](specification.md) for the full Roads phase-1 contract.

## Overview

`wepppy.nodb.mods.roads` is the phase-1 Roads integration for WEPPcloud runs that already have a baseline WEPP watershed solution. It lets a user upload roads as GeoJSON, inspect discovered feature properties, map those properties to Roads semantics, prepare monotonic road segments, and then run a Roads-specific watershed update.

The module is centered on the run-scoped `Roads` NoDb controller in [roads.py](roads.py). It persists state to `roads.nodb`, stages uploaded GeoJSON under `roads/`, writes prepared segment artifacts under `wepp/roads/segments/`, and writes Roads run outputs under `wepp/roads/output/`.

Primary users are WEPPcloud operators and analysts who need to test how inslope roads change runoff, sediment, and watershed results without modifying the baseline run. Primary developers are people working in NoDb, Roads UI/routes, and Roads RQ orchestration.

## Workflow

1. Run baseline WEPP for the project.
2. Enable the `Roads` mod from the WEPPcloud run page.
3. Upload a Roads GeoJSON file.
4. Review the discovered attribute catalog and map GeoJSON fields to `design`, `surface`, and `traffic`.
5. Choose fallback values for `surface` and `traffic`.
6. Click `Prepare Segment Candidates` to create monotonic segments and low-point attribution artifacts.
7. Click `Run WEPPcloud Roads` to execute Roads segment runs, combine pass files, rerun the Roads-scoped watershed, and regenerate Roads report resources.
8. Review Roads status, Roads-scoped report links, regenerated resources, and diagnostics.

## Components

| Component | Purpose |
| --- | --- |
| [roads.py](roads.py) | Run-scoped `Roads(NoDbBase)` controller, upload/config/query surface, prepare/run orchestration, artifact summaries |
| [monotonic_segments.py](monotonic_segments.py) | Splits linework into monotonic segments and attributes low points to channels/hillslopes |
| `legacy_templates/soils/` | Legacy-derived single-OFE road soil templates |
| `legacy_templates/managements/` | Legacy-derived road management templates used during segment WEPP runs |
| [specification.md](specification.md) | Full implementation contract, artifact layout, mapping rules, and phase-1 assumptions |

## GeoJSON Preparation

### Required format

Roads uploads must be:

- GeoJSON `FeatureCollection`
- containing `LineString` or `MultiLineString` features only
- small enough to fit the Roads upload limit (`max_upload_mb`, default `50`)
- described in the run input CRS or with a valid GeoJSON `crs.properties.name`

The controller only inspects top-level `feature.properties` keys for attribute discovery and mapping. Nested property-path mapping is out of scope for this phase.

### Eligible road designs

Only the following designs are eligible for inslope segment processing in phase 1:

- `Inslope_bd`
- `Inslope_rd`

If a feature maps to any other design, it can remain in the uploaded GeoJSON but it will not become an eligible Roads segment for prepare/run work.

### Recommended properties

The Roads UI can map arbitrary top-level property names, but these are the canonical semantics:

| Semantic | Typical values | Notes |
| --- | --- | --- |
| `design` | `Inslope_bd`, `Inslope_rd` | Required for prepare-stage eligibility |
| `surface` | `gravel`, `paved`, `asphalt`, `dirt`, `native` | Aliases normalize to `gravel` or `paved` |
| `traffic` | `high`, `low`, `none` | `no` and `notraffic` normalize to `none` |

If `surface` or `traffic` is missing or invalid:

- when a mapping is set, Roads falls back to the user-selected default value
- when a mapping is unset, Roads falls back to legacy property keys and then to the configured default

### Recommended authoring rules

- Put the road attributes you care about directly on `feature.properties`.
- Use one feature per logical road segment when possible.
- Keep the road centerline geometry clean; self-intersections and noisy vertex order make monotonic splitting harder to interpret.
- Use consistent casing for enumerated values even though the controller normalizes many aliases.
- If you already know the Roads semantics, include explicit `design`, `surface`, and `traffic` fields to reduce UI mapping work.

### Minimal example

```json
{
  "type": "FeatureCollection",
  "crs": {
    "type": "name",
    "properties": {
      "name": "EPSG:4326"
    }
  },
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [-116.0, 45.0],
          [-116.0005, 45.0005]
        ]
      },
      "properties": {
        "ROADTYPE": "Inslope_bd",
        "SURF_CLASS": "asphalt",
        "TRAF_LEVEL": "low"
      }
    }
  ]
}
```

In the Roads UI, that upload would typically be mapped as:

- `design` -> `ROADTYPE`
- `surface` -> `SURF_CLASS`
- `traffic` -> `TRAF_LEVEL`

## User Interface Guide

### Prerequisites on the run page

Before Roads is useful, the run must already have:

- a baseline WEPP solution
- a WBT-based delineation backend

Roads is backend-gated. Non-WBT runs cannot enable the mod.

### Upload and attribute discovery

After upload, the Roads control shows:

- the uploaded GeoJSON path and feature count
- a discovered attribute catalog
- sample values for discovered fields
- persisted mapping controls for `design`, `surface`, and `traffic`

This discovery catalog is specific to the current upload. Uploading a new file resets stale mapping state and then attempts best-effort remapping by exact field-name match.

### Mapping controls

The Roads control exposes five mapping-related controls:

| Control | Purpose |
| --- | --- |
| `Design field` | Selects the field used to decide inslope eligibility during prepare and run |
| `Surface field` | Selects the primary surface field |
| `Traffic field` | Selects the primary traffic field |
| `Surface fallback value` | Chooses `gravel` or `paved` when mapped surface is missing/invalid |
| `Traffic fallback value` | Chooses `high`, `low`, or `none` when mapped traffic is missing/invalid |

Click `Apply Attribute Mapping` after changing the mapping/default controls. This persists the settings to the run-scoped Roads controller and clears stale prepare/run state.

### Prepare Segment Candidates

`Prepare Segment Candidates` runs the deterministic preprocessing stage. It:

- splits the uploaded linework into monotonic segments
- orients segments from high point to low point
- identifies low points
- attributes channel and receiving-hillslope Topaz IDs for eligible inslope segments
- writes segment preparation artifacts and summary diagnostics

The prepare stage is where bad design mapping shows up first. If the mapped `design` field does not resolve to `Inslope_bd` or `Inslope_rd`, the feature will not become an eligible Roads segment.

### Run WEPPcloud Roads

`Run WEPPcloud Roads` uses the latest prepared segments and:

- builds single-OFE road segment runs from the legacy-derived soil/management templates
- executes segment WEPP runs
- injects segment pass effects into watershed routing
- runs the Roads-scoped watershed update
- regenerates Roads-scoped report resources under `wepp/roads/output/interchange/`

If the upload or Roads parameters changed after prepare, the run stage requires a fresh prepare cycle.

## Results and Artifacts

### What the user sees

After a successful Roads run, the WEPPcloud Roads UI and Roads results page expose:

- controller status and run summary state
- Roads-scoped report links
- regenerated resource inventory
- diagnostics JSON for `roads_status` and `roads_summary`

The Roads results summary page is rendered from [summary.htm](../../../weppcloud/templates/reports/roads/summary.htm).

### Important output locations

| Path | Purpose |
| --- | --- |
| `roads/roads.uploaded.geojson` | Staged copy of the uploaded source GeoJSON |
| `wepp/roads/roads.log` | Roads lifecycle and execution log |
| `wepp/roads/segments/roads.inslope.monotonic.geojson` | Prepared monotonic segment GeoJSON |
| `wepp/roads/segments/roads.inslope.low_points.geojson` | Low-point features for prepared segments |
| `wepp/roads/segments/roads.inslope.summary.json` | Prepare-stage summary diagnostics |
| `wepp/roads/segments/roads.segment.pass.manifest.json` | Segment run and pass-combination manifest |
| `wepp/roads/output/interchange/README.md` | Roads-scoped regenerated resource manifest |
| `wepp/roads/output/interchange/roads_segment_loss_summary.parquet` | Segment-level Roads loss summary |

### Report links

When regeneration succeeds, Roads results can include links such as:

- Watershed Loss Summary
- Return Periods
- Yearly Water Balance
- Daily Streamflow
- Average Annual Water Balance
- GL Dashboard
- Storm Event Analyzer
- Road Segment Loss Summary (`Parquet` and on-demand `CSV`)

These links are gated by the presence of Roads-scoped regenerated resources. If a required output is missing, the link is hidden rather than routed to stale baseline content.

## Configuration

The controller persists Roads settings in `roads_params`.

| Parameter | Default | Description |
| --- | --- | --- |
| `input_crs` | `EPSG:4326` | Input CRS used when the upload does not provide a GeoJSON CRS block |
| `sample_step_m` | `null` | Optional segment sampling step for profile evaluation |
| `tolerance_m` | `0.5` | Monotonic segmentation tolerance |
| `soil_texture_default` | `loam` | Default soil texture when no segment override is present |
| `surface_default` | `gravel` | Fallback surface value used by Roads mapping/runtime logic |
| `traffic_default` | `low` | Fallback traffic value used by Roads mapping/runtime logic |
| `rfg_pct_default` | `15.0` | Default rock fragment percentage |
| `road_width_m_default` | `4.0` | Default road width for generated single-OFE profiles |
| `max_upload_mb` | `50` | Maximum upload size for Roads GeoJSON |
| `attribute_field_map.design` | `null` | User-selected field for design resolution |
| `attribute_field_map.surface` | `null` | User-selected field for surface resolution |
| `attribute_field_map.traffic` | `null` | User-selected field for traffic resolution |

Attribute discovery profiling is also configurable through the Roads params contract:

- `attribute_discovery_profile_feature_limit`
- `attribute_discovery_value_preview_limit`
- `attribute_discovery_value_max_chars`

## Key Concepts

| Term | Meaning |
| --- | --- |
| `eligible segment` | A prepared monotonic segment whose design resolves to an in-scope inslope design |
| `low point` | The downslope end of an oriented monotonic road segment |
| `mapped segment` | An eligible segment whose low point was attributed to both channel and receiving hillslope context needed for Roads execution |
| `Roads-scoped output` | A regenerated report/query dataset under `wepp/roads/output/` that does not overwrite baseline `wepp/output/` |

## Developer Notes

### Public module surface

The package exports:

- `Roads`
- `MonotonicConversionSummary`
- `convert_geojson_file_to_monotonic_segments`
- `convert_geojson_to_monotonic_segments`
- `convert_geojson_to_monotonic_segments_with_low_points`

See [__init__.py](__init__.py) for the canonical export list.

### Integration points

- NoDb controller: [roads.py](roads.py)
- Segment utility: [monotonic_segments.py](monotonic_segments.py)
- WEPPcloud routes: [roads_bp.py](../../../weppcloud/routes/nodb_api/roads_bp.py)
- Run-page control: [roads_pure.htm](../../../weppcloud/templates/controls/roads_pure.htm)
- Frontend controller: [roads.js](../../../weppcloud/controllers_js/roads.js)

### Validation entry points

Use these focused checks when changing Roads behavior:

```bash
wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1
wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1
wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1
wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
wctl run-npm test -- roads
wctl run-npm lint
```

For final handoff, run:

```bash
wctl run-pytest tests --maxfail=1
```

## Operational Notes

- Roads persists to `roads.nodb` and follows standard NoDb locking semantics.
- Parameter changes and new uploads clear stale prepare/run summaries and return the controller to `idle`.
- Warning diagnostics are summarized in prepare/run outputs when mapped fields are missing or invalid.
- Roads requires baseline WEPP outputs and does not replace the baseline `wepp/output/` dataset tree.

## Further Reading

- [specification.md](specification.md)
- [NoDb AGENTS.md](../../AGENTS.md)
- [Roads routes in NoDb API](../../../weppcloud/routes/nodb_api/README.md)
- [Roads GeoJSON attribute mapping work package](../../../../docs/work-packages/20260326_roads_geojson_attribute_mapping/package.md)
