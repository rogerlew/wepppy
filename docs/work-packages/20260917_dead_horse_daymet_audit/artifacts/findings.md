# Dead Horse Creek Daymet M3 audit findings

Audit date: 2026-09-17 UTC. Run: `thespian-cleanness`.
Accepted attempt: `8190121c8a4b45e1952861e74d909693`.

## Verdict

**M3 arithmetic and current report: PASS. Historical event validation: not established. Climate provenance artifact: confirmed units defect.**

The accepted result is current and reproducible from the saved inputs. Switching to Daymet changes rainfall-frequency scenarios but leaves the spatial predictors and equation-derived 50% likelihood intensities unchanged. Both Daymet and the earlier GridMET series contain zero precipitation throughout the paper's August 5–12, 2021 Dead Horse Creek window. This does not demonstrate absence of a real storm.

## Identity and lineage

The owner catalog is `observed_daymet`, using the basin centroid (-107.21618322112406, 39.6392704740886), 1980–2024, 45 represented years, 16,437 daily rows and 4,670 wet days. `ObservedPRISM` is the legacy enum name for mode 9; `climate.py` explicitly identifies that mode as Daymet. It does not establish PRISM rainfall provenance. The CLI header's nominal 100 simulated years is not the actual observed record length; the frequency manifest correctly counts 45 represented years.

The Daymet client fills each leap year's missing final day by copying day 365. Thus the Gregorian 16,437-row record contains twelve filled final-day records. These are not additional independent observed days. This does not affect the non-leap-year August 2021 comparison.

The accepted CLI SHA-256 is `884cb1660dc22d413d77547860fdbd0af2f50459eb8b3558ed3cf442dc3f1f9f`.
[Comparison evidence](comparison.json) retains the exact public Daymet query, downloaded 2021 hash, owner settings and source checks. [Publisher CSV](daymet_publisher_2021.csv) preserves the independent download. All 365 publisher precipitation values, after the documented PRN quantization, match the retained 2021 series exactly. This independently corroborates the point and calendar alignment for the comparison year; it is not an independent re-download of all 45 years.

## Numerical and report checks

[Independent numerical evidence](numeric_audit.json) verifies:

- 14,010 event rows, 12 design rows and three inverse rows against the M3 logistic equations and intensity/depth conversion. Maximum probability error: 1.12e-16; maximum depth error: 3.56e-15 mm.
- Every event backlink against the CLI cache; every design intensity against independently sorted wet-event intensities at the manifest's partial-duration rank. Actual CLI dates and daily precipitation also match the cache for every row.
- Predictor rasters and source/result hashes; published result tables equal the accepted attempt's tables.
- Independently reconstructed T = 0.2757535126, F = 0.4287942748, S = 0.5595864610. Area = 26.8329 km²; usable support = 146,161 / 268,329 cells (54.47%). All 122,168 exclusions are missing SBS; soil thickness exists throughout the basin.

Normal authenticated browser access returned HTTP 200, identified M3 as current at 15, 30 and 60 minutes, and served five attachments whose bytes match the saved artifacts. Reload passed without page errors. See [browser evidence](browser/thespian-cleanness/evidence.json), [screenshot](browser/thespian-cleanness/report.png), and [closeout checks](closeout.json). The audit did not rerun jobs, rebuild climate, restart services, or change project settings.

## Rainfall-frequency comparison

The following probabilities are conditional M3 likelihoods at the listed 15-minute rainfall intensities. Recurrence is rainfall partial-duration-series average recurrence interval, not an annual debris-flow probability. The climate records differ in duration and generation, so this is a comparison of the saved assessments rather than a controlled product-only experiment.

| Rainfall recurrence | GridMET I15 (mm/h) | Daymet I15 (mm/h) | GridMET likelihood | Daymet likelihood |
| --- | ---: | ---: | ---: | ---: |
| 1 year | 23.89 | 24.80 | 31.72% | 34.19% |
| 2 year | 29.67 | 31.62 | 48.61% | 54.63% |
| 5 year | 44.24 | 39.67 | 85.06% | 76.43% |
| 10 year | 49.50 | 54.58 | 91.59% | 95.32% |

All three assessments, including the original synthetic PRISM assessment, retain identical predictors, coverage and inverse rows. P50 intensities remain **30.1168 / 22.2398 / 18.9890 mm/h** for 15 / 30 / 60 minutes. [Full design comparison](design_comparison.csv) includes all durations and the original assessment.

## Comparison with Rengers et al. (2024)

The paper assigns Dead Horse Creek deposition to approximately August 5–12, 2021 from imagery, without identifying a unique triggering storm (section 3.4.3). Its 25.9 mm/h threshold is a fire-wide M1 summary, not this basin's M3 target. The paper also describes internal sediment storage and minor outlet fan development at Dead Horse Creek, with karst and Hanging Lake potentially affecting response (section 5). These distinctions prevent interpreting the current basin likelihood as validation of outlet sediment delivery. [Rengers et al. (2024)](https://nhess.copernicus.org/articles/24/2093/2024/)

For each of the eight dates, the freshly downloaded Daymet daily precipitation, recovered retained precipitation and CLI precipitation are all 0 mm. There are no saved wet-event rows in that interval. See [daily comparison](august_2021_daily.csv) and [event export](august_2021_events.csv). No dates were shifted to manufacture agreement. The previous GridMET audit reached the same zero-rainfall result.

Daymet supplies daily meteorology at 1 km resolution, not measured 15-minute storm intensities. The CLI's subdaily peaks remain CLIGEN-generated. A centroid pixel cannot establish basin-wide absence of localized precipitation. [Daymet description](https://daymet.ornl.gov/overview)

## Confirmed artifact defect and climate-quality limitation

**Units defect:** `build_observed_daymet` initially saves the source DataFrame, passes that same object to `df_to_prn`, and later overwrites the source parquet. `df_to_prn` mutates precipitation into rounded hundredths of inches and temperature into rounded Fahrenheit. The final parquet retains column labels `prcp(mm/day)`, `tmax(degc)` and `tmin(degc)`. Every retained precipitation and temperature entry exactly matches the corresponding PRN field, confirming the incorrect units, not merely a suspected display problem.

Example: January 1, 1980 has stored precipitation 60 under the mm/day label; its actual PRN-equivalent depth is 60 × 0.254 = 15.24 mm, published as 15.2 mm in the CLI. Across all dates, recovered precipitation and CLI differ by at most 0.05 mm. Against fresh publisher 2021 rainfall, the maximum difference is 0.16 mm, consistent with PRN quantization plus CLI rounding. The verified M3 path reads the correctly scaled CLI; this defect corrupts the source artifact's unit contract rather than demonstrating mis-scaled M3 results.

Evidence locations: [df_to_prn](../../../../wepppy/climates/cligen/cligen.py) and [build_observed_daymet](../../../../wepppy/nodb/core/climate_build_helpers.py). Source-code hashes are retained in closeout evidence. Smallest follow-up: preserve the source DataFrame's physical units across PRN serialization, test the generated parquet and CLI together, and explicitly handle previously mislabeled artifacts. Existing artifacts must not be silently treated as true millimeters/Celsius. This audit makes no repair or schema mutation.

**Quality guard:** the owner retains `silent_pass_observed_quality_guard=true`, `adjust_mx_pt5=false`, and a CLIGEN failed-convergence warning. The saved CLIGEN log contains precipitation-random-deviate quality failures. Therefore numerical correctness is not a clean bill of health for the generated storm distribution. The post-fire report's visible text does not surface that upstream warning. A follow-up should preserve the warning's relevance when interpreting generated rainfall scenarios; do not equate report currentness with climate quality.

## Remaining scientific limitations and disposition

The 26.8329 km² basin exceeds the report's 0.2–8 km² published applicability range; 45.53% lacks SBS coverage. Missing SBS is not established unburned area. Unchanged soil and burn-severity inputs mean switching climate cannot resolve those limitations. This audit recalculates raster aggregates and verifies saved source hashes; it does not repeat the original audit's full upstream soil-record investigation.

Disposition: close the requested read-only audit with numerical/browser passes and the above explicit findings. The next implementation work is the source-parquet units defect; the next empirical validation work requires representative subdaily storm measurements and an appropriately defined spatial/temporal comparison. Neither is claimed complete here.
