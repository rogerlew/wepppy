# PATH Cost-Effective Quick Start

PATH Cost-Effective (PATH-CE) finds the least-cost combination of post-fire mulch
treatments that meets your sediment targets, and shows you which hillslopes to
treat on an interactive map.

## What This Is For

After a wildfire, mulching reduces erosion — but budgets are finite and not every
hillslope needs the same treatment (or any treatment). PATH-CE answers the
question: **which hillslopes should be mulched, and at what rate, to meet my
sediment goals for the least money?**

It works from Omni treatment scenarios you have already run — mulching at
½, 1, and 2 tons per acre — and compares each against the post-fire baseline.
An optimization then assigns at most one treatment per hillslope so that:

- every hillslope above your sediment-yield limit is treated down below it where
  possible, and
- average-annual sediment discharge at the watershed outlet is brought down to
  your target,

at the lowest total treatment cost. You get a summary of the selected plan, an
interactive report (treatment map, threshold sliders, and a cost surface showing
how price responds to your targets), and downloadable tables.

## When to Use It

- You have a burned-area run (SBS map) and are weighing mulch treatment options
  and budgets.
- You need a defensible, repeatable way to prioritize hillslopes for treatment
  rather than treating everything or guessing.
- You want to see how treatment cost changes as sediment targets are tightened
  or relaxed before committing to one plan.

PATH-CE currently optimizes mulching only. If you are comparing other practices
(thinning, prescribed fire), run them as Omni scenarios and compare their
outputs directly.

## Before You Begin

PATH-CE never creates Omni scenarios for you. It checks that the pieces below
exist before solving and tells you exactly what is missing, but you must
provision them first.

You need a completed WEPPcloud run with:

1. **A fire scenario.** A disturbed-land configuration with an SBS (soil burn
   severity) map uploaded, the watershed built, and WEPP run.
2. **Omni scenarios.** In the Omni Scenario Builder, add:
   - an **Undisturbed** scenario, and
   - a **Mulching** scenario for each application rate you want PATH-CE to
     consider, with **Base scenario** set to **SBS Map**. The ground-cover
     options correspond to the treatment rates: 15% ≈ ½ tons/acre, 30% ≈ 1
     ton/acre, 60% ≈ 2 tons/acre.

   Then click **Run Omni** and wait for it to finish.
3. **Omni contrasts.** In the Omni Contrasts Runner, run contrasts so each
   mulching scenario is compared against the SBS Map baseline. PATH-CE builds
   its outlet sediment numbers from these comparisons, so they are required —
   not optional.

If you configure a treatment in PATH-CE that has no matching Omni scenario or
contrast, the run stops with a message naming what to provision.

## Key Terms

- **Sediment yield (Sdyd)** — the average-annual sediment leaving an individual
  hillslope, expressed per acre (metric tonnes per acre per year). A
  hillslope-scale number.
- **Sediment discharge (Sddc)** — the average-annual sediment passing the
  watershed outlet (metric tonnes per year). A watershed-scale number.
- **Treatment** — one mulching intensity (½, 1, or 2 tons/acre), backed by an
  Omni scenario. PATH-CE assigns at most one treatment per hillslope.
- **Untreatable** — a hillslope that stays above the yield limit under every
  configured treatment, or whose yield increases under every treatment. These
  are reported separately rather than assigned a treatment.

All sediment quantities come from the WEPP/Omni model chain — they are model
estimates, not measurements.

## Settings

| Setting | What it means | Units | Why it matters |
| --- | --- | --- | --- |
| Outlet Sediment Discharge Threshold | The most average-annual sediment you will accept at the watershed outlet after treatment | tonnes/yr (display follows your unit preference) | The main watershed-scale target. Lower values demand more treatment. A value at or above the post-fire discharge removes this requirement entirely; a value of 0 asks for the maximum achievable reduction. |
| Hillslope Sediment Yield Threshold | The per-hillslope yield ceiling; hillslopes above it must be treated | tonnes/acre | Controls which hillslopes are forced into the plan. Lower values pull more hillslopes in and raise cost. Default is 15. |
| Slope ≥ / Slope ≤ | Restrict candidate hillslopes by average slope | degrees | Use when treatment is only practical (or only planned) on certain terrain. Leave blank to consider all hillslopes. |
| Burn Severities | Restrict candidate hillslopes by burn severity class | High / Moderate / Low | Use to target treatment at, for example, only high and moderate severity ground. Leave empty to include all. |
| Treatments table | Which mulch rates are available and what they cost | unit cost in $/acre; fixed cost in $ | Costs drive the optimization. The label and rate are set by the chosen Omni scenario; you edit the costs. |

Cost notes: per-hillslope cost is *area × unit cost × rate*, plus a one-time
fixed cost (mobilization, staging) charged once per treatment type used
anywhere in the plan. The default unit cost ($2,475/acre for all rates) and
fixed costs ($500 / $1,000 / $1,500) are placeholders — replace them with local
quotes before treating the dollar figures as meaningful.

## Steps

1. On your run page, enable the **Path CE** mod. The PATH Cost-Effective panel
   appears on the run page.
2. Read the **Omni Preconditions** section of the panel and confirm you have
   provisioned the Omni scenarios and contrasts described above.
3. Set the **Outlet Sediment Discharge Threshold**. To pick a realistic value,
   open the Omni Scenarios report and note the post-fire (SBS Map) outlet
   discharge — your target should normally sit below it. Leaving it at 0 asks
   for the maximum achievable reduction (see Interpreting Results).
4. Set the **Hillslope Sediment Yield Threshold**, or keep the default of 15
   tonnes/acre.
5. Optional: restrict candidates with the slope and burn-severity filters.
6. In the **Treatments** table, keep the rates you provisioned in Omni and
   remove any you did not. Enter your unit and fixed costs. Use **Add
   Treatment** to bring back a removed rate.
7. Click **Run PATH Cost-Effective**. Your settings are saved as part of the
   run — there is no separate save step.
8. Watch the status panel. A run validates preconditions, prepares data,
   solves, sweeps nearby thresholds (for the report's sliders), and renders
   the report. The first run takes the longest; repeat runs reuse the sweep
   when only sub-integer threshold changes were made.
9. When the run completes, review the summary and open the resources in the
   **Run Results** panel.

## Interpreting Results

**Solution** is the first thing to check:

- **Optimal** — your thresholds are achievable, and the plan shown is the
  least-cost way to meet them.
- **Second-best (thresholds infeasible)** — no combination of the configured
  treatments can meet your targets. PATH-CE instead reports the plan that
  maximizes outlet-discharge reduction under the same per-hillslope rules.
  This is expected when the outlet threshold is 0 or set very low. If you
  wanted a least-cost plan, raise one or both thresholds and rerun.

Other summary fields:

| Output | What it represents | How to read it |
| --- | --- | --- |
| Selected Hillslopes | Number of hillslopes assigned a treatment | The size of the plan. The map in the report shows where they are. |
| Total Cost / Total Fixed Cost | Variable (area-based) and one-time costs in $ | Only as reliable as the costs you entered. |
| Total Sddc Reduction | Combined outlet-discharge reduction from the selected treatments (tonnes/yr) | How much the plan improves the outlet. |
| Final Sddc | Modeled outlet discharge after treatment (tonnes/yr) | Compare against your threshold and the post-fire value. |
| Untreatable | Hillslopes no configured treatment can fix | These stay above the yield limit regardless of budget. Consider whether other practices apply there. |

The **Run Results** panel links the interactive report and CSV downloads
(selection, per-hillslope final yields, untreatable hillslopes, and the full
threshold sweep). In the report, the sliders and cost surface re-solve at
whole-number threshold combinations so you can explore cost sensitivity; your
exact configured run is marked distinctly, and its numbers match the summary.

## Assumptions and Limits

- All sediment values are model estimates from the WEPP/Omni chain. They are
  most useful for comparing options and prioritizing; absolute values carry
  the uncertainty of the underlying model chain. Field review is still needed
  before implementation.
- Only mulch treatments are optimized, and only the rates you provisioned in
  Omni.
- Sediment quantities are metric tonnes throughout, including where treatment
  rates are labeled "tons/acre" (the label reflects mulch application
  convention). The hillslope yield unit is metric tonnes per acre.
- Untreatable hillslopes are excluded from the plan by design, even where
  treating them would help the outlet. They are surfaced in the report instead.
- On runs whose Omni contrasts were built in grouped mode, burn severity is
  assigned per group from its dominant land cover, and a group dominated by
  unburned ground may have no severity at all — the burn-severity filter is
  most meaningful on per-hillslope contrast runs.
- The report's sliders explore whole-number thresholds only; your configured
  run uses your exact values.

## Troubleshooting

- **"Omni scenario summaries are missing treatment scenario(s) …"** — a
  treatment in your table has no matching Omni scenario. Add the Mulching
  scenario (base scenario: SBS Map) and click Run Omni, or remove that
  treatment row.
- **"… no completed 'sbs_map'-control contrasts …"** — the Omni contrasts for
  that treatment have not been run. Open the Omni Contrasts Runner and run
  contrasts against the SBS Map control.
- **Messages about missing watershed files** — the watershed has not been
  built (or was rebuilt without its outputs). Rerun the watershed steps, then
  rerun Omni.
- **"A PATH Cost-Effective run is already in progress"** — wait for the
  current job to finish; each run replaces the previous results.
- **"Report not rendered: subcatchments.WGS.geojson not found"** — the run's
  map export files are missing, so the report was skipped. The optimization
  results and CSVs are still valid.
- **Every run says Second-best** — your thresholds are stricter than any
  treatment combination can satisfy. Raise the outlet threshold toward the
  post-fire discharge, raise the yield threshold, or add higher mulch rates
  in Omni.

## Related Docs

- [Omni scenarios and contrasts](../../../../nodb/mods/omni/ENDUSER.md)
- [Mods overview](../weppcloud/mods-overview.md)
- [Getting started with WEPPcloud](../weppcloud/getting-started.md)
