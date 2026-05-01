# Hillslope MOFE Water-Balance Contract

## Purpose
This contract defines the **full physical daily water-balance closure audit** for MOFE (multi-OFE hillslope) diagnostics in `tools/hillslope_mofe_daily_closure_audit.py`.

Scope constraints:
- Source-of-truth producer behavior is `/workdir/wepp-forest`.
- Contract equations use WEPP variable names first, then map to interchange fields.
- MOFE chain checks focus on adjacent OFE transfer semantics.

## Source Evidence Index
### Producer source (`/workdir/wepp-forest`)
- R1 Daily water-output term definitions, including `RM`, `Q`, `UpStrmQ`, `SubRIn`, `latqcc`, `QOFE`, `Tile`, `SoilWaterTotal`, profile-capacity terms: `/workdir/wepp-forest/src/outfil.for:620-646`
- R2 Channel-format-only extra terms (`Surf`, `Base`) and separate header branch: `/workdir/wepp-forest/src/outfil.for:655-692`
- R3 Interception is removed from infiltration input (`fin`) using `plaint`/`resint`/`pintlv`: `/workdir/wepp-forest/src/watbal.for:331-346`
- R4 Non-channel MOFE runon transfer equations and first-OFE zero runon behavior: `/workdir/wepp-forest/src/watbal.for:355-370`
- R5 Contour/channel runon branch (`runoffin = roffon`) and channel subsurface aggregation branch: `/workdir/wepp-forest/src/watbal.for:352-355,404-423`
- R6 Lateral subsurface generation and clipping (`latqcc`, `sbrunf`, shortfall correction): `/workdir/wepp-forest/src/watbal.for:694-709,732-735,783-784`
- R7 WEPP internal (commented) daily water-balance check equation and `watcon` update context: `/workdir/wepp-forest/src/watbal.for:954-999`
- R8 Water-file write mapping for `RM`, `Q/QOFE`, `UpStrmQ`, `SubRIn`, `latqcc`, `Tile`, `Irr`, `SoilWaterTotal`: `/workdir/wepp-forest/src/watbal.for:1023-1024,1073-1105`
- R9 Interception ET component (`etplcp`) is computed but not written in `H.wat` record: `/workdir/wepp-forest/src/watbal.for:942-951,1077-1105`
- R10 Hillslope outlet runoff volume (`runvol`) on final OFE: `/workdir/wepp-forest/src/contin.for:1237-1246`
- R11 PASS serialization of `runvol`, `sbrunf`, `sbrunv`; `sbrunv = sbrunf * slplen * fwidth`: `/workdir/wepp-forest/src/wshpas.for:154-165,220-223,230-237`
- R12 Optional element runoff partition terms (`QRain`, `QSnow`): `/workdir/wepp-forest/src/sedout.for:461-477,481-494`; header: `/workdir/wepp-forest/src/outfil.for:725-731`

### WEPP published documentation (interpretation anchor)
- D1 Canonical WEPP daily water-balance equation (Chapter 5 Eq. 5.1.1), with interception term `I`: https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/chap5.pdf
- D2 Subsurface-routing/channel-era context (`SUBEVENT`, upstream subsurface contribution routing):
  - https://www.ars.usda.gov/midwest-area/west-lafayette-in/national-soil-erosion-research/docs/wepp/wepp-release-notes/
  - https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/subsurface.pdf

## Canonical Physical Basis
WEPP Chapter 5 Eq. 5.1.1 expresses daily water balance with explicit interception (`I`) and storage change terms (D1).

Producer implementation evidence in `watbal` shows the same physical structure:
- Interception is explicitly subtracted in infiltration/water-input formation (`fin`) (R3).
- OFE runon terms are explicitly added (`runoffin`, `subrin`) (R4, R5).
- Lateral flow and deep percolation terms are generated and removed (R6).
- A code-commented daily balance check equation exists for `watcon` updates (R7).

## Normative Terms for This Audit
Per OFE/day, this audit uses:
- Inputs: `RM`, `UpStrmQ`, `SubRIn`
- Outputs: `QOFE`, `latqcc`, `Dp`, `Ep`, `Es`, `Er`, `Tile`
- Storage candidates:
  - preferred: `SoilWaterTotal + Snow-Water`
  - fallback: `Total-Soil Water + frozwt + Snow-Water`

Root-zone/profile clarification:
- WEPP documentation often frames Eq. 5.1.1 in root-zone terms (D1).
- Interchange exports are profile-oriented (`SoilWaterTotal`, profile capacities) from `watbal` write logic (R1, R8).
- This audit therefore computes closure on exported profile terms and reports basis explicitly.

## Full Physical Closure Equations (Audit Contract)
### 1. Known exported-term closure (per OFE/day)
Define:
- `ET = Ep + Es + Er`
- `KnownInputs = RM + UpStrmQ + SubRIn`
- `KnownOutputs = QOFE + latqcc + Dp + ET + Tile`
- `Storage = SoilWaterTotal + Snow-Water` when `SoilWaterTotal` is available
- else `Storage = Total-Soil Water + frozwt + Snow-Water`
- `DeltaStorage(d) = Storage(d) - Storage(d-1)` per OFE

Residual:
- `Residual_full_exported = KnownInputs - KnownOutputs - DeltaStorage`

Interpretation:
- `Residual_full_exported = 0` means exported terms close for that OFE/day.
- Non-zero residual is interpreted as an **implied unresolved term** from canonical physics that is not fully observable in interchange (for example interception and other unexported storage/flux components).

### 2. Daily hillslope aggregation (contracted output)
Per day, aggregate OFE terms by area-weighted volume and convert back to depth:
- `mm_day = 1000 * sum(mm_ofe * Area_ofe * 0.001) / sum(Area_ofe)`

The tool reports:
- daily full-physics residual depth,
- max/mean absolute OFE residual for the day,
- outlier OFE id + residual,
- whole-run quantiles and totals.

### 3. Unresolved-term interpretation (required)
Because `H.wat` does not export all canonical Eq. 5.1.1 terms, the tool must label residuals as:
- `implied_unresolved_term_mm` (same signed magnitude as `Residual_full_exported`), and
- not as strict model mass-balance failure by default.

Evidence for missing exported terms:
- Interception handling is explicit in runtime physics (R3), but interception terms are not exported as standalone `H.wat` columns (R1, R8).
- `etplcp` (interception ET component) is computed internally but not included in the water-file write record (R9).
- `Surf` and `Base` are channel-format terms only and not in the standard non-channel hillslope format used for `H.wat` interchange (R1 vs R2).

## Interchange Mapping Contract
### H.wat (required)
Required for full-physics closure in this package:
- `RM`, `UpStrmQ`, `SubRIn`, `QOFE`, `latqcc`, `Dp`, `Ep`, `Es`, `Er`, `Tile`, `Area`, `OFE`
- storage: `Snow-Water` and one of:
  - preferred `SoilWaterTotal`, or
  - fallback `Total-Soil Water` + `frozwt`

Optional diagnostics:
- `P`, `Irr`, profile-capacity terms, `QRain`, `QSnow` (via optional `H.element`) for contextual interpretation.

### H.pass (required)
Used for outlet reconciliation diagnostics:
- `runvol` (m^3)
- `sbrunv` (m^3)

Producer basis:
- outlet `runvol` generation in `contin` (R10)
- pass serialization and subsurface event handling in `wshpas` (R11)

## MOFE-to-MOFE Transfer Closure Checks
Per day and adjacent OFE pair `(i-1 -> i)` ordered upslope-to-downslope:

1. `subsurface_transfer_residual_m3`
- `SubRIn(i)*0.001*Area(i) - latqcc(i-1)*0.001*Area(i-1)`
- strict near-zero invariant under non-channel/non-contour branch semantics (R4, R6).

2. `surface_transfer_residual_m3_geometry_sensitive`
- `UpStrmQ(i)*0.001*Area(i) - QOFE(i-1)*0.001*Area(i-1)`
- diagnostic only; geometry-sensitive because exact transfer uses `efflen/slplen` factors not exported in interchange (R4, R8).

3. `first_ofe_runon_checks`
- minimum OFE id per day should have `UpStrmQ ~= 0`, `SubRIn ~= 0` under non-channel branch semantics (R4).

Applicability note:
- Strict adjacent-chain invariants apply to non-channel/non-contour semantics only.
- Channel/contour routing branches use different runon construction and channel subsurface accumulation (R5), so these are diagnostic/N/A there.
- This gating is scientifically consistent with the subsurface-routing/channel-era updates described in D2.

## Hillslope-Scale Runoff Reconciliation Check
Daily diagnostic between required interchange datasets:
- `runoff_pass_m3 = sum(H.pass.runvol for day)`
- `runoff_wat_outlet_qofe_m3 = QOFE(outlet_ofe)*0.001*Area(outlet_ofe)`
- `runoff_pass_vs_wat_outlet_residual_m3 = runoff_pass_m3 - runoff_wat_outlet_qofe_m3`

This is a producer-consistency diagnostic (R8, R10, R11), not an unconditional zero invariant in all routing/threshold branches.

## Selector and Input Contract (Tooling)
- Selector: exactly one of `--wepp-id` or `--topaz-id`.
- Required inputs: interchange directory containing `H.wat.parquet` and `H.pass.parquet`.
- Optional diagnostics: `H.soil.parquet`, `H.element.parquet`.

## Non-Goals
- This contract does not change WEPP physics.
- Residual diagnostics are constrained by exported term coverage.
- Optional diagnostics must never block baseline artifact generation.
