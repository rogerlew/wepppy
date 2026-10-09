# RRINIT Assessment and Sensitivity Decision

Historical pre-adoption inventory. The later approved low-severity forest
4 -> 6 cm change is recorded in
[ADR-0083](../../adrs/ADR-0083-low-severity-forest-initial-random-roughness.md).
The original values and artifacts below are retained as assessment evidence.

2026-10-09 UTC. Recommendation: run one bounded sensitivity study before changing
defaults. No production parameters, model code or run outputs were changed, and
no simulations were launched. This assessment combines parsed management files,
static WEPP 261009 source analysis and the delegated [literature review](literature-review.md).

## Current Values

The standard disturbed.json mapping uses the following initial random roughness.
Values below are centimeters; serialized rrinit is in meters.

| Vegetation | Unburned | Low severity | Moderate severity | High severity | Prescribed fire |
| --- | ---: | ---: | ---: | ---: | ---: |
| Forest | 10 | 4 | 6 | 6 | 6 |
| Young forest | 8 | 4 | 6 | 6 | 6 |
| Shrub | 6 | 6 | 6 | 6 | 6 |
| Tall grass | 2 | 2 | 2 | 2 | 2 |

Deciduous and mixed forest also start at 10 cm. Young forest does not have
separate burned templates: the remapper groups it with forest. Shrub and grass
only receive burned templates when their respective burn-remapping options are
enabled. Prescribed classes are separate mappings, not another SBS severity.

Primary management files under wepppy/wepp/management/data/UnDisturbed:

- Old_Forest.man, Young_Forest.man, Shrub.man, Tall_Grass.man: unburned.
- Low_Severity_Fire.man, Moderate_Severity_Fire.man, High_Severity_Fire.man,
  Prescribed_Fire.man: forest family, including burned young forest.
- Shrub_Low/Moderate/High_Severity_Fire.man: shrub wildfire severities.
  Shrub prescribed fire uses Prescribed_Fire.man in the standard mapping.
- Grass_Low/Moderate/High_Severity_Fire.man: grass wildfire severities;
  grass prescribed fire uses the low-severity grass file.

**These are not universal values across all WEPPpy mappings.** The inventory
parsed 275 relevant mapping records across ten maps and 25 distinct management
templates; all selected initial scenarios are lanuse=1 (cropland equations).
All 25 templates passed serialization/reparse checks for roughness values.
Across these maps, young-forest rrinit spans 2/8/10 cm, shrub 6/10 cm and tall
grass 0.8/2/4/6/10 cm. Examples include 6 cm grass-burn templates in Australian,
European and Virgin Islands maps, and special revegetation mappings using
10 cm across several classes. These may reflect intended mapping semantics;
they are not silently classified as bugs or normalized by this review.

[The full inventory](artifacts/management-inventory.csv) identifies each map,
key, class and exact file. A proposed default revision must name its mapping
scope rather than assume every class label selects the same management.
The inventory addresses JSON files by explicit path. A short mapping alias
does not always select the similarly named file: load_map checks the esdac
alias before disturbed aliases, for example. Resolve the project's actual
mapping rather than infer it from a filename in this inventory.

## Which Value Actually Reaches WEPP?

1. The management map selects a .man template. managements.py:892 parses rrinit;
   line 931 serializes it with five decimal places, without a cm conversion.
2. The standard disturbed_land_soil_lookup.csv has no rrinit column. Its default
   rows do not replace template roughness. However, custom lookup rows can
   supply ini.data.rrinit: management_overrides.py:73 applies generic plant/ini
   overrides, and Landuse preparation applies those to management objects,
   including MOFE segments. Uploaded/custom managements are another authority.
3. The actual prepared p*.man files, not a class label or display table, are
   the final input evidence. Existing projects must regenerate them after any
   accepted default change. Regenerate matching-build passes for watershed work.
4. infile.for:774 reads the five-value initial-condition record. Line 1356
   transfers rrini1 to rrinit. Line 1454 floors it at 0.006 m. By contrast,
   cumulative rainfall rfcum is converted from mm to m at line 1435.

**Packaged export mismatch:** mods/disturbed/data/extended_land_soil_lookup.csv
currently says young forest 2 cm, shrub 10 cm and tall grass 10 cm, versus the
standard parsed templates' 8/6/2 cm. These are twelve differing rows across four
textures. build_extended_land_soil_lookup (disturbed.py:1730) builds an export
using map-derived management fields; this is not proof of a project's effective
overridden value. Never revise just that export and assume model inputs changed.
The [summary](artifacts/inventory-summary.json) retains all discrepancies and
input/source hashes. No lookup or template was edited to resolve them here.

## Static Model Trace

rrinit is initial random roughness, not ridge height rhinit, Manning n, canopy
height, litter thickness or routing roughness-element height. Some legacy
comments call it ridge roughness, but the input mapping and official definition
distinguish the variables. The selected natural-vegetation templates deliberately
use cropland/perennial equations; native-rangeland rules are not interchangeable.

### State Evolution

soil.for:741 initializes rrc from rrinit. Tillage can replace rrinit using
implement roughness and disturbed fraction (lines 373-375), although the
standard selected templates have no surface-operation sequences. Later decay
is rrc = max(0.006, rrinit * exp(produc)), with produc based on rainfall, residue
and a clay/organic-matter decay coefficient from scon.for:567-575.

Crucially, soil.for:532 is inside the bd(i) < bdcons(i) guard at line 464, in a
loop over the first two soil layers. If the guard is false, that decay update
is skipped. rrinit is therefore not guaranteed to be only a short-lived spin-up
parameter. Typical templates also initialize rfcum near 400 mm. Measure actual
daily rrc rather than assume it equals rrinit forever or inevitably decays.
SOIL output reports rrc in mm (watbal_hourly.for:1112).

### Runoff Volume and Timing

IRS computes potential depression storage in meters:

```text
D = max(0, 0.112 R + 3.1 R^2 - 1.20 R S)
R = effective rrc in meters; S = slope in m/m
```

See irs.for:304-356, grna.for:516-535 and depsto.for. Connected OFEs use a
length-weighted equivalent depth. This changes rainfall-excess delivery and
can indirectly change soil wetting and returned water; it is not merely a peak
or display parameter. MIXPEAK has no direct rrinit input, but its rainfall and
returned-water operands can change downstream of these processes.

FRCFAC uses both rroinr (often rrinit when no operations apply) and rrc/rroinr
to compute interrill friction (frcfac.for:169-198). Cover and living vegetation
are additional terms. Equivalent friction enters RDAT's flow coefficient
alpha = sqrt(8 g S / frcteq), rdat.for:100. Peaks and duration can change.
For cropland, the direct rill-friction formula does not contain rrinit; the
broad-sheet-flow branch can replace it with interrill friction. Do not assume
one universal proportional relationship between rrinit and routing friction.

INFPAR also uses min(rrc, 0.04) in a conductivity/crusting adjustment, but only
when lanuse=1 and ksflag=1 (infpar.for:414-432). The standard disturbed lookup
rows inspected here have ksflag=0, so that specific pathway is normally off.
Do not confuse ksflag with the separate keffflag values used in some burn rows.

### Erosion and Sediment

PARAM computes rif = clamp(1.14 - 23 rrc, 0, 1), then particle-specific interrill
delivery ratios and their weighted total intdr (param.for:417-452). At effective
rrc >= 1.14/23 = 0.049565 m, intdr is zero and the interrill contribution to
detinr is zero (lines 482-503). This does not turn off all erosion: rill erosion,
transport and deposition remain separate. Lowering roughness across this range
can increase delivered sediment, even if another hydraulic effect looks modest.

SOIL separately multiplies critical shear by 1 + 8(rrc - 0.006), within other
adjustments (soil.for:1046,1099). Peak/duration changes also propagate through
XINFLO/PARAM and sediment routing. Changes cannot be adjudicated using runoff
alone or by assuming sediment should be preserved exactly.

### Other Conditional Effects

Snow redistribution uses rrc (sndrft.for:145). Snowmelt and soil-temperature
aerodynamic calculations can use rrc depending on snow depth and vegetation
height (melt.for:110; tmpadj.for:173). Wet/snow-influenced conditions should be
represented before adopting broad new defaults, without expanding into a snow
or routing rewrite.

## Analytic Illustration, Not Simulation

The table assumes effective rrc equals the listed value and slope is 20%.
Initial bare interrill friction further assumes rroinr=rrc; cover is excluded.

| Effective roughness, cm | Potential storage, mm | Interrill factor rif | Roughness shear multiplier | Bare interrill friction |
| --- | ---: | ---: | ---: | ---: |
| 0.6 | 0 | 1.00 | 1.000 | 4.07 |
| 1 | 0 | 0.91 | 1.032 | 4.86 |
| 2 | 0 | 0.68 | 1.112 | 12.07 |
| 4 | 0 | 0.22 | 1.272 | 15.01 |
| 6 | 3.48 | 0 | 1.432 | 15.14 |
| 8 | 9.60 | 0 | 1.592 | 15.15 |
| 10 | 18.20 | 0 | 1.752 | 15.15 |

Thus 10 to 4 cm is not just a small friction adjustment: in this illustration
it removes 18.2 mm potential storage and reactivates interrill sediment delivery.
On a 40% slope the equation gives zero storage even at 10 cm, while the sediment
and friction pathways still differ. These are properties of implemented
equations, not claims about observed natural depression storage.
[Additional slopes and near-threshold values](artifacts/static-equation-illustrations.csv)
are retained for reproducibility. No hydrologic simulation was used to produce
these numbers.

## Sensitivity Recommendation

**Subsequent scaffold finding:** the existing
[Disturbed harness assessment](harness-assessment.md) recommends extending
tests/disturbed rather than constructing the generic matrix below. It retains
four committed soil textures and the existing climate, adds young forest, and
addresses hourly/PASS-v3 and event-matching gaps. Its 448-run single-profile
grid (up to 896 with one gentler profile) supersedes the earlier 444-run proposal
as an implementation scaffold. The scientific rationale and test levels remain.

**Yes: conduct a bounded rrinit study before selecting replacement defaults.**
The literature supports testing millimeter/centimeter-scale roughness, while
the code shows several important competing effects. It does not support a
defensible new low/moderate/high burn table without model-response evidence.

1. Freeze wepp_261009 and the chosen mapping. Audit actual generated management
   records and generic overrides first. Use a committed bounded fixture set or
   reproducible generator; external watershed studies remain supplementary.
2. Start with forest, young forest, shrub and tall grass crossed with unburned,
   low, moderate and high severity. Keep all sixteen reporting cells; deduplicate
   only when complete generated inputs are identical, not merely rrinit values.
   Young/mature forest burn aliases deserve an explicit check. Prescribed fire
   is an optional separate extension, not a synonym for low severity.
3. For each cell, use its current value plus 0.006, 0.010, 0.020 and 0.040 m,
   deduplicating equal levels. These are exploratory test values, not approved
   defaults. Unlike a +/-1% mutation, they cross the implemented response ranges.
4. A concrete upper bound is three slope settings (10%, 20%, 40%) and two
   contrasting soil profiles under one fixed multi-year climate record with
   ordinary storms and wet/return events. Before deduplicating equivalent
   templates, this is 444 runs for the standard matrix. Confirm return actually
   occurs in the selected control rather than retuning Ksat to manufacture it.
   Add only selected 0.049/0.050 m boundary probes if interpretation needs them.
5. Change rrinit only within each comparison. Keep rhinit, covers, rainfall,
   Ksat, erodibility, routing coefficients and management schedules fixed.
   Between vegetation/burn cells, retain their existing physical parameter sets.
   Report actual daily rrc, first-year versus later behavior, event frequencies,
   runoff/streamflow volumes, peaks/durations, small events, dry/wet conditions,
   interrill/rill contributions where available, and hillslope sediment delivery.
6. Review magnitude, frequency and affected conditions, not just aggregate fits.
   No zero-residual or universal convergence requirement. Do not adjust other
   parameters to rescue an unfavorable rrinit response. Advance only a small
   defensible candidate to fresh same-build watershed checks for water, timing,
   recession and channel sediment effects, with unchanged ledger comparisons.

## Revision Disposition

No numeric default change is justified yet. Retain current controls, investigate
the non-monotonic forest burn values and map/export differences, and bring the
bounded study results to Roger. A final revision needs explicit mapping scope,
parameterization ADR, management/export precedence checks, regenerated-input
evidence and regression coverage. Do not update only a CSV export, silently
override all regional maps, change rrinit as a workaround for peak/routing defects,
or claim that field litter thickness supplies a roughness value.

## Reproduction

Run with the WEPPpy venv from the repository root:

```bash
python docs/work-packages/20261009_rrinit_parameter_review/audit_rrinit.py --forest-source /home/workdir/wepp-forest-release-20261009/src
```

The inventory uses the existing parser and temporary serialization files only.
Its first pass stopped on the /workdir versus /home/workdir path alias; resolving
the same source path corrected that inventory issue. Production data remained
unchanged. Commits and file hashes are in inventory-summary.json.
