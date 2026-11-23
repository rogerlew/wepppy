# Es Fangar ESDAC same-unit recovery study

## Authority and method

The operator authorized a bounded same-soil-unit study on 2026-11-20 UTC. Production use requires review of distance, representativeness, and regression evidence. The 1, 2 and 3 km bins below bracket the exploratory search. They are not proposed runtime defaults.

The authoritative polygon lookup uses the European Soil Database v2.0 SGDBE polygon geometry and its SMU, dominant STU, and percentage fields. The official source archive is retained privately on forest as `esdb-v2.zip`, SHA-256 `a4b38aab09c507ea3b46dede5d8c027b0ea3f1320502ffc542bcd24bbb54d918`. The direct download was the European Commission ESDAC archive. [Source and schema](https://esdac.jrc.ec.europa.eu/ESDB_Archive/ESDB_Data_Distribution/ESDB_Data_full_distribution/ESDB_data_vx.cfm)

Using GDAL coordinate transforms, compare each original hillslope with the centers of ESDAC's installed 1 km physical grid cells. A candidate must have the same mapped polygon SMU and dominant STU and valid numeric bulk density, texture, organic carbon and gravel in both materials. Compute distances in ETRS89-LAEA meters. The diagnostic tests donor completeness and polygon membership. It does not identify the STU actually allocated to each property-grid pixel. [JRC soil property layer method](https://esdac.jrc.ec.europa.eu/content/european-soil-database-derived-data)

## Results

All 58 hillslopes intersect SMU `340230`, whose dominant STU `340759` covers **35%** of that SMU. The same mapped unit is eligible for the study. Matching that unit alone says little about where the dominant STU occurs inside it.

The forest baseline writer reproduced 21 generated profiles and 37 rejections. The [six-field raster readback](20261120_esdac_six_field_readback.json) confirmed all six fields were zero in all 37 rejects and none of the 21 accepted cases. Running the same writer with containing-cell sampling for ESDAC categorical and physical rasters generated 22 profiles. Six rejects recovered and five accepted locations regressed. Both methods used the same installed rasters, soil writer and HydroGrids lookup. A blanket pixel-selection switch would change currently working behavior.

For the **31 original rejects still missing required subsoil in their containing cell**, the [scan](20261120_esdac_same_unit_scan.csv) found at least one complete same-unit donor at these distances.

| Cumulative distance from target to donor center | Hillslopes with a donor |
| --- | ---: |
| 1 km | 9 of 31 |
| 2 km | 29 of 31 |
| 3 km | 31 of 31 |

The nearest qualified candidates are 578.2–2,067.9 m away. All 31 select one of two cells, 27 select (2218, 3614), and four select (2216, 3612). A distance and coverage result alone cannot establish representativeness. Check field-level categorical agreement, whether donors preserve native target topsoil and depth, output validity, the 21 existing successes, and sensitivity to donor identity and allowable distance.

## Representativeness controls

The selected two donor cells have byte-equivalent sampled numeric values for the 12 topsoil and subsoil fields. The 11 eligible cells pooled across target neighborhoods contain two distinct complete physical profiles. The nearest-donor topsoil vector matches neither of the two topsoil vectors sampled for the 31 targets under the current runtime policy.

| Profile | Bulk density (g/cm³) | Clay/Sand/Silt (%) | Organic carbon (%) | Gravel (%) |
| --- | ---: | --- | ---: | ---: |
| Selected donor topsoil | 1.39 | 21 / 36 / 43 | 0.65 | 6 |
| Target topsoil, 11 hillslopes | 1.41 | 19 / 37 / 44 | 2.13 | 16 |
| Target topsoil, 20 hillslopes | 1.38 | 24 / 42 / 34 | 1.61 | 21 |
| Selected donor subsoil | 1.38 | 23 / 34 / 43 | 0.43 | 10 |

The complete donor screen provides a source-backed candidate. It does not establish that replacing the full profile is appropriate. The follow-up writer experiment retains the target's topsoil, categorical layer boundaries, CEC and hydraulic lookup and substitutes the six donor subsoil fields together.

All 31 candidate substitutions generated a base soil and parsed successfully with the repository's WEPP soil parser. Across the compared categorical raster fields, the chosen donors agreed with the targets for full FAO label, dominant parent material, surface and subsoil texture classes, depth classes, and top and subsoil CEC. These are coarse indicators shared within the mapped unit. They do not identify an allocated STU for the individual property pixels. The [writer results](20261120_esdac_same_unit_builds.json) record distance, output status, base soil key and categorical differences for each case. The output is a mechanical viability test, with scientific approval and downstream acceptance still open.

## Fallback candidate

The operator directed that an ESDAC-only, editable subsoil profile be available when source-backed recovery cannot be established. The archive from the [prior ESDAC availability study](../../20261106_esdac_missing_data/artifacts/availability-report.md) contains 657 accepted two-material soil outputs with source field comments. Using their displayed subsoil values, compute the median and interquartile range for each of the six source properties. Rank observed six-field profiles by the sum of absolute differences from the medians, scaled by each property's interquartile range. The highest-ranked profile is 25% clay, 41% sand, 34% silt, 1.4 g/cm³ bulk density, 0.4% organic carbon and 6% gravel. Using one observed profile preserves a coherent 100% texture composition. This is a starting profile for review, with no claim of calibration for individual locations.

The six target topsoil fields remain unchanged in the candidate writer experiment. The existing soil writer still derives and validates hydraulic and WEPP parameters. The experimental scripts and generated base files are retained in the private forest study directory beside the incident archives.

The [default-profile writer run](20261120_esdac_candidate_default_builds.json) generated and reparsed 37 of 37 formerly rejected base soils. It exercised the real parameterization and writer with the new subsoil fields injected only for those diagnostic cases. It did not exercise application persistence, automatic fallback admission or a deployed replay.

For the 31 hillslopes with both experimental artifacts, all emitted layer boundaries and the first horizon were identical between the donor and default variants. The maximum absolute parsed differences among later horizons were 0.02 g/cm³ bulk density, 7 percentage points sand, 2 clay, 0.03 organic matter, 4 coarse fragments, 0.368 in the conductivity field, 0.0057 wilting point and 0.0098 field capacity. These compare inputs produced by the two trials. No WEPP response comparison has been run.

## Disturbed format blocker

Actual saved `eu-disturbed` state uses soil format 7778. Using the project's unburned Forest and Agriculture land-use classes, the writer produced files for 27 of the 37 default-profile cases. The other 10 use base soils directly. All 27 rewritten files failed downstream ESDAC validation on missing `luse` and `stext` metadata. The donor-profile experiment exposed the same failure on all 21 rewrites, with 10 retaining base files.

The [format control experiment](20261120_esdac_disturbed_format_controls.json) used both an unchanged accepted ESDAC source soil and soils from the two recovery experiments. The 7778 writer followed by the canonical readback rejected all three for the same metadata reasons. Format 9002 passed for the same three with the same intended class and texture. The 7778 numeric record format does not persist the optional land-use and texture fields consumed by the generic ESDAC metadata gate. Retain the configured format and make the validation and provenance contract format aware. The comparison establishes a separate failure class and does not authorize a switch to 9002.

## Fixed application preset

The operator selected fixed starter values available before any build. The starting profile is 25% clay, 40% sand, 35% silt, 1.4 g/cm³ bulk density, 0.5% organic carbon and 5% gravel. These are generic inputs for a plausible loam. The earlier study-derived profile remains diagnostic comparison evidence.

The [fixed-preset experiment](20261120_esdac_fixed_preset_builds.json) generated and parsed base soils for all 37 original rejects using the real writer and the original target topsoil and other inputs. This confirms mechanical viability of the precise profile. It does not cover the application option, admission, retry or full Disturbed/WEPP replay.
