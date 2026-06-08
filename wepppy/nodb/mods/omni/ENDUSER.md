# Omni Scenarios and Contrasts

Omni has two related but different features:

- **Omni Scenarios** create whole-run alternatives from one project so you can compare burned, unburned, and treatment cases side by side.
- **Omni Contrasts** apply a treatment scenario only to selected hillslopes or areas so you can test targeted treatment strategies.

Most users should start with **Omni Scenarios** and stop there unless they specifically need targeted treatment placement. Scenarios are the easier and more common workflow. Contrasts are more advanced and are best used after you already understand the scenario results.

## What This Is For

Use Omni when you want to answer questions such as:

- How different would this watershed look if it were unburned instead of burned?
- How do low-, moderate-, and high-severity scenarios compare?
- How much could mulch, thinning, or prescribed fire reduce runoff or erosion?
- What happens if I treat only the hillslopes contributing the most runoff or soil loss?

Omni works by cloning your project into organized child runs under `_pups/omni/`, rebuilding the needed inputs, running WEPP, and collecting the results into comparison-ready outputs.

## When to Use It

Use **Omni Scenarios** when you need full-project alternatives such as:

- an `undisturbed` companion run for a burned project,
- uniform low-, moderate-, or high-severity alternatives,
- treatment scenarios such as mulch, thinning, or prescribed fire,
- scenario comparisons in reports, GL-Dashboard, and Storm Event Analyzer.

Use **Omni Contrasts** when you need a more specific question answered, such as:

- what happens if I treat only the hillslopes driving most of the runoff problem,
- what happens if I treat a mapped polygon area,
- what happens if I treat selected hillslope groups or subcatchments.

For a burned-versus-unburned comparison, prefer adding an Omni `undisturbed` scenario instead of creating a separate forked run. That path is faster in wall time and keeps the comparison available directly in scenario-aware tools such as GL-Dashboard and Storm Event Analyzer.

## Before You Begin

Before using Omni, make sure you have:

- a project that already runs successfully,
- a clear question you want to compare,
- the treatment types or severity alternatives you want to test,
- enough confidence in the base project inputs that comparisons are worth interpreting.

If you plan to use **Contrasts**, build and review the **Scenarios** first. Contrasts depend on having meaningful control and treatment scenarios to compare.

## Key Terms and Settings

| Setting or term | What it means | Typical values | Why it matters |
| --- | --- | --- | --- |
| Scenario | A full cloned run with altered burn severity or treatment settings | `undisturbed`, `uniform_low`, `uniform_high`, `mulch`, `thinning`, `prescribed_fire` | Scenarios are the main way to compare whole-project alternatives |
| Contrast | A targeted treatment application to selected hillslopes or areas | One contrast run per selected area or group | Contrasts answer where a treatment would help most |
| Control scenario | The baseline scenario used for comparison in a contrast build | Often `uniform_high` or another burned case | Defines the untreated condition |
| Contrast scenario | The treatment scenario applied to the selected hillslopes | Often `mulch`, `thinning`, or `undisturbed` | Defines the treated condition |
| `undisturbed` scenario | An Omni scenario with no fire effects | Scenario key `undisturbed` | The recommended companion run for burned-versus-unburned comparison |
| Selection mode | How Contrast chooses hillslopes or areas | Cumulative contribution, user-defined areas, user-defined hillslope groups, stream-order grouping | Controls where the treatment is applied |
| Base scenario | The scenario a dependent scenario builds from | Often `undisturbed` or a burn scenario | Important for treatment logic such as mulch or prescribed fire |

## Omni Scenarios

### What Scenarios Do

Omni Scenarios create complete alternative runs from one project. Each scenario becomes its own child run under `_pups/omni/scenarios/`, with its own WEPP inputs and outputs.

This is the right tool when your question is about comparing whole-run alternatives.

### Recommended Scenario Workflow

1. Add the **Omni Scenarios** mod to the project.
   Expect a new Omni control panel to appear.

2. Start with the scenario set that answers your main question.
   For burned-versus-unburned comparison, start by adding `undisturbed`.

3. Add any additional severity or treatment scenarios you need.
   Common choices are `uniform_low`, `uniform_moderate`, `uniform_high`, `mulch`, `thinning`, and `prescribed_fire`.

4. Run the scenarios.
   Expect Omni to clone the project, rebuild the needed inputs, run WEPP, and store each scenario under `_pups/omni/scenarios/`.

5. Compare results in the scenario report, GL-Dashboard, or Storm Event Analyzer.
   Expect those tools to treat Omni scenarios as comparable alternatives rather than unrelated runs.

### Scenario Types

| Scenario type | What it means | When to use it |
| --- | --- | --- |
| `undisturbed` | No fire effects | Best first comparison for a burned project |
| `uniform_low` | Low severity everywhere | Sensitivity testing or planning-level comparison |
| `uniform_moderate` | Moderate severity everywhere | Sensitivity testing or planning-level comparison |
| `uniform_high` | High severity everywhere | Worst-case style comparison |
| Custom SBS map | Spatially variable burn severity from a raster | When you have a mapped severity product |
| `mulch` | Post-fire ground cover treatment | When you want to test erosion reduction after fire |
| `thinning` | Pre-fire canopy and fuel reduction treatment | When you want to test a forest treatment alternative |
| `prescribed_fire` | Low-intensity fire treatment in forest context | When you want to compare planned low-intensity burning against wildfire outcomes |

### Important Scenario Notes

- For many users, the most useful first step is adding an `undisturbed` scenario to a burned project.
- `mulch` scenarios depend on a burned base scenario because mulch is applied after fire.
- `thinning` and `prescribed_fire` run in an undisturbed context. If your project base is burned, include an Omni `undisturbed` scenario so those scenarios have the correct clone context.
- Scenario list order is not the same as execution order. Omni resolves dependencies internally.

## Omni Contrasts

### What Contrasts Do

Omni Contrasts are for targeted treatment placement. Instead of treating the whole project, Contrasts apply the treatment scenario only to selected hillslopes or areas and then compare the treated result against a control scenario.

This is the right tool when your question is not "Which whole scenario is better?" but rather "Where should I apply the treatment?"

### Recommended Contrast Workflow

1. Build and review your scenarios first.
   Expect to choose a control scenario and a treatment scenario from that scenario set.

2. Pick the control and contrast scenarios.
   A common pattern is a burned control scenario plus a treatment scenario such as mulch.

3. Choose a selection mode.
   This determines which hillslopes will receive the treatment in each contrast run.

4. Run the contrasts.
   Expect Omni to create targeted child runs under `_pups/omni/contrasts/`.

5. Review the contrast report.
   Expect watershed-level and targeted-area comparisons between the untreated control and the treated result.

### Contrast Selection Modes

| Selection mode | What it does | Best use |
| --- | --- | --- |
| Cumulative contribution | Selects hillslopes contributing the most runoff or soil loss up to a threshold | Prioritizing treatment on the most influential hillslopes |
| User-defined areas | Uses uploaded polygons to define treatment zones | Testing mapped treatment areas |
| User-defined hillslope groups | Uses hillslope IDs you provide | Testing known groups of hillslopes |
| Stream-order grouping | Groups hillslopes by drainage structure | Testing subcatchment-scale treatment ideas |

### User-Defined Areas

If you use polygon areas, hillslopes are included when at least half of the hillslope area falls inside a polygon. This makes the result easier to interpret, but it also means polygon boundaries do not create exact partial-hillslope treatment fractions.

### Stream-Order Grouping

Stream-order grouping bundles hillslopes by where they sit in the drainage network, so each contrast treats one drainage unit at a time instead of individual hillslopes.

Streams have an "order" that describes their place in the network. Small headwater channels are low order. Where channels join, they form larger, higher-order channels downstream. Stream-order grouping uses this structure to organize hillslopes by the part of the network they drain into.

Here is what happens when you choose this mode:

- Omni first simplifies the channel network by trimming the smallest headwater tributaries. The **Order reduction passes** setting controls how much trimming is done: each pass removes another level of the smallest remaining headwater channels. The minimum is 1, and 1 is the default. A higher number leaves fewer, larger channels, which produces fewer and broader groups. A lower number keeps more channels and produces more, smaller groups.
- The watershed is then re-divided around the simplified network, so each remaining channel segment gathers the hillslopes that drain to it into one group.
- Each original hillslope is assigned to the group it overlaps the most. Every hillslope ends up in exactly one group.
- Channel areas themselves are not treated as hillslope groups.

Omni then creates one contrast for every group, for each control-and-treatment scenario pair you selected. That lets you compare what happens when a treatment is applied to one drainage unit at a time, rather than to hand-picked hillslopes or mapped polygons.

Use this mode when your question is about drainage structure, such as which subcatchments contribute the most or where treatment at the drainage-unit scale would help most. If a group ends up with no hillslopes after trimming, its contrast is skipped and noted in the report.

## Interpreting Results

### Scenario Results

Scenario outputs are most useful for:

- burned versus unburned comparison,
- comparing whole-treatment alternatives,
- understanding how runoff and sediment respond at hillslope and watershed scale,
- checking scenario differences directly in GL-Dashboard and Storm Event Analyzer.

Useful scenario outputs include:

- watershed totals,
- hillslope summaries,
- scenario report tables,
- `scenarios.out.parquet`,
- `scenarios.hillslope_summaries.parquet`.

### Contrast Results

Contrast outputs are most useful for:

- estimating the benefit of treating selected hillslopes,
- identifying whether a small treated area can reduce a large part of the problem,
- comparing targeted treatment placement strategies.

Useful contrast outputs include:

- contrast report tables,
- per-contrast run outputs under `_pups/omni/contrasts/`,
- `contrasts.out.parquet`.

When interpreting contrasts, remember that the result reflects both:

- the quality of the underlying control and treatment scenarios,
- the hillslope-selection method you chose.

## Assumptions and Limits

- Omni comparisons are only as good as the base project inputs and the scenario definitions you start from.
- Scenarios compare whole-run alternatives. Contrasts compare targeted treatment placement and should not be confused with whole-watershed treatment scenarios.
- For a burned-versus-unburned comparison, Omni `undisturbed` is usually a better workflow than creating a separate forked run, because it keeps the runs inside one comparison system.
- Contrasts are more advanced and easier to misinterpret if the control scenario, treatment scenario, or selection mode is poorly chosen.
- User-defined area contrasts use hillslope inclusion rules, not exact partial-area treatment fractions.
- Scenario and contrast outputs are modeled estimates, not field measurements. They still require professional judgment.

## Troubleshooting

| Problem | What it usually means | What to check |
| --- | --- | --- |
| Scenario results are hard to compare | Too many scenarios were built at once or the base comparison is unclear | Start with `undisturbed` plus one or two key alternatives before expanding |
| A treatment scenario does not behave as expected | The scenario may depend on the wrong base context | Check whether mulch is tied to a burned base and whether thinning or prescribed fire need `undisturbed` context |
| Contrast results are confusing | The scenario pair or selection mode may not match the question you are asking | Recheck the control scenario, contrast scenario, and selection mode |
| Targeted treatment seems to have little effect | The selected hillslopes may not drive much runoff or sediment, or the treatment may be too limited spatially | Review the selection method and compare against scenario-wide treatment results |

## Related Docs

- [Omni Module README](README.md)
- [Getting Started](../../../weppcloud/routes/usersum/weppcloud/getting-started.md)
- [WEPP Model](../../../weppcloud/routes/usersum/weppcloud/wepp-model.md)
- [GL Dashboard Notes](../../../../docs/ui-docs/gl-dashboard.md)
- [Storm Event Analyzer Notes](../../../../docs/ui-docs/storm-event-analyzer.md)
