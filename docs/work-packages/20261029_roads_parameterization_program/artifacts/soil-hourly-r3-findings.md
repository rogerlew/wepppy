# Generated-soil runtime interaction on revision 3

The runtime bridge showed a strong daily-mode response in legacy soils. This
conditional extension tests whether that response transfers to the generated
profiles on the same 96 misses and 20 passing controls. No production parameters,
runtime defaults, withheld outcomes or UI behavior changed.

## Execution and verification

The four-cell generated/legacy × hourly/daily panel contains 464 labeled cells.
PMET and snow sidecars remain present. The declaration identifies 196 unique new
runs: 116 generated and 80 legacy. It reuses 232 hourly baseline cells and 22
labeled daily bridge cells; 14 further labels share newly executed legacy decks.
Reuse requires the exact complete consumed-input hash signature, not matching labels.

All 196 new native runs pass physical audits. Fresh verification rehashes recorded
inputs/outputs, recomputes native physical audits for all 444 distinct destination
directories, and recomputes magnitude scores for all 464 cells. All 464 physical
checks pass. An additional readback binds reused bridge records to the frozen
bridge-results hash and all 196 new records to their results inventory.

## Numerical result

| Soil/runtime | Recovered original misses /96 | Retained passing controls /20 |
| --- | ---: | ---: |
| Generated/hourly (baseline) | 0 | 20 |
| Generated/daily | 26 | 18 |
| Legacy/hourly | 79 | 20 |
| Legacy/daily | 93 | 20 |

Generated/daily recovers one of five meaningful high misses, 11 of 48 meaningful
low misses, and 14 of 43 small-reference exceedances. It also loses two controls:

- Flagstaff sand, outunrut paved/no traffic: reference 0; candidate 1.12074 kg/year,
  above the unchanged 1 kg/year small-load ceiling.
- Site sand, outunrut gravel/high traffic: reference 20.2164 kg/year;
  candidate 1077.7169 kg/year, approximately 53.3 times the reference.

Reject a global hourly-off change. Whole legacy/daily substitution is a diagnostic
control, not the intended generated-soil parameterization. Its three remaining
misses are aliases of one Flagstaff loam input, so they are not three independent
model failures. The larger generated-profile mismatch remains after separating
runtime effects. This panel is selected development evidence, not a new 840-case
acceptance result. The full baseline remains 713/766 meaningful and 31/74 small passes.

## Next: physically coupled role treatment

Keep the current hourly/PMET/snow runtime fixed for the next generated-soil work.
Audit the source-to-native road/fill/buffer hydraulic state before choosing a new
parameter rule. The existing candidate caps road conductivity and adjusts erosion
but retains surface bulk density and organic matter across roles.

A verified readback of one fixed configuration per development material
(`generated-role-surface-state-r3.json`) provides a concrete hypothesis:
material 2711184 retains surface bulk density 0.78 g/cm³ and organic matter 11% for
road, fill and buffer; their first-day reported porosity is 66.93%. Material 2711250
retains density 0.90 g/cm³, organic matter 7.5%, and first-day porosity 62.85%. These
are observations of this experimental treatment, not proof that the source soil
is wrong or that compaction alone solves the sediment discrepancy. First-day
output is not an instrumented pre-event initialization state.

The next audit must trace bulk density, porosity, field capacity/wilting point,
suction and dynamic conductivity together; identify source-supported role rules;
and predeclare a physically consistent coupled transformation before a native
ablation. Preserve texture, deeper horizons, 200 mm normalization and restriction
provenance. Do not mix format 98.4 and 9002 blocks or treat legacy-derived hydraulic
values as field calibration. Do not alter general SSURGO generation or Disturbed
behavior. Existing acceptance/withheld/UI gates remain unchanged.

The five rejected hourly/original-Penman guard stops belong to the separate runtime
bridge; none occurs in this PMET-retained four-cell comparison. Their raw evidence
and unresolved negative-demand classification remain retained.
