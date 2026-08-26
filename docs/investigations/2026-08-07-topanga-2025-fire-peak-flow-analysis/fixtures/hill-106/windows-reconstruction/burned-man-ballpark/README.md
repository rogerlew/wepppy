# Burned Management Ballpark

This derived fixture records the Windows WEPP management sweep used to
ballpark W. Elliot's reported Hill 106 burned water balance. All runs used the
vendored climate and slope, the reconstructed burned AR=10 `7778` soil, no
hydrology sidecars, and `C:\WEPP\wepp\wepp_2024.exe` on `blarhg`.

## Method

The first 45-year, 32-lane factorial sweep replaced each of the five records
that differ between the WEPPcloud burned and undisturbed management files. It
isolated three consequential changes:

- maximum root depth: `0.2` to `0.5 m`;
- initial canopy/interrill cover: `0.27/0.55` to `0.70/0.90`;
- maximum leaf-area index: `2` to `5`.

Changing the fragile/non-fragile residue code or initial rill cover had
negligible effects. `factorial/summary.csv` contains all lanes.

The follow-up sweep fixed root depth and initial canopy/interrill cover at the
undisturbed values, varied maximum LAI from `2` through `4`, and used Elliot's
stated 40-year simulation length. `lai-summary.csv` contains all lanes.

## Closest Lane

The LAI `2.25` lane closely reproduces Elliot's rounded burned results:

| Statistic | LAI 2.25 replay | Elliot report |
| --- | ---: | ---: |
| Precipitation (mm/year) | 610.61 | 612 |
| Surface runoff (mm/year) | 245.22 | 246 |
| ET (mm/year) | 345.48 | 346 |
| Lateral flow (mm/year) | 18.23 | 18 |
| Maximum lateral flow (mm/day) | 0.80 | 0.8 |

The `lai-2p25/` directory preserves its complete input set, standard streams,
and every output requested by `p106.run`. This is a calibrated ballpark, not
proof of Elliot's original management values. The original `.man` remains the
preferred evidence.

## Reproduction

The PowerShell drivers are stored in the investigation `artifacts/` directory:

- `run_burned_man_sweep.ps1` runs the factorial screen;
- `run_burned_man_lai_sweep.ps1` runs the 40-year LAI refinement.

