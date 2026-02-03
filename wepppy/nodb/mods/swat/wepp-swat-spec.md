# WEPP-SWAT+ Integration Spec

## Purpose
Document a practical path to run WEPP hillslopes and route the resulting flow and sediment through SWAT+ for channel dynamics and basin-scale routing, using SWAT+ recall (point source/inlet) inputs and routing connectivity.

See `wepppy/nodb/mods/swat/swat-nodb-spec.md` for the NoDb contract and WEPPcloud integration details, and `wepppyo3/docs/wepp-hill-pass-to-swat-rec-spec.md` for the Rust recall conversion rules.

## Scope and assumptions
- WEPP provides hillslope-scale runoff and sediment time series at a daily step.
- SWAT+ is used for channel/routing dynamics downstream of those hillslopes.
- The integration uses SWAT+ recall objects (point source/inlet) to inject WEPP time series into the SWAT+ routing network.

## SWAT+ IO facts relevant to the handoff

### Input file format basics
- SWAT+ input files are free-format and space-delimited.
- Most input files use a title line followed by a header line, but there are exceptions. For recall daily files, line 2 is `NBYR`, and the header line appears on line 3.
- `file.cio` lists the input files used in a run; `recall.rec` is the recall category entry, and unused files can be set to `null`.

Sources:
- https://swatplus.gitbook.io/io-docs/introduction-1/input-file-format
- https://swatplus.gitbook.io/io-docs/introduction-1/master-file-file.cio

### Routing connectivity and recall objects
- SWAT+ uses connect files to route flow between spatial objects.
- The recall connect file is `recall.con` and is used for point source/inlet objects.
- The recall connect file points to `recall.rec` for the object data records.

Sources:
- https://swatplus.gitbook.io/io-docs/introduction/connectivity
- https://swatplus.gitbook.io/io-docs/introduction-1/connectivity/hru.con/hru

### Recall master file (`recall.rec`)
`recall.rec` declares each recall dataset:
- NUMB (sequence)
- NAME (recall object name/label)
- TYP (1 = daily, 2 = monthly, 3 = annual)
- FILENAME (data file to read)

Source:
- https://swat.tamu.edu/media/116078/inputs_swatplus.pdf (RECALL.REC section)

### Recall data files (e.g., `recall_day.rec`)
Recall data files contain a time series with:
- Line 1: title (ignored by SWAT+)
- Line 2: `NBYR` (number of years of recall data)
- Line 3: header line with **exact** column order:
  - `IYR ISTEP flo sed orgn sedp no3 solp psol psor chla nh3 C no2 cbod dox bacp bacpl met1 met2 met3 san sil cla sag lag grv temp`
- Lines 4+: daily rows matching the header order.

For WEPP handoff, populate `flo`, `sed`, and the sediment class fields (`san sil cla sag lag grv`). Set all nutrient/pesticide/bacteria/metal/temp fields to `0` until explicitly supported.

Source:
- https://swat.tamu.edu/media/116078/inputs_swatplus.pdf (RECALL.DAY.REC example + variable definitions)

### Output controls and verification
- `print.prt` controls which objects are printed and at what time step. WEPPpy stores it as `Swat.print_prt` (bitmask per object) seeded from the template and renders it during build.
- Default daily outputs enable `channel_sd`, `hyd`, and basin `basin_wb`; `recall` is off unless explicitly enabled for QA.
- Recall outputs include `recall_day.txt`, `recall_mon.txt`, `recall_yr.txt`, and `recall_aa.txt` and are optional (enable when validating the WEPP handoff).
- Routing unit outputs include `ru_day.txt`, `ru_mon.txt`, `ru_yr.txt`, and `ru_aa.txt`.
- Hydrograph outputs (`hydin_*` and `hydout_*`) can be enabled to confirm object-to-object connections.

Sources:
- https://swatplus.gitbook.io/io-docs/introduction-1/simulation-settings/print.prt
- https://swatplus.gitbook.io/io-docs/introduction-1/simulation-settings/print.prt/object
- https://swatplus.gitbook.io/io-docs/swat%2B-output-files/recall
- https://swatplus.gitbook.io/io-docs/swat%2B-output-files/hydrographs
- https://swatplus.gitbook.io/io-docs/swat%2B-output-files/routing-unit
### Channel routing choice: SWAT-DEG vs. standard channel objects
- The SWAT+ IO docs mark `channel` output objects as "currently not used," while `channel_sd` is the SWAT-DEG channel output object.
- Connectivity for SWAT-DEG channels uses `chandeg.con`, which points to `channel-lte.cha`; the `channel.con` connection is currently not used.
- The active channel input files listed include `channel-lte.cha` and `hyd-sed-lte.cha`; the legacy `channel.cha`, `hydrology.cha`, and `sediment.cha` are marked as currently not used.
**Adopt SWAT-DEG as the canonical channel object set for WEPPpy integration.**

Sources:
- https://swatplus.gitbook.io/io-docs/introduction-1/simulation-settings/print.prt/object
- https://swatplus.gitbook.io/io-docs/introduction/connectivity
- https://swatplus.gitbook.io/io-docs/introduction-1/connectivity/hru.con/hru
- https://swatplus.gitbook.io/io-docs/introduction-1/master-file-file.cio

## Proposed integration mapping (WEPP -> SWAT+)

### Data mapping (daily)
| WEPP output | SWAT+ recall field | Notes |
| --- | --- | --- |
| Daily runoff volume | FLO | Convert to m^3 per day. |
| Daily sediment yield | SED | Convert to metric tons per day. |
| Optional nutrient/constituent outputs | ORGN/SEDP/NO3/SOLP/etc. | Use only if WEPP provides compatible daily loads. |
| Particle size fractions | SAN/SIL/CLA/SAG/LAG/GRV | Use WEPP's 5 classes; set GRV to 0. |

### Particle size class mapping (WEPP -> SWAT+)
WEPP hillslope pass files store per-class sediment concentration and per-class load fraction for `i = 1..npart`, where `npart` defaults to 5 in this codebase (`npart = 5` in `src/inidat.for`). The hillslope pass file write call includes both `sedcon(i,nplane)` and `frcflw(i,nplane)` arrays for `i = 1..npart` in `src/wshpas.for` (the `write (48,1000)` record). These are WEPP's sediment class concentrations and class fractions per runoff event/day.

WEPP's class order is defined in `src/wshimp.for` where the fractions are mapped:
`pcl = frac(1)`, `psl = frac(2)`, `psa = frac(3)`, `pla = frac(4)`, `psd = frac(5)`,
corresponding to **clay, silt, small aggregate, large aggregate, sand**.

Map these to SWAT+ recall daily sediment class loads as follows (metric tons per day):
| WEPP class index | WEPP class | SWAT+ recall field |
| --- | --- | --- |
| 1 | clay | CLA |
| 2 | silt | SIL |
| 3 | small aggregate | SAG |
| 4 | large aggregate | LAG |
| 5 | sand | SAN |

SWAT+ has a gravel field (GRV); WEPP hillslope pass files do not provide a gravel class, so set **GRV = 0** and keep the per-class loads consistent with total `SED`.

### File wiring
1. Create `recall.rec` with one record per WEPP hillslope (or per aggregated hillslope group). Use `TYP = 1` for daily inputs.
2. For each record, create a `recall_day.rec`-style time series file with NBYR, header, and daily rows.
3. Update `file.cio` to include `recall.rec` (and ensure `recall.con` is listed in the connect section).
4. Populate `recall.con` to connect each recall object to the desired downstream object (channel, routing unit, or outlet).

### Per-hillslope recall file organization (WEPP IDs)
Use WEPP hillslope IDs for all recall naming and joins.

Recommended layout:
```
<run>/swat/TxtInOut/
  file.cio
  recall.rec
  recall.con
  recall/
    hill_00001.rec
    hill_00002.rec
    ...
```

Conventions:
- WEPP hillslope outputs are expected at `wepp/output/H<wepp_id>.pass.dat`.
- Use the same `wepp_id` in:
  - `recall.rec` NAME field
  - recall filename (use a basename like `hill_{wepp_id:05d}.rec`)
  - `recall.con` recall object identifier
- Prefer zero-padded IDs to keep filenames sortable and consistent.
- **Important:** SWAT+ reads `recall.rec` with list-directed input, which treats `/` as an end-of-record marker. Keep `recall.rec` filenames free of path separators. If you store recall files under `TxtInOut/recall/`, copy/flatten them into `TxtInOut/` before running SWAT+.

### Time alignment
Ensure SWAT+ `time.sim` covers the same simulation period as the WEPP daily output, and that `ISTEP` values align with day-of-year numbering for each `IYR`. SWAT+ accepts start years like `1` as long as `time.sim` and all time-series inputs (recall, climate) use the same year numbering.

## WEPPpy + WBT + Peridot resource inventory (for SWAT inputs)

### Delineation outputs (weppcloud-wbt)
The WBT backend produces the core watershed rasters and network topology used by Peridot:
- `dem/wbt/subwta.tif`: TOPAZ-style hillslope/channel IDs (channels end in `4`).  
  (see `weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/hillslopes_topaz.spec.md`)
- `dem/wbt/netw.tsv`: channel link table with connectivity, link length, elevations, order, and upstream areas.  
  (see `weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/hillslopes_topaz.spec.md`)
- Supporting rasters used by Peridot (`relief.tif`, `flovec.tif`, `fvslop.tif`, `taspec.tif`)  
  (see `peridot/README.md`)

### Abstraction outputs (Peridot)
Peridot turns the WBT topology into WEPP-ready slope files and metadata tables:
- `watershed/channels.csv`: channel geometry + metadata columns  
  (`topaz_id`, `slope_scalar`, `length`, `width`, `direction`, `order`, `aspect`, `area`, `elevation`, `centroid_*`)  
  (see `peridot/src/watershed_abstraction/flowpath_collection.rs`)
- `watershed/hillslopes.csv`: hillslope geometry + metadata columns  
  (`topaz_id`, `slope_scalar`, `length`, `width`, `direction`, `aspect`, `area`, `elevation`, `centroid_*`)  
  (see `peridot/src/watershed_abstraction/flowpath_collection.rs`)
- `watershed/network.txt`: channel connectivity graph (key | upstream list)  
  (see `peridot/src/topaz/netw.rs`)
- `watershed/slope_files/channels.slp` and `watershed/slope_files/hillslopes/*.slp`: WEPP slope profiles  
  (see `peridot/README.md`)

### WEPPpy post-processing (ID mapping + parquet)
WEPPpy converts Peridot CSVs to parquet and adds WEPP ID mappings. **Assume these parquet files are the canonical inputs** for SWAT integration:
- `watershed/hillslopes.parquet` + `watershed/channels.parquet` with `wepp_id` and `chn_enum`  
  (see `wepppy/topo/peridot/peridot_runner.py`)
- Mapping logic for Topaz IDs ↔ WEPP IDs and channel enumeration  
  (see `wepppy/topo/watershed_abstraction/wepp_top_translator.py`)

### WEPP hillslope pass outputs (time series for recall)
WEPPpy parses the master hillslope pass file into event tables:
- `pass_pw0.txt` → `pass_pw0.events.parquet` and `pass_pw0.metadata.parquet`  
  (see `wepppy/wepp/interchange/watershed_pass_interchange.py`)
- Event rows include `runvol`, `sedcon_1..n`, `frcflw_1..n`, and identifiers (`wepp_id`, `julian`, etc.)  
  (see `wepppy/wepp/interchange/watershed_pass_interchange.py`)
- Particle-class order in the pass file is defined by the WEPP source (see `src/wshimp.for` in this repo).

## Peridot -> SWAT+ network and recall.con mapping

This section describes how to use Peridot outputs to construct the SWAT+ channel network, assign channel parameters, and generate `recall.con`.

### Source files
- Channel geometry and order: `watershed/channels.csv` (Peridot).
- Channel connectivity: `watershed/network.txt` (Peridot).
- Channel drainage area: `dem/wbt/netw.tsv` (WBT).
- Hillslope identifiers and mapping: `watershed/hillslopes.parquet` + `watershed/channels.parquet` (WEPPpy).
- Hillslope recall time series: `wepp/output/H{wepp_id}.*` (WEPP hillslope pass files).

### Channel objects and parameters (SWAT-DEG)
For each channel (one per `topaz_id` ending in `4`):
1. Identify the channel row in `watershed/channels.csv` and `watershed/channels.parquet`.
2. Populate geometry:
   - `CHL` (length) from `channels.csv:length` (meters).
   - `CHS` (slope) from `channels.csv:slope_scalar` (dimensionless).
   - `CHW` (width) from either:
     - Bieger 2015 regressions (`--bieger2015-widths`), or
     - QSWAT+ width formula `CHW = WM * DA^WE` using `netw.tsv:areaup` (km^2).
   - `CHD` (depth) from QSWAT+ depth formula `CHD = DM * DA^DE` using `netw.tsv:areaup`.
3. Populate channel type and roughness/erodibility defaults from WEPPcloud advanced options (see table above):
   - `mann`, `fpn`, `erod_fact`, `cov_fact`, `d50`.

Channel IDs:
- Use `watershed/channels.parquet` to map `topaz_id` -> `wepp_id` and `chn_enum`.
- The SWAT+ `chandeg.con` should use consistent channel indices (typically `chn_enum`).

### Channel connectivity (SWAT-DEG)
`watershed/network.txt` stores downstream -> upstream mappings:
```
<downstream_topaz_id>|<upstream_topaz_id>,<upstream_topaz_id>,...
```
To build `chandeg.con`:
1. Convert all Topaz channel IDs in `network.txt` to SWAT channel indices using `channels.parquet` (`topaz_id` -> `chn_enum`).
2. For each downstream channel, write connect records linking each upstream channel to the downstream channel.
3. Ensure the output ordering is topologically valid (upstream-to-downstream or use SWAT+ object indexing rules).

### recall.con construction (one recall per hillslope)
Each hillslope recall object must be connected to its **immediate downstream channel**:
1. For each hillslope `topaz_id` in `watershed/hillslopes.parquet`, compute the channel Topaz ID:
   - `chn_topaz_id = topaz_id + (4 - (topaz_id % 10))` (i.e., map 1/2/3 -> 4).
2. Map `chn_topaz_id` to `chn_enum` using `watershed/channels.parquet`.
3. Use the hillslope `wepp_id` as the recall object identifier (consistent with recall file naming).
4. Write `recall.con` records that connect each recall object to its `chandeg` channel index.

Notes:
- Use sequential recall object numbers in `recall.rec` to avoid sparse allocations in SWAT+.
- Keep recall file names aligned with `wepp_id` (see per-hillslope recall organization above).
## Sufficiency check for SWAT inputs

### Recall (point source/inlet) inputs
**Sufficient** to build SWAT+ recall time series:
- Daily water volume (m^3): `runvol` plus optional components controlled by flags:
  - `include_subsurface`: add `sbrunv`
  - `include_tile`: add `drrunv`
  - `include_baseflow`: add `gwbfv` (WEPP-forest baseflow; written separately from `runvol/sbrunv/drrunv`)
- Daily sediment by class: use WEPP `sedcon_1..5` and `frcflw_1..5` with `runvol` to compute class loads, then map to SWAT+ CLA/SIL/SAG/LAG/SAN.
- Stable ID mapping: `topaz_id` → `wepp_id` (WEPPpy) and channel connectivity from `network.txt`.

### Channel parameterization (SWAT-DEG)
**Partially sufficient** for geometry and connectivity:
- Available now: channel length, slope, width, order, area, and network topology (`channels.csv`, `netw.tsv`, `network.txt`).
- **Missing / needs derivation** for SWAT-DEG channel inputs:
  - Channel cross-section (bankfull depth, side slopes, bottom width if required separately from width).
  - Manning roughness for bed/banks.
  - Bed/bank erodibility and critical shear (or equivalent SWAT-DEG sediment parameters).
  - Channel material/cover indicators (e.g., sediment grain size or protection factor).
  - Any initial or calibration parameters required by `channel-lte.cha` / `hyd-sed-lte.cha`.

### Where SWAT+ channel parameters usually come from (docs-based)
- **Geometry (width, depth, slope, length)**: SWAT+ IO docs list these as "calculated by QSWAT+" in `hyd-sed-lte.cha`, i.e., derived from GIS/delineation inputs. This aligns with using WBT/Peridot outputs plus empirical width–area or width–order relationships.  
  (see `hyd-sed-lte.cha` in SWAT+ IO docs)
- **Channel order**: `channel-lte.cha` explicitly includes ORDER along with CHW/CHD/CHS/CHL and Manning’s n; order is part of the channel record definition.  
  (see `CHANNEL-LTE.CHA` in the SWAT+ input/output PDF)
- **Roughness (Manning’s n)**: The SWAT+ input documentation provides Manning’s n tables by channel type (e.g., earth vs. natural streams), implying roughness is selected from reference tables/landcover rather than derived from area alone.  
  (see Manning’s n table in SWAT+ input/output PDF)
- **Erodibility / cover / bed material**: SWAT+ documentation describes erodibility as a material property (measurable via jet tests) and provides guidance for related parameters (e.g., hydraulic conductivity by bed material). These are typically sourced from literature, field data, or calibration, not purely from drainage area.  
  (see SWAT+ theoretical docs for channel erodibility; SWAT+ input/output PDF for CHK and CHEROD guidance)

### Is it reasonable to use uparea/order/width rules?
Yes for **geometry**: using upstream area and/or order to derive width/depth/slope is consistent with how QSWAT+ populates geometry fields, and `hyd-sed-lte.cha` explicitly treats these as computed values.  
For **roughness, erodibility, D50, cover**: use lookup tables (by channel type/landcover/material) or calibration; area/order alone is usually insufficient.

### QSWAT+ width and depth estimation (bankfull geometry)
QSWAT+ estimates bankfull geometry using power-laws on drainage area:  
`width = WM * DA^WE` and `depth = DM * DA^DE` where `DA` is drainage area in km^2, `WM/WE` are width parameters, and `DM/DE` are depth parameters. The computed values are stored in GIS tables (`gis_channels.wid2/dep2` for main channels and `gis_lsus.wid1/dep1` for tributary/LSU channels).  
Sources: QSWAT+ manual section "Channel widths and depths".  
https://www.scribd.com/document/525723843/QSWATPlus-Manual-v2-0-1

### Bieger 2015 regional regression widths (WEPPpy canonical)
Bieger et al. (2015) provides regional regressions for bankfull width (and depth) as a function of drainage area. WEPPpy exposes this as the canonical width option via `--bieger2015-widths` in the Peridot abstraction workflow.  
Sources:  
https://swat.tamu.edu/media/114657/bieger_etal_2015.pdf  
https://digitalcommons.unl.edu/usdaarsfacpub/1515/  
`wepppy/topo/peridot/peridot_runner.py`, `peridot/README.md`

### Peridot implementation note (support both width methods)
- Use `netw.tsv` drainage area for each channel link (WBT `areaup` is in m^2) and convert to km^2 before applying either formula.  
  (see `weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/hillslopes_topaz.spec.md`)
- Implement a model flag to choose width method:
  - `width_method = qswat` -> `width = WM * DA^WE`
  - `width_method = bieger2015` -> regional regression widths
- Depth can follow QSWAT+ (`depth = DM * DA^DE`) regardless of width method, unless a regional depth regression is also enabled.

## Additional data that may be desirable
- A consistent channel-parameter lookup (by order, geology, or landuse) to fill roughness and erodibility gaps.
- Bieger (2015) width regressions (`--bieger2015-widths`) are the canonical WEPPpy workflow when channel widths must be derived from drainage area.  
  (see `wepppy/topo/peridot/peridot_runner.py` and `peridot/README.md`)
- Explicit aggregation rules if multiple hillslopes are injected into a single SWAT channel (using `channel_hillslopes` and `network.txt`).  
  (see `wepppy/topo/watershed_abstraction/wepp_top_translator.py`)

## WEPPcloud advanced options (SWAT+ channel parameters)

Expose the following as user-facing overrides, with safe defaults and clear hints. These map directly to `hyd-sed-lte.cha` fields in SWAT+.

| UI label | SWAT+ field | Default | Range (doc) | Suggested hint text |
| --- | --- | --- | --- | --- |
| Channel Manning's n | `mann` | 0.05 | Typical 0.025-0.150 (Chow, 1959 table in SWAT+ docs) | "Roughness for the main channel. Choose from the SWAT+ Manning's n reference table based on channel condition (clean, winding, weedy, etc.)." |
| Floodplain Manning's n | `fpn` | n/a | Typical 0.025-0.150 (same table) | "Roughness for the floodplain. Use the same Manning's n table; higher values for dense vegetation." |
| Channel erodibility factor | `erod_fact` | 0.01 | >= 0 (no explicit range in SWAT+ IO docs); SWAT 2012 IO lists 0.001-3.75 cm^3/N-s for Kd (if using jet-test values). | "Channel bed/bank erodibility. If you have jet-test (ASTM D5852-95) results, use the derived Kd; otherwise start with default and calibrate." |
| Channel cover factor | `cov_fact` | 0.01 | 0-1 | "0 = fully protected by vegetation; 1 = bare/fully exposed. Start low for vegetated channels." |
| Channel median sediment size (D50) | `d50` | 12 mm | > 0 (range not specified in SWAT+ IO docs) | "Representative median bed material size. Use local bed material data when available; otherwise choose a class-consistent value." |

References: SWAT+ `hyd-sed-lte.cha` field definitions and ranges, SWAT+ Manning's n table, SWAT+ channel erodibility theory, and SWAT 2012 IO guidance on erodibility ranges.  
https://swatplus.gitbook.io/io-docs/introduction-1/channels/hyd-sed-lte.cha  
https://swatplus.gitbook.io/io-docs/introduction-1/channels/hyd-sed-lte.cha/mann  
https://swatplus.gitbook.io/io-docs/theoretical-documentation/section-7-main-channel-processes/sediment-routing/channel-erodibility-factor  
https://swat.tamu.edu/media/69374/ch25_input_rte.pdf  

### Advanced options schema stub
Use this as a starting point for the WEPPcloud control layer (names + validation).

```yaml
swat:
  channel_params:
    mann:
      label: Channel Manning's n
      default: 0.05
      min: 0.001
      max: 0.2
      hint: Roughness for the main channel. Choose from the SWAT+ Manning's n table based on channel condition.
    fpn:
      label: Floodplain Manning's n
      default: null
      min: 0.001
      max: 0.2
      hint: Roughness for the floodplain. Use the same Manning's n table; higher for dense vegetation.
    erod_fact:
      label: Channel erodibility factor
      default: 0.01
      min: 0.0
      max: null
      hint: Channel bed/bank erodibility. Use jet-test derived Kd if available; otherwise calibrate.
    cov_fact:
      label: Channel cover factor
      default: 0.01
      min: 0.0
      max: 1.0
      hint: 0 = fully protected by vegetation; 1 = bare/fully exposed.
    d50_mm:
      label: Channel D50 (mm)
      default: 12.0
      min: 0.001
      max: null
      hint: Representative median bed material size. Use local bed material data when available.
```

## Validation checkpoints
- If validating recall handoff, enable recall outputs in `print.prt` (toggle `swat.print_prt.objects.recall` or the mask) and compare `recall_day.txt` to the injected WEPP time series.
- Enable routing unit outputs to verify downstream mass balance and channel routing response.
## Open questions / risk items
- What level of sediment partitioning is needed (total SED only vs. size-class fractions) for channel process fidelity?
- Are nutrient/pesticide loads required, or is hydrology + sediment sufficient for the first phase?
- Which empirical or lookup methods will supply missing SWAT-DEG channel parameters (roughness, erodibility, cross-section)?

## Current progress (2026-01)
- SWAT NoDb end-to-end build succeeds, including recall conversion, connectivity, and template patching.
- Recall files now match SWAT+ daily format and are calendar-aware (Rust output or Python fallback).
- `recall.rec` filenames are sanitized (no `/`); recall files are copied into `TxtInOut/`.
- `recall.con` AREA_HA is populated from hillslope areas.
- `om_water.ini` and `plant.ini` are generated when missing; `hru-data.hru` `surf_stor` set to `null`.
- Aquifer objects/outflows are disabled by default to avoid missing aquifer connectivity.
- Guarded SWAT+ binary maintained in fork to prevent floating-point exceptions in channel routines.

## Checklist issues
- [x] Align recall years with `time.sim`/climate (either offset recall years or update `time.sim`/weather inputs).
- [x] Fix `time.sim` patching: update manifest paths after recall flattening or derive bounds directly from `recall.rec`.
- [x] Correct `_read_recall_bounds` to parse `jday/mo/day_mo/iyr` (or make format detection header-driven).
- [x] Validate `recall_wst` against `weather-sta.cli` and fail fast on unknown stations (avoid undefined search results).
- [x] Decide single source of truth for recall daily format: emit SWAT+ daily rows directly in Rust **or** make Python conversion mandatory + validated.
- [x] Update `object.cnt` recall counts using only `status=written` entries (avoid skipped-file desyncs).
- [x] Wire `time_start_year` into recall export or `time.sim` patching (config currently unused).
- [x] Harden `build_recall_connections` mapping; document/guard nonstandard TOPAZ IDs.
- [x] Use calendar-aware month/day conversion during recall conversion (leap years + non-Gregorian calendars).
- [x] Revisit `recall_subdir` flattening; either keep `TxtInOut/recall/` or document/validate the flattening step.
- [x] Replace `netw.tsv` area unit heuristic with an explicit unit check or config override.
- [x] Ensure `width_method=bieger2015` does not silently fall back to QSWAT regression unless explicitly requested.
- [x] Document/validate `WST` defaults for `recall.con`/`chandeg.con` (default `auto`).
- [x] Patch `recall.con` AREA_HA from hillslope parquet (SWAT area_calc/out expects non-zero recall areas).
- [x] Ensure `om_water.ini` and `plant.ini` exist in `TxtInOut` (template safety).
- [x] Patch `hru-data.hru` surface storage (`surf_stor`) to `null` to avoid wetland init crashes.
- [x] Disable aquifer objects/outflows unless aquifer connectivity is explicitly provided.
- [x] Maintain a guarded SWAT+ binary (numeric stability patches) in the fork.

### Test criteria
- Time alignment: `time.sim` start/end years cover recall years (or recall years offset to match climate). When `force_time_start_year` is set, recall + `time.sim` start at that year.
- Recall format: SWAT reads recall files without format warnings; `recall_day.txt` matches input totals (flo/SED/classes) for a sampled hillslope.
- Connectivity: `recall.con` + `chandeg.con` generate non-empty `hydin_*`/`hydout_*` outputs for SWAT-DEG channels.
- Station mapping: every `WST` in `recall.con`/`chandeg.con` resolves to a row in `weather-sta.cli`.
- Counts: `object.cnt` `rec` count equals number of rows in `recall.rec` (written only).
- Calendar handling: leap-year day 366 preserved when present; CLI calendar lookup (when provided) yields continuous dates; Gregorian fallback clamps to valid months/days.
- Subdir layout: `recall.rec` uses basenames (no `/`), and root-level recall files exist even if `TxtInOut/recall/` is used for storage.
- Area/geometry sanity: channel widths/depths positive; drainage areas plausible and consistent with `netw_area_units`.
- Aquifer disabled: `object.cnt` shows `aqu=0` (and `aqu2d=0` when present) and `rout_unit.con` has no `aqu` outflows.
- Stability: SWAT run completes without SIGFPE on baseline WEPP-SWAT runs.
## References
- https://swatplus.gitbook.io/io-docs/introduction-1/input-file-format
- https://swatplus.gitbook.io/io-docs/introduction-1/master-file-file.cio
- https://swatplus.gitbook.io/io-docs/introduction/connectivity
- https://swatplus.gitbook.io/io-docs/introduction-1/connectivity/hru.con/hru
- https://swat.tamu.edu/media/116078/inputs_swatplus.pdf
- https://swatplus.gitbook.io/io-docs/introduction-1/simulation-settings/print.prt
- https://swatplus.gitbook.io/io-docs/introduction-1/simulation-settings/print.prt/object
- https://swatplus.gitbook.io/io-docs/swat%2B-output-files/recall
- https://swatplus.gitbook.io/io-docs/swat%2B-output-files/hydrographs
- https://swatplus.gitbook.io/io-docs/swat%2B-output-files/routing-unit
- https://swatplus.gitbook.io/io-docs/introduction-1/channels/hyd-sed-lte.cha
- https://swatplus.gitbook.io/io-docs/introduction-1/channels/hyd-sed-lte.cha/mann
- https://swatplus.gitbook.io/io-docs/theoretical-documentation/section-7-main-channel-processes/sediment-routing/channel-erodibility-factor
- https://swat.tamu.edu/media/69374/ch25_input_rte.pdf
- https://www.scribd.com/document/525723843/QSWATPlus-Manual-v2-0-1
- https://swat.tamu.edu/media/114657/bieger_etal_2015.pdf
- https://digitalcommons.unl.edu/usdaarsfacpub/1515/
