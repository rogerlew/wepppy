# Soil source comparison protocol

Predeclared 2026-09-09 before thickness calculation or paired interpretation.

## Panel and acquisition

Use the 12 `controlled` reference outlets in the closed terrain package's
`resolution_comparison.csv`, retaining site labels, nested dependence, and
0.02–8 km2 calibration-area flags. Hold accepted 10 m T and masks fixed.
Read projects only; use `/tmp/staley-m3-soils-study/` for source acquisition.
The initial inventory confirms all three live `soils/` directories absent.

Acquire bounded map-unit windows from the installed 2025 gNATSGO mosaic;
verify each key's NRCS survey lineage, since a mosaic name alone does not
prove SSURGO origin. Freeze minimal SDA tables and request metadata. This
combines 2025 spatial labels with retrieval-date tables; do not claim historical
snapshot consistency. Use nearest-neighbor categorical alignment to the 10 m
grid; this does not increase soil mapping detail. Acquire original USGS THICK
COG windows at native resolution, keeping NaN and negative sentinels invalid.
Area-average valid continuous values onto the project grid, separately tracking
source support; never extrapolate missing values. Channel cells remain included.

## Comparisons and screens

Report paired thickness cm, S, signed/absolute differences, support fractions,
and min/median/max across outlets. Full-catchment estimates are available only
on complete support; partial known-support estimates are explicitly diagnostic.
Common-support comparisons use the same valid spatial cells and report remaining
component support; they cannot remove unobserved component bias. Sensitivities
use 50%, 75%, 90%, 95%, and 100% support cutoffs to show availability counts,
without approving any production cutoff. Compare interval sum, union, and
maximum endpoint; record topology problems rather than repair them silently.

Set diagnostic F=0.5 and rainfall accumulations 5, 10, 20 mm for each duration
15/30/60 min; these are study scenarios, not climatology or defaults. Also use
STATSGO-derived 50% and 75% threshold accumulations as fixed paired rainfall
scenarios to ensure nonsaturated comparisons. Report probability change in
percentage points and inverse-threshold change in mm, mm/hour, and percent
relative to STATSGO. Missing source support yields unavailable comparisons. Invalid/nonpositive
denominators or negative thresholds abort the diagnostic evaluation explicitly;
with fixed F=0.5 and nonnegative inputs these indicate invalid study inputs.
Never clip them to zero. Use stable logistic evaluation.

Numerical screens: interval/tabular arithmetic within 1e-9 cm; Float32 raster
propagation within 1e-4 cm; forward/inverse probability within 1e-12. Scientific
source acceptance has no published numeric equivalence limit established here.
Report effect sizes without importing terrain's 5-point/10% screen. Agreement
is comparability evidence, not outcome validation; disagreement or unresolved
source semantics supports retaining the original predictor pending owner review.

## Compatibility and regression plan

Only additive offline tables/rasters in new output directories; no project
cache, NoDb, WEPP `.sol`, or `wepp/runs` writes and no existing field renames.
Read SQLite with encoded file URIs and `mode=ro`; reject absent, malformed,
or incompatible sources explicitly. Acquisition and evaluation are separate;
evaluation cannot fetch or rebuild missing data. Test synthetic edge cases and
frozen public records through the actual adapter, raster builder, catchment S,
and diagnostic outputs; compare input hashes before and after. No production
availability policy or UI/RQ/NoDb contract changes are authorized by this study.

Revision before final evaluation: mask reconstruction uses the archived
controlled 10 m FillDepressions (fix_flats=true, increment=0.00001) and D8Pointer
commands. The initial native-pointer count mismatch was rejected before analysis.
