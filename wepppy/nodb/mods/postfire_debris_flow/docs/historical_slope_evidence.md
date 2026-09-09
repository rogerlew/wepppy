# Historical USGS slope preprocessing and M1 compatibility

Status: verified source inspection, 2026-09-09 UTC. This evidence strengthens
ADR-0058's accepted Horn choice. It does not establish the original 2017
calibration preprocessing or validate a replacement against observed events.

## Findings and confidence

| Finding | Confidence and limit |
| --- | --- |
| Preserved USGS script named for 2022 uses ArcGIS Spatial Analyst slope in degrees, then ≥23° and the moderate/high mask for M1. | Confirmed from pinned Git source. Script was uploaded in February 2023; its filename alone does not prove a 2022 operational deployment. |
| Its unspecified ArcPy method resolves to planar slope, whose complete-neighborhood derivatives match Horn 3×3. | Supported by the call and Esri's documented default/equations; not an executed historical ArcGIS binary comparison. Edge/NoData behavior differs from strict nine-valid-cell Horn. |
| The original 2017 calibration used this same preprocessing. | Plausible continuity inference, not established by the manuscript or this later script. |
| The inspected pfdf slope helper uses pysheds downstream flow slopes. | Confirmed for pinned local revision below; this is a directional gradient rather than Horn surface slope. |
| Migration to pysheds occurred in 2023. | Confirmed by September 2023 Git history and upstream release/tag record; do not project current behavior backward into 2017. |
| The changed slope preprocessing is a regression in calibration compatibility. | Suspected, scientifically material; correctness against original calibration remains unresolved. No signed magnitude or predictive-accuracy claim is established. |

## Reproducible historical evidence

Repository inspected read-only: `/workdir/usgs-pfdf` (local mirror/fork of USGS
pfdf). Original import commit:
`b2a9aa22628c066450a927c4bd1d08a4035c0199`, authored
2023-02-01T16:46:46+00:00, subject “Upload step 2”. Historical path:
`PostFireDFAssessment_M1_Step2_ModelCalcs_ARCPRO_2022-02-08.py`.
Script SHA-256: `f2b37db223556ac98e834dd6f3b968ec744a0bcad19caf46f39f627f3b182af6`.

[Upstream pinned script](https://code.usgs.gov/ghsc/lhp/pfdf/-/blob/b2a9aa22628c066450a927c4bd1d08a4035c0199/PostFireDFAssessment_M1_Step2_ModelCalcs_ARCPRO_2022-02-08.py).
At that revision, line 1307 calls ArcPy Slope in degrees with no method argument;
line 1323 thresholds it inclusively at 23 degrees; line 1369 intersects the
result with the prepared moderate/high mask. Line 1388 calls the TauDEM upstream
sum helper. Routing/accumulation and surface-slope estimation are distinct steps.
No GDAL slope call was found in this inspected M1 path; this does not establish
which tools every historical USGS workflow used.

To reproduce without copying GPL files into WEPPpy, use `git show` in the
reference checkout with the commit/path above and inspect lines 1300–1400.
The surrounding code also invokes a null-replacement helper with zero for the
slope, severity and intersection masks. That call-site evidence must not become
permission to zero-fill missing observations in our accepted support policy.

[Esri Slope parameters](https://pro.arcgis.com/en/pro-app/3.3/tool-reference/spatial-analyst/slope.htm)
identify PLANAR as the default.
[Esri's equations and edge rules](https://pro.arcgis.com/en/pro-app/3.5/tool-reference/spatial-analyst/how-slope-works.htm)
describe weighted 3×3 derivatives. Their complete-neighborhood form is Horn;
missing-neighbor weights and validity thresholds require separate comparison.
These documents support interpretation of the historical call, not proof of
its exact installed version, DEM conditioning or calibration provenance.

## Current helper and migration evidence

Inspected pfdf revision: `2be86e5928cb5d2940f6bfb68193b00722505056`.
`pfdf/watershed.py`, `slopes`, calls pysheds `grid.cell_slopes` at line 254.
`docs/guide/watershed/watershed.rst` describes D8 flow slopes for hazard models.
`pfdf/models/staley2017.py`, M1 terrain helper, thresholds supplied slopes at
23 degrees and computes their intersection with moderate/high burn severity.
The M1 API accepts a slope raster; callers can supply a different estimator.
Therefore scope the finding to this supplied preprocessing path, not all
possible pfdf model use or every operational assessment.

Migration commits include `443310a09a5bf607f7e66f7ae563986f55f395f2`
(2023-09-11, implement pysheds/backend) and
`93c5200af7bc448b3d0788bf7accca37fb5bc8a1`
(2023-09-18, restructure segments and s17 for pysheds).
[USGS tags](https://code.usgs.gov/ghsc/lhp/pfdf/-/tags) and the
[migration merge request](https://code.usgs.gov/ghsc/lhp/pfdf/-/merge_requests/15/commits)
provide upstream history. Package findings also record hashes for the separately
inspected pysheds files and their downstream drop/distance helper.

## Scientific significance and implementation consequences

An empirically fitted coefficient applies to a particular predictor definition
and preprocessing. Keeping the ≥23° cutoff and coefficients while changing
surface slope to routed directional slope can change which cells contribute to
T. The two estimators can differ even with complete, correctly aligned inputs.
This is a potential change in the regression input, not just software choice.

Use Horn for the owned implementation. Treat current pfdf as a versioned
comparison target, not the scientific oracle for M1 T. Agreement with its D8
helper must not be an acceptance condition or justify replacing Horn. Verify
Horn independently on analytical surfaces; compare complete-neighborhood
ArcGIS-style derivatives separately from edge and NoData behavior. GDAL Horn
is useful as an independent numerical comparator, not historical usage evidence.

Quantify threshold-crossing cells, burned/steep area, T and downstream scenario
probability differences on identical DEMs, grids and support. Separate estimator,
DEM conditioning, edge handling and missing-data policy effects. Record this as
method sensitivity, not proof that any method better predicts observed flows.
Our uncertainty-preserving intersection remains an intentional departure from
legacy zero-replacement calls. Full legacy parity is not claimed.

The source mismatch warrants investigation as a suspected preprocessing
regression. Calling current pfdf definitively wrong, estimating its operational
impact, or claiming exact reproduction of 2017 requires further evidence.
No upstream issue, email, or other external communication has been sent.
No GPL code/tests are copied or translated; implementation remains independently
derived from published mathematics and the accepted owned contract.
