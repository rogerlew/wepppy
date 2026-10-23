# Roads parameter validation — current results

Site: **clogging-starch**. **516/516 profile cases completed**: 504 factorial combinations and 12 one-factor controls. All four textures—clay, loam, sand and silt—are included. Three full-upload additive checks and a separately qualified unrutted subset check completed; the full-upload unrutted control was rejected.

## Scope and interpretation

The common site climate contains 5,844 daily records, **2000–2015 (16 years)**; its legacy header advertises 100 years. The pinned `wepp_260409` hillslope executable matches the source project. Roads production builders and native PASS/WAT readers generated these results. This is a numerical and integration validation, not field calibration.

Detachment is native full-profile detachment, averaged over all 16 years including zero-output days. For mixed profiles it includes road, fill, buffer and/or landuse OFEs; it is **not road-prism-only erosion**. Density divides by actual WAT full-profile area. Export is profile sediment leaving the slope, not watershed outlet yield. Different arrangements have different footprints, so their differences do not isolate routing alone.

The seven arrangements are bare/rocked inslope direct (one OFE), bare/rocked road–buffer (two), rutted road–fill–buffer (three), and unrutted landuse–road–fill with/without downstream landuse (three/four). Each crosses three geometries, four soils, two surfaces and three traffic states.

## Geometry and input assumptions

| Geometry | Source segment | Road length (m) | Grade (%) |
| --- | --- | --- | --- |
| short | roads-seg-000033 | 0.0086105 | 0.1 |
| median | roads-seg-000036 | 2.6205 | 29.243 |
| long | roads-seg-000002 | 583.19 | 4.9662 |

The shortest segment is about **8.6 mm**, a numerical/segmentation stress case. The lower median is only 2.62 m; these controls do not represent typical road lengths. Reference width is 4 m; requested rock fragments are 15%; fill/buffer/upstream landuse are each 30 m at 10%. Production mapping makes road rock content 65% for gravel or 95% for paved, fill 40%, and buffer/landuse 15%. The rock_0/rock_40 controls change fill and buffer/landuse rock content; road rock content stays fixed. These are experimental assumptions. Unrutted profiles use the production geometry transformation and bounds; slope-file lengths and widths are rounded to three decimals. WAT area is retained independently. Shared snow, ET and groundwater inputs come from the site; the legacy road plant names use the existing first-record ET coefficient fallback (0.95/0.8). These isolated profiles do not reproduce full-project strip allocation.

## Four-texture comparison

Roads texture keys clay/loam/sand/silt select legacy clay-loam/loam/sandy-loam/silt-loam templates. These matched rows hold median road geometry, gravel and low traffic fixed. Values are annual detachment, full-profile detachment density, deposition and sediment export.

| Texture | Arrangement | Area m² | Detach kg/yr | Detach kg/m²/yr | Deposit kg/yr | Export kg/yr |
| --- | --- | --- | --- | --- | --- | --- |
| clay | bare_direct | 10.48 | 5.1004 | 0.48668 | 0 | 5.1004 |
| clay | rocked_direct | 10.48 | 4.5068 | 0.43004 | 0 | 4.5069 |
| clay | bare_buffer | 130.48 | 10.131 | 0.077647 | -0.049914 | 10.081 |
| clay | rocked_buffer | 130.48 | 9.4479 | 0.072409 | -0.049914 | 9.398 |
| clay | rutted | 250.48 | 12.48 | 0.049825 | -0.015181 | 12.465 |
| clay | unrutted_three | 120.7 | 5.8675 | 0.048612 | 0 | 5.8675 |
| clay | unrutted_four | 175.81 | 15.047 | 0.085586 | -0.015684 | 15.031 |
| loam | bare_direct | 10.48 | 6.9712 | 0.66519 | 0 | 6.9712 |
| loam | rocked_direct | 10.48 | 6.1169 | 0.58367 | 0 | 6.1169 |
| loam | bare_buffer | 130.48 | 11.939 | 0.091498 | -0.14324 | 11.795 |
| loam | rocked_buffer | 130.48 | 11.444 | 0.087709 | -0.13902 | 11.305 |
| loam | rutted | 250.48 | 14.535 | 0.05803 | -0.048506 | 14.487 |
| loam | unrutted_three | 120.7 | 5.3419 | 0.044258 | -0.0083416 | 5.3336 |
| loam | unrutted_four | 175.81 | 12.118 | 0.068927 | -0.070309 | 12.048 |
| sand | bare_direct | 10.48 | 5.9726 | 0.56991 | 0 | 5.9727 |
| sand | rocked_direct | 10.48 | 5.1048 | 0.4871 | 0 | 5.1048 |
| sand | bare_buffer | 130.48 | 6.3942 | 0.049005 | -0.45563 | 5.9386 |
| sand | rocked_buffer | 130.48 | 6.1395 | 0.047053 | -0.45369 | 5.6858 |
| sand | rutted | 250.48 | 9.6099 | 0.038366 | -0.41222 | 9.1977 |
| sand | unrutted_three | 120.7 | 3.6219 | 0.030008 | -0.048068 | 3.5738 |
| sand | unrutted_four | 175.81 | 10.046 | 0.057142 | -0.079101 | 9.9671 |
| silt | bare_direct | 10.48 | 6.3439 | 0.60534 | 0 | 6.3439 |
| silt | rocked_direct | 10.48 | 5.5646 | 0.53098 | 0 | 5.5646 |
| silt | bare_buffer | 130.48 | 13.977 | 0.10712 | -0.10038 | 13.876 |
| silt | rocked_buffer | 130.48 | 13.47 | 0.10323 | -0.10038 | 13.369 |
| silt | rutted | 250.48 | 15.014 | 0.059941 | -0.044238 | 14.97 |
| silt | unrutted_three | 120.7 | 5.937 | 0.049188 | -0.0059975 | 5.931 |
| silt | unrutted_four | 175.81 | 16.209 | 0.092198 | -0.012828 | 16.196 |

## Variability across the complete factorial matrix

Each texture has 126 combinations. Ranges mix geometry, surface, traffic and arrangement; they are not uncertainty intervals.

| Texture | Cases | Min kg/m²/yr | Median kg/m²/yr | Max kg/m²/yr |
| --- | --- | --- | --- | --- |
| clay | 126 | 4.208e-07 | 0.13981 | 64.112 |
| loam | 126 | 1.2211e-07 | 0.093059 | 90.926 |
| sand | 126 | 6.7128e-07 | 0.040909 | 56.42 |
| silt | 126 | 4.9812e-07 | 0.1039 | 92.534 |

## Paired surface and traffic contrasts

Within each pair all other factors remain fixed. Ratios are omitted when the denominator is zero; the suite does not impose a universal monotonic ranking.

| Detachment density ratio | Pairs | Numerator greater | Zero denominator | Min | Median | Max |
| --- | --- | --- | --- | --- | --- | --- |
| paved/gravel | 252 | 90 | 0 | 4.7297e-06 | 0.7014 | 79.86 |
| low/high | 168 | 0 | 0 | 0.25001 | 0.3423 | 1 |
| none/low | 168 | 79 | 0 | 0.00015737 | 0.99266 | 1.1674e+06 |

## One-factor sensitivity controls

Reference: median geometry, rutted, loam, gravel, low traffic. Each control changes one requested input. The doubled grade requests 58.4865%; the production clamp emits 40%. Requested/effective geometry and clipping flags are retained.

| Control | Area m² | Detach kg/yr | Detach kg/m²/yr | Runoff m³/yr | Lateral m³/yr | Baseflow m³/yr |
| --- | --- | --- | --- | --- | --- | --- |
| core | 250.48 | 14.535 | 0.05803 | 111.79 | 0 | 298.66 |
| width_2 | 125.24 | 7.2676 | 0.058029 | 55.894 | 0 | 149.33 |
| width_8 | 500.96 | 29.07 | 0.058029 | 223.58 | 0 | 597.32 |
| grade_half | 250.48 | 10.487 | 0.041869 | 112.17 | 0 | 298.68 |
| grade_double | 250.48 | 16.245 | 0.064856 | 111.79 | 0 | 298.66 |
| fill_length_10 | 170.48 | 12.952 | 0.075973 | 65.17 | 0 | 210.05 |
| fill_length_60 | 370.48 | 20.602 | 0.055608 | 183.37 | 0 | 429.94 |
| fill_grade_2 | 250.48 | 14.072 | 0.056181 | 111.67 | 0 | 298.77 |
| fill_grade_30 | 250.48 | 33.981 | 0.13566 | 112.02 | 0 | 298.5 |
| buffer_length_5 | 150.48 | 16.552 | 0.10999 | 89.913 | 0 | 165.55 |
| buffer_length_60 | 370.48 | 16.479 | 0.04448 | 144.84 | 0 | 455.12 |
| rock_0 | 250.48 | 15.981 | 0.063803 | 140.71 | 0 | 268.4 |
| rock_40 | 250.48 | 10.203 | 0.040735 | 65.516 | 0 | 347.8 |

## Scientific assessment and exceptions

The matrix is internally readable and complete, but the largest detachment rates
should not be interpreted as calibrated road erosion predictions. Across all
cases, full-profile detachment density ranges from about **1.22 × 10⁻⁷ to
92.53 kg/m²/year**. The maximum is the long, silt, paved, high-traffic, bare-ditch
single-OFE case: about 215,859 kg/year over 2,333 m². That corresponds to roughly
925 metric tonnes/ha/year and warrants field/context review before operational
use. Legacy paved templates reduce interrill erodibility and conductivity while
retaining rill erosion parameters; “paved” here does not guarantee negligible
modeled detachment or represent an erosion-proof pavement slab.

Texture-wide median densities are approximately **0.140 clay, 0.0931 loam,
0.0409 sand and 0.104 silt kg/m²/year**. These describe the declared factorial
experiment, not universal soil rankings. The matched four-texture table and
paired contrasts isolate more factors than the pooled range. Large geometry and
arrangement effects remain; the millimeter-scale case is especially sensitive
to file precision and its mixed-profile denominator.

All 516 native profiles produced **zero PASS lateral-flow volume**. That is an
observed result of these legacy road profile inputs, not evidence that whole
watershed lateral flow is zero. The separate project checks preserve nonzero
baseline hillslope contributions. Their surface runoff is checked against the
canonical PASS volume, while lateral flow and other local terms are reconciled
to the area-accounting WAT source; raw diagnostic WAT Q is not substituted for
PASS runoff.

Native deposition is negative in 328 cases and zero in the remainder; its sign
is preserved. There are 187 sediment-export/detachment ratios slightly above
one, with a maximum of approximately **1.000038**. These small differences are
consistent with serialized PASS precision; ratios are not clipped. Every case
has positive mean annual detachment in this experiment, but positive detachment
and monotonic parameter responses are not acceptance requirements.

The full-upload unrutted rejection is a separate integration limitation. A
sampled downstream distance exceeds the representative hillslope lengths for
two crossings, leaving a non-positive upstream OFE. The published positive
unrutted case excludes exactly the identified source feature; it does not certify
that the original entire upload can be represented as unrutted roads.

The largest no-traffic/low-traffic detachment-density ratio is about **1.17 million**
for the short, loam, paved, rutted case. Its denominator is nearly zero:
1.22 × 10⁻⁷ versus 0.143 kg/m²/year (about 0.0000293 versus 34.2 kg/year over
240.04 m²). No traffic selects different vegetation/residue management, rather
than applying another scalar erodibility reduction to low traffic. This ratio
is a model-input response amplified by a near-zero denominator, not evidence
that removing traffic physically multiplies erosion by a million.

## Separate full-project checks

Fresh copies of the site were explicitly assigned each design and run through upload, preparation, execution and current-result publication. Unrutted requires explicit feature fill/buffer inputs: 30 m at 10% each here. Daily area-weighted precipitation, lateral flow, percolation and ET components reconcile to persisted accounting WAT; runoff reconciles to canonical PASS volume. Current receipts and source/baseline hashes were checked. Site eligibility rules still skip segments; nonzero completed profiles and expected additive/replacement targets are required.

**Full-upload unrutted rejection:** all 55 input features were retained. Two records failed the non-positive upstream-OFE guard at Topaz 271/272, and no current result receipt was published. The sampled downstream distance (188.45 m) exceeds the representative hillslope lengths (140.51/69.05 m); this is a limitation of the current profile representation, not proof that the physical road is impossible. The separate positive control excludes exactly source feature OSUNUM6 (54 of 55 inputs), whose identity is pinned. It proves feasible replacement integration, **not whole-site unrutted success or a like-for-like watershed design comparison**. Only one road replacement profile plus one remainder is exercised on one target hillslope; 38 other crossing candidates are excluded by existing eligibility rules. Skipped manifest records in the table do not include those excluded candidates.

| Design | Input features | Prepared | Completed profiles | Skipped records | Modeled area m² | P mm/yr | Runoff mm/yr | Lateral mm/yr | Baseflow mm/yr | ET mm/yr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| inslope_bd | 55 | 39 | 34 | 1 | 4.4182e+05 | 2097.6 | 192 | 1212.4 | 89.012 | 606.24 |
| inslope_rd | 55 | 39 | 34 | 1 | 4.4182e+05 | 2097.6 | 192 | 1212.4 | 89.012 | 606.24 |
| outslope_rutted | 55 | 39 | 34 | 1 | 4.4182e+05 | 2097.6 | 207.83 | 1196.7 | 94.119 | 605.05 |
| outslope_unrutted (subset) | 54 | 38 | 1 | 0 | 4.4181e+05 | 2097.6 | 188.06 | 1210.9 | 94.49 | 606.23 |

Baseline mean annual depths (same 16-year record): Precipitation 2097.6 mm, Runoff 191.69 mm, Lateral Flow 1223.9 mm, Baseflow 75.035 mm, Percolation 62.88 mm, ET 609.21 mm.

## Reproducibility and limitations

The suite discovered and repaired a no-traffic single-OFE management reference failure and a stray character in the paved sandy-loam rocked-ditch soil template. All plant definitions/references are now preserved. Fourteen previously working pilot PASS files were byte-identical after the management repair. Early clone attempts also exposed a stale-path logging side effect; final clones rebase paths before loading controllers. The original scientific outputs and saved state were unchanged.

Generated 2026-10-23T17:15:49.598557+00:00. Matrix definition: 516 unique cases; all complete calendars and finite required native metrics. Exact requested/emitted dimensions, source identities and generated input/output hashes are committed alongside the source report in `tests/roads/matrix_results_current.json` and `tests/roads/analysis_provenance_current.json`. Raw model artifacts remain in the retained validation roots. Repository freshness tests detect source/report drift. There is no claim of field accuracy, production deployment, or repair of existing project results.
