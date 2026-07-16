# WEPPcloud Platform Enhancements and Simulation Summary

**NASA ROSES — Utility Watersheds Project**
**Summary Report — July 2026**

---

## 1. Overview

WEPPcloud is a web-based interface and computational platform for the Water Erosion Prediction Project (WEPP) model, providing physically based, distributed simulation of hillslope hydrology, soil erosion, and sediment delivery at the watershed scale. Under this project, WEPPcloud was extended from a single-watershed, interactive tool into a platform capable of regional, multi-scenario simulation campaigns targeting municipal water-supply watersheds at risk from wildfire.

Two categories of work are summarized here:

1. **Platform enhancements** — new tooling for automated batch execution across large watershed collections, systematic scenario and treatment comparison, and modern high-performance data delivery and visualization.
2. **Simulation campaigns** — production model runs on the `wepp1` compute server covering **129 water-supply watersheds** comprising **106,133 delineated hillslopes**, each simulated under burned, unburned, and fuel-treatment scenarios driven by multi-decade (39–45 year) daily climate records. In total these campaigns executed approximately **504,000 individual hillslope-scale WEPP simulations** — roughly **19.7 million simulated hillslope-years** — plus watershed-scale channel routing for 565 completed watershed–scenario combinations.

---

## 2. Platform Enhancements

### 2.1 Batch Runner

A batch execution framework was developed to run the same model configuration across dozens to hundreds of watersheds automatically. Prior to this work, each WEPPcloud watershed required interactive, step-by-step configuration; regional screening applications (for example, identifying water-supply intakes or culverts at risk of post-fire sediment impacts) were impractical at that pace.

The Batch Runner workflow:

- **Define once, run everywhere.** The operator prepares a single canonical "base" project that fixes the digital elevation model source, land cover mapping, soils database, climate parameterization, and WEPP model version for the entire campaign.
- **Watershed collections from GIS data.** The watershed set is defined by uploading a GeoJSON feature collection. Features may be watershed boundary polygons or outlet points; a companion command-line utility delineates watershed boundaries from pour-point coordinates when polygons are not available in advance. Run identifiers are generated from feature attributes (e.g., public water system codes) through validated naming templates, so every run is traceable back to its source feature.
- **Autonomous pipeline execution.** For each watershed, the system clones the base project and walks the complete modeling pipeline without operator intervention: DEM acquisition, channel network delineation, outlet snapping, subcatchment delineation and abstraction, land cover and soils parameterization, climate assembly, vegetation and evapotranspiration time-series retrieval, WEPP hillslope simulations, watershed-scale channel routing, and scenario post-processing.
- **Parallel, fault-isolated scheduling.** Runs are dispatched to a dedicated job queue serviced by a pool of workers, scheduled largest-watershed-first to minimize total wall-clock time. A failure in one watershed does not interrupt the others.
- **Progress monitoring.** A console-style dashboard reports per-watershed, per-stage progress in real time, backed by a live status event stream. On completion, every run is classified (complete, incomplete, failed, or missing) and a batch-level summary is published.
- **Durable restarts.** Motivated by operational experience with the OR/WA production campaign (Section 3), the framework was hardened so that re-running a batch re-enqueues only the watersheds that need work — failed, incomplete, or affected by base-configuration corrections — while completed watersheds are preserved. Configuration drift (for example, a corrected climate record) is detected automatically, and only the affected pipeline stages are invalidated and recomputed.
- **Output aggregation.** Each watershed produces the full standardized WEPPcloud output set (Section 2.3), and batch-level visualization merges geometry and summary attributes across all runs into a single interactive map view (Section 2.5).

### 2.2 Omni Scenarios and Contrasts

The Omni framework manages multiple versions of the same watershed simultaneously, enabling systematic "what-if" analysis of fire and fuel-management alternatives. Each scenario is a complete, independently runnable clone of the parent project — immutable inputs (climate, terrain) are shared, while land cover, soils, and disturbance state are modified per scenario and the full WEPP simulation is re-executed.

**Supported scenario types:**

| Scenario | Description |
|---|---|
| Burned — SBS map | Fire effects parameterized from a spatially variable soil burn severity (SBS) raster, including predictive SBS maps produced under this project |
| Burned — uniform severity | Uniform low, moderate, or high soil burn severity applied watershed-wide |
| Unburned / undisturbed | Baseline conditions with no fire effects |
| Prescribed fire | Low-intensity burn applied to mature forest |
| Thinning | Mechanical fuel treatment; canopy cover target of 40% or 65% combined with residual ground cover reflecting harvest method (75–93%) |
| Mulching | Post-fire ground-cover treatment (15%, 30%, or 60% ground cover increase, corresponding to ½–2 tons/acre) applied on top of a burned base scenario |

Treatment scenarios additionally accept per-scenario placement filters — minimum/maximum hillslope slope and burn severity class — so that, for example, mulch can be restricted to moderately-to-severely burned hillslopes steeper than a slope threshold.

**Contrasts** automatically compute and visualize differences between scenarios to highlight areas of improvement or degradation. A contrast applies the treatment scenario to a selected subset of hillslopes while the remainder of the watershed retains control-scenario conditions, then routes the combined watershed response and reports the change in outlet discharge and sediment relative to the control. Four selection modes are supported:

1. **Cumulative targeting** — hillslopes are ranked by an objective parameter (soil loss, runoff depth, or runoff volume) and selected until a configurable fraction of the watershed total is captured, identifying the smallest treatment footprint with the largest expected benefit.
2. **User-defined areas** — treatment zones supplied as GIS polygons (e.g., planned treatment units).
3. **User-defined hillslope groups** — custom comparison groups of explicitly listed hillslopes.
4. **Stream-order grouping** — the channel network is pruned by Strahler stream order for a configurable number of passes, and hillslopes are grouped by the channel segment they drain to. This provides scenario comparison filtered by channel size, from headwater tributaries up to mainstem reaches.

Contrast results are compiled into analysis-ready tables (control-minus-treatment differences for every reported output), rendered as summary reports with discharge and soil-loss deltas per contrast, and displayed as labeled treatment-area overlays on the interactive map.

### 2.3 WEPP Output Interchange (High-Performance Data Layer)

WEPP's native outputs are fixed-width FORTRAN text reports — adequate for single runs but unsuited to regional analysis. WEPPcloud now converts all model inputs and outputs into columnar **Apache Parquet** tables with versioned, unit-annotated schemas. The interchange layer covers:

- **Inputs and attributes:** land use, soils, climate, watershed structure and hillslope attributes, and remotely sensed vegetation time series.
- **Hillslope outputs:** water balance, runoff and sediment delivery by event, element-level detail, and annual loss summaries, aggregated across all hillslopes in a watershed.
- **Watershed outputs:** channel water balance, channel peak discharge, event-by-event outlet response, sediment class data, and annual loss reports for hillslopes, channels, and the outlet.
- **Derived products:** a daily watershed water and sediment budget table, and return-period analyses of extreme events.

Conversion is parallelized across processor cores and performed once per simulation; the resulting Parquet tables are roughly an order of magnitude smaller than the raw text and can be queried in milliseconds-to-seconds rather than re-parsed. The same tables also support export to HEC-DSS for interoperability with U.S. Army Corps of Engineers hydraulic modeling tools.

### 2.4 Query-Engine API

A new query-engine service provides real-time analytical access to every Parquet table in a project. Clients submit declarative JSON queries — datasets, columns, filters, joins, aggregations, and computed columns — and the service compiles them to SQL executed by an embedded DuckDB analytical engine directly against the project's Parquet files. Capabilities include:

- Cross-table joins (for example, land cover × soils × sediment yield by hillslope) and grouped aggregations, with results returned in sub-second time for typical requests.
- Spatial data integration: watershed geometry (GeoJSON, GeoPackage, FlatGeobuf, shapefile) can be joined to tabular model output on hillslope identifiers.
- Scenario-aware queries: the same query can be pointed at any Omni scenario of a project, enabling programmatic scenario comparison.
- An interactive browser-based query console, a self-describing schema catalog per project, and an authenticated machine-to-machine interface (Model Context Protocol) that allows AI assistants and external analysis pipelines to query model results directly.

### 2.5 GL-Dashboard

The GL-Dashboard is a fast, WebGL-based interactive report tool for viewing project inputs and outputs. Built on the deck.gl rendering framework and driven live by the query-engine API, it replaces static report pages with a single explorable view:

- **Map layers:** hillslopes and channels colored by any model output measure (runoff volume, baseflow, soil loss, sediment deposition and yield, channel discharge, channel soil loss), with yearly and event-by-event modes controlled by time sliders; input raster overlays including land cover, soils, soil burn severity, rangeland vegetation cover, and remotely sensed evapotranspiration.
- **Linked graphs:** climate and evapotranspiration time series, cumulative contribution curves, and Omni scenario/contrast comparisons (box plots of hillslope soil loss and runoff; bar charts of outlet sediment and discharge), synchronized with map selection.
- **Scenario comparison mode:** hillslopes colored by the difference between any two scenarios, providing immediate visual identification of where treatments help most.
- **Batch mode:** an entire batch campaign is rendered as one merged watershed map, with per-run geometry and summary attributes fanned in from all member watersheds — the primary visual interface for regional screening results.

---

## 3. Simulation Campaigns

### 3.1 Watershed Collections

Three production campaigns were executed on the `wepp1` compute server, all targeting source-water watersheds for public drinking-water systems:

- **`nasa-roses-202606-psbs`** — the primary regional campaign: **93 HUC10 watersheds** in Oregon and Washington containing surface-water intakes for public water systems (e.g., municipal supplies drawing from the Snake River, and analogous sources statewide). Watersheds were parameterized with the disturbed-WEPP configuration using multiple overland flow elements per hillslope, capturing along-slope variation in cover and soils. Burn conditions were driven by **predictive soil burn severity (pSBS) rasters** produced under this project.
- **`victoria-ca-2026-sbs`** — **32 catchments** in the Greater Victoria (British Columbia) water-supply area, including the Sooke and Council Creek drainages, run with the Canadian locale configuration as an international transferability demonstration.
- **`bremerton-2026-psbs`** — **4 catchments** supplying the City of Bremerton, Washington, run with predictive SBS parameterization; this campaign also exercised the Omni contrast (targeted-treatment) workflow.

### 3.2 Scenarios

Each watershed was simulated under a base scenario and up to four Omni alternatives:

1. **Burned** — predictive soil burn severity map (base scenario)
2. **Unburned** — undisturbed baseline
3. **Prescribed fire** — low-intensity burn of mature forest
4. **Thinning** — 40% canopy cover, 75% ground cover
5. **Thinning** — 65% canopy cover, 93% ground cover

All scenarios for a given watershed share identical terrain and climate forcing, so differences in simulated response are attributable solely to the disturbance or treatment.

### 3.3 Climate Forcing

Simulations were driven by multi-decade observed daily climate records, spatially adjusted with PRISM precipitation climatology:

- Oregon/Washington and Bremerton campaigns: gridMET-based observed daily climate, **1986–2024 (39 years)**.
- Victoria campaign: Daymet-based observed daily climate, **1980–2024 (45 years)**.

Multi-decade daily forcing enables event-based and return-period analysis of post-fire response — including the large, infrequent storm events that dominate sediment delivery risk — rather than average-annual estimates alone.

### 3.4 Model Outputs

For every watershed–scenario combination, the following outputs were produced and published in the standardized Parquet interchange format, queryable through the query-engine API and viewable in the GL-Dashboard:

- **Hillslope, by event:** runoff, sediment detachment and transport, and peak flow for every runoff-producing event in the simulation period.
- **Hillslope, annual:** water balance components (precipitation, runoff, lateral flow, percolation, evapotranspiration) and soil loss.
- **Channel:** soil loss and deposition by channel reach, channel water balance, and channel peak discharge.
- **Watershed outlet:** daily discharge, event peak flows, sediment yield, and sediment particle-class composition.
- **Derived analyses:** daily watershed water and sediment budgets, and return-period rankings of extreme runoff and sediment events.

Scenario and contrast comparison tables (treated-versus-control differences for all reported measures) accompany each Omni-enabled project, supporting identification of the watersheds — and the hillslopes within them — where fuel treatments yield the greatest reduction in post-fire runoff and sediment delivery to water-supply intakes.
