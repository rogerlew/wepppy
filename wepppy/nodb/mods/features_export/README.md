# Features Export

> Export run-scoped spatial and tabular datasets using reusable profiles.

## Overview

Features Export lets you build a repeatable export request, save/share it as profile text, and rerun it against the current run. The UI is profile-based: every setting in the form maps to a profile request payload.

## Profile-Based Workflow

1. Choose a preset profile or paste profile YAML/JSON text.
2. Review/update format, units, CRS, layer selections, temporal settings, and selectors.
3. Export and download the generated ZIP artifact.

### Built-in preset profiles

| Profile key | UI label | Purpose |
| --- | --- | --- |
| `post_wepp` | Post Wepp | Baseline spatial export for watershed/landuse/soils/WEPP summary layers. |
| `prep_details` | Prep details | Tabular prep-details replacement (`csv`, concatenated carrier tables). |
| `temporal_yearly` | Temporal yearly | Yearly WEPP temporal export (`parquet`). |
| `prep_wepp_gpkg_gdb` | Post Wepp (GPKG + GDB) | Virtual preset added when discovery conditions are met. |

You can also use **Specify Export from Profile** to paste `profile.yml` content from a previous export.

## Controls And Options

### Run Settings

| Control | Options | Description |
| --- | --- | --- |
| Load Export Profile | Dynamic preset buttons | Applies a full request payload to the form without submitting. |
| Specify Export from Profile | Paste YAML/JSON + `Load profile` | Resolves profile text and applies it to all controls. |
| Clear selection | `Clear selection` button | Clears selected datasets and dataset-level column/temporal overrides. |
| Format | `GeoPackage`, `Geodatabase`, `GeoParquet`, `Parquet (tabular)`, `CSV (tabular)`, `GeoJSON`, `KMZ` | Chooses export writer and packaging behavior. |
| CRS | `WGS84 (EPSG:4326)`, `UTM (EPSG:<run zone>)` | Spatial reference for geometry outputs. Hidden for tabular formats (`csv`, `parquet`). |
| Units | `Unitizer Selections`, `SI`, `English` | Controls unit system for unitized output fields. |
| Year selection | `All`, `Exclude first year`, `Exclude first two years`, `Exclude first five years`, `Custom exclusions` | Applies to yearly/annual-average temporal modes. |
| Custom excluded year indices | Text input (for example `0,1,2`) | Used only when Year selection = `Custom exclusions`. |

### Tabular-only options (`csv` / `parquet`)

| Control | Options | Description |
| --- | --- | --- |
| Concatenate tables | `on` / `off` | Merges carrier outputs into consolidated hillslope/channel tables and adds provenance columns. |
| Temporal table layout | `wide`, `long` | `wide` appends temporal tokens into column names; `long` emits temporal selector columns across rows. |

### Layer Catalog (dataset-level controls)

| Control | Options | Description |
| --- | --- | --- |
| Dataset checkbox | Per dataset | Includes/excludes dataset in export request. |
| Dataset temporal mode | `annual_average`, `yearly`, `event` (only supported values shown per dataset) | Overrides temporal mode per selected dataset. |
| Dataset columns | Per-column include checkboxes | Selects exported columns; required identity/join fields remain locked-in. |

### Scenario Catalog (conditional controls)

| Control | Options | Description |
| --- | --- | --- |
| Output Scopes | `Baseline`, `Roads` | Shown when scope-aware layers are selected. |
| Omni selectors | Scenario checklist or Contrast checklist | Shown when Omni datasets are selected; scenario and contrast modes are mutually exclusive. |
| Omni quick actions | `Select All`, `Unselect All` | Bulk selection for scenarios or contrasts. |

### Temporal (conditional controls)

| Control | Options | Description |
| --- | --- | --- |
| Event selector | `By date`, `By return period` | Shown when any selected dataset is in `event` mode. |
| Dates | Comma-separated `YYYY-MM-DD` | Used when Event selector = `By date`. |
| Return periods | Comma-separated numeric years | Used when Event selector = `By return period`. |

### SWAT Options (conditional controls)

| Control | Options | Description |
| --- | --- | --- |
| SWAT run | `latest` or discovered run IDs | Chooses SWAT output run source. |
| Table filter mode | `All tables`, `Include selected tables`, `Exclude selected tables` | Controls SWAT table filtering behavior. |
| SWAT tables | Dynamic checklist from run catalog | Table names discovered from `swat/outputs/run_*/interchange/*`. |

## Exportable Datasets

The catalog currently exposes 27 dataset layer IDs. Availability of any dataset depends on run outputs and module state.

Channel summary note:
`wepp.summary.channels` resolves its internal source join on `wepp_id` so `loss_pw0.chn.parquet` metrics align with `watershed/channels.parquet` attributes before the consolidated channel carrier retargets to the geometry-facing channel identity.

| Family | Layer ID | Dataset label |
| --- | --- | --- |
| Watershed | `watershed.subcatchments` | `hillslopes.parquet` |
| Watershed | `watershed.channels` | `channels.parquet` |
| Landuse | `landuse.dominant` | `landuse.parquet` |
| Soils | `soils.dominant` | `soils.parquet` |
| WEPP Summary | `wepp.summary.hillslopes` | `loss_pw0.hill.parquet` |
| WEPP Summary | `wepp.summary.channels` | `loss_pw0.chn.parquet` |
| WEPP Temporal | `wepp.temporal.events` | `return_period_events.parquet` |
| WEPP Interchange | `wepp.interchange.hill_pass` | `H.pass.parquet` |
| WEPP Interchange | `wepp.interchange.hill_element` | `H.element.parquet` |
| WEPP Interchange | `wepp.interchange.hill_wat` | `H.wat.parquet` |
| WEPP Interchange | `wepp.interchange.hill_ebe` | `H.ebe.parquet` |
| WEPP Interchange | `wepp.interchange.hill_soil` | `H.soil.parquet` |
| WEPP Interchange | `wepp.interchange.hill_pass_events` | `pass_pw0.events.parquet` |
| WEPP Interchange | `wepp.interchange.hill_pass_metadata` | `pass_pw0.metadata.parquet` |
| WEPP Interchange | `wepp.interchange.h_loss` | `H.loss.parquet` |
| WEPP Interchange | `wepp.interchange.chnwb` | `chnwb.parquet` |
| WEPP Interchange | `wepp.interchange.soil_pw0` | `soil_pw0.parquet` |
| WEPP Interchange | `wepp.interchange.loss_all_years_hill` | `loss_pw0.all_years.hill.parquet` |
| WEPP Interchange | `wepp.interchange.loss_all_years_channel` | `loss_pw0.all_years.chn.parquet` |
| Ash / WATAR | `ash.transport.hillslope_annuals` | `hillslope_annuals.parquet` |
| Omni Scenarios | `omni.scenarios.hillslopes` | `H.loss.parquet (Scenario)` |
| Omni Contrasts | `omni.contrasts.hillslopes` | `H.loss.parquet (Contrast)` |
| SWAT Interchange | `swat.interchange.table` | `{table_name}.parquet` (runtime-discovered table names) |
| AgFields Spatial | `ag_fields.subfields` | `sub_fields.WGS.geojson` |
| AgFields Spatial | `ag_fields.fields` | `fields.WGS.geojson` |
| AgFields Metrics | `ag_fields.metrics.subfields` | `H.pass.parquet` |
| AgFields Metrics | `ag_fields.metrics.fields` | `H.pass.parquet` |
