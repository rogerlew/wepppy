# Dead Horse Creek M3 audit findings

Audit: 2026-09-17 UTC (2026-09-16 Pacific). Run `thespian-cleanness`, accepted
attempt `0a34c96cd0dc4e6bb7bb7780d8f8915b`, completed 00:39:30 UTC.

## Disposition

**Saved M3 computation and report checks pass. Predictive validation is not
established.** No arithmetic, stale-publication, source-substitution or report
projection defect was found in the inspected paths. The most consequential
limitations are incomplete SBS support, basin size and lack of a uniquely
paired observed storm. No run, model parameter or production code was changed.

[Live report](https://wc.bearhive.duckdns.org/weppcloud/runs/thespian-cleanness/config/report/postfire_debris_flow/)
uses PRISM-based simulated climate, 100 labeled years and project-climate PDS
rainfall frequencies. Its events are not observations of the 2021 debris flow.
The displayed five-year rainfall probability is conditional on that rainfall,
not a five-year debris-flow recurrence estimate.

## Verified calculations

| Quantity | Independently checked result |
| --- | --- |
| Full watershed area | 26.8329 km²; 268,329 cells at 10 m |
| Full watershed relief | 1,428.41650390625 m |
| M3 T, relief / sqrt(area in m²) | 0.2757535126256827 |
| Moderate/high cells / common support, F | 62,673 / 146,161 = 0.42879427480654897 |
| Mean recorded thickness on common support | 142.1349610966043 cm |
| M3 S, mean thickness / 254 | 0.5595864610102531 |
| P50, 15-minute intensity | 30.11676101418647 mm/hour |
| P50, 30-minute intensity | 22.2398083080446 mm/hour |
| P50, 60-minute intensity | 18.989028280111235 mm/hour |

Independent scalar evaluation uses `p = sigmoid(B + R*(Ct*T + Cf*F + Cs*S))`,
where R is accumulation in mm during the selected window. M3 coefficient tuples
(B, Ct, Cf, Cs) are (-3.71, .32, .33, .47), (-3.79, .21, .19, .36), and
(-3.46, .14, .10, .18) for 15/30/60 minutes. This independently evaluates the
published equation; it does not call the production scalar evaluator.
Publication transcription evidence is retained in the
[earlier coefficient audit](../../20260908_staley_watershed_engine/artifacts/coefficient_check.md).

All 32,520 event probabilities, 12 design rows and three inverse rows match to
less than 1e-12 probability error. Rainfall intensities match every original
climate row and the selected PDS ranks exactly. Relief and means were recomputed
from saved raster values; the retained routed basin matches the project domain.
This does not independently delineate a new watershed from a different DEM.

The authenticated browser loaded the actual report, all three duration payloads,
five downloads and a reload successfully. HTTP payloads equal local read-only
projections; all response-curve points pass independent equations. Report text
correctly warns about basin size, incomplete support, simulation labels and
conditional probability. This was a report read audit, not a new RQ submission.

## Comparison with Rengers et al. (2024)

The requested [paper](https://nhess.copernicus.org/articles/24/2093/2024/)
evaluates M1 initiation thresholds and a separate Gartner volume model.
Its 2021 benchmark is the **fire-wide median M1 I15 P50 of 25.9 mm/hour**;
the 2022 benchmark is **M1 P75 of 33.7 mm/hour**. Neither is a published
Dead Horse Creek M3 threshold (sections 3.1 and 4.1).

Section 3.4.3 places Dead Horse Creek deposition approximately **August 5–12,
2021**, without a uniquely identified storm. Figure 5c documents a small
in-channel fan upstream of the Colorado River. The saved outlet
(-107.183875°, 39.592795°) is consistent with that vicinity; exact published
basin polygon parity has not been established.

| Comparison at 15 minutes | Result | Interpretation |
| --- | --- | --- |
| Saved M3 basin P50 versus paper's M1 fire-wide P50 | 30.12 versus 25.9 mm/hour; +4.22 (+16.28%) | Different model and spatial summary; not a residual or validation score |
| Saved M3 probability evaluated at 25.9 mm/hour | 37.30% | Hypothetical rainfall scenario, not an observed Dead Horse storm |
| Saved M3 probability at 33.7 mm/hour | 60.86% | Does not reproduce the paper's M1/year-2 P75 benchmark |

The paper's volume comparisons cannot validate M3 occurrence probabilities.
No exact measured Dead Horse triggering intensity is assigned in this audit.

## Findings and recommendations

### A1 — High validation limitation: missing storm/outcome pairing

The accepted climate has 10,840 simulated wet events, expanded to three duration
rows each. Comparing a simulated event date or design recurrence with an uncertain
2021 event would create unsupported evidence. The official observation release
is [USGS DOI 10.5066/P9Z7RROL](https://doi.org/10.5066/P9Z7RROL).
Its landing page was accessible, but ScienceBase catalog/file requests returned
403; attempts to retrieve the named CSVs from the public object endpoint also
returned 403. No raw measured CSV was acquired and no absence of rows is inferred.

**Next step:** acquire the observation/gauge files, preserve the August 5–12
window, and identify representative north-side gauges and all candidate storms.
If timing remains ambiguous, report a bounded multi-storm hindcast. Do not label
one selected storm a verified triggering event. Several observed basin/storm
outcomes would be needed to assess probability calibration.

### A2 — High applicability limitation: basin larger than study range

26.8329 km² is 3.35 times the 8 km² upper study-area limit already disclosed by
the report. A large downstream catchment integrates potential initiation areas
and deposition reaches; this audit does not establish that a whole-basin
likelihood calibrates to each upstream debris-flow source.

**Next step:** identify a documented initiation/erosion reach and its contributing
basin before selecting a smaller validation unit. Preserve this run as the
whole-basin assessment; do not move the outlet solely to improve agreement.

### A3 — High input-representativeness limitation: 45.53% excluded by SBS

The uploaded `GrizzlyCreek_SBS_final.tif` is byte-identical to the
[official BAER download](https://burnseverity.cr.usgs.gov/baer/baer-imagery-support-data-download/2020/grizzly-creek):
SHA-256 `7d1ed360d8e639050cf3879293efcdbee216bd9a4faac4e03399442416d97405`.
Its native grid is 20 m, NAD83 / UTM 13N. Four recognized categories 1–4 map to
canonical 0–3 without any class or mask disagreement in independent nearest
sampling. The TIFF has no declared NoData tag, but also contains nonclass value
127, which the accepted project excludes.

Of 122,168 excluded basin cells, 97,075 sample native value 127 and 25,093 fall
outside the native raster extent. **All basin cells have usable soil thickness.**
The missing SBS forms a large contiguous upper-basin region, not random sampling.
See [support map](sbs_support.png). Actual categories on included cells are
25,142 unburned, 58,346 low, 47,799 moderate and 14,874 high.

Treating every excluded cell as unburned, solely as a sensitivity, would change
F from 0.42879 to 0.23357 and mean soil thickness from 142.13 to 129.50 cm. With
unchanged terrain, I15 P50 would rise from **30.12 to 36.65 mm/hour**. This
illustrates sensitivity to support; it is not an approved correction or proof
that omitted cells are unburned.

**Next step:** establish the missing area's status from authoritative fire
perimeter/imagery or a validated complete SBS product. Any classification or
support-policy change needs an explicit decision and a new preserved attempt.
Do not silently fill value 127 or areas outside the source raster with zero.

### A4 — Medium provenance limitation: soil coverage is not component completeness

The independent check covers all 19 basin map units and 151 usable components.
Non-R horizon interval unions reproduce their accepted thicknesses exactly;
component-percentage weighting reproduces map-unit means. Primary and fallback
raster differences are below 0.00001 cm (floating-point storage/conversion).
Full-basin source counts are 245,558 SSURGO cells and 22,771 original-STATSGO
THICK fallback cells; included support has 134,889 and 11,272 respectively.

Usable component percentages vary. For example, map unit 496828 uses 45% and
496884 uses 80%; rock/nonsoil and other omitted weights are retained in the
source audit. An available map-unit mean is not a measured depth everywhere in
that pixel. Recorded profile thickness is also not established bedrock depth.

**Next step:** retain these provenance qualifications in any validation dataset.
A separate original-STATSGO-only sensitivity could assess source-policy effects;
no source switch or calibration adjustment was made here.

## Reproduction, preservation and limits

From the repository root:

```bash
wctl exec -T weppcloud python /workdir/wepppy/docs/work-packages/20260916_dead_horse_m3_audit/artifacts/audit_saved.py
wctl exec -T weppcloud python /workdir/wepppy/docs/work-packages/20260916_dead_horse_m3_audit/artifacts/audit_sources.py
node docs/work-packages/20260916_dead_horse_m3_audit/artifacts/browser_audit.cjs
python docs/work-packages/20260916_dead_horse_m3_audit/artifacts/verify_closeout.py
```

Artifacts include [numeric results](numeric_audit.json), [source checks](source_audit.json),
[report/browser evidence](browser/thespian-cleanness/evidence.json),
[final checks](closeout_checks.json) and [initial preservation](preservation.json).
Sixty-nine recorded hashes match. All 181 protected scientific/state files
remain unchanged, including SQLite sidecars, inputs, results and NoDb records.
Ordinary login/access telemetry is outside scientific preservation scope.

The initial standalone HTTP report request returned 404 without authentication;
normal agent login succeeded. An initial audit JSON serialization rejected
nullable parquet NaN values; the retained failure log records that harness issue.
A preliminary diagnostic counted every finite SBS value as classified; recognizing
only classes 1–4 correctly excludes 127 and yields exact mask agreement. Neither
issue required a product change. Raw data download failures are retained.

The reproduced Figure 5 is Rengers et al. (2024), CC BY 4.0, unchanged; source,
license and checksum are in [paper_reference.json](paper_reference.json). The
support map is an audit visualization of saved rasters. Published-polygon
identity, a unique observed triggering intensity, new-run reproducibility and
multi-basin predictive calibration remain unverified. These limits do not
prevent completing this read-only audit.
