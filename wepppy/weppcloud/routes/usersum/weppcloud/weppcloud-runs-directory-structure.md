# WEPPcloud Runs Directory Structure

WEPPcloud projects are file-based. Each run stores its setup, derived geometry, model inputs, and model outputs in folders and `.nodb` files inside one run directory.

## What This Page Helps You Do

Use this page when you need to locate the main files in a run for browsing, download, QA, troubleshooting with support, or advanced analysis.

Not every run contains every folder. Some files appear only after delineation, landuse and soil builds, WEPP execution, Omni scenario work, or optional modules. Treat the run directory as read-only unless you are intentionally doing advanced support or developer work.

## Key Idea

- `.nodb` files hold the saved project state that WEPPcloud uses for modeling. They act like the run's working memory: project settings, map choices, build status, and module settings are stored there so the interface knows what has already been set up.
- `dem/`, `landuse/`, `soils/`, and `watershed/` hold derived inputs and geometry.
- `wepp/runs/` holds WEPP input files.
- `wepp/output/interchange/` holds Parquet outputs used by dashboards, reports, and query tools.

## Common `.nodb` Files

Core `.nodb` files are part of normal project setup. Additional module `.nodb` files may also be present when the interface or configuration enables those capabilities.

| File | Plain-language purpose |
| --- | --- |
| `ron.nodb` | The main project record. It stores the run identity, interface choices, map information, and which major capabilities are active. |
| `watershed.nodb` | Watershed delineation and hillslope or channel setup information used by the watershed tools. |
| `topaz.nodb` | Legacy TOPAZ terrain and delineation information when a TOPAZ-style workflow is used. |
| `landuse.nodb` | Landcover and management choices used to build landuse for the run. |
| `soils.nodb` | Soil-source choices and soil-build settings used for the run. |
| `climate.nodb` | Climate-source selections, station or gridded settings, and climate-build information. |
| `wepp.nodb` | WEPP run settings, run status, and output-related state. |
| `disturbed.nodb`, `omni.nodb`, `observed.nodb`, and similar files | Module-specific settings and results for optional workflows enabled in the project. |

## Common Folders and Files

Typical runs often look broadly like this:

```text
<run>/
  ron.nodb
  watershed.nodb
  landuse.nodb
  soils.nodb
  climate.nodb
  wepp.nodb
  dem/
    wbt/ or topaz/
  landuse/
    landuse.parquet
  soils/
    soils.parquet
  watershed/
    hillslopes.parquet
    channels.parquet
  wepp/
    runs/
    output/
      interchange/
  _pups/
    omni/
      scenarios/
      contrasts/
```

## Key Files and Folders

| Relative path | What it usually contains | Why users look there |
| --- | --- | --- |
| `dem/wbt/subcatchments.geojson` | WBT hillslope polygons | Map geometry for hillslopes and subcatchments |
| `dem/wbt/channels.geojson` | WBT channel lines | Channel network geometry |
| `dem/topaz/SUBCATCHMENTS.JSON` | TOPAZ-style hillslope polygons | TOPAZ equivalent of the WBT subcatchments file |
| `dem/topaz/CHANNELS.JSON` | TOPAZ-style channel lines | TOPAZ equivalent of the WBT channels file |
| `landuse/landuse.parquet` | Hillslope landuse and management assignments | Check how land cover and management were parameterized |
| `soils/soils.parquet` | Hillslope soil properties and WEPP soil attributes | Check soil assignment and derived soil parameters |
| `watershed/hillslopes.parquet` | Hillslope attributes and join keys | Join geometry, landuse, soils, and WEPP outputs |
| `watershed/channels.parquet` | Channel attributes | Review channel properties when available |
| `wepp/runs/` | WEPP input decks such as `.sol`, `.slp`, `.man`, `.cli`, and `.run` files | Inspect the actual files passed to WEPP |
| `wepp/output/interchange/` | Parquet outputs such as `H.wat.parquet`, `H.soil.parquet`, `loss_pw0.hill.parquet`, and `loss_pw0.out.parquet` | Browse or analyze model results |
| `_pups/omni/scenarios/<name>/` | Scenario-specific copies or derived outputs | Compare alternate scenario runs inside one project |
| `_pups/omni/contrasts/<id>/` | Contrast-specific outputs | Review contrast comparisons when Omni Contrasts are used |

## Where To Start For Common Questions

| If you want to find... | Start here |
| --- | --- |
| Hillslope polygons for mapping | `dem/wbt/subcatchments.geojson` or the TOPAZ equivalent |
| Channel geometry | `dem/wbt/channels.geojson` or the TOPAZ equivalent |
| The hillslope join table used by many tools | `watershed/hillslopes.parquet` |
| Landuse assignments | `landuse/landuse.parquet` |
| Soil assignments | `soils/soils.parquet` |
| WEPP-ready input files | `wepp/runs/` |
| Dashboard-friendly WEPP outputs | `wepp/output/interchange/` |

## Limits and Common Mistakes

- WBT and TOPAZ runs do not use identical filenames. The WBT files are typically lowercase GeoJSON files, while TOPAZ files commonly use uppercase JSON names.
- Some files do not exist until the relevant build step has completed.
- Omni scenario and contrast folders appear only when those workflows are used.
- Older or migrated runs may still contain legacy root-level sidecar files, but the current canonical paths are directory-based paths such as `landuse/landuse.parquet` and `soils/soils.parquet`.
- Editing `.nodb`, GeoJSON, or Parquet files by hand can desynchronize the project from the WEPPcloud interface.

## Related Docs

- [NoDb Platform Overview](../../../../nodb/README.md)
- [WEPP Interchange Outputs](wepp-interchange.md)
- [Omni Scenarios and Contrasts](../../../../nodb/mods/omni/ENDUSER.md)
- [Profile JWT Dataset Access (Python/R)](profile-jwt-dataset-access-python-r.md)
