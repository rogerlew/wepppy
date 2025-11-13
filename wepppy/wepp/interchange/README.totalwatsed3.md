# totalwatsed3 Aggregation
> Fuses WEPP hillslope water, sediment, and ash-transport outputs into a single daily table served as `totalwatsed3.parquet`.

## Overview
`totalwatsed3.parquet` is produced by `wepppy.wepp.interchange.totalwatsed3.run_totalwatsed3`. The helper reads the per-hillslope interchange artifacts emitted by WEPP (`H.pass.parquet`, `H.wat.parquet`) and, when present, the WEPP–Ash Transport summaries under `<run>/ash`. The rows are grouped by simulation date (`year`, `julian`, `sim_day_index`, etc.) so that each record represents the watershed-wide totals for a given day:

- Volumes (m³) from `H.wat` are summed, then converted back to depths (mm) via watershed area.
- Sediment masses are derived from the pass file (`H.pass`) and converted to both kg (`seddep_*`) and a dimensionless volumetric concentration (`sed_vol_conc`).
- Optional ash metrics are joined by date and scaled using either supplied area hints or the Watershed controller.

The resulting table is written to `<run>/wepp/output/interchange/totalwatsed3.parquet` using the schema defined in `totalwatsed3.py`.

## Source Artifacts

| Artifact | Path | Purpose |
| --- | --- | --- |
| Hillslope PASS | `H.pass.parquet` | Event-scale runoff, detachment, and sediment concentration (`sedcon_*`) for every WEPP hillslope. |
| Hillslope WAT | `H.wat.parquet` | Daily hydrology terms (`Area`, `Q`, `Ep`, …) per hillslope/OFE combination. |
| Ash Transport (optional) | `<run>/ash/H{wepp_id}_ash.parquet` | Daily ash water/wind transport statistics per hillslope, merged when present. |

Only the PASS file includes per-particle sediment concentrations (`sedcon_1`-`sedcon_5`, kg m⁻³). Those values are multiplied by the per-event runoff volume (`runvol`, m³) to recover per-class sediment mass in kilograms. The water-balance terms come from `H.wat` where inputs are expressed as depths (mm); the aggregator multiplies each depth by the contributing area to recover volumes, performs any needed sums, and finally divides by area again to restore depths.

## Output Snapshots

Key output columns (see `SCHEMA` in `totalwatsed3.py` for the complete list):

- `runvol`, `sbrunv`, `tdet`, `tdep`: watershed totals (m³ or kg).
- `seddep_1`–`seddep_5`: total mass per sediment class (kg) computed as `Σ sedcon_i * runvol`.
- `sed_vol_conc`: watershed-wide volumetric sediment concentration (m³ of solids per m³ of runoff).
- `Area`, `P`, `RM`, `Q`, `Dp`, `latqcc`, … : volumetric sums from `H.wat`, later converted to depths (`Precipitation`, `Runoff`, etc.).
- Ash transport columns (`wind_transport (tonne)`, `ash_transport (tonne/ha)`, …) when the ash directory is available.

Nulls from missing PASS or ash rows are filled with zeros before the final Arrow table is materialised.

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
2. Convert each class to solids volume: `V_i = seddep_i / ρ_i` where `ρ_i` is the density from the table above.
3. Sum the solids volume: `V_total = Σ_i V_i`.
4. Divide by total runoff: `sed_vol_conc = V_total / runvol_total` (guarded so zero runoff yields zero concentration).

This mirrors the physics in WEPP: the numerator reconstructs the actual cubic meters of sediment solids mobilised that day, while the denominator is the water volume those solids travelled with. The resulting value is dimensionless (m³ m⁻³) and represents the watershed-average volumetric sediment concentration for that day. `totalwatsed3` stores it immediately after the `seddep_*` columns so future stakeholders can append per-class volumetric fractions alongside it.

### Proof Sketch

- WEPP emits `sedcon_i` in kg m⁻³ (`sloss.for:305-316`, `wshimp.for:235-244`).
- `totalwatsed3` multiplies `sedcon_i` by `runvol` (m³) to obtain kg (`seddep_i`).
- Dividing each `seddep_i` by the class density (kg m⁻³) produces a solids volume (m³).
- Summing those volumes and dividing by the aggregated `runvol` (m³) cancels the units, giving m³ m⁻³, matching the physical definition of volumetric concentration.

Consequently `sed_vol_conc` is a direct, unit-consistent translation of the WEPP physics into the aggregated daily dataset, with specific-gravity metadata baked in so per-class volumetric columns can be added without re-litigating the derivation.
