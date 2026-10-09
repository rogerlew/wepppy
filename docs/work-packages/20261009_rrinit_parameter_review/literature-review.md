# RRINIT Literature Review

2026-10-09 UTC. Research delegated to the hydrologist agent at Roger's request;
the parent integrated its returned memo. No parameters or simulations changed.

## Definition and Interpretation

WEPP identifies rrinit as initial random roughness in meters, distinct from
ridge height rhinit and time-varying rrc. Chapter 7, glossary p. 7.47 and
sections 7.5-7.6 describe the distinction and tillage/rainfall evolution. Its
critical-shear roughness multiplier is 1 + 8(RRt - 0.006), with a historical
6 mm minimum. These are model equations, not evidence of a universal forest
surface roughness. [USDA WEPP Chapter 7](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/chap7.pdf).

Elevation dispersion is not litter thickness, Manning n or obstacle height.
Measurement spacing, footprint, slope/trend removal, rocks, root crowns and
litter handling affect transferability. A uniform layer adds elevation but
does not add its thickness to the standard deviation of surface elevations.

## Evidence

| Source and setting | Values in meters | Interpretation and limits |
| --- | --- | --- |
| Elliot and Hall, 1997 draft, WEPP Forest Applications, Table A2 p. 12 | Forest 0.100; fillslope 0.050; road 0.006 | Historical model recommendations, not a presented field distribution with uncertainty. Provides a documented basis for the existing 10 cm forest value, not proof it is optimal today. [USFS original](https://forest.moscowfsl.wsu.edu/engr/forestap/forestap.pdf). |
| Walker et al., 2025, temperate forests in Massachusetts and New York; 410 profiles at 24 sites | Mean detrended RMS height 0.009 and 0.006 | Loose surface debris removed; approximately 1 m profiles. Strong measurements of that defined surface, not intact-litter or western-forest bounds. Methods and results pp. 4642-4644. [Paper](https://doi.org/10.1109/JSTARS.2025.3530710), [USDA summary](https://www.ars.usda.gov/research/publications/publication/?seqNo115=418443). |
| de Figueiredo et al., 2012, mechanically prepared afforestation plots, NE Portugal | Treatment means 0.0143-0.0785; planting holes 0.0227; control 0.0286 | Detrended profiles, approximately 3 m long at 0.10 m spacing. The control was abandoned agricultural land. Evidence concerns site preparation, not a universal young-forest age ratio. Table 3 p. 1754. [Original paper](https://bibliotecadigital.ipb.pt/bitstreams/561bb11b-24ec-4359-a981-92309aa8d62e/download). |
| Moffet et al., 2007, Idaho mountain big sagebrush prescribed burn | Unburned 0.0211; burned 0.0108 | Eight plots per treatment; ground elevations on six cross-slope transects. Table 1 p. 81. Relevant measured burn contrast, but native-rangeland WEPP differs from WEPPpy's cropland/perennial templates. [USFS paper](https://www.fs.usda.gov/rm/pubs/rmrs_p047/rmrs_p047_079_084.pdf). |
| Stoof, 2011 thesis, Portuguese shrubland winter burn | Reported RR 0.0108 before; 0.0093 immediately after; 0.0076 and 0.0081 later | Immediate decrease was not significant. Crucial ambiguity: section 5.2.4 calls the statistic standard error, not elevation SD/RMS. Do not directly import these values until that definition is resolved. Table 5.5 p. 80. [Thesis](https://edepot.wur.nl/169616), [subsequent paper](https://doi.org/10.1016/j.geoderma.2014.09.020). |
| Renard et al., 1997, RUSLE handbook, Table 5-6 p. 174 | Tallgrass prairie 0.00762; natural shrub 0.02032; sagebrush 0.02794 | Converted from 0.30, 0.80 and 1.10 inches. Supporting handbook estimates, not verified original measurements or WEPP burn-severity defaults. [USDA AH 703](https://www.ars.usda.gov/ARSUserFiles/60600505/RUSLE/AH_703%20-%20Predicting%20Soil%20Erosion%20by%20Water%20-%20A%20Guide%20to%20Conservation%20Planning%20With%20the%20RUSLE%20%28RUSLE%29.pdf). |
| Vazquez Alvarado et al., 2018, oak forest, Mexico | Reported indices 0.59 / 0.41 / 0.31 for unburned/moderate/high | Dimensionless chain indices, not roughness lengths. Evidence for a severity association only; these numbers cannot become rrinit in meters. Methods and Table 2. [Original paper](https://cienciasforestales.inifap.gob.mx/index.php/forestales/article/download/121/1591?inline=1). |

White's multi-fire grassland comparison found reduced microtopographic variation
after four of five fires, but not after the second Bernalillo prescribed burn.
Thus neither a universal smoothing response nor a severity assignment follows
from the label prescribed fire. See pp. 416-417 and Figure 2.
[White 2011](https://research.fs.usda.gov/download/treesearch/39013.pdf).

## Implication for This Review

The literature supports a bounded exploration around 0.006, 0.010 and 0.020 m,
retaining every current default as a control. Add 0.040 m as an intermediate
contrast for high-default classes. These are test levels, not proposed final
class/severity defaults. The historical 0.100 m forest recommendation and
millimeter-scale forest observations describe different evidence types and
possibly different effective surfaces; do not simply replace one with the other.

Local static analysis makes a direct reduction consequential: the current
cropland interrill-delivery factor reaches zero near effective rrc=0.049565 m.
Moving below it can increase modeled sediment supply. RR decay is conditional
in the current implementation, so high initial values cannot be assumed to wash
out immediately. Hydrology and sediment therefore need joint assessment.

Evidence gaps: no defensible universal young/mature forest ratio; no comparable
elevation-SD dataset covering all requested burn severities; limited direct
tallgrass measurements; unresolved litter/soil-surface transferability; and
method ambiguity for some published indices. No lower default or monotonic
severity curve is approved by this review.
