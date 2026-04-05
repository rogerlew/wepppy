# WEPPcloud-(Un)Disturbed-Earth

Use **WEPPcloud-(Un)Disturbed-Earth** when your watershed is outside the current United States, Europe, and Australia regional interfaces. This page describes the global Earth workflow launched by `earth.cfg`, including what data stack it uses, when it is the right starting point, and what to check before you trust the results.

## What This Page Helps You Do

This interface gives you a global version of the familiar disturbed or undisturbed WEPPcloud workflow. It uses the **WBT** delineation backend, so watershed preprocessing follows the newer WEPPcloud-WBT path instead of the older TOPAZ path. You can:

- start an **undisturbed** run by skipping burn severity input,
- start a **post-fire** run by supplying a burn severity map when you have one,
- use the built-in **ash** and **debris-flow** modules available in the Earth configuration,
- build a first-pass watershed model in places where no more specialized regional interface exists.

If your project is in the conterminous United States, Hawaii, Alaska, Europe, or Australia, prefer those dedicated interfaces first. They use more region-specific soils, land cover, and climate handling.

## What The Earth Interface Uses

| Component | Earth interface default | Why it matters |
| --- | --- | --- |
| Terrain | `Copernicus DEM 30 m` | Gives broad global elevation coverage for watershed delineation. |
| Watershed delineation | `WEPPcloud-WBT` with `breach_least_cost` conditioning | Uses the newer WBT preprocessing path for channels and hillslopes. |
| Land cover | `C3S land cover` with the `c3s-disturbed` mapping | Converts global land-cover classes into WEPPcloud landuse and management assumptions. |
| Soils | `ISRIC` global soils | Provides the baseline soil-property source where SSURGO or other regional databases are not available. |
| Climate | `CLIGEN` stations selected from `ghcn_stations.db` | Supplies the stochastic weather basis for the run. |
| Disturbance setup | `sol_ver = 9002` | Uses the disturbed-soil parameter family also used in other disturbed workflows. |
| Enabled modules | `disturbed`, `debris_flow`, `ash` | Supports post-fire erosion, debris-flow screening, and ash transport workflows. |

In practice, this means the Earth interface is best read as a **broad-coverage screening workflow**. It is designed to get you to a usable model in data-sparse areas, not to outperform region-specific interfaces where those exist. It also means Earth is closer in delineation behavior to the WBT-based workflows than to the legacy TOPAZ workflows.

## Recommended Workflow

1. Start with the Earth interface only when your watershed falls outside a better regional option.
2. Keep the first watershed modest in size so you can inspect the terrain, channels, land cover, and soils before scaling up.
3. Build the watershed in undisturbed mode first if your main question is baseline runoff or erosion.
4. Add burn severity only after the baseline run looks reasonable and the watershed geometry is correct.
5. Review land cover, soils, and climate carefully before interpreting sediment totals or treatment differences.

The most important early check is whether the global input layers look plausible for your watershed. If the hillslopes, land cover, or soils look obviously wrong, fix that understanding first rather than calibrating around a bad starting setup.

## Limits and Common Mistakes

| Common issue | What to do instead |
| --- | --- |
| Using Earth for a watershed in the United States, EU, or AU | Use the dedicated regional interface first. Those data stacks are usually more defensible. |
| Treating global land cover and soils as field-verified truth | Read them as generalized inputs that need a reasonableness check. |
| Starting with a very large basin | Begin with a smaller test watershed and confirm the setup before expanding the area. |
| Jumping straight to post-fire scenarios | Run the undisturbed case first so you have a baseline for comparison. |
| Over-interpreting climate precision in remote areas | Check whether the selected climate behavior is reasonable for the site, especially where station coverage is sparse or elevation gradients are strong. |

The Earth workflow is especially useful when you need a consistent first-pass method across multiple countries or remote areas. Its main limitation is that global layers are usually more generalized than local or national datasets.

## Related Docs

- [Getting Started](getting-started.md)
- [WEPPcloud Data Attribution](data-attribution.md)
- [Disturbed Land Soil Lookup](disturbed-land-soil-lookup.md)
