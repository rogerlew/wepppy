# Parameterization Research - Deciduous and Mixed Forest Managements

Date: 2026-06-26

## Scope

This artifact records the sources and parameter choices used to split NLCD
forest classes `41`, `42`, and `43` into separate WEPP managements:

| NLCD | Class | WEPP disturbed class | Management |
|------|-------|----------------------|------------|
| 41 | Deciduous Forest | `deciduous forest` | `UnDisturbed/Deciduous_Forest.man` |
| 42 | Evergreen Forest | `forest` | `UnDisturbed/Old_Forest.man` |
| 43 | Mixed Forest | `mixed forest` | `UnDisturbed/Mixed_Forest.man` |

The goal is winter snow-season canopy separation, because WEPP snowmelt and
interception behavior consume canopy cover directly.

## Authorities

- WEPP field semantics were mapped from
  `wepppy/wepp/management/managements.py` and the local plant file
  specification at
  `wepppy/weppcloud/routes/usersum/input-file-specifications/plant-file.spec.md`.
  Relevant fields are `ini.data.cancov`, `plant.data.bb`,
  `plant.data.xmxlai`, `plant.data.decfct`, `plant.data.dropfc`,
  `plant.data.spriod`, `plant.data.tmpmin`, and yearly perennial dates
  `jdharv`, `jdplt`, and `jdstop`.
- The existing forest lineage is W. Elliot / FS-WEPP style. Disturbed WEPP
  documentation describes young and old undisturbed forests, forest fires,
  skid trails, harvested forests, and rangeland plant communities as its core
  management domains:
  <https://forest.moscowfsl.wsu.edu/fswepp/docs/distweppdoc.html>.
- MRLC NLCD definitions distinguish the three forest classes. Deciduous forest
  has more than 75 percent tree species that shed foliage seasonally;
  evergreen forest has more than 75 percent species that maintain leaves all
  year; mixed forest has neither deciduous nor evergreen species greater than
  75 percent of total tree cover:
  <https://www.mrlc.gov/data/legends/national-land-cover-database-class-legend-and-description>.
- NASA defines LAI as one-sided green leaf area per ground area for broadleaf
  canopies and one-half total needle surface area per ground area for conifers:
  <https://www.earthdata.nasa.gov/topics/biosphere/leaf-area-index>.
- Keenan et al. (2015) reported Harvard Forest mean spring budburst on day of
  year 126 and autumn senescence on day of year 286:
  <https://harvardforest.fas.harvard.edu/publications/pdfs/Keenan_GlobChanBio_2015.pdf>.
- Vose et al. reported mature hardwood stand LAI from 4.3 to 5.4, supporting a
  deciduous maximum LAI of 5.0:
  <https://research.fs.usda.gov/download/treesearch/4724.pdf>.
- Varhola et al. found forest cover explained much of the variance in relative
  changes in snow accumulation and ablation, motivating canopy differentiation:
  <https://research.fs.usda.gov/treesearch/48807>.
- Lundquist et al. (2013) documents the climate-dependent snow-retention effect
  of forest density and canopy structure:
  <https://agupubs.onlinelibrary.wiley.com/doi/full/10.1002/wrcr.20504>.

## Parameter Mapping

| Target | Evergreen baseline | Deciduous | Mixed |
|--------|--------------------|-----------|-------|
| Initial canopy cover | `0.90` | `0.20` | `0.55` |
| Maximum LAI (`xmxlai`) | `14.0` | `5.0` | `9.5` |
| Canopy coefficient (`bb`) | `14.0` | `14.0` | `1.0` |
| Senescence date (`jdharv`) | `0` | `286` | `286` |
| Perennial plant date (`jdplt`) | `0` | `0` | `0` |
| Senescence period (`spriod`) | `90` | `45` | `45` |
| Decomposition factor (`decfct`) | `1.0` | `0.20` | `0.55` |
| Drop fraction (`dropfc`) | `1.0` | `0.20` | `0.55` |
| Minimum temperature (`tmpmin`) | `-40.0` | `-24.0` | `-25.0` |
| Growth trigger inputs | disabled | `beinp=13`, `btemp=4`, `crit=30`, `critvm=0.1` | same |

## Decisions

Evergreen remains `Old_Forest.man`. It is the existing static conifer
parameterization with `cancov=0.90`, `xmxlai=14.0`, no senescence, and no leaf
drop.

Deciduous uses `xmxlai=5.0`, matching the mature hardwood LAI range. It keeps
the high forest canopy coefficient so leaf-on cover can become high in summer,
but it sets autumn senescence to day 286 and a cold-season threshold of
`tmpmin=-24.0` so WEPP output reaches a low winter `Cancov`.

Mixed uses a single perennial as a defensible NLCD default because the
management format does not support simultaneous evergreen and deciduous plant
cohorts in one OFE. The `xmxlai=9.5` value is the midpoint between the existing
evergreen LAI 14.0 and the selected deciduous LAI 5.0. The initial canopy and
drop/decomposition factors are `0.55`, representing partial evergreen
retention. The lower canopy coefficient `bb=1.0` damps the cover response so
WEPP output is intermediate in winter and does not saturate at the evergreen
cover level.

The perennial plant date stays `0` for both new managements. Testing showed a
nonzero `jdplt=126` behaves like first-year planting in this WEPP pathway and
zeroes the established canopy, causing both new managements to emit zero
canopy for the validation run. Leaf-on recovery is instead represented through
the plant growth constants plus the senescence date.

## Lookup Determination

New `disturbed_land_soil_lookup.csv` rows are required because the disturbed
lookup key is `(luse, stext)` and `luse` must match the `DisturbedClass` from
`disturbed.json`.

The new `deciduous forest` and `mixed forest` rows copy soil-hydraulic values
from the existing `forest` rows for each texture. The soil type is not changed
by deciduous vs mixed canopy, so columns such as `ki`, `kr`, `shcrit`, `avke`,
`bd`, `ksatadj`, `ksatfac`, `ksatrec`, `keffflag`, and `lkeff` remain shared.

Plant and canopy values differ:

| Class | `rdmax` | `xmxlai` | `plant.data.decfct` | `plant.data.dropfc` | `pmet_kcb` | `pmet_rawp` |
|-------|---------|----------|---------------------|---------------------|------------|-------------|
| `forest` | `2` | `14` | `1` | `1` | `0.95` | `0.8` |
| `deciduous forest` | `2` | `5` | `0.2` | `0.2` | `0.95` | `0.8` |
| `mixed forest` | `2` | `9.5` | `0.55` | `0.55` | `0.95` | `0.8` |

No CSV schema change is required.

## Validation Summary

The WEPP validation is recorded in
`docs/work-packages/20260626_deciduous_mixed_forest_managements/artifacts/winter-cancov-validation.md`.
It confirms final-year winter mean `Cancov` ordering:

| Class | Final-year winter mean `Cancov` |
|-------|---------------------------------|
| Deciduous | `6.653%` |
| Mixed | `44.446%` |
| Evergreen | `90.000%` |

The deciduous value is lower than the ecological branch/stem cover target
because WEPP's `Cancov` output is live canopy cover in this pathway. The model
does show the required snow-season separation and strong leaf-on recovery.
