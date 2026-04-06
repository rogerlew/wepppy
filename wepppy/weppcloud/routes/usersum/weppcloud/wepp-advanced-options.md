# WEPP Advanced Options

This page explains every control in **WEPP -> WEPP Advanced Options** in WEPPcloud.

Most projects should run with defaults. Use these controls when you have a clear reason (for example, calibration against observed hydrographs, known snow/frost behavior, or a post-fire recovery scenario).

## Location in the UI

1. Open a run.
2. Open the **WEPP** control panel.
3. Expand **WEPP Advanced Options**.

## How To Use This Page

Each section below uses the same pattern:

- **What this section does**: plain-language intent.
- **Inputs and parameters**: every field in that advanced section.
- **Modeling impact**: how water balance, runoff, baseflow, or erosion can change.
- **When to adjust**: practical guidance.
- **Cautions**: common mistakes and side effects.

## Recommended workflow

1. Change one section at a time.
2. Re-run WEPP.
3. Compare runoff, peak flow, recession behavior, and erosion/sediment outputs.
4. Record what you changed and why.

## 1) WEPP UI - Hourly Seepage

### What this section does

Switches WEPP from daily water-balance seepage handling to an hourly path (`wepp_ui.txt` present).

### Inputs and parameters

| UI control | What it means |
|---|---|
| **Run hourly seepage (wepp_ui.txt)** | Enables hourly water-balance/seepage logic. |

### Modeling impact

- Runs soil-water calculations in hourly substeps (24 per day) and then rolls seepage/drainage totals up to daily outputs.
- Percolation and seepage are handled differently than the daily path, so infiltration/percolation partition and runoff timing can shift.
- Usually most noticeable when short-duration storm timing matters.
- Can change event timing and short-term peaks, even when seasonal totals are similar.
- Initial near-surface wetness can differ from the daily path, which can affect early-event runoff and erosion response.

### When to adjust

- Use when daily behavior is too coarse for the watershed response you are calibrating.
- Common in workflows using 7778-style soil behavior.

### Cautions

- For 2006-era soil versions, this option may not produce a `wepp_ui.txt` effect.
- This is a structural simulation-path toggle, not just an output setting.
- The file acts as an on/off trigger by presence; there are no numeric fields in `wepp_ui.txt`.

## 2) Potential ET (PMET)

### What this section does

Controls whether WEPP uses Penman-Monteith ET coefficients from `pmetpara.txt`.

### Inputs and parameters

| UI control | What it means |
|---|---|
| **Basal crop coefficient ratio (kcb)** | Mid-season crop coefficient used in PMET ET calculations. |
| **Readily available water fraction (rawp)** | Fraction of total available root-zone water that can be used before water-stress reduction begins. |
| **Run PMET (pmetpara.txt)** | Enables PMET file use; if off, WEPP uses the legacy Penman ET path. |

### Modeling impact

- `kcb` primarily shifts plant transpiration demand. Higher values usually increase transpiration and reduce water left for deep drainage/baseflow.
- `rawp` sets how soon water stress starts (`RAW = rawp x TAW`). Lower values trigger stress earlier and suppress transpiration sooner in dry periods.
- ET changes alter soil moisture carryover, which feeds back into runoff generation and erosion potential in later storms.

### When to adjust

- ET calibration against observed seasonal dryness/wetness.
- Cases where default ET assumptions over- or under-dry the soil profile.

### Cautions

- In disturbed workflows, PMET coefficients may be generated from disturbed land/soil lookups instead of manual entries.
- In current WEPP builds, if a crop/land-cover code is missing from `pmetpara.txt`, the model may use the first record in that file as fallback.
- Changing ET parameters can improve one season but degrade another; always validate across multiple years/storms.

## 3) Frost

### What this section does

Writes `frost.txt` to control winter freeze/thaw process parameters.

### Inputs and parameters

| UI control | What it means |
|---|---|
| **Write frost inputs (frost.txt)** | Enables explicit winter-parameter file use. |
| **wintRed** | 1 = allow winter water redistribution around freeze/thaw fronts; 0 = disable that redistribution step. |
| **fineTop** | Number of fine computational layers in each top 10 cm soil section (1-10); higher values increase surface frost-resolution detail. |
| **fineBot** | Number of fine computational layers in deeper sections (1-10); higher values increase deeper frost-resolution detail. |
| **ksnowf** | Snow thermal conductivity adjustment factor (0.1-10). |
| **kresf** | Residue thermal conductivity adjustment factor (0.1-10). |
| **ksoilf** | Soil thermal conductivity adjustment factor (0.1-10). |
| **kfactor(1)** | Lower conductivity limit for frozen annual/fallow-like conditions. |
| **kfactor(2)** | Lower conductivity limit for frozen pasture/perennial-like conditions. |
| **kfactor(3)** | Lower conductivity limit for frozen forest/tree-like conditions. |

### Modeling impact

- Freeze/thaw settings strongly influence winter infiltration capacity and runoff partitioning.
- Thermal factors (`ksnowf`, `kresf`, `ksoilf`) affect how quickly frost forms/thaws through snow/residue/soil layers.
- `wintRed` directly controls whether the model redistributes water around freeze/thaw fronts, which can change thaw-season runoff pulses.
- `kfactor` values set lower bounds on frozen-soil hydraulic conductivity, which can strongly shift winter runoff and related erosion transport.

### When to adjust

- Cold-region basins where winter runoff timing or frozen-soil response is a major calibration target.

### Cautions

- Aggressive changes can create unrealistic winter hydrographs.
- Keep calibration physically defensible (snowpack, frost depth, thaw timing).

## 4) Snow

### What this section does

Writes `snow.txt` to control rain/snow partition and snow density behavior.

### Inputs and parameters

| UI control | What it means |
|---|---|
| **Write snow inputs (snow.txt)** | Enables explicit snow parameter file use. |
| **Rain/snow threshold temperature** | Temperature threshold used to separate rainfall vs snowfall. |
| **Density of new snow** | New snow density parameter. |
| **Snow settling density** | Settled snow density parameter. |

### Modeling impact

- Threshold temperature directly shifts how much precipitation enters as rain vs snow.
- `newsnw` controls new-snow density and early snowpack compaction behavior.
- `ssd` controls when settling behavior changes in denser snowpacks.
- These settings mainly affect runoff timing/volume and therefore event-driven erosion timing.

### When to adjust

- Snow-dominated or mixed rain/snow watersheds with known snowmelt timing mismatches.

### Cautions

- If values are unrealistic, melt timing errors can overwhelm downstream calibration work.

## 5) Baseflow Processing

### What this section does

Writes `gwcoeff.txt` to configure groundwater storage, baseflow release, and deep seepage behavior.

### Inputs and parameters

| UI control | What it means |
|---|---|
| **Initial groundwater storage (mm)** | Initial groundwater storage depth used by the linear-reservoir baseflow option. |
| **Baseflow coefficient (per day)** | Fraction of groundwater storage released to baseflow per day. Supported range is 0.01-0.10/day. |
| **Deep seepage coefficient (per day)** | Fraction of groundwater storage routed to deep seepage per day. |
| **Watershed groundwater baseflow threshold area (ha)** | Area threshold used in channel logic to separate ephemeral/perennial handling of baseflow contribution. |

### Modeling impact

- Larger **initial storage** can increase early-period baseflow.
- Larger **baseflow coefficient** steepens hydrograph recession (faster groundwater release).
- Larger **deep seepage coefficient** removes more groundwater from channel-return pathways.
- **Threshold area** affects where accumulated baseflow contributes through channel network classifications (ephemeral vs perennial behavior).

### When to adjust

- When simulated recession curves are too slow or too fast.
- When channel low-flow persistence is poorly matched.

### Cautions

- In single-storm workflows, WEPPcloud writes `gwcoeff.txt` with zero initial groundwater storage and zero baseflow coefficient, so user-entered baseflow settings are effectively bypassed.
- Tune with hydrograph recession metrics, not just peak flow.

## 6) Channel Inputs (chan.inp)

### What this section does

Controls channel hydrograph output configuration and selected channels in `chan.inp`.

### Inputs and parameters

| UI control | What it means |
|---|---|
| **Output interval override (dtchr_override, seconds)** | Routing/output timestep in seconds. Must be >= 60. Defaults: `600` for continuous runs, `60` for single-storm runs. |
| **Channel hydrograph output (ichout_override)** | `1` = peaks only; `3` = full timestep hydrograph. Defaults: `1` for continuous runs, `3` for single-storm runs. |
| **Channel TOPAZ IDs of interest** | Channel IDs to include in channel hydrograph output list (space/comma separated, each ending in `4`). |

### Modeling impact

- `dtchr` changes channel-routing timestep, which can change hydrograph timing/shape and numerical behavior (not only file detail).
- Smaller timestep and full hydrograph output provide richer diagnostics but larger files and longer post-processing.
- `ichout` and channel lists mainly control reporting scope/format, not channel physics.

### When to adjust

- Troubleshooting routing behavior on specific channels.
- Producing higher-detail channel diagnostics for short windows.

### Cautions

- Full hydrograph output can create very large files on long runs.
- Keep channel ID lists intentional.
- These controls apply to watershed/channel-routing runs; hillslope-only runs do not use channel output controls.

## 7) Channel Parameters

### What this section does

Controls channel resistance and erodibility assumptions, including optional slope-dependent critical shear (`tcr.txt`).

### Inputs and parameters

| UI control | What it means |
|---|---|
| **Use variable channel critical shear ... (tcr.txt)** | Enables slope-dependent channel critical shear formulation. |
| **Critical shear (N/m^2)** | Constant critical shear for channel detachment threshold. |
| **Channel erodibility (s/m)** | Channel erodibility coefficient used in channel detachment calculations. |
| **Minimum channel width (m)** | Lower bound on channel widths used during channel slope preparation. |
| **Total Manning roughness coefficient allowing for vegetation (chnn)** | Effective roughness with vegetation influence. |
| **Manning roughness coefficient for bare soil (chnnbr)** | Bare-channel roughness reference value. |
| **taumin / taumax / k / n** | Parameters of the slope-to-critical-shear curve when variable critical shear is enabled. |

### Modeling impact

- **Critical shear** and **erodibility** are first-order controls on channel detachment and sediment delivery.
- **Manning roughness** affects flow velocity, depth, travel time, and shear stress.
- **Minimum width** prevents unrealistically narrow channels from driving extreme hydraulic responses.
- Variable-critical-shear mode links channel shear resistance to channel slope using a shaped response curve.

### When to adjust

- Channel sediment calibration.
- Routing/velocity/shear mismatches in channel-focused validation.

### Cautions

- Changing multiple channel physics parameters at once makes calibration unstable.
- Keep `chnn` and `chnnbr` physically consistent.

## 8) Bedrock

### What this section does

Overrides restrictive-layer hydraulic conductivity (`kslast`) in generated soil inputs.

### Inputs and parameters

| UI control | What it means |
|---|---|
| **Hydraulic conductivity for restrictive layer (kslast)** | Conductivity assigned to restrictive layer beneath soil profile (WEPPcloud soil-input units, typically mm/h). |

### Modeling impact

- Lower `kslast` limits downward percolation at the restrictive layer, often increasing near-surface wetness, runoff potential, and erosion response.
- Higher `kslast` allows more deep percolation and can reduce quick runoff response.
- When a restrictive layer is active, this bottom-boundary conductivity can materially alter baseflow vs quickflow partitioning.

### When to adjust

- Watersheds with known shallow restrictive layers or bedrock conductivity evidence.

### Cautions

- This is a powerful structural soil-hydrology control; avoid using it as a generic calibration knob without field justification.

## 9) Clip Hillslopes

### What this section does

Limits hillslope length while preserving hillslope area by increasing width.

### Inputs and parameters

| UI control | What it means |
|---|---|
| **Clip hillslopes** | Enables hillslope length clipping. |
| **Hillslope clip length (m)** | Target maximum hillslope length used during slope-file preparation. |

### Modeling impact

- Shorter effective slope length often reduces hillslope transport distance and can reduce predicted erosion on very long slopes.
- Preserving area avoids changing gross contributing area while still changing hillslope geometry and hydraulic/erosion response.

### When to adjust

- Extremely long abstracted hillslopes that are known to over-predict erosion.

### Cautions

- Clipping is recommended when very long abstracted hillslopes are likely to overestimate soil loss.
- Multi-OFE workflows can limit applicability of this option.
- If changing the clip length does not change results, verify applied slope lengths in prep-details outputs; this control may not be wired consistently in all deployments.

## 10) Soil Options

### What this section does

Adjusts soil profile depth constraints and initial soil saturation before runs are prepared.

### Inputs and parameters

| UI control | What it means |
|---|---|
| **Clip Soils Maximum Depth** | Enables maximum depth clipping. |
| **Soils Maximum Depth (mm)** | Upper bound on profile depth (deeper horizons are truncated). |
| **Clip Soils Minimum Depth** | Enables minimum depth enforcement. |
| **Soils Minimum Depth (mm)** | Raises shallow profiles so minimum depth is met. |
| **Initial soil saturation (fraction)** | Initial saturation assigned across prepared soil profiles. |

### Modeling impact

- Shallower max depth reduces storage volume, which can increase runoff and erosion sensitivity.
- Larger minimum depth increases storage in shallow soils, often damping quick runoff response.
- Higher initial saturation increases early-event runoff likelihood and can increase early-event erosion.
- In hourly-seepage UI mode, initialization handling differs slightly from the daily path, so initial-saturation sensitivity can be stronger.

### When to adjust

- Sensitivity analysis around storage depth and antecedent moisture assumptions.

### Cautions

- If both min/max clipping are enabled, minimum depth must be <= maximum depth.
- Large `initial_sat` shifts can dominate first-event calibration and mask other parameter effects.

## 11) Phosphorus

### What this section does

Writes `phosphorus.txt` for optional phosphorus concentration routing.

### Inputs and parameters

| UI control | What it means |
|---|---|
| **Surface runoff concentration (mg/L)** | Concentration assigned to surface runoff pathway. |
| **Subsurface lateral flow concentration (mg/L)** | Concentration assigned to lateral subsurface flow pathway. |
| **Baseflow concentration (mg/L)** | Concentration assigned to baseflow pathway. |
| **Sediment concentration (mg/kg)** | Concentration assigned to sediment-associated phosphorus. |

### Modeling impact

- Changes phosphorus load outputs only.
- Does not directly change runoff, infiltration, or erosion mechanics.

### When to adjust

- Water-quality workflows requiring phosphorus export estimates.

### Cautions

- All four values are required for `phosphorus.txt` to be written.
- In some regional workflows (for example Lake Tahoe), defaults can be auto-populated from module-specific data.

## 12) Export Configuration

### What this section does

Controls post-run export products generated automatically after watershed runs complete.

### Inputs and parameters

| UI control | What it means |
|---|---|
| **Prep details** | Generates prep-details export artifacts. |
| **Geopackage export (.gpkg)** | Generates modern GIS package outputs. |
| **Legacy ArcMap export (.shp)** | Generates legacy shapefile-style ArcMap outputs. |

### Modeling impact

- No direct impact on simulated hydrology or erosion.
- Affects post-processing time and generated deliverables.

### When to adjust

- Reporting or delivery workflows that require standardized GIS artifacts.

### Cautions

- Additional export products increase run-completion processing time.

## 13) Interchange

### What this section does

Controls cleanup of raw WEPP text outputs after successful interchange conversion to parquet artifacts.

### Inputs and parameters

| UI control | What it means |
|---|---|
| **Delete raw WEPP outputs after successful interchange conversion** | Keeps interchange artifacts and removes selected raw text outputs after successful conversion. |

### Modeling impact

- No direct impact on hydrology or erosion simulation results.
- Changes which output artifacts remain available for debugging/inspection.

### When to adjust

- Runs where storage footprint is a concern and parquet interchange outputs are the primary deliverable.

### Cautions

- Keeping only converted artifacts can reduce ability to inspect raw WEPP text outputs later.

## 14) WEPP Exec

### What this section does

Controls binary selection and whether watershed/channel execution is included.

### Inputs and parameters

| UI control | What it means |
|---|---|
| **WEPP binary version** | Selects which available WEPP executable is used. |
| **Run WEPP Watershed** | Enables/disables watershed/channel routing run stage. |
| **Prep Only** (button) | Prepares hillslope/watershed inputs without running watershed simulation. |
| **Run WEPP Watershed** (button) | Runs watershed stage (requires prior hillslope products). |

### Modeling impact

- Binary changes can alter numerical behavior, bug fixes, or compatibility.
- Disabling watershed run prevents channel routing outputs from being generated.
- Prep-only does not produce new watershed simulation outputs by itself.
- Watershed execution controls whether channel-network routing is run after hillslope preparation.

### When to adjust

- Reproducibility checks against prior runs.
- Troubleshooting version-specific behavior.
- Verifying binary lineage and compiler history using the [WEPP-Forest Change Log](./wepp-forest-change-log.md).

### Cautions

- Multi-OFE workflows require newer binaries.
- Keep binary choice consistent across scenario comparisons.

## 15) Revegetation Scenarios

### What this section does

Applies optional post-fire cover transformation scenarios that rescale RAP cover time series before WEPP prep.

### Inputs and parameters

| UI control | What it means |
|---|---|
| **Cover transformation scenario** | Choose observed cover, built-in recovery curves, or user-defined transform mode. |
| **Upload cover transform file (.csv)** | Upload custom per-year cover-scale factors for burn-class and vegetation combinations. |

### Modeling impact

- Changes vegetation/cover trajectories used in `.cov` inputs.
- Cover changes feed directly into infiltration, runoff, and erosion response through canopy/residue/cover effects.
- Most influential in post-disturbance recovery simulations.

### When to adjust

- Disturbance and recovery scenario analysis.
- Testing management assumptions about recovery speed and cover composition.

### Cautions

- User CSV uploads are accepted by filename/type; keep file structure consistent with expected cover-transform format.
- Use physically defensible recovery assumptions and document the scenario source.

## Related references

- [Disturbed Land Soil Lookup Table](./disturbed-land-soil-lookup.md)
- [WEPPcloud User Guide](./user-guide.md)
