# totalwatsed3 Aggregation
> Fuses WEPP hillslope water, sediment, and ash-transport outputs into a single daily table served as `totalwatsed3.parquet`.

## Overview
`totalwatsed3.parquet` is produced by `wepppy.wepp.interchange.totalwatsed3.run_totalwatsed3`. The helper reads the per-hillslope interchange artifacts emitted by WEPP (`H.pass.parquet`, `H.wat.parquet`) and, when present, optional soil/element diagnostics (`H.soil.parquet`, `H.element.parquet`) plus WEPP–Ash Transport summaries under `<run>/ash`. The rows are grouped by simulation date (`year`, `julian`, `sim_day_index`, etc.) so that each record represents the watershed-wide totals for a given day:

- Most hydrologic volumes (m³) are summed from `H.wat`, then converted back to depths (mm) via watershed area.
- `Runoff` depth is computed from `H.pass` runoff volume (`runvol`) over aggregated watershed area.
- Sediment masses are derived from the pass file (`H.pass`) and converted to both kg (`seddep_*`) and a dimensionless volumetric concentration (`sed_vol_conc`).
- Optional ash metrics are joined by date and scaled using either supplied area hints or the Watershed controller (per-ash-type mass totals plus volumetric concentration/black fraction when bulk densities are known).

The resulting table is written to `<run>/wepp/output/interchange/totalwatsed3.parquet` using the schema defined in `totalwatsed3.py`.

## Source Artifacts

| Artifact | Path | Purpose |
| --- | --- | --- |
| Hillslope PASS | `H.pass.parquet` | Event-scale runoff, detachment, and sediment concentration (`sedcon_*`) for every WEPP hillslope. |
| Hillslope WAT | `H.wat.parquet` | Daily hydrology terms (`Area`, `Q`, `Ep`, …) per hillslope/OFE combination. |
| Hillslope SOIL (optional) | `H.soil.parquet` | Daily soil profile state; `TSMF` is used for full-profile true moisture fraction when present. |
| Hillslope ELEMENT (optional) | `H.element.parquet` | Daily event partitioning; `QRain` and `QSnow` are area-weighted into watershed-scale depths when present. |
| Ash Transport (optional) | `<run>/ash/H{wepp_id}_ash.parquet` | Daily ash water/wind transport statistics per hillslope, merged when present. |

Only the PASS file includes per-particle sediment concentrations (`sedcon_1`-`sedcon_5`, kg m⁻³). Those values are multiplied by the per-event runoff volume (`runvol`, m³) to recover per-class sediment mass in kilograms. The water-balance terms come from `H.wat` where inputs are expressed as depths (mm); the aggregator multiplies each depth by the contributing area to recover volumes, performs any needed sums, and finally divides by area again to restore depths.

PASS, WAT, optional soil, and optional element aggregations each use a separate
DuckDB connection. Closing a connection after its result is materialised releases
its scan and aggregation buffers before the next large parquet query begins; the
connections must not be combined into one long-lived interchange session.

## Output Snapshots

Key output columns (see `SCHEMA` in `totalwatsed3.py` for the complete list):

- `runvol`, `sbrunv`, `tdet`, `tdep`: watershed totals (m³ or kg).
- `seddep_1`–`seddep_5`: total mass per sediment class (kg) computed as `Σ sedcon_i * runvol`.
- `sed_del`: total daily sediment delivery (kg), computed as `Σ seddep_i`.
- `sed_vol_conc`: watershed-wide volumetric sediment concentration (m³ of solids per m³ of runoff).
- `Area`, `P`, `RM`, `Q`, `Dp`, `latqcc`, … : volumetric sums from `H.wat`, later converted to depths (`Precipitation`, `Lateral Flow`, etc.).
- `SoilWaterTotal`, `ProfileDepth`, `ProfilePorosityCap`, `ProfileFCStore`, `ProfileWPStore`: optional producer-authoritative storage/capacity terms from `H.wat` in mm. They are null for legacy WEPP executables that do not emit the additive columns.
- `TSMF`: area-weighted true soil moisture fraction from `H.soil` when available (null when absent).
- `QRain`, `QSnow`: area-weighted runoff-partition depths from `H.element` when available (null when absent).
- MOFE aggregation rules (multi-OFE hillslopes): per-OFE columns in `H.wat` are not all physically summable across OFEs without producing a non-canonical total. `totalwatsed3` handles this by:
  - **`latqcc`**: uses only the outlet-facing (last) OFE per hillslope/day to avoid counting internal lateral-routing transfers multiple times. DuckDB first computes one maximum OFE identifier per hillslope and joins that small lookup into the daily aggregate; it does not retain a per-row partition window over the full WAT table.
  - **`Runoff` (the user-facing column)**: computed from `H.pass.runvol` volume divided by aggregated watershed area, not from summed `Q` or `QOFE`. `runvol` is the canonical hillslope runoff volume under both legacy and `wepp_260516`+ builds.
  - **`Q` and `QOFE` aggregate columns** (the literal `SUM(col * 0.001 * Area)` over OFEs): retained for diagnostic continuity but **not** the canonical hillslope totals. Under `wepp_260516` and later, per-OFE `QOFE = Q` in `H.wat`, so the two aggregates are equal post-fix. Under legacy builds the per-OFE `QOFE` was inflated by an OFE-count-scaled factor that did not appear in `Q`; see the canonical definitions for the per-OFE `Q`, `QOFE`, and `Area` columns in the main interchange README [§H.wat Multi-OFE Schema Semantics](README.md#hwat-multi-ofe-schema-semantics) and the historical context in `/workdir/wepp-forest/docs/20260504-stakeholder-watbalance.md` §QOFE: canonical definition.
- Ash transport columns when the ash directory is available:
  - Totals and per-area masses: `wind_transport`, `water_transport`, `ash_transport`, `transportable_ash` (+ `_per_ha`).
  - Per-ash-type masses: `{wind,water,ash}_transport_{black,white}` (+ `_per_ha` via per-type area).
  - Ash volumetrics: `ash_vol_conc` (ash solids volume / runoff), `sed+ash_vol_conc` (sediment + ash solids volume / runoff), `ash_black_pct_by_vol` (% of ash solids volume that is black ash).

Nulls from missing PASS or ash rows are filled with zeros before the final Arrow table is materialised.

## Storage Terms

`Total-Soil Water` in `H.wat` is WEPP's unfrozen profile-water term. It is not interchangeable with `TSW` in `H.soil`, which is a top-layer diagnostic. When available, prefer `SoilWaterTotal` for full-profile storage closure because WEPP emits it as `watcon + frozwt`.

The optional `H.wat` capacity terms are direct WEPP outputs in mm: `ProfileDepth = solthk(nsl)`, `ProfilePorosityCap = sum(por * dg)`, `ProfileFCStore = sum(thetfc * dg)`, and `ProfileWPStore = sum(thetdr * dg)`. `totalwatsed3` area-weights these fields when present and preserves nulls when parsing legacy layouts.

## Volumetric Concentration Details

### WEPP Provenance
Within WEPP/WEPP-Forest the per-class sediment concentrations are derived directly from erosion physics:

- `sloss.for:305-316` computes `sedcon(ipart,nplane)` on the last OFE of every hillslope as:  
  `sedcon = avsole / (runoff * efflen) * frcflw`, resulting in kg m⁻³.
- `wshimp.for:235-244` performs the same calculation for impoundment routed flows: class-specific sediment masses (`clout`, `slout`, …) are divided by `runvol` to yield kg m⁻³.

The WEPP particle system sets explicit specific gravities (unitless) for the five canonical classes inside `prtcmp.for:122-126`:

| Class | Description | Specific Gravity | Density (kg m⁻³) |
| --- | --- | --- | --- |
| 1 | Primary clay | 2.60 | 2 600 |
| 2 | Primary silt | 2.65 | 2 650 |
| 3 | Small aggregates | 1.80 | 1 800 |
| 4 | Large aggregates | 1.60 | 1 600 |
| 5 | Primary sand | 2.65 | 2 650 |

Specific gravity × 1 000 kg m⁻³ (density of water) yields the absolute particle density used to convert mass to volume.

### Implementation in `totalwatsed3`

`totalwatsed3.py` implements the following steps for every grouped day:

1. Aggregate class masses per day: `seddep_i = Σ sedcon_i * runvol`.
2. Compute total sediment delivery: `sed_del = Σ_i seddep_i`.
3. Convert each class to solids volume: `V_i = seddep_i / ρ_i` where `ρ_i` is the density from the table above.
4. Sum the solids volume: `V_total = Σ_i V_i`.
5. Divide by total runoff: `sed_vol_conc = V_total / runvol_total` (guarded so zero runoff yields zero concentration).
6. When ash is present, compute `ash_vol_conc` using per-hillslope ash masses and bulk densities from `Ash.meta` (defaulting to baked-in black/white values); `sed+ash_vol_conc` adds sediment solids; `ash_black_pct_by_vol` reports the black-ash share of ash solids volume.

This mirrors the physics in WEPP: the numerator reconstructs the actual cubic meters of sediment solids mobilised that day, while the denominator is the water volume those solids travelled with. The resulting value is dimensionless (m³ m⁻³) and represents the watershed-average volumetric sediment concentration for that day. `totalwatsed3` stores it immediately after the `seddep_*` columns so future stakeholders can append per-class volumetric fractions alongside it.

### Proof Sketch

- WEPP emits `sedcon_i` in kg m⁻³ (`sloss.for:305-316`, `wshimp.for:235-244`).
- `totalwatsed3` multiplies `sedcon_i` by `runvol` (m³) to obtain kg (`seddep_i`).
- Dividing each `seddep_i` by the class density (kg m⁻³) produces a solids volume (m³).
- Summing those volumes and dividing by the aggregated `runvol` (m³) cancels the units, giving m³ m⁻³, matching the physical definition of volumetric concentration.

Consequently `sed_vol_conc` is a direct, unit-consistent translation of the WEPP physics into the aggregated daily dataset, with specific-gravity metadata baked in so per-class volumetric columns can be added without re-litigating the derivation.
