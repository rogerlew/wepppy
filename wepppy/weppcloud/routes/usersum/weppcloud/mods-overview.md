# Mods Overview
> Quick reference for the optional mods toggled from the run header `Mods` menu.

Not every mod is available on every run.
- `openet_ts` is shown to Admin users.
- `debris_flow` is shown to PowerUser users.
- `roads` and `rusle` require WBT delineation backend runs.
- `rusle` also requires `disturbed`; enabling `rusle` auto-enables internal `polaris` support.
- `omni` depends on `treatments` and enables it when needed.

## RAP Time Series (`rap_ts`)
- Purpose: Build multi-year RAP fractional cover summaries for hillslopes (and optional multi-OFE footprints).
- Use when: You need observed interannual cover trends or time-varying WEPP cover inputs.
- Outputs: `rap/rap_ts.parquet`, RAP rasters under `rap/`, and generated WEPP cover files such as `runs/p<wepp_id>.cov`.
- README: [RAP / RAP_TS](../../../../nodb/mods/rap/README.md)

## OpenET Time Series (`openet_ts`)
- Purpose: Pull monthly OpenET ET from Climate Engine and summarize it to hillslopes by dataset key.
- Use when: You need monthly observed ET series (for example `ensemble` or `eemetric`) aligned to project years.
- Outputs: `openet/openet_ts.parquet` and per-hillslope caches under `openet/individual/<dataset_key>/`.
- README: [OpenET](../../../../nodb/mods/openet/README.md)

## Ash Transport (`ash`)
- Purpose: Simulate post-fire ash transport and contaminant movement from hillslopes using burn severity, hydrology, climate, and optional ash rasters.
- Use when: You need watershed-scale ash and contaminant estimates after wildfire.
- Outputs: `ash/H<wepp_id>_ash.parquet` hillslope files and aggregated AshPost products under `ash/post/` (parquet tables plus schema README).
- README: [Ash Transport](../../../../nodb/mods/ash_transport/README.md)

## Treatments (`treatments`)
- Purpose: Apply treatment scenarios (mulch, thinning, prescribed fire, and related mappings) to selected hillslopes or an uploaded treatment raster.
- Use when: You need scenario-ready treatment edits to landuse/soils before WEPP runs (including Omni workflows).
- Outputs: Treatment rasters under `treatments/` (for example `treatments.tif`) and persisted mapping/state in `treatments.nodb`.
- README: [Treatments](../../../../nodb/mods/treatments/README.md)

## Observed Data (`observed`)
- Purpose: Parse observed timeseries CSV input and compute model-fit statistics against WEPP hillslope/channel results.
- Use when: You are calibrating or validating with measured data.
- Outputs: `observed/observed.csv`, comparison CSVs under `observed/`, and persisted results in `observed.nodb`.
- README: [Observed](../../../../nodb/mods/observed/README.md)

## Debris Flow (`debris_flow`)
- Purpose: Compute debris-flow probability and volume matrices from USGS-style equations using soils, slope, burn severity, and precip-frequency inputs.
- Use when: You need post-fire debris-flow hazard screening.
- Outputs: Datasource-specific precipitation/volume/probability matrices persisted in `debris_flow.nodb` and surfaced in the debris-flow UI/report.
- README: [Debris Flow](../../../../nodb/mods/debris_flow/README.md)

## Roads (`roads`)
- Purpose: Convert uploaded roads GeoJSON into monotonic segment candidates, map lowpoints to channels/hillslopes, and run roads-scoped WEPP integration.
- Use when: You need to evaluate road-related runoff/sediment effects alongside baseline watershed results.
- Outputs: `roads/roads.uploaded.geojson`, `wepp/roads/segments/*` prepare artifacts, and roads outputs under `wepp/roads/output/interchange/`.
- README: [Roads](../../../../nodb/mods/roads/README.md)

## Features Export (`features_export`)
- Purpose: Package run-scoped spatial/tabular datasets (WEPP, Omni, Ash/WATAR, SWAT, AgFields, and others) into download formats.
- Use when: You need GIS-ready or tabular export bundles for downstream analysis.
- Outputs: Bundles under `export/features/artifacts/<artifact_id>/` (for example `features_export.<format>.zip`) including payload files plus `manifest.json` and `README.md`.

## DSS Export (`dss_export`)
- Purpose: Export WEPP channel/outlet timeseries to HEC-DSS for HEC tools.
- Use when: You need DSS files for HEC-HMS/HEC-RAS workflows after WEPP outputs are available.
- Outputs: `export/dss/totalwatsed3_chan_<id>.dss`, `export/dss/peak_chan_<id>.dss`, channel/boundary sidecar files, and `export/dss.zip`.

## Omni (`omni`)
- Purpose: Build and run scenario clones (uniform severity, treatments, SBS-map variants, and contrasts) from one base run.
- Use when: You need side-by-side scenario and targeted contrast comparisons.
- Outputs: Scenario/contrast run trees under `_pups/omni/` and summary tables such as `_pups/omni/scenarios.out.parquet` and `_pups/omni/contrasts.out.parquet`.
- README: [Omni](../../../../nodb/mods/omni/README.md)

## Path CE (`path_ce`)
- Purpose: Solve a cost-effective treatment optimization (linear programming) from Omni outputs to pick hillslope treatments that meet thresholds.
- Use when: You need ranked treatment selections based on sediment/discharge targets and treatment costs.
- Outputs: `path/analysis_frame.parquet`, `path/hillslope_sdyd.parquet`, `path/untreatable_hillslopes.parquet`, plus `path_ce.nodb` status/results.
- README: [Path CE](../../../../nodb/mods/path_ce/README.md)

## RUSLE (`rusle`)
- Purpose: Build gridded RUSLE factors (`R`, `K`, `LS`, `C`, `P`) and final annual detachment raster (`A = R*K*LS*C*P`).
- Use when: You need spatial erosion-potential mapping for disturbed WBT runs.
- Outputs: RUSLE rasters and manifests under `rusle/` (for example `r.tif`, `ls.tif`, `k_*.tif`, `c_*.tif`, `a_<c_mode>_<k_mode>.tif`, `manifest.json`, `README.md`).
- README: [RUSLE](../../../../nodb/mods/rusle/README.md)
