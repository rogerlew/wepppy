# M3 resolution decision

## Recommendation

Require genuine 10 m terrain for initial M3 support. Do not accept 30 m as a
generally equivalent substitute or invent a minimum catchment-size exemption
from this small panel. This is an evidence-based engineering recommendation;
no production availability/UI rule was implemented or changed.

The accepted quantity is maximum upstream raw elevation minus outlet raw
elevation, divided by sqrt(upstream area including outlet). The owned Rust
implementation matches independent analytical cases and sampled study
catchment extrema/counts. It deliberately does not reproduce the pinned
reference's relief defects. Neither the terrain tests nor this sensitivity
study establish predictive calibration against observed debris flows.

## Panel and pairing

Three supplied sites yield 12 assessed outlets: each supplied terminal plus
nested outlets near 0.02, 0.1 and 1 km2. Each has a controlled and a native
10 m/30 m comparison, giving 24 pairs and 864 diagnostic M3 scenarios.
All assessed catchments have coverage flag zero, confirmed independently from
saved masks; no match was unavailable. This establishes no detected upstream
edge/NoData contact, not proof that the source terrain/routing is error-free.

Controlled comparisons use the same 10 m raw source, area-average 30 m
aggregation and owned FillDepressions/D8Pointer preprocessing at both
resolutions. Native comparisons use the supplied raw DEMs and canonical
breach-derived routing; source, alignment and snapping differences remain.
The frozen [protocol](study_protocol.md) specifies selection and snapping.

Requested geographic coordinates do not exactly reproduce stored requested
projected coordinates: discrepancies range from 4.4 to 27.6 m in
[the coordinate audit](requested_coordinate_audit.csv). They are distinct
records and were not silently equated. Fixed targets for nested/controlled
comparisons are the actual stored 10 m snapped pixel centers transformed by
the raster affine. Native terminal comparisons intentionally retain supplied
snapped centers; pair offsets are 16.37 m (Moscow), 17.91 m (Topanga), and
6.97 m (user-labeled AZ ponderosa).

Keep the supplied `az_ponderosa` label as a provenance identifier. Its stored
coordinates are about -106.671, 35.732 (EPSG:32613); do not infer geography
from its name. Its terminal area is about 23 km2, exceeding the publication's
reported 0.02-8 km2 study range, and is therefore an out-of-range diagnostic.
The other terminal areas are approximately 6.6 and 5.0 km2. Nested cases supply
the small-catchment evidence missing from terminal-only comparisons.

## Measured results

The predeclared primary screen requires every paired scenario to remain within
5 probability percentage points and 10% relative inverse-threshold change.
These are engineering criteria, not published Staley tolerances.

| Comparison | Pairs passing primary screen | Largest probability change | Largest inverse-threshold change |
| --- | --- | --- | --- |
| Controlled source/preprocessing | 10/12 | 10.598 percentage points | 12.479% |
| Native canonical workflows | 10/12 | 8.165 percentage points | 9.562% |

Controlled failures occur at Moscow's approximately 0.1 km2 outlet and
Topanga's 0.02 km2 outlet. The latter changes H from 82.729 to 62.334 m,
area from 20,000 to 18,000 m2 and overlap to approximately 0.597. Its matched
pixel centers are only 10 m apart. Resolution-associated delineation and
measurement effects are material even with a common source/preprocessing rule.

Native failures occur at Moscow's approximately 0.1 km2 outlet and the
user-labeled AZ approximately 0.1 km2 outlet. At the latter, the 30 m catchment
is only 18,900 m2 versus 100,000 m2, with overlap approximately 0.183 despite
centers 6.97 m apart. This is a pairing/delineation failure mode, not evidence
that smoothing alone creates the probability difference. A small snap offset
cannot establish equivalent contributing catchments.

All main terminal outlets agree within 0.459 probability percentage points and
0.534% inverse-threshold change. Accepting 30 m from those cases alone would
hide the demonstrated small-catchment failures. The largest absolute inverse
threshold difference is 5.488 mm/hour (controlled Topanga, 15 min, F=S=0.25,
75% probability: 49.676 to 55.164 mm/hour). The largest native absolute
threshold difference is 4.726 mm/hour. At 50% reference probability, maximum
probability difference is 9.481 points; saturation does not explain agreement.

Boundary intersection/union is a diagnostic estimate using nearest-neighbor
30 m mask reprojection to the 10 m reference grid, with each mask's native
area in the denominator. It is not an exact polygon-overlay area. Full rasters
were retained; grids were not clipped to their rectangle intersection.

## Sensitivity to engineering criteria

| Probability / inverse-threshold screen | Controlled passing | Native passing |
| --- | --- | --- |
| 2 percentage points / 5% | 8/12 | 6/12 |
| 5 percentage points / 10% (primary) | 10/12 | 10/12 |
| 10 percentage points / 20% | 11/12 | 12/12 |

Even the looser screen does not accept all controlled pairs. The study does
not justify a universal 30 m cutoff, although the larger sampled catchments
are less sensitive. To revisit 30 m support, add a broader panel with explicit
same-channel outlet correspondence, small catchments, conditioning-sensitive
terrain and calibration-range coverage; predeclare any proposed size policy
before evaluating that panel. This follow-up is not needed to recommend the
conservative 10 m initial requirement now.

## Runtime and reproducibility

The representative 1198-by-1162 grid has 1,392,076 cells. Three complete
H/A/coverage executions took approximately 0.31-0.32 seconds with about
106 MiB peak RSS on a dual Xeon E5-2697 v2 host (48 logical CPUs, about
126 GiB RAM). These are local warm-cache process/I/O measurements under
concurrent host load, not isolated scaling claims. The traversal is serial
O(N), and the process environment caps existing WBT helpers at 12 workers.
Exact final measurements and binary identity are in [runtime.csv](runtime.csv),
[environment.json](environment.json), and [validation](validation.md).

[Resolution CSV](resolution_comparison.csv), [scenario CSV](m3_sensitivity.csv),
[plot](resolution_sensitivity.png), command transcript and source hashes are
retained. The reproducible harness is
`/workdir/weppcloud-wbt/tools/staley_m3_resolution_study.py`; generated rasters
remain in the external study directory recorded in validation. The three-site
Western US panel does not establish CONUS-wide validity.
