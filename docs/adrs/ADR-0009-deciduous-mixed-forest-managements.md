# ADR: Deciduous and Mixed Forest Managements

Status: Accepted
Date: 2026-06-26

## Context

WEPPcloud previously mapped NLCD forest classes `41` (Deciduous Forest), `42`
(Evergreen Forest), and `43` (Mixed Forest) to the same undisturbed evergreen
management, `UnDisturbed/Old_Forest.man`. That file has static high canopy
cover, high LAI, no senescence, and no leaf drop.

This made deciduous and mixed forest hillslopes carry an evergreen winter
canopy in generated WEPP inputs. That is physically wrong for snow-season
interception and melt behavior, and it prevents openWEPP snow fixtures from
selecting distinct deciduous and mixed forest canopy regimes.

## Decision

WEPPcloud will use distinct undisturbed forest managements for NLCD `41`, `42`,
and `43`.

- NLCD `41` maps to `deciduous forest` and
  `UnDisturbed/Deciduous_Forest.man`.
- NLCD `42` remains `forest` and `UnDisturbed/Old_Forest.man`.
- NLCD `43` maps to `mixed forest` and `UnDisturbed/Mixed_Forest.man`.

The disturbed soil lookup gains `deciduous forest` and `mixed forest` rows for
the existing texture buckets. Those rows reuse existing `forest`
soil-hydraulic parameters and change only canopy/plant parameters.

## Decision Provenance (Required for Parameterization Changes)

Decision Venue: Codex work package execution, 2026-06-26 America/Los_Angeles
Participants Present: WEPPcloud operator/user, Codex coding agent
Decision Owner(s): WEPPcloud operator/user
Implementer(s): Codex coding agent

## Change Summary

Old behavior:

- NLCD `41`, `42`, and `43` all resolved to `DisturbedClass: "forest"`.
- All three used `UnDisturbed/Old_Forest.man`.
- All three used `cancov=0.90`, `xmxlai=14.0`, no senescence, and
  `plant.data.decfct=1`, `plant.data.dropfc=1`.

New behavior:

| NLCD | Disturbed class | Management | `cancov` | `xmxlai` | `bb` | `jdharv` | `jdplt` | `decfct/dropfc` |
|------|-----------------|------------|----------|----------|------|----------|---------|-----------------|
| 41 | `deciduous forest` | `Deciduous_Forest.man` | `0.20` | `5.0` | `14.0` | `286` | `0` | `0.20` |
| 42 | `forest` | `Old_Forest.man` | `0.90` | `14.0` | `14.0` | `0` | `0` | `1.00` |
| 43 | `mixed forest` | `Mixed_Forest.man` | `0.55` | `9.5` | `1.0` | `286` | `0` | `0.55` |

Both new managements set plant growth constants `beinp=13`, `btemp=4`,
`crit=30`, `critvm=0.1`, `spriod=45`, and `gddmax=0`. Deciduous sets
`tmpmin=-24.0`; mixed sets `tmpmin=-25.0`.

New lookup rows are added for `deciduous forest` and `mixed forest` for each
canonical texture. Soil-hydraulic columns are copied from `forest`; plant
columns are changed to the table above.

Forest-family routing helpers now include `deciduous forest` and
`mixed forest` wherever unburned forest behavior or forest-cover treatment
normalization is required.

## Rationale

MRLC defines deciduous forest as tree cover where more than 75 percent of tree
species shed foliage seasonally, evergreen forest as tree cover where more
than 75 percent maintain leaves year-round, and mixed forest as neither group
exceeding 75 percent of tree cover. A single evergreen management cannot
represent those classes.

The selected deciduous LAI of `5.0` is within mature hardwood LAI evidence.
The mixed LAI of `9.5` is the midpoint between the existing evergreen LAI
`14.0` and the selected deciduous LAI `5.0`, reflecting a simple 50/50 NLCD
mixed-forest default.

WEPP validation showed that setting `jdplt=126` on an established perennial
forest management zeroed the winter canopy as if the plant were newly
established. The accepted representation keeps `jdplt=0`, sets autumn
senescence at day `286`, and uses plant growth constants plus temperature
thresholds to create the observed seasonal trajectory.

## Alternatives Considered

1. Keep all forest classes mapped to `Old_Forest.man` - rejected because it
   preserves false evergreen winter canopy for deciduous and mixed forests.
2. Set `jdplt=126` directly from observed budburst timing - rejected because
   the WEPP perennial pathway treated it as first-year planting and produced
   invalid zero-canopy output for the seasonal forest managements.
3. Add separate evergreen and deciduous plant cohorts for mixed forest -
   rejected because the WEPP single-OFE management format does not support
   simultaneous plant cohorts in the required path.
4. Share the existing `forest` lookup rows without new `luse` values - rejected
   because `disturbed_land_soil_lookup.csv` keys on `(luse, stext)` and the
   new `DisturbedClass` values require matching rows to avoid fallback errors.

## Consequences

Existing projects that rebuild landuse after this change will resolve NLCD
`41` and `43` to new managements. Previously generated runs are unchanged until
inputs are rebuilt.

The deciduous WEPP output reaches very low winter `Cancov` because this pathway
tracks live canopy cover and does not explicitly carry branch/stem interception
area in `Cancov`. This is conservative for winter canopy attenuation and
removes the larger error of treating deciduous forest as evergreen.

The mixed management is a single-perennial approximation of an evergreen and
deciduous blend. It is intended as a default NLCD class parameterization, not a
site calibration.

## Hemisphere Scope and Limitations

(Documented during review, 2026-06-26.)

These managements are valid for the **Northern Hemisphere only**, for two
independent reasons:

1. **Fixed-date leaf-off.** The deciduous and mixed managements trigger leaf-off
   with a fixed Julian senescence date (`286`, ~Oct 13) and disable WEPP's
   heat-unit senescence path (`gddmax=0`). Day 286 is an NH-autumn day; in the
   Southern Hemisphere it is mid-spring, so the canopy would drop in SH spring and
   persist through SH winter — the seasonal cycle inverted.
2. **WEPP annual-cycle bookkeeping.** The WEPP engine's pre-winter / frost-cycle
   resets (`contin.for`) assume NH winter timing. A perennial whose growing season
   straddles the calendar-year boundary (SH summer, Dec–Feb) would have its
   GDD/frost cycle reset mid-season, independent of the management file. This is an
   engine-level constraint, not a management-file property.

In practice this is not a current limitation: WEPPcloud's climate stack
(DAYMET / GRIDMET / CLIGEN / PRISM) is CONUS-bound, so all targets are NH. The
scope is recorded so the assumption is explicit rather than silent.

A Southern-Hemisphere variant would require, at minimum, shifting the senescence
date by ~+182 days (to ~day 104, mid-April) and verifying WEPP's winter-cycle
handling for an SH season; reason (2) cannot be fixed in the management file
alone. If the leaf-off is later moved to WEPP's temperature-driven heat-unit
senescence (`gddmax>0` + `dlai`; see
`docs/work-packages/20260626_deciduous_mixed_forest_managements/artifacts/gdd-senescence-experiment.md`),
the *leaf phenology* becomes hemisphere-robust and only reason (2) remains
NH-specific.

The evergreen management (`Old_Forest.man`, no senescence, static canopy) has no
seasonal leaf cycle and is canopy-neutral with respect to hemisphere, but
inherits the same WEPP winter-cycle assumption.

### Related limitation: fixed-date leaf-off is not climate-adaptive

Even within the NH/CONUS target, the fixed senescence date applies one leaf-off
day (~Oct 13) to every site regardless of climate or elevation, whereas real
leaf-off ranges from late September (high-elevation aspen) to early November
(southern hardwood). Because the downstream snow fixtures span Minnesota,
Vermont, Colorado, and Appalachian climates — and leaf-off timing relative to
snow onset is the snow-relevant signal — the climate-adaptive
`gddmax>0`/`dlai` senescence route (which WEPP supports via `grow.for`'s
`fphu ≥ dlai` trigger) is the preferred follow-up. The `jdplt=126` failure
documented under Alternatives concerned the *planting / leaf-out* path, not
leaf-off senescence, so it does not establish that the heat-unit senescence path
fails; that path was disabled (`gddmax=0`), not shown to fail. See the
work-package experiment note above.

## Evidence

- Work package:
  `docs/work-packages/20260626_deciduous_mixed_forest_managements/`
- Parameterization research:
  `docs/work-packages/20260626_deciduous_mixed_forest_managements/artifacts/parameterization-research.md`
- Winter canopy validation:
  `docs/work-packages/20260626_deciduous_mixed_forest_managements/artifacts/winter-cancov-validation.md`
- MRLC NLCD class definitions:
  <https://www.mrlc.gov/data/legends/national-land-cover-database-class-legend-and-description>
- NASA LAI definition:
  <https://www.earthdata.nasa.gov/topics/biosphere/leaf-area-index>
- Keenan et al. phenology evidence:
  <https://harvardforest.fas.harvard.edu/publications/pdfs/Keenan_GlobChanBio_2015.pdf>
- Hardwood LAI evidence:
  <https://research.fs.usda.gov/download/treesearch/4724.pdf>
- FS-WEPP / Disturbed WEPP lineage:
  <https://forest.moscowfsl.wsu.edu/fswepp/docs/distweppdoc.html>

## Risk and Rollback Notes

Risk: deciduous or mixed forest hydrology and erosion reports can change after
landuse is rebuilt because canopy and LAI inputs are now different. This is the
intended correction, but operators should treat before/after comparisons as a
parameterization change.

Risk: mixed forest remains an approximate single-plant representation. If a
site-specific mixed forest calibration is later needed, add a new management
variant rather than changing this NLCD default silently.

Rollback: remap NLCD `41` and `43` in `disturbed.json` back to
`UnDisturbed/Old_Forest.man`, remove the new lookup rows, and remove the
forest-family helper coverage for `deciduous forest` and `mixed forest`.

## Implementation Notes

Regression coverage verifies:

- `disturbed.json` resolves NLCD `41`, `42`, and `43` to distinct managements.
- The new `.man` files parse and expose the expected plant and perennial
  scalars.
- The disturbed lookup includes `deciduous forest` and `mixed forest` rows with
  copied soil-hydraulic values and distinct plant values.
- Disturbed forest-family helper functions include the new classes and continue
  to handle burned forest treatment suffixes.
- RAP_TS cover application includes unburned deciduous and mixed forest classes
  and excludes burned forest classes.
