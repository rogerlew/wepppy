# Hill 106 Burned–Undisturbed Input Difference Inventory

This inventory compares the prepared Hill 106 inputs for the corrected
no-restrictive-layer, natural-land `Kcb = 1.20` experiment.

## File-level comparison

| Input | Result |
| --- | --- |
| `p106.cli` | Identical |
| `p106.slp` | Identical |
| `p106.run` | Identical |
| `wepp_ui.txt` | Identical |
| `p106.man` | Six numeric differences |
| `p106.sol` | Three numeric differences plus the land-use label |
| `pmetpara.txt` | Scenario-wide record ordering and descriptions differ |

The complete numeric inventory is in
[`hill106-input-parameter-differences.csv`](hill106-input-parameter-differences.csv).
No other numeric values differ in the prepared Hill 106 management or soil
files. Both soil files end in `0 0.0 0.0`, so neither has a restrictive layer.
All horizon properties other than first-horizon Ksat are identical.

## PMET interpretation

The fourth `pmetpara.txt` field is a generated plant-loop sequence number, not
a WEPP hillslope identifier. It must not be joined to `wepp_id = 106`. The Hill
106 management plant loop is `Tah_9591`; every `Tah_9591` record in both
scenario sidecars uses `Kcb = 1.20` and `rawp = 0.8`. PMET therefore adds no
Hill 106 numeric factor to the burned–undisturbed sweep.

## Candidate binary sweep

There are nine effective numeric factors: six management values and three soil
values. A complete two-level factorial using the prepared burned and
undisturbed endpoints contains `2^9 = 512` Hill 106 runs. The text-only soil
land-use label should travel with the soil template for provenance but should
not be treated as an independent numeric factor.

Run the sweep with `wepp_260803` and score every mutation on the same fixed
event dates. Retain daily runoff and ET summaries, but use `PeakRO`, effective
duration, time of concentration, routing coefficient, and total-profile soil
moisture as the primary diagnostic responses. This design estimates main
effects and interactions without committing to a process hypothesis first.
