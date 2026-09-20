# Post-fire debris-flow likelihood: user guide

WEPPcloud's **Post-fire debris flow** module estimates the likelihood of a
debris flow for a specified rainfall intensity and a burned watershed, using
the M1 and M3 equations from [Staley et al. (2017)](https://doi.org/10.1016/j.geomorph.2016.10.019).
It also estimates the rainfall intensity at which the equation reaches 50%
likelihood. It does not estimate debris-flow volume, travel distance or inundation.

**Release status: Preview.** The workflow is available to users, but validation
across fires and operational edge cases is still expanding. Review the documented
limitations and independently verify results before using them for consequential
decisions.

## Choose a model

**M1 is the default and recommended model.** M3 provides an alternative when
continuous dNBR is unavailable. Both require a delineated watershed, soil burn
severity (SBS), and built project climate.

| Input | M1 | M3 |
| --- | --- | --- |
| Terrain | Fraction both at least 23° slope and moderately/highly burned | Basin relief divided by square root of basin area |
| Fire | Mean dNBR, in addition to SBS | Fraction moderately/highly burned from SBS |
| Soil | Fine-earth erodibility, Kf, prepared automatically from NRCS-derived STATSGO | Soil thickness from SSURGO, with original STATSGO thickness as fallback |
| Additional preparation | Upload continuous dNBR | Build project Soils |

Neither model requires enabling RUSLE or POLARIS. A categorical SBS map does
not replace M1's continuous dNBR map. M3 currently requires a 10 m project grid
and the NED13/2022 DEM source. Both use the WBT terrain backend and are available
for continental-US projects; their empirical basis is recently burned Western
US watersheds. The reported study range is approximately 0.2–8 km².

## Run an assessment

1. Delineate the watershed and outlet of interest. Check that the basin represents
   the drainage you intend to assess.
2. Enable **Post-fire debris flow** in the Mods menu. Set the SBS map and build
   project climate. Expand **Precipitation Frequency Estimates** in the Climate
   results and review the short-duration intensities as described below.
3. Select **M1** or **M3** and complete the required project data shown in the control.
4. For M1, upload continuous dNBR, preferably a single-band GeoTIFF. Check the
   accepted filename, scale and coverage. **Auto** estimates the scale; if it
   cannot resolve it, select the appropriate scale and retry the retained map.
   For M3, build project Soils; no dNBR upload is required.
5. Select **Project climate** or available **NOAA** design rainfall and run the
   model. After a completed assessment, the **Summary** card appears between
   Status and Details. Open **View likelihood report** below the summary pane.
6. Review input coverage and rainfall provenance before interpreting the results.
   Download the result tables and response-curve CSV for your records.

Changing the selected model does not relabel an earlier result. The report
shows the latest accepted assessment and identifies the model used. The Summary
card lists its model, completion time, valid coverage and any basin-size warning.
It labels retained stale assessments **Previous run**. Before the first completed
assessment, no report card is shown. Raw model files and the validity mask remain
available through the likelihood report and project file browser. After
changing climate, SBS or other relevant inputs, rerun the assessment to obtain
results for those inputs. Reloading the report alone does not recompute it.

## Read the report

- **Assessment summary** groups the accepted model and completion time, result
  status, input coverage and assessment-specific notices. “None recorded.” means
  the accepted assessment has no additional notice; it does not remove the
  interpretation limits shown below the pane.
- **Likelihood** is conditional on the displayed rainfall and post-fire inputs.
  A value of 70% is not a 70% annual probability of a debris flow.
- **Rainfall window** selects 15, 30 or 60 minutes. Intensity is a rate: 24 mm/h
  sustained for 15 minutes is 6 mm of rainfall. The three windows are separate
  model estimates; do not add or average their probabilities.
- **50% rainfall intensity** is where the model equation reaches 50% likelihood.
  It is not a safe/unsafe boundary or an operational warning threshold.
- **Design rainfall** describes rainfall frequency. A rainfall return period
  is not a debris-flow return period. NOAA scenarios are statistical design
  storms, not observations of a particular event.
- **Event rows** evaluate the project climate's storms against the same fixed
  post-fire landscape. Calendar dates do not mean the landscape's recovery was
  simulated. Synthetic climate year labels are not historical event dates.
- **Storm event filters** accept a minimum likelihood from 0% to 100%, an
  original year label and one of the listed sort orders. Select **Apply filters**
  after changing them; **Reset filters** restores the original event order and
  includes all storms.
- **Valid coverage** measures the area with usable required inputs. Missing
  cells are excluded rather than treated as zero. Coverage is not a confidence
  score; inspect the downloadable mask when coverage is incomplete.

The response curve shows how likelihood changes with rainfall intensity for
the accepted basin inputs. Event filters help locate dates and high-likelihood
storms. Selecting an event displays its estimates for all three rainfall windows.
Display units follow the project's SI/English preference.

## Check Precipitation Frequency Estimates before interpreting likelihood

Rainfall intensity is a critical input to both empirical models. After building
climate, expand **Precipitation Frequency Estimates** in the Climate results.
Repeat this review after changing the climate source, CLIGEN station, record
period or MX .5 adjustment; do not assume a changed setting improves the relevant
storm intensities.

The first table summarizes the generated CLI record. Its columns are rainfall
average recurrence intervals (ARI) in years; its rows include precipitation
depth, storm duration and 10-, 15-, 30- and 60-minute intensity. When available,
the **NOAA Atlas 14 Precipitation Frequency Estimates** table below provides
an independent statistical rainfall reference at the project location.

1. Start with **15-min intensity**, then check **30-min intensity** and
   **60-min intensity**, matching the windows used in the debris-flow report.
   The Climate table's 10-minute row is not a direct M1/M3 input.
2. Compare the CLI and NOAA values at the **same duration and recurrence
   interval**. Check the displayed units: these rows are intensity rates, not
   accumulated depths. For example, compare CLI 15-min intensity at 10 years
   with NOAA 15-min at 10 years, not NOAA 60-min or daily precipitation.
3. Look for large differences and whether they persist across windows and
   recurrence intervals. Lower CLI intensities can produce lower modeled
   likelihoods; higher ones can produce higher likelihoods. Review the climate
   choices and local evidence before treating either difference as an error.
   NOAA is a reference distribution, not a requirement to tune the CLI until
   every value matches.
4. Check record length. The CLI table displays only supported recurrence
   intervals up to the number of represented climate years; an 18-year record
   shows 1, 2, 5 and 10 years, not 25, 50 or 100. Estimates from a short record
   are sensitive to a few large storms. Missing columns are not zero rainfall.
5. Compare these intensities with the debris-flow report's response curve and
   50% rainfall intensity. This shows whether the differences fall in a part of
   the curve where likelihood changes sharply. For design-storm screening,
   compare assessments using Project climate and available NOAA rainfall.
   The rainfall-source choice does not replace historical CLI event rows with
   observed NOAA storms.

Each CLI metric is ranked independently. A column's precipitation depth, storm
duration and intensity values need not come from the same event; do not combine
them into a synthetic storm or divide the displayed depth by the displayed
duration to reconstruct I15. For sparse records, the Climate summary can also
repeat the last available positive value where the post-fire report instead
marks a scenario unavailable. Inspect availability in the debris-flow report
rather than interpreting repeated Climate values as independent evidence.

Agreement in this frequency report checks the overall rainfall distribution,
not the timing or intensity of a particular historical event. A climate can
match NOAA's frequent-storm intensities and still miss the gauge peak on a
debris-flow date. Use observed subdaily rainfall for that event comparison.
The report tables can be retained from **View Climate Files and Log** as
`wepp_cli_pds_mean_metric.csv` and, when present,
`atlas14_intensity_pds_mean_metric.csv`.

## Observed daily climate is not observed storm intensity

**Daymet and GridMET provide daily precipitation totals, not subdaily rainfall
intensity data.** They do not provide the observed storm duration or the timing
and magnitude of its peak. In these WEPPcloud workflows, CLIGEN imputes those
missing storm characteristics using the selected station's monthly storm
statistics, including applicable adjustments:

- **Duration:** the generated storm's length in hours.
- **`tp`:** time to peak intensity, expressed as a fraction of storm duration.
- **`ip`:** peak intensity divided by the storm's average intensity, a
  dimensionless ratio rather than an intensity in mm/h.

CLIGEN generates these values to represent monthly storm statistics; it does
not fit them to an observed hyetograph for each date. The daily precipitation
total and generated duration, `tp` and `ip` define the CLI storm shape from
which the report derives 15-, 30- and 60-minute intensities. Those intensities
are therefore **imputed/model-derived, not Daymet or GridMET observations**.
Changing the CLIGEN station or MX .5 adjustment can change them even when the
daily precipitation input is unchanged. Agreement with monthly statistics does
not establish that a particular historical storm's peak was reproduced.

This distinction matters for individual convective storms: the daily product
can represent a wet sequence while the generated storm misses its measured
short-duration peak. Use a local recording gauge when evaluating correspondence
with a known event, and check its gaps, time convention and location. The gauge
comparison below was performed offline; it does not imply that selecting
Daymet or GridMET imports a gauge hyetograph into the report.

## Validation

These case studies provide complementary evidence: Thomas Fire checks M1
against an existing USGS assessment and verifies the complete reporting path;
Grizzly Creek checks M3's response to measured storm intensity. They support
confidence in the implementation and its rainfall response. They do not by
themselves establish probability calibration across fires.

### M1: Thomas Fire, San Ysidro Creek

The `nervous-mesquite` project represents a 7.7669 km² basin near San Ysidro Creek,
affected by the 2017 Thomas Fire. Its closest spatial match is USGS basin 19384
(7.6260 km²); the basin polygons have 96.10% intersection-over-union.

The September 17, 2026 verification used the current STATSGO fine-earth Kf
source and independently checked the predictors, 8,067 event-duration results,
12 design results, three 50% thresholds and 416 exported response-curve rows.
A stack restart and browser-submitted rerun also verified the report, downloads,
unit changes and persistence after reload.

| Comparison at 15-minute rainfall | WEPPcloud M1 | Historical USGS assessment |
| --- | ---: | ---: |
| Likelihood at 24 mm/h | 72.19% | 69.35% |
| Intensity at 50% likelihood | 19.01 mm/h | 19.59 mm/h |
| Mean fine-earth Kf | 0.139396 | 0.139364 |

The likelihood difference is approximately **2.84 percentage points**. The USGS
50% intensity above was independently calculated from its rounded published
predictors. Basin boundaries and terrain/fire predictors differ, so exact
agreement is not expected.

An earlier WEPPcloud assessment used a different soil-erodibility method and
gave 85.63% at the same rainfall. That is historical evidence of input-source
sensitivity, not the current Kf result. The corrected source brings the
assessment much closer to the USGS benchmark without retuning model coefficients.
This comparison verifies implementation and reference-assessment correspondence;
it is not an observed-gauge reconstruction of the January 2018 disaster.

Evidence: [original spatial and USGS comparison](../../../../docs/work-packages/20260916_thomas_fire_verification/artifacts/findings.md)
and [current Kf rerun and end-to-end acceptance](../../../../docs/work-packages/20260916_thomas_fire_restart_rerun/artifacts/acceptance.md).

### M3: Grizzly Creek Fire, East Fork Deadhorse gauge

The `thespian-cleanness` project represents Dead Horse Creek within the 2020
Grizzly Creek Fire. The USGS East Fork Deadhorse gauge (GCEC2), inside the modeled
basin, recorded strong storms during the July 30–August 2, 2021 sequence.

The table compares measured peak 15-minute intensity (I15) with the saved
Daymet- and GridMET-derived CLIs. Gauge likelihoods use the same M3 equation and
unchanged basin predictors, substituting only the measured rainfall intensity.

| Date | Gauge I15, mm/h | Daymet CLI I15, mm/h | GridMET CLI I15, mm/h | M3 with gauge | M3 with Daymet CLI | M3 with GridMET CLI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| July 31, 2021 | 77.22 | 24.75 | 9.84 | 99.70% | 34.06% | 7.60% |
| August 2, 2021 | 78.23 | 14.14 | 2.14 | 99.73% | 12.26% | 3.09% |

**This is encouraging evidence for M3's response to the observed storms.**
The measured intensities exceed the basin's calculated 50% threshold of
30.12 mm/h by a wide margin. The low saved CLI likelihoods on these dates mainly
reflect underestimated short-duration rainfall peaks. For these storms, the
Daymet/GridMET → CLIGEN → CLI pathway does not reproduce the observed intensity.
This finding does not establish that either daily climate product is generally
unsuitable, or that one is consistently better than the other.

July 31 is the leading working hypothesis for correspondence with the regional
debris-flow episode; August 2 remains a strong local rainfall candidate.
[Rengers et al. (2024)](https://nhess.copernicus.org/articles/24/2093/2024/)
separately place the Dead Horse Creek deposit approximately August 5–12 from
imagery. The dated image pair needed to resolve this discrepancy was not in
the inspected supplement. Thus this is an observed-rainfall response check,
with exact attribution of the mapped deposit still open.

The modeled basin is 26.8329 km², larger than the stated 0.2–8 km² study range,
and its common valid coverage is 54.47%. The gauge measures local rainfall;
uniform rainfall across the entire basin is not established. Those limits
matter when transferring this encouraging result to other watersheds.

The [USGS raw gauge archive](https://www.sciencebase.gov/catalog/item/63617bebd34ebe4425065664)
contains generally five-minute GCEC2 observations for July 13–September 29, 2021
and June 24–October 27, 2022, sufficient to derive 15-minute intensities where
records are complete. There are recording gaps, including on July 30 and
August 2, 2021; July 31 has no timestamp gaps exceeding five minutes.

Evidence: [storm correspondence audit and calculations](../../../../docs/work-packages/20260917_dead_horse_storm_correspondence/artifacts/findings.md),
[gauge coverage checks](../../../../docs/investigations/20260917_dead_horse_gauge_coverage/coverage.json)
and [USGS rainfall and debris-flow data release](https://doi.org/10.5066/P9Z7RROL).

## If results look unexpected

Check the reported model and accepted inputs first, then rainfall origin and
window, input coverage, and whether the assessment is current. For a historical
storm, compare the actual gauge intensity before interpreting a low CLI-based
likelihood as a model failure. Do not treat missing observations as dry weather.

If inputs changed, rebuild the affected project data through the normal controls
and explicitly rerun the assessment. Failed attempts preserve previous accepted
results; a retained report is not proof that the latest attempted run succeeded.
Keep the job ID and downloaded evidence when reporting a problem.

For scientific methods and developer details, see the [module README](README.md)
and [specification](specification.md).
