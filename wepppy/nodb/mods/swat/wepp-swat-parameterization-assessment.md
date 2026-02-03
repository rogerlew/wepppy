# WEPP–SWAT+ Parameterization Assessment (Hydrology, Sediment, Nutrients, Water Quality)

> Goal: identify which **SWAT+** parameters are worth exposing in WEPPcloud for calibration when SWAT+ is used primarily for **routing/channel processes** on top of **WEPP hillslope** outputs.
>
> Context: current integration uses SWAT+ **recall** objects to inject WEPP time series into the SWAT-DEG channel network. See:
> - `wepppy/nodb/mods/swat/swat-nodb-spec.md` (NoDb/UI contract)
> - `wepppy/nodb/mods/swat/wepp-swat-spec.md` (IO mapping + current exposed fields)

## Scope (Mode A only)

This assessment assumes the current integration pattern: **WEPP-forced, channel-only SWAT+**.

WEPP provides the **inflow hydrograph and sediment loads** (daily) via recall files. SWAT+ then provides:
- Channel hydraulics (routing residence time, losses, attenuation).
- Channel sediment processes (deposition, re-entrainment, bank erosion, sorting).
- Optional in-stream nutrients / water quality **if** nutrient constituent inputs are provided (currently they are not).

Implication: classic SWAT land-phase calibration knobs like `cn2`, `alpha_bf`, `gw_delay`, `sol_awc`, etc. mostly do **not** influence outlet flow/sediment when the basin is being force-fed by recall objects. Calibration should focus on:
- Recall preprocessing (scaling/bias correction; if allowed).
- Channel geometry + roughness + bed conductivity.
- SWAT-DEG sediment parameters.
- In-stream nutrient kinetics (only if loads are injected).

## Inventory: SWAT+ input surfaces currently in play

The current WEPP–SWAT+ assembly is template-based (copy + patch). In the shipped template (`wepppy/nodb/mods/swat/templates/ref_1hru/`), channel process control is primarily via:

- `hyd-sed-lte.cha` (channel hydraulic + sediment properties per channel “hyd” record)
- `nutrients.cha` (channel nutrient/water-quality kinetics per channel “nut” record)
- `channel-lte.cha` (wires each channel object to an `initial.cha` + a `hyd-sed-lte.cha` record + a `nutrients.cha` record)
- `parameters.bsn`, `codes.bsn` (basin-level flags and some global coefficients)
- recall: `recall.rec` + per-hillslope recall daily files + `recall.con` (WEPP injection)

Other template surfaces that may be useful later for calibration automation (not a Mode A UI priority):
- `cal_parms.cal` (SWAT+ editor list of calibratable parameters + min/max by object type)
- `calibration.cal` (example calibration file; HRU-oriented in the shipped template)

WEPPpy currently patches (at least):
- `hyd-sed-lte.cha` (uniform overrides applied to every record for a small subset: `mann`, `fpn`, `erod_fact`, `cov_fact`, `d50`).
- `channel-lte.cha`, `chandeg.con`, `object.cnt`, `time.sim`, `file.cio`, `recall.con` area.

## What SWAT parameters should be exposed (recommended)

Design constraint for WEPPcloud UX: expose *few* knobs by default; group the rest behind “Advanced / Expert” panels and/or named “profiles”. Also prefer **uniform** (global) overrides first; per-order/per-channel can be a Phase 2.

### A. Channel hydrology / routing (Mode A)

Primary goal: match observed **hydrograph timing and attenuation** given fixed inflows.

Recall note: if your WEPP variant provides explicit groundwater baseflow volume (e.g., `gwbfv` in `H.pass.parquet`), include it in recall `flo` (set `swat.include_baseflow=true`) to better match WEPP watershed streamflow. Deep seepage (`gwdsv`) should not be injected; it is a loss on the WEPP side.

Recommended additions (high leverage, low ambiguity):

| User-facing knob | Suggested config key | SWAT+ file/field | Why it matters |
| --- | --- | --- | --- |
| Channel bed hydraulic conductivity (alluvium/bed seepage) | `swat.channel_k` | `hyd-sed-lte.cha:k` | Controls transmission losses (especially arid/alluvial systems). |
| Width scale factor | `swat.channel_wd_scale` | `hyd-sed-lte.cha:wd` (multiply) | Width strongly affects velocity, depth, travel time, shear stress. |
| Depth scale factor | `swat.channel_dp_scale` | `hyd-sed-lte.cha:dp` (multiply) | Same; also affects wetted perimeter and erosion capacity. |
| Slope scale factor | `swat.channel_slp_scale` | `hyd-sed-lte.cha:slp` (multiply) | Affects hydraulics + sediment transport capacity. |
| Floodplain roughness | `swat.channel_fpn` (already) | `hyd-sed-lte.cha:fpn` | Influences overbank flow attenuation (when active). |

Keep (already exposed / already required):
- `swat.channel_mann` (`hyd-sed-lte.cha:mann`)
- `swat.width_method` + (`qswat_*` coefficients or Bieger widths) for first-pass geometry.

Conditional / expert-only (depends on how SWAT-DEG uses these in your revision/template):
- `hyd-sed-lte.cha:fps`, `hyd-sed-lte.cha:wd_rto`, `hyd-sed-lte.cha:eq_slp`, `hyd-sed-lte.cha:side_slp`

Notes:
- If geometry is derived (QSWAT+ power law or regional regressions), “scale factors” are more stable for calibration UX than exposing absolute per-channel width/depth.
- Consider a “force geometry regen” action for large edits (so derived fields stay internally consistent).

### B. Channel sediment (SWAT-DEG) (Mode A)

Primary goal: match observed **suspended sediment** (and, if available, bed change or depositional patterns) given fixed WEPP-delivered sediment.

Recommended additions (high leverage):

| User-facing knob | Suggested config key | SWAT+ file/field | Why it matters |
| --- | --- | --- | --- |
| Channel erodibility factor | `swat.channel_erod_fact` (already) | `hyd-sed-lte.cha:erod_fact` | Bank/bed erosion sensitivity; often calibration-critical. |
| Channel cover factor | `swat.channel_cov_fact` (already) | `hyd-sed-lte.cha:cov_fact` | Protection/armoring proxy; strongly affects erosion. |
| Median bed material size (D50) | `swat.channel_d50_mm` (already) | `hyd-sed-lte.cha:d50` | Controls transport capacity and deposition. |
| Bedload fraction | `swat.channel_bed_load_frac` | `hyd-sed-lte.cha:bed_load` | Partitions total load into bed vs suspended (affects deposition/transport). |

Recommended additions (often important when calibrating nutrients/adsorbed P or sediment composition):

| User-facing knob | Suggested config key | SWAT+ file/field | Why it matters |
| --- | --- | --- | --- |
| Bank/bed clay fraction | `swat.channel_clay_pct` | `hyd-sed-lte.cha:clay` | Affects cohesion + adsorbed P behavior. |
| Bank/bed carbon fraction | `swat.channel_carbon_frac` | `hyd-sed-lte.cha:carbon` | Influences organic matter related processes (model dependent). |
| Bank/bed dry bulk density | `swat.channel_dry_bd` | `hyd-sed-lte.cha:dry_bd` | Mass conversion for bed/bank processes. |

Defer (needs clarity on SWAT+ revision behavior + how WEPP sediment classes are used downstream):
- Any attempt to calibrate particle-size fractions via SWAT parameters; instead, treat this as a **recall mapping**/preprocessing problem (WEPP class-to-SWAT class mapping + possible bias correction).

### C. In-stream nutrients / water quality (Mode A)

Important constraint: SWAT+ cannot “invent” nutrients/water quality without sources. With recall-only injection, you need to supply constituent loads/concentrations into recall (daily file columns like `orgn`, `sedp`, `no3`, `solp`, `chla`, `nh3`, `no2`, `cbod`, `dox`, bacteria, metals) before in-stream calibration is meaningful.

#### C1. Expose recall constituent injection (prerequisite)
Even though this is not strictly “SWAT parameterization”, it is essential for any WQ goal in a WEPP-forced system:
- Allow user-supplied constituent time series (CSV upload, or link to existing run artifacts).
- Or support simple concentration-based derivation: `load = flow * concentration`, with concentrations configurable by landuse/region/profile.

Suggested first-pass config (global constants; later allow per-hillslope class):
- `swat.recall_no3_mg_l`, `swat.recall_solp_mg_l`, `swat.recall_orgn_mg_l`, `swat.recall_sedp_mg_l`, `swat.recall_chla_ug_l`, `swat.recall_cbod_mg_l`, etc.

#### C2. Expose channel nutrient kinetics (SWAT+ `nutrients.cha`)
The template ships a single nutrient record (`nutcha1`) wired to all channels via `channel-lte.cha:cha_nut`.

Recommendation: implement “named profiles” first, then allow overrides of a small subset of coefficients:
- Profile selection: `swat.channel_nutrients_profile = nutcha1` (or allow `nutcha2`, etc).
- Expert overrides (uniform across channels) for the most calibratable/identifiable parameters:
  - Nitrification: `nh3n_no2n`, `no2n_no3n`
  - Settling: `ptln_stl`, `ptlp_stl`, `cst_stl`, `cbn_bod_stl`, `alg_stl`
  - Algae: `alg_grow`, `alg_resp`, `chla_alg`, `alg_n`, `alg_p`, `alg_o2_prod`, `alg_o2_resp`
  - Oxygen: `o2_nh3n`, `o2_no2n`
  - Bacteria: `bact_die`

Keep “everything else” hidden unless you have strong use cases and supporting observations.

### D. Basin/global knobs (Mode A)

The SWAT+ templates include basin-level parameter files:
- `wepppy/nodb/mods/swat/templates/ref_1hru/parameters.bsn`
- `wepppy/nodb/mods/swat/templates/ref_1hru/codes.bsn`

In Mode A, most basin/landscape parameters are either irrelevant or currently marked “not used” in SWAT+ IO docs. Still, a few global knobs can matter when they influence channel processes directly.

Recommended (only if verified in your SWAT+ revision that they are active in the channel configuration you run):
- `parameters.bsn:cha_d50` as a global default (only if you want a basin-level fallback for channel D50).
- `codes.bsn` flags that actually change activated process modules (verify with SWAT+ docs + a micro test case).

## Prioritized exposure roadmap (pragmatic)

### Phase 1 (keep UI small; immediately useful)
- Routing: `channel_mann`, `channel_k`, `channel_wd_scale`, `channel_dp_scale`, `channel_slp_scale`
- Sediment: `channel_erod_fact`, `channel_cov_fact`, `channel_d50_mm`, `channel_bed_load_frac`
- “Advanced output controls”: `print.prt` defaults enable daily `channel_sd` + `hyd` and basin `basin_wb`; enable `recall` only for QA (or reapply via `Swat.enable_print_prt_daily_channel_outputs()`).
### Phase 2 (water quality enablement)
- Recall constituent injection (time series or concentration-derived loads).
- `nutrients.cha` profile selection + a short list of expert overrides.

### Phase 3 (higher dimensional calibration)
- Parameter-by-order (Strahler order bins) for `mann`, `k`, `erod_fact`, `cov_fact`, `d50`, geometry scalars.
- Optional per-subbasin/per-channel overrides (requires UX design + guardrails).

## What information would help refine this assessment

To make the recommended exposure list tighter (and avoid surfacing “dead” knobs), it would help to know:

1. SWAT+ revision/version actually targeted by the bundled binary (and whether you expect to support multiple revisions).
2. Which outputs are the calibration targets:
   - Flow only, flow + sediment, or flow + sediment + nutrients/water quality?
3. Whether you intend to provide nutrient/WQ sources (and from where):
   - WEPP-derived loads, external monitoring loads, EMC-based derivation, point sources?
4. Which observation data streams are available for calibration (and their time scale):
   - Daily flow, sediment concentration/loads, NO3/SRP/TP, chlorophyll-a, DO/BOD, bacteria.
5. Whether channel transmission losses are expected to be important (arid vs humid settings).
6. Desired calibration workflow:
   - Manual tuning in WEPPcloud UI, scripted calibration runs (batch), or SWAT-CUP integration (SUFI-2/GLUE/PSO)?

## References (starting points)

- SWAT+ IO docs (GitBook):
  - `hyd-sed-lte.cha`: https://swatplus.gitbook.io/io-docs/introduction-1/channels/hyd-sed-lte.cha
  - `nutrients.cha`: https://swatplus.gitbook.io/io-docs/introduction-1/channels/nutrients.cha
  - `codes.bsn`: https://swatplus.gitbook.io/io-docs/introduction-1/basins/codes.bsn
  - `parameters.bsn`: https://swatplus.gitbook.io/io-docs/introduction-1/basins/parameters.bsn
- SWAT-CUP manual (Abbaspour): https://swat.tamu.edu/software/swat-cup/
- Sensitivity examples (parameter grouping and identifiability patterns): SWAT-CUP documentation + widely cited SWAT sensitivity studies.
