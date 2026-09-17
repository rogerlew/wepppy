# Thomas Fire verification findings

Audit completed 2026-09-16 UTC. Run: `nervous-mesquite` on forest. Accepted M1
attempt: `a909f2c1b3c0468084d31a8cdd0e24f2`, completed 20:53:29 UTC.

## Verdict

**Numerical implementation verified for this saved run; equivalence to the USGS
assessment is not established.** There are actionable input-comparability and
interpretation shortcomings, but no demonstrated M1 equation, rainfall-unit,
publication-freshness or report-projection defect. This is not a validation of
M3, probability calibration across fires, or operational warning performance.

The nearest spatially matching USGS basin is **19384, San Ysidro Creek**. For
the same 15-minute intensity of 24 mm/hour (6 mm accumulation), WEPPcloud gives
85.6264% and USGS gives 69.3538%: **16.2726 percentage points higher**. This
difference is principally attributable, algebraically, to the soil predictor.
Higher than USGS does not establish overprediction relative to reality.

## What passed

- Recomputed all 8,067 event-duration probabilities (2,689 wet storms), 12 design
  probabilities and three inverse thresholds using independently transcribed
  published coefficients. Maximum probability error: `1.11e-16`; maximum
  accumulation/intensity conversion error: `7.11e-15` mm.
- Every event intensity/date/total agrees with its source climate row. Every
  NOAA design intensity agrees with the saved Atlas 14 mean/PDS table.
- Independently aggregated T, F and S: exact agreement. Independently calculated
  Horn slopes: exact agreement on compared basin cells; no threshold or
  steep-and-burned intersection disagreements.
- Basin: 7.7669 km²; common support: 77,667/77,669 cells. SBS has 97 unknown
  basin cells, but 95 are non-steep and therefore known-false intersections.
  The resulting two-cell exclusion is consistent with the declared policy.
- Source hashes and saved table hashes match. The actual read-only report
  reader validates the accepted attempt, reports `current=true`, and returns
  identical design/inverse values. No browser visual/accessibility audit was
  performed; the report's wording was inspected in its source.
- Original uploaded dNBR is byte-identical to the official BAER archive member:
  SHA-256 `7b6021fe757402376a2a1893786515bb983f2b695b04738986ba9c5264bbf140`.
  Saved normalization uses 0.001, not an additional factor of 1,000 in M1.
  This establishes source identity, not identity to every historical USGS
  preprocessing step. Original SBS lineage was not independently checksum-matched.
- Hashes of 53 monitored scientific/state files were unchanged across the
  read-only audit. No run/job/cache/soil changes or model reruns were performed.

Evidence: [saved checks](saved_run_audit.json), [USGS comparison](usgs_comparison.json),
[source identity](reference_zip_inventory_source_hash.json).

## Matched-basin comparison

| Quantity | WEPPcloud | Historical USGS |
| --- | ---: | ---: |
| Basin area, km² | 7.7669 | 7.6260 |
| T, steep and moderate/high burn fraction | 0.741267 | 0.683425 |
| F, normalized mean dNBR | 0.541045 | 0.542329 |
| S, soil erodibility | 0.337162 | 0.139364 |
| P at I15 = 24 mm/hour | 85.6264% | 69.3538% |
| I15 at P = 50%, mm/hour | 16.0898 | 19.5920* |

*USGS P50 above is independently calculated from the published table's rounded
predictors, not read from its threshold layer. Reference probability is read
directly from its DBF. Recalculation differs by `8.21e-7`, within the `1.335e-6`
probability bound implied by six-decimal predictor rounding. The reference
README has inconsistent rainfall wording and prints 0.67 for the soil coefficient;
the released table and published model agree with 6 mm accumulation and 0.70.
Do not copy those README inconsistencies into model code.

CRS was transformed from WGS84 / UTM11 to NAD83 / UTM11 for comparison.
Intersection/union is **96.10%**; 98.92% of the USGS basin lies inside this run.
Outlets differ by approximately 72.8 m. The run includes most of adjacent small
basin 19381. Selecting the *nearest* outlet alone would match that wrong basin;
maximum polygon overlap identifies 19384 unambiguously. The datum transform
has no site-specific survey accuracy claim.

## Actionable findings

### TF-01 — High: soil-source comparability materially changes the likelihood

**Confirmed input-method difference, not a demonstrated unit bug.** The run's
POLARIS nomograph estimates K using modeled structure/permeability and estimated
very-fine sand; its optional coarse-fragment adjustment was not applied because
inputs were unavailable. USGS stores mean Kf = 0.139364. The historical XML
names **STATSGO** as its soil source; do not describe this particular reference
as confirmed SSURGO. This corrects the initial audit hypothesis.

At 6 mm rainfall the changes in model logit attributable to T/F/S are
`+0.142292 / -0.005160 / +0.830750`. Soil accounts for **85.8% of the net logit
difference** (not 85.8% of probability points or predictive error). Replacing
only the run's S with the reference S yields **72.1888%**. Shared-support run
K remains 0.337298, so the boundary difference does not explain the K discrepancy.

**Smallest next action:** make source/method and comparability visible in the
report, and retain this basin as a source-sensitivity benchmark. Support an
explicit reference-input comparison when available, without rejecting otherwise
valid POLARIS runs or rebuilding WEPP soils. Do not substitute the reference
scalar into normal runs, retune coefficients, or add strict soil gates on this
single example. Whether POLARIS improves or worsens real predictive calibration
requires a multi-basin outcome study.

Code evidence: `report.py:summary` returns predictor values/units but not the
manifest's detailed `k_provenance`; report Methods lists T/F/S without explaining
this source difference. Existing generic preprocessing caveat is helpful but
does not communicate the magnitude found here.

### TF-02 — Medium: calendar labels obscure modeled subdaily rainfall

**Confirmed interpretation gap.** This run uses GridMetPRISM for 1980–2025.
`climate_build_helpers.py:build_observed_gridmet` supplies daily gridMET data to
CLIGEN; `ClimateFile.as_dataframe` derives short-window intensities from the
generated storm shape. Calendar dates alone do not establish observed I15/I30/I60.

The January 9, 2018 source row is 55.4 mm, duration 1.5 hours, peak ratio 1.0;
its modeled intensities are approximately 36.9333 mm/hour for all three windows.
M1 therefore returns 99.1009% for I15. This is consistent arithmetic, **not an
observed-rainfall hindcast validation** of the Montecito disaster. No gauge
hyetograph was ingested or independently validated by this audit.

**Smallest next action:** separate date semantics from rainfall provenance;
label these peaks as modeled/disaggregated, keep that context in exports, and
offer a clearly identified observed-storm comparison in a later scoped change.
Current JS says dates retain accepted climate provenance but does not explain
the subdaily distinction. Existing fixed-postfire/no-recovery text is correct
and should remain. NOAA supplies design rainfall, not these historical event rows.

### TF-03 — Medium: terrain/preprocessing parity remains unresolved

**Confirmed predictor difference; root cause not isolated.** T differs by 0.057842.
On shared spatial support the run's T is 0.757318, still above USGS 0.683425.
Thus merely trimming the extra outlet area would not establish agreement.
Possible contributors include DEM vintage, raster alignment, burn map version
and slope processing. The audit verifies our declared Horn implementation,
not the exact 2018 ArcGIS implementation/input DEM.

**Smallest next action:** preserve the matched basin and source-table fixture;
compare historical DEM/SBS grids and intermediate masks before changing slope
algorithms or thresholds. Do not assume present-day pfdf preprocessing is the
2018 reference. F already differs by only 0.001284, and uploaded dNBR identity
is established, making an extra dNBR scaling correction unjustified.

### TF-04 — Low: default scenarios do not expose a useful reference storm

All saved 15-minute NOAA recurrence scenarios start at 36 mm/hour (one-year
PDS), already 98.89% likelihood. They omit the USGS 24 mm/hour benchmark and
much of the response transition near the 16.09 mm/hour P50 threshold.

**Smallest next action:** consider an explicitly labeled fixed-intensity scenario
comparison or response curve including the chosen reference intensity. Never
relabel a NOAA return period to force a match. This audit evaluated 24 mm/hour
offline and did not alter saved scenarios.

## Scientific limits and acceptance of future remediation

The January 2018 debris flow is a positive occurrence, not repeated trials that
can distinguish 69% from 86% calibration. A genuine predictive validation needs
both occurrence and nonoccurrence basins, compatible observed rainfall, and
held-out calibration/discrimination checks. No false-positive rate, confidence
interval or model-ranking claim is supported by this one-basin audit.

Preserve the report's conditional-likelihood, fixed-postfire-state, coverage-not-
confidence, no-runout/volume/damage, and non-official-assessment caveats. This
basin is within but near the upper end of the stated 0.2–8 km² study range.
Do not interpret these results as a contemporary hazard forecast for a fire
that occurred in 2017 without representing recovery/current conditions.

Future acceptance: (1) keep saved numerical checks passing; (2) show source and
subdaily provenance clearly; (3) reproduce the USGS probability from its inputs
within documented rounding tolerance; (4) preserve explicit run/reference
boundary differences. Source swaps or scientific parameter changes require a
separate authorized implementation and, where applicable, an ADR. No fixes were
implemented under this audit.

## Reproduction, references and retained limitations

Run `wctl run-python` on [audit_saved_run.py](audit_saved_run.py) and
[compare_usgs.py](compare_usgs.py). Both write only package evidence. The
[bounded ZIP reader](read_reference.py) requires no new dependency, checks range
responses, and records URLs/member hashes. Public reference assets total about
7.5 MB; downloaded compressed reference bytes were about 2 MB plus 30 MB for
the hash-only official dNBR check. The full 170/206 MB hazard archives and
127 MB imagery archive were not downloaded. No run input was installed.

Primary references, accessed 2026-09-16:

- [USGS Thomas shapefiles](https://landslides.usgs.gov/static/landslides-realtime/fires/20171204_thomas/Shapefiles.zip):
  basin 19384, `thm2017_Basin_DFPredictions_15min_24mmh`, pour points, XML and
  READMEs retained with hashes in [inventory](reference_zip_inventory.json).
  XML assessment date is January 3, 2018; archive HTTP last-modified is February
  23, 2026. The latter is distribution metadata, not a new fire/model date.
- [USGS model coefficient documentation](https://ghsc.code-pages.usgs.gov/lhp/pfdf/guide/models/s17.html):
  independently transcribed M1 equation/predictor and duration coefficients.
- [Official Thomas BAER archive](https://edcintl.cr.usgs.gov/downloads/sciweb1/shared/MTBS_Fire/data/baer/ca3442911910020171205.zip):
  continuous dNBR source identity; retained hash-only evidence, no duplicate TIFF.
- [Bessette-Kirton and colleagues, 2019](https://repository.mines.edu/bitstream/handle/11124/173211/03-04_Bessette-Kirton.pdf):
  initial San Ysidro 7.6 km²/69% benchmark, superseded for numerical comparison by
  original USGS table and spatial match.
- [USGS user-needs report](https://pubs.usgs.gov/publication/ofr20231025/full):
  context for distinguishing initiation likelihood from downstream consequences.

Initial ScienceBase JSON access encountered a challenge; legacy official USGS
public downloads succeeded. No access control was bypassed. Original SBS
download/checksum and historical DEM were not independently acquired. Exact
historical input reproduction and observed-rainfall validation remain open.

Audit-tool iterations: the first USGS comparison applied an inappropriate
`1e-10` tolerance to six-decimal source predictors; retained
[initial result](usgs_comparison_initial_tolerance_failure.json) and replaced it
with the analytical rounding bound, then passed. An added NOAA check initially
raised `ValueError: '1' is not in list` because the CSV header contains a leading
space; whitespace stripping fixed the audit parser. Neither failure involved
application code or a run write. These are audit-tool corrections, not model defects.
