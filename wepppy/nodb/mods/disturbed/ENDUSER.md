# (Un)Disturbed Landuse and Soil Parameterization

In WEPPcloud's `(Un)Disturbed` interfaces, the Disturbed module is part of the normal landuse and soil-building workflow. It parameterizes hillslopes using disturbed class and burn severity so the interface can represent both unburned and burned conditions with one consistent framework.

## What This Is For

In the `(Un)Disturbed` interfaces, Disturbed is the layer that translates vegetation type and burn severity into WEPP-ready management and soil parameters. It is used for:

- unburned conditions,
- low-, moderate-, and high-severity fire conditions,
- comparisons across forests, shrublands, and grass-dominated hillslopes,
- treatment and calibration workflows that need one consistent parameterization system.

That means the Disturbed workflow is not only for post-fire maps. It also provides the default landuse and soil parameterization for unburned runs inside these interfaces.

In practice, the module does four things:

1. reads a soil burn severity (SBS) raster or a uniform severity choice,
2. combines that severity information with disturbed class information such as forest, shrub, or grass,
3. assigns lookup-based landuse and soil parameters to modeled hillslopes or OFEs,
4. updates the WEPP inputs used by the run.

The intended benefit is directional realism across heterogeneous ecosystems. In general, more severely burned parameterizations should produce more runoff and erosion than unburned parameterizations on the same hillslope, while still preserving the effects of vegetation type, soils, topography, and climate.

## How It Fits in (Un)Disturbed Interfaces

If you are using a WEPPcloud `(Un)Disturbed` interface, you are already using this workflow. Users do not normally add or remove the Disturbed module as a separate step.

Your practical choices are usually:

- which severity input represents the watershed best,
- whether to upload an SBS raster or use a uniform severity scenario,
- whether the default parameterization is adequate for the question you are asking,
- whether advanced calibration changes are needed.

For an unburned project, the workflow still runs. In that case, hillslopes are parameterized with unburned disturbed classes rather than bypassing the disturbed system entirely.

## What You Need to Review

The most important inputs to review are:

- the burn-severity input for the run,
- the vegetation classes present in the watershed,
- whether the results need only default directional behavior or more explicit calibration,
- whether the disturbed lookup table should remain at project defaults.

If you are uploading an SBS raster, the safest input is a single-band integer GeoTIFF with a valid projected coordinate system. For preparation details, see [SBS Map Utilities](../baer/README.sbs_map.md).

## Key Terms and Settings

| Setting or term | What it means | Typical values | Why it matters |
| --- | --- | --- | --- |
| SBS map | A soil burn severity raster used to classify burn effects across the watershed | Unburned, low, moderate, high | This is the main spatial input that drives post-fire parameter changes |
| Uniform severity | A single severity level applied everywhere in the watershed | Low, moderate, or high | Useful for sensitivity testing or when you do not have a mapped SBS product |
| Disturbed class | The vegetation or landuse class used by the disturbed parameterization | Forest, shrub, grass, and related classes | Disturbed class determines which management and soil adjustments apply before severity is considered |
| Dominant hillslope severity | The severity class that occupies the largest area on a modeled hillslope in standard single-OFE workflows | One class per hillslope | WEPP inputs are usually assigned at the hillslope scale, so sub-hillslope mosaics are simplified unless a workflow preserves multiple OFEs |
| `burn_shrubs` | Whether shrub hillslopes are remapped to burned shrub classes | `True` or `False` | Affects how shrub-dominated hillslopes respond in advanced or platform-level configurations |
| `burn_grass` | Whether grass hillslopes are remapped to burned grass classes | `True` or `False` | Affects how grass-dominated hillslopes respond in advanced or platform-level configurations; the current default is off |
| Disturbed land-soil lookup table | The per-project table of disturbed soil and vegetation parameters | User-editable CSV | Controls erodibility, effective hydraulic conductivity, hydrophobicity, and plant parameters, and also serves as a global calibration harness |
| Hydrophobicity | Water repellency after fire, represented through lookup-table soil parameters | Usually strongest in high-severity fire classes | Stronger hydrophobicity generally means less infiltration and more surface runoff |

## Lookup Table Schemes (Base vs Extended)

The disturbed workflow can operate on either a base lookup table or an extended lookup table. The base table is the standard calibration surface; the extended table is a generated merge that includes management-file fields.

| Lookup variant | Runtime file | Row identity fields | Plant scalar fields |
| --- | --- | --- | --- |
| Base | `disturbed/disturbed_land_soil_lookup.csv` | `luse`, `stext` | `rdmax`, `xmxlai` |
| Extended | `disturbed/disturbed_land_soil_lookup_extended.csv` | `disturbed_class`, `stext` (plus helper fields `landuse`, `sev_enum`) | `plant.data.rdmax`, `plant.data.xmxlai` |

When the extended table is generated, WEPPcloud normalizes the scalar plant keys from base (`rdmax`, `xmxlai`) into extended namespaced fields (`plant.data.rdmax`, `plant.data.xmxlai`).

## Steps

1. Start the project in a WEPPcloud `(Un)Disturbed` interface.
   Expect the interface to use the disturbed parameterization during landuse and soil building, even if the scenario is unburned.

2. Provide the severity input for the scenario.
   This may be an uploaded SBS raster or a uniform severity choice, depending on the workflow and question.

3. Upload or validate the disturbed map when a raster is being used.
   Expect WEPPcloud to generate preview products and a normalized 4-class severity map.

4. Review whether the severity input and its coverage match the watershed you intend to model.
   In standard single-OFE workflows, expect each modeled hillslope to receive one dominant severity class based on the uploaded raster.

5. Let WEPPcloud build landuse and soil inputs through the disturbed parameterization.
   Expect management and soil inputs to be assigned from disturbed class, severity, and soil texture rather than from a separate unburned-versus-burned module choice.

6. Optional: review or edit the disturbed land-soil lookup table only if you have defensible local calibration information.
   This is the main global calibration harness for adjusting landuse and soil behavior across disturbed classes and severity classes.

7. Rebuild or rerun the project after the disturbed inputs are set.
   Expect WEPPcloud to generate lookup-based management and soil inputs for the modeled hillslopes.

8. Compare unburned and burned outputs.
   Expect the largest differences in cover, infiltration, runoff, and sediment delivery where severity is moderate or high, especially on forested hillslopes.

## What the Module Changes

| Output or change | What it represents | Units or format | How to interpret it |
| --- | --- | --- | --- |
| Disturbed management files (`.man`) | Management parameterization derived from disturbed class and severity | WEPP management files | Burned classes usually reduce cover and recovery-related vegetation settings relative to unburned classes |
| Disturbed soil files (`.sol`) | Soil parameterization derived from disturbed class, severity, and texture | WEPP soil files | Higher severity classes usually lower infiltration and increase erodibility relative to unburned classes |
| Normalized 4-class SBS map | The validated burn-severity map used by the run | Raster classes | Confirms the classes actually entering the disturbed workflow |
| Hillslope runoff and sediment response | The simulated hydrologic and erosion response from the chosen disturbed parameterization | Model outputs such as runoff depth, sediment yield, or delivery | Compare across unburned and burned scenarios to understand the size and location of disturbance effects |

## Interpreting Results

The disturbed parameterization is intended to be directionally correct across mixed vegetation and soil settings. In practical terms, that means:

- unburned classes should generally behave less aggressively than burned classes,
- high-severity classes should generally produce more runoff and erosion than low-severity classes on the same hillslope,
- forest, shrub, and grass classes should still retain distinct response patterns.

High-severity fire classes usually produce the largest changes because they combine lower cover with stronger changes to infiltration and erodibility. In practical terms, this often means:

- more surface runoff,
- more frequent or larger sediment delivery,
- higher sensitivity to intense rainfall,
- larger differences between burned and unburned scenarios.

Moderate and low severity classes usually show smaller shifts, but the response still depends on vegetation type, soil texture, slope, and climate. Forest hillslopes often show larger post-fire changes than grass hillslopes because the drop in cover and interception is larger.

If results change only a little across severity scenarios, common explanations include:

- most hillslopes remained unburned,
- the dominant class on many hillslopes is still unburned or low severity,
- the watershed is dominated by vegetation or soils with weaker severity contrasts,
- grass burning was left off in a workflow where that distinction matters,
- even under burned parameterization, the watershed may still infiltrate enough water to limit large changes in runoff and erosion events,
- local soils already had low infiltration or high runoff in the baseline case.

Interpret outputs as modeled scenarios, not field measurements. The strongest comparisons are usually:

- burned versus unburned annual totals,
- hillslope-to-hillslope spatial patterns,
- frequency of runoff or sediment-producing events,
- treatment-versus-burned comparisons using the same climate inputs.

Single storm events can still behave unexpectedly because antecedent moisture matters. A more severely parameterized hillslope does not guarantee a larger response in every individual event.

The lookup table can also be used as a calibration harness. When that table is edited carefully, it lets advanced users change landuse and soil behavior globally across disturbed classes instead of tuning one hillslope at a time.

## Assumptions and Limits

- In standard single-OFE workflows, the module assigns one dominant severity class per modeled hillslope. Fine-scale burn mosaics inside a hillslope are simplified.
- Multi-OFE workflows can preserve more within-hillslope variation, but they still use lookup-based disturbed classes rather than direct measurement of every soil property.
- The current empirical basis for the default parameterization is strongest in Rocky Mountain and Pacific Northwest coniferous forest settings. Results may be less reasonable in ecosystems with very different vegetation, soils, fuels, or post-fire hydrologic response.
- Output quality depends on the quality of the SBS map, the watershed delineation, the baseline soils, and the baseline land-cover classification.
- Fire effects are represented through lookup-table parameter changes, not through direct measurement of water repellency or erosion at each site.
- Even unburned conditions in these interfaces are represented through the disturbed parameterization. The question is not whether Disturbed is active, but which disturbed classes and severities best represent the scenario.
- By default, the strongest hydrophobicity effects are typically represented in high-severity fire classes. If the lookup table is edited, that behavior can change.
- Shrub and grass responses depend on the `burn_shrubs` and `burn_grass` settings. If those are off, those hillslopes may remain closer to baseline conditions.
- This workflow is designed for post-disturbance scenario modeling. It should not replace field validation, local professional judgment, or calibration when decisions are high stakes.
- Feedback on cases where the default parameterization does not transfer well to other regions or vegetation communities is welcome.

## Troubleshooting

| Problem | What it usually means | What to check |
| --- | --- | --- |
| The map fails validation | The SBS raster is missing projection metadata, uses non-integer values, has too many classes, or has an unrecognized color table | Reproject to a valid projected coordinate system, export as a single-band integer GeoTIFF, and review [SBS Map Utilities](../baer/README.sbs_map.md) |
| Results do not change much after applying disturbance | The watershed may be mostly unburned, the dominant class may still be unburned on many hillslopes, shrub/grass burning may be disabled, or the watershed may still infiltrate enough water to limit large runoff and erosion changes even under burned parameterization | Check the normalized SBS map, hillslope coverage, the shrub/grass settings, and whether local soils and slopes are likely to remain infiltration-dominated |
| Results change too much | High-severity area may be overrepresented or the lookup table may have been edited aggressively | Review the disturbed land-soil lookup table and compare against project defaults |
| A local calibration does not match field observations | The default lookup table is generalized and may not represent local soils, fuels, or recovery conditions exactly | Use field evidence carefully, document any lookup-table changes, and compare against the baseline run |

## Related Docs

- [Disturbed Lands Module README](README.md)
- [Disturbed Land Soil Lookup](../../../weppcloud/routes/usersum/weppcloud/disturbed-land-soil-lookup.md)
- [SBS Map Utilities](../baer/README.sbs_map.md)
- [Soil File Specification](../../../weppcloud/routes/usersum/input-file-specifications/soil-file.spec.md)
